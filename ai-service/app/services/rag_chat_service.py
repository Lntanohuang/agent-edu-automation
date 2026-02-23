"""
RAG chat orchestration service.
"""
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tracing import traceable
from app.llm.model_factory import ollama_qwen_llm
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
    response = await ollama_qwen_llm.ainvoke(
        [SystemMessage(content=prompt), HumanMessage(content=human_text)]
    )
    return message_content_to_text(getattr(response, "content", ""))


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
    vector_store = get_rag_vector_store()
    retrieval_query = query
    if history_text:
        retrieval_query = f"{query}\n\n历史上下文（精简）:\n{history_text}"

    retrieved_docs = vector_store.similarity_search(retrieval_query, k=6)
    selected_skill = select_skill(query)
    skill_query = query if not history_text else f"历史对话（精简）:\n{history_text}\n\n当前问题：{query}"
    skill_result = await selected_skill.run(skill_query, retrieved_docs)

    generated_tasks = await teaching_task_skill.run(
        query=query,
        answer=skill_result.answer,
        retrieved_docs=retrieved_docs,
        existing_tasks=skill_result.exploration_tasks,
    )
    audited = source_audit_skill.run(
        answer=skill_result.answer,
        sources=skill_result.sources,
        retrieved_docs=retrieved_docs,
    )

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
    def __init__(self):
        self.source_audit_skill = SourceAuditSkill()
        self.teaching_task_skill = TeachingTaskGeneratorSkill()
        self.summary_store = ConversationSummaryStore(max_conversations=500)
        self.mongo_chat_store = MongoChatStore()

    @staticmethod
    def _doc_to_message(doc: dict) -> BaseMessage | None:
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
        effective_history_messages = list(history_messages)
        if conversation_id and not effective_history_messages:
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
                    except Exception as exc:
                        logger.warning(
                            "RAG history summarization failed",
                            error=str(exc),
                            conversation_id=conversation_id,
                        )

            summary_text = state.summary
            state.updated_at = time.time()
        else:
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
