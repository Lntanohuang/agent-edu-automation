"""
RAG chat orchestration service.
"""
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tracing import traceable
from app.llm.model_factory import chat_llm
from app.llm.vector_store import get_rag_vector_store
from app.memory.conversation_summary import (
    ConversationSummaryStore,
    compose_history_context,
    count_user_turns,
    history_to_text,
    message_content_to_text,
    should_summarize_stateful,
    should_summarize_stateless,
    trim_history_messages,
)
from app.memory.mongo_chat_store import MongoChatStore
from app.skills import select_skill
from app.skills.source_audit.skill import SourceAuditSkill
from app.skills.teaching_task_generator.skill import TeachingTaskGeneratorSkill

logger = get_logger(__name__)
SUMMARY_EVERY_USER_TURNS = 5
_MAX_RETRY_ON_LOW_CONFIDENCE = 1


@traceable(
    run_type="llm",
    name="RAG History Summarization",
    project_name=settings.langsmith_project_name,
)
async def _summarize_history_with_ai(
    existing_summary: str,
    unsummarized_history_text: str,
    *,
    langsmith_extra: dict | None = None,
) -> str:
    """调用 LLM 做历史摘要压缩，产出后续可复用的长期记忆。"""
    prompt = (
        "你是对话记忆压缩器。请把对话整理成可用于后续问答的摘要。\n"
        "要求：\n"
        "1) 保留事实、约束、偏好、未完成任务、关键术语/书名；\n"
        "2) 删除寒暄和重复；\n"
        "3) 使用中文要点，控制在 8 条以内。\n"
    )
    human_text = (
        f"已有摘要：\n{existing_summary or '(无)'}\n\n"
        f"新增对话：\n{unsummarized_history_text}\n\n"
        "请输出更新后的摘要。"
    )
    response = await chat_llm.ainvoke(
        [SystemMessage(content=prompt), HumanMessage(content=human_text)]
    )
    return message_content_to_text(getattr(response, "content", ""))


@traceable(
    run_type="llm",
    name="RAG Answer Quality Self-Eval",
    project_name=settings.langsmith_project_name,
)
async def _self_evaluate_answer(
    query: str,
    answer: str,
    *,
    langsmith_extra: dict | None = None,
) -> str | None:
    """用 LLM 自评回答质量，如果不完整则返回提示文本，否则返回 None。"""
    try:
        eval_prompt = (
            "你是回答质量评审员。请判断以下回答是否充分回应了用户问题。\n"
            "只输出一行：如果回答充分，输出'PASS'；如果不充分，输出简短原因（不超过30字）。"
        )
        response = await chat_llm.ainvoke([
            SystemMessage(content=eval_prompt),
            HumanMessage(content=f"用户问题：{query}\n\n回答：{answer}"),
        ])
        eval_text = message_content_to_text(getattr(response, "content", "")).strip()
        if eval_text.upper().startswith("PASS"):
            return None
        return eval_text
    except Exception as exc:
        logger.warning("Answer self-evaluation failed", error=str(exc))
        return None


def _append_quality_note(skill_result, note: str):
    """在 skill_result.answer 末尾追加质量提示。"""
    skill_result.answer = f"{skill_result.answer}\n\n【自评提示】{note}"
    return skill_result


@traceable(
    run_type="chain",
    name="RAG Skill Pipeline",
    project_name=settings.langsmith_project_name,
)
async def _run_rag_pipeline(
    query: str,
    history_text: str = "",
    *,
    langsmith_extra: dict | None = None,
    source_audit_skill: SourceAuditSkill,
    teaching_task_skill: TeachingTaskGeneratorSkill,
) -> dict:
    """执行 RAG 主链路：检索 -> 技能生成 -> 审计（低置信度重试一次） -> 质量自评 -> 任务补全。"""
    vector_store = get_rag_vector_store()
    retrieval_query = query
    if history_text:
        retrieval_query = f"{query}\n\n历史上下文（精简）:\n{history_text}"

    retrieved_docs = vector_store.similarity_search(retrieval_query, k=6)
    selected_skill = await select_skill(query)
    skill_query = query if not history_text else f"历史对话（精简）:\n{history_text}\n\n当前问题：{query}"
    skill_result = await selected_skill.run(skill_query, retrieved_docs)

    audited = source_audit_skill.run(
        answer=skill_result.answer,
        sources=skill_result.sources,
        retrieved_docs=retrieved_docs,
    )

    # ── P1: SourceAudit 反馈循环 — 低置信度时扩大检索重试一次 ──
    if audited.confidence == "low":
        logger.info("SourceAudit confidence=low, retrying with expanded retrieval (k=12)")
        retry_docs = vector_store.similarity_search(query, k=12)
        if retry_docs:
            retry_result = await selected_skill.run(skill_query, retry_docs)
            retry_audited = source_audit_skill.run(
                answer=retry_result.answer,
                sources=retry_result.sources,
                retrieved_docs=retry_docs,
            )
            if retry_audited.confidence != "low":
                skill_result = retry_result
                audited = retry_audited
                audited.source_notes.append("经扩大检索重试后置信度提升。")
                retrieved_docs = retry_docs
            else:
                audited.source_notes.append("扩大检索重试后置信度仍为 low。")

    # ── P1: 回答质量自评 ──
    quality_note = await _self_evaluate_answer(query, skill_result.answer, langsmith_extra=langsmith_extra)
    if quality_note:
        skill_result = _append_quality_note(skill_result, quality_note)
        audited.source_notes.append(f"质量自评: {quality_note}")

    generated_tasks = await teaching_task_skill.run(
        query=query,
        answer=skill_result.answer,
        retrieved_docs=retrieved_docs,
        existing_tasks=skill_result.exploration_tasks,
    )

    answer = audited.audited_answer
    if quality_note:
        answer = f"{skill_result.answer}"
        if audited.confidence != "high":
            answer = audited.audited_answer
    if skill_result.book_labels:
        answer = f"{answer}\n\n依据书本标签：{', '.join(skill_result.book_labels)}"

    return {
        "answer": answer,
        "skill_used": skill_result.skill_used,
        "sources": skill_result.sources,
        "exploration_tasks": generated_tasks,
        "book_labels": skill_result.book_labels,
        "confidence": audited.confidence,
        "audit_notes": audited.source_notes,
    }


class RagChatService:
    """RAG 对话编排服务，负责记忆、检索、技能路由和持久化。"""

    def __init__(self):
        self.source_audit_skill = SourceAuditSkill()
        self.teaching_task_skill = TeachingTaskGeneratorSkill()
        self.summary_store = ConversationSummaryStore(max_conversations=500)
        self.mongo_chat_store = MongoChatStore()

    @staticmethod
    def _doc_to_message(doc: dict) -> BaseMessage | None:
        """将 Mongo 文档恢复为 LangChain 消息对象。"""
        role = str(doc.get("role") or "").strip()
        content = str(doc.get("content") or "").strip()
        if not content:
            return None
        if role == "assistant":
            return AIMessage(content=content)
        if role == "tool":
            return ToolMessage(content=content, tool_call_id="mongo-tool-call")
        if role == "system":
            return SystemMessage(content=content)
        return HumanMessage(content=content)

    async def chat(
        self,
        *,
        query: str,
        history_messages: list[BaseMessage],
        conversation_id: str | None,
        max_history_tokens: int,
        langsmith_extra: dict | None = None,
    ) -> dict:
        """单轮对话入口：补历史、做摘要、跑 RAG、并落库结果。"""
        effective_history_messages = list(history_messages)
        if conversation_id and not effective_history_messages:
            # 前端未传历史时，从 Mongo 回填最近消息用于上下文续写。
            persisted_docs = self.mongo_chat_store.list_recent_messages(
                conversation_id,
                limit=settings.mongodb_history_limit,
            )
            restored: list[BaseMessage] = []
            for doc in persisted_docs:
                msg = self._doc_to_message(doc)
                if msg is not None:
                    restored.append(msg)
            effective_history_messages = restored

        # Ensure the current user query is included in this turn context.
        effective_history_messages.append(HumanMessage(content=query))

        trimmed_history = trim_history_messages(effective_history_messages, max_history_tokens)
        recent_history_text = history_to_text(trimmed_history)
        user_turn_count = count_user_turns(effective_history_messages)
        summary_text = ""

        if conversation_id:
            state = self.summary_store.get_or_create(conversation_id)
            self.summary_store.reset_if_history_restarted(state, len(effective_history_messages))

            # 有状态会话：按轮次做增量摘要，降低长上下文成本。
            if should_summarize_stateful(
                state=state,
                user_turn_count=user_turn_count,
                summarization_interval_turns=SUMMARY_EVERY_USER_TURNS,
            ):
                start_idx = min(state.last_summarized_message_count, len(effective_history_messages))
                delta_messages = effective_history_messages[start_idx:]
                delta_text = history_to_text(delta_messages)
                if delta_text:
                    try:
                        new_summary = await _summarize_history_with_ai(
                            existing_summary=state.summary,
                            unsummarized_history_text=delta_text,
                            langsmith_extra=langsmith_extra,
                        )
                        if new_summary:
                            state.summary = new_summary
                            state.last_summarized_message_count = len(effective_history_messages)
                            state.last_summarized_user_turns = user_turn_count
                            self.summary_store.persist(conversation_id, state)
                    except Exception as exc:
                        logger.warning(
                            "RAG history summarization failed",
                            error=str(exc),
                            conversation_id=conversation_id,
                        )

            summary_text = state.summary
            state.updated_at = time.time()
        else:
            # 无状态会话：达到阈值时对本轮完整历史做一次摘要。
            if should_summarize_stateless(
                user_turn_count=user_turn_count,
                summarization_interval_turns=SUMMARY_EVERY_USER_TURNS,
            ):
                full_history_text = history_to_text(effective_history_messages)
                if full_history_text:
                    try:
                        summary_text = await _summarize_history_with_ai(
                            existing_summary="",
                            unsummarized_history_text=full_history_text,
                            langsmith_extra=langsmith_extra,
                        )
                    except Exception as exc:
                        logger.warning("RAG stateless summarization failed", error=str(exc))

        history_context_text = compose_history_context(summary_text, recent_history_text)
        result = await _run_rag_pipeline(
            query=query,
            history_text=history_context_text,
            langsmith_extra=langsmith_extra,
            source_audit_skill=self.source_audit_skill,
            teaching_task_skill=self.teaching_task_skill,
        )

        answer_text = str(result.get("answer") or "").strip()
        if not answer_text:
            raise ValueError("RAG 生成结果为空，请检查检索内容或模型输出。")
        result["answer"] = answer_text

        # Persist this turn into MongoDB when conversation_id is available.
        if conversation_id:
            self.mongo_chat_store.append_message(
                conversation_id=conversation_id,
                role="user",
                content=query,
                metadata={},
            )
            self.mongo_chat_store.append_message(
                conversation_id=conversation_id,
                role="assistant",
                content=result["answer"],
                metadata={
                    "skill_used": result["skill_used"],
                    "sources": result["sources"],
                    "book_labels": result["book_labels"],
                    "confidence": result["confidence"],
                },
            )

        return result
