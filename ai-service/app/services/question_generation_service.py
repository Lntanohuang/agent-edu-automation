"""
教材驱动的智能出题服务。
"""
from typing import Literal
import re
import time

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import settings
from app.core.exceptions import LLMError, RetrievalError, ValidationError as PlatformValidationError
from app.core.logging import get_logger
from app.core.tracing import traceable
from app.llm.model_factory import skill_llm
from app.llm.output_fixer import try_parse_with_fix
from app.llm.structured_output import (
    build_format_constrained_human_suffix,
    build_format_constrained_system_prompt,
)
from app.llm.vector_store import get_rag_vector_store

logger = get_logger(__name__)
DEFAULT_QUESTION_TYPES = ["单选题", "多选题", "判断题", "填空题", "简答题", "案例分析题"]
OBJECTIVE_TYPES = {"单选题", "多选题", "判断题", "填空题", "single_choice", "multiple_choice", "true_false", "fill_blank"}
SINGLE_CHOICE_TYPES = {"单选题", "single_choice"}
MULTIPLE_CHOICE_TYPES = {"多选题", "multiple_choice"}
TRUE_FALSE_TYPES = {"判断题", "true_false"}
FILL_BLANK_TYPES = {"填空题", "fill_blank"}
AMBIGUOUS_FILL_BLANK_TOKENS = {"言之成理", "合理即可", "可自拟", "略", "不唯一"}


class DifficultyDistribution(BaseModel):
    easy: int = Field(default=20, ge=0, le=100)
    medium: int = Field(default=60, ge=0, le=100)
    hard: int = Field(default=20, ge=0, le=100)

    @model_validator(mode="after")
    def validate_total(self):
        total = self.easy + self.medium + self.hard
        if total <= 0:
            raise ValueError("难度分布总和必须大于 0")
        return self


class QuestionGenerateInput(BaseModel):
    subject: str = Field(default="劳动法", description="学科方向")
    topic: str = Field(default="教材重点章节", description="题目主题")
    textbook_scope: list[str] = Field(default_factory=list, description="教材标签过滤")
    question_count: int = Field(default=10, ge=1, le=50, description="题目数量")
    question_types: list[str] = Field(default_factory=lambda: list(DEFAULT_QUESTION_TYPES), description="题型列表")
    difficulty_distribution: DifficultyDistribution = Field(default_factory=DifficultyDistribution, description="难度分布")
    output_mode: Literal["practice", "paper"] = Field(default="practice", description="生成模式")
    total_score: int = Field(default=100, ge=1, le=300, description="试卷总分")
    include_answer: bool = Field(default=True, description="必须输出答案")
    include_explanation: bool = Field(default=True, description="必须输出解析")
    require_source_citation: bool = Field(default=True, description="必须引用出处")


class SourceCitation(BaseModel):
    book_label: str = Field(default="", description="教材标签")
    source: str = Field(default="", description="来源标识")
    chapter_or_page: str = Field(default="", description="章节或页码")
    chunk_index: int | None = Field(default=None, description="切片索引")
    snippet: str = Field(default="", description="引用原文片段")


class GeneratedQuestion(BaseModel):
    question_id: str = Field(default="", description="题号ID")
    question_type: str = Field(default="", description="题型")
    difficulty: str = Field(default="中等", description="难度")
    stem: str = Field(default="", description="题干")
    options: list[str] = Field(default_factory=list, description="选项")
    answer: str = Field(default="", description="参考答案")
    explanation: str = Field(default="", description="解析")
    knowledge_points: list[str] = Field(default_factory=list, description="知识点")
    source_citations: list[SourceCitation] = Field(default_factory=list, description="出处引用")
    score: float = Field(default=10.0, ge=0, description="题目分值")
    answer_uniqueness: str = Field(default="not_required", description="答案唯一性要求")

    @field_validator("answer", mode="before")
    @classmethod
    def coerce_answer(cls, v):
        """qwen-plus 多选题答案常返回 ['A','B','C'] list，这里合并为逗号字符串。"""
        if isinstance(v, list):
            return ",".join(str(x) for x in v)
        if v is None:
            return ""
        return str(v)

    @field_validator("options", "knowledge_points", mode="before")
    @classmethod
    def coerce_string_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class GeneratedQuestionSet(BaseModel):
    title: str = Field(default="", description="题集标题")
    subject: str = Field(default="劳动法", description="学科")
    output_mode: str = Field(default="practice", description="模式")
    question_count: int = Field(default=0, description="题目数量")
    total_score: float = Field(default=0.0, description="总分")
    questions: list[GeneratedQuestion] = Field(default_factory=list, description="题目列表")

    @model_validator(mode="before")
    @classmethod
    def unwrap_nested(cls, data):
        """qwen-plus 可能将输出包裹在容器对象中（如 {"question_set": {...}}）。"""
        if isinstance(data, dict) and len(data) == 1:
            key = next(iter(data))
            inner = data[key]
            if isinstance(inner, dict) and key not in cls.model_fields:
                return inner
        return data


class QuestionGenerationResult(BaseModel):
    question_set: GeneratedQuestionSet
    book_labels: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)


def _resolve_book_label(metadata: dict) -> str:
    label = str(metadata.get("book_label") or "").strip()
    if label:
        return label
    file_name = str(metadata.get("file_name") or "").strip()
    if file_name:
        return file_name
    source = str(metadata.get("source") or "").strip()
    return source or "未知教材"


def _build_context_text(docs: list[Document], *, max_chars: int = 9000) -> str:
    segments: list[str] = []
    current_len = 0
    for index, doc in enumerate(docs, start=1):
        metadata = dict(doc.metadata or {})
        label = _resolve_book_label(metadata)
        source = str(metadata.get("source") or metadata.get("file_name") or "").strip()
        chapter_or_page = str(metadata.get("page") or metadata.get("chapter") or "").strip()
        chunk_index = metadata.get("chunk_index")
        snippet = (doc.page_content or "").strip().replace("\n", " ")
        if len(snippet) > 320:
            snippet = snippet[:320] + "..."
        block = (
            f"[{index}] BookLabel={label} | Source={source} | ChapterOrPage={chapter_or_page} | "
            f"ChunkIndex={chunk_index}\nContent: {snippet}"
        )
        if current_len + len(block) > max_chars:
            break
        segments.append(block)
        current_len += len(block)
    return "\n\n".join(segments)


def _collect_labels_and_sources(docs: list[Document]) -> tuple[list[str], list[str]]:
    labels = sorted({_resolve_book_label(dict(doc.metadata or {})) for doc in docs})
    sources = sorted(
        {
            str((doc.metadata or {}).get("source") or (doc.metadata or {}).get("file_name") or "").strip()
            for doc in docs
            if str((doc.metadata or {}).get("source") or (doc.metadata or {}).get("file_name") or "").strip()
        }
    )
    return labels, sources


def _normalize_question_type(question_type: str) -> str:
    raw = (question_type or "").strip()
    lowered = raw.lower()
    if raw in OBJECTIVE_TYPES:
        return raw
    mapping = {
        "single": "single_choice",
        "single-choice": "single_choice",
        "single_choice": "single_choice",
        "multiple": "multiple_choice",
        "multiple-choice": "multiple_choice",
        "multiple_choice": "multiple_choice",
        "truefalse": "true_false",
        "true_false": "true_false",
        "true-false": "true_false",
        "fillblank": "fill_blank",
        "fill_blank": "fill_blank",
        "fill-blank": "fill_blank",
    }
    if lowered in mapping:
        return mapping[lowered]
    return raw


def _extract_choice_tokens(answer: str) -> list[str]:
    compact = answer.replace("，", ",").replace("、", ",").replace(" ", "").upper()
    if not compact:
        return []
    if re.fullmatch(r"[A-Z]+", compact):
        return list(compact)
    parts = [part for part in compact.split(",") if part]
    if all(re.fullmatch(r"[A-Z]", token) for token in parts):
        return parts
    return []


def _is_single_choice_answer_deterministic(answer: str, options: list[str]) -> bool:
    text = answer.strip()
    if not text:
        return False
    choice_tokens = _extract_choice_tokens(text)
    if len(choice_tokens) == 1:
        return True
    normalized_options = [str(opt).strip() for opt in options if str(opt).strip()]
    if text in normalized_options:
        return True
    return False


def _is_multiple_choice_answer_deterministic(answer: str, options: list[str]) -> bool:
    text = answer.strip()
    if not text:
        return False
    choice_tokens = _extract_choice_tokens(text)
    if not choice_tokens:
        normalized_options = [str(opt).strip() for opt in options if str(opt).strip()]
        return text in normalized_options
    if len(set(choice_tokens)) != len(choice_tokens):
        return False
    return len(choice_tokens) >= 1


def _is_true_false_answer_deterministic(answer: str) -> bool:
    normalized = answer.strip().lower()
    valid = {"true", "false", "t", "f", "对", "错", "正确", "错误", "yes", "no"}
    return normalized in valid


def _is_fill_blank_answer_deterministic(answer: str) -> bool:
    text = answer.strip()
    if not text:
        return False
    if any(token in text for token in AMBIGUOUS_FILL_BLANK_TOKENS):
        return False
    return True


def _validate_objective_answer(question_type: str, answer: str, options: list[str], index: int) -> None:
    normalized_type = _normalize_question_type(question_type)
    if normalized_type in SINGLE_CHOICE_TYPES:
        if not _is_single_choice_answer_deterministic(answer, options):
            raise ValueError(f"第 {index} 题单选答案不可判定或不唯一")
    elif normalized_type in MULTIPLE_CHOICE_TYPES:
        if not _is_multiple_choice_answer_deterministic(answer, options):
            raise ValueError(f"第 {index} 题多选答案不可判定")
    elif normalized_type in TRUE_FALSE_TYPES:
        if not _is_true_false_answer_deterministic(answer):
            raise ValueError(f"第 {index} 题判断题答案必须为 对/错 或 True/False")
    elif normalized_type in FILL_BLANK_TYPES:
        if not _is_fill_blank_answer_deterministic(answer):
            raise ValueError(f"第 {index} 题填空答案不可判定")


def _normalize_score(question_set: GeneratedQuestionSet, output_mode: str, total_score: int) -> None:
    questions = question_set.questions
    if not questions:
        return
    current_total = sum(max(q.score, 0) for q in questions)
    if output_mode == "paper":
        target_total = float(total_score)
        if current_total <= 0:
            avg = target_total / len(questions)
            for item in questions:
                item.score = round(avg, 2)
        else:
            ratio = target_total / current_total
            for item in questions:
                item.score = round(max(item.score, 0) * ratio, 2)
        question_set.total_score = round(sum(q.score for q in questions), 2)
    else:
        if current_total <= 0:
            for item in questions:
                item.score = 0
        question_set.total_score = round(sum(q.score for q in questions), 2)


def _validate_questions(
    question_set: GeneratedQuestionSet,
    request: QuestionGenerateInput,
    retrieved_docs: list[Document],
) -> list[str]:
    notes: list[str] = []
    fallback_source = ""
    fallback_label = "未知教材"
    fallback_snippet = ""
    fallback_chunk = None
    if retrieved_docs:
        metadata = dict(retrieved_docs[0].metadata or {})
        fallback_source = str(metadata.get("source") or metadata.get("file_name") or "").strip()
        fallback_label = _resolve_book_label(metadata)
        fallback_snippet = ((retrieved_docs[0].page_content or "").strip().replace("\n", " "))[:200]
        fallback_chunk = metadata.get("chunk_index")

    if len(question_set.questions) > request.question_count:
        question_set.questions = question_set.questions[:request.question_count]
        notes.append("模型返回题目数量超过限制，已自动裁剪。")

    for idx, item in enumerate(question_set.questions, start=1):
        if not item.question_id:
            item.question_id = f"Q{idx:03d}"
        if not item.question_type:
            item.question_type = "简答题"
        if not item.stem.strip():
            raise ValueError(f"第 {idx} 题缺少题干")
        if not item.answer.strip():
            raise ValueError(f"第 {idx} 题缺少答案")
        if not item.explanation.strip():
            raise ValueError(f"第 {idx} 题缺少解析")
        normalized_type = _normalize_question_type(item.question_type)
        if normalized_type in OBJECTIVE_TYPES:
            item.question_type = normalized_type
            item.answer_uniqueness = "required_unique_or_deterministic"
            if normalized_type in {"单选题", "多选题", "single_choice", "multiple_choice"} and len(item.options) < 2:
                raise ValueError(f"第 {idx} 题为选择题但选项不足")
            _validate_objective_answer(normalized_type, item.answer, item.options, idx)
        else:
            item.answer_uniqueness = "not_required"

        if not item.source_citations:
            item.source_citations = [
                SourceCitation(
                    book_label=fallback_label,
                    source=fallback_source,
                    chapter_or_page="",
                    chunk_index=fallback_chunk if isinstance(fallback_chunk, int) else None,
                    snippet=fallback_snippet,
                )
            ]
            notes.append(f"第 {idx} 题未返回出处，已补充默认引用。")

    question_set.question_count = len(question_set.questions)
    return notes


@traceable(
    run_type="chain",
    name="Question Generation Pipeline",
    project_name=settings.langsmith_project_name,
)
async def _run_question_generation_pipeline(
    request: QuestionGenerateInput,
    *,
    langsmith_extra: dict | None = None,
    trace_id: str | None = None,
) -> QuestionGenerationResult:
    """
    智能出题主流程：教材检索 -> 结构化生成 -> 校验。
    """
    trace = trace_id or "-"
    started_at = time.time()
    logger.info(
        "question_pipeline_started",
        trace_id=trace,
        subject=request.subject,
        topic=request.topic,
        output_mode=request.output_mode,
        requested_question_count=request.question_count,
        textbook_scope_count=len(request.textbook_scope),
    )

    request.include_answer = True
    request.include_explanation = True
    request.require_source_citation = True

    vector_store = get_rag_vector_store()
    query_text = (
        f"请为{request.subject}生成题目。主题：{request.topic}。"
        f"题型：{', '.join(request.question_types)}。"
        f"题量：{request.question_count}。模式：{request.output_mode}。"
    )

    retrieval_started_at = time.time()
    if request.textbook_scope:
        scope = [label.strip() for label in request.textbook_scope if label and label.strip()]
        unique_scope = list(dict.fromkeys(scope))
        scoped_docs: list[Document] = []
        seen_keys: set[str] = set()
        for label in unique_scope:
            docs = vector_store.similarity_search(
                query_text,
                k=max(8, request.question_count * 2),
                filter={"book_label": label},
            )
            for doc in docs:
                metadata = dict(doc.metadata or {})
                dedup_key = f"{metadata.get('source')}|{metadata.get('chunk_index')}|{doc.page_content[:80]}"
                if dedup_key in seen_keys:
                    continue
                scoped_docs.append(doc)
                seen_keys.add(dedup_key)
        retrieved_docs = scoped_docs
        if not retrieved_docs:
            raise RetrievalError("指定教材范围未检索到有效内容，请确认教材已索引且 book_label 正确。")
    else:
        retrieved_docs = vector_store.similarity_search(query_text, k=max(12, request.question_count * 2))
    logger.info(
        "question_pipeline_retrieval_done",
        trace_id=trace,
        elapsed_ms=round((time.time() - retrieval_started_at) * 1000, 1),
        retrieved_doc_count=len(retrieved_docs),
    )

    if not retrieved_docs:
        raise RetrievalError("知识库中没有可用教材内容，请先上传并索引教材。")

    labels, sources = _collect_labels_and_sources(retrieved_docs)
    context_text = _build_context_text(retrieved_docs)
    logger.info(
        "question_pipeline_context_built",
        trace_id=trace,
        book_label_count=len(labels),
        source_count=len(sources),
        context_chars=len(context_text),
    )

    base_system_prompt = (
        f"你是一名法学课程命题专家。请仅基于给定教材/法规片段出题，不要编造法条或案例出处。\n"
        f"当前学科：{request.subject}\n"
        "必须遵守：\n"
        "1) 每题都要可解。\n"
        "2) 单选/多选/填空/判断题需可判定，答案唯一或标准明确。\n"
        "3) 每题必须给出答案(answer)与解析(explanation)；案例分析题需给出要点式参考答案。\n"
        "4) answer 字段必须是字符串类型，不得为数组；多选题答案写成 'A,B,C' 形式。\n"
        "5) 每题必须给出 source_citations，至少 1 条，且包含书本/法规标签与原文片段。\n"
        "6) 输出字段严格匹配结构化 schema，不要额外字段。\n"
        "7) 结构化输出必须是合法 json（小写 json），不要输出额外文本。"
    )
    base_human_prompt = (
        f"出题需求：\n"
        f"- 学科：{request.subject}\n"
        f"- 主题：{request.topic}\n"
        f"- 模式：{request.output_mode}\n"
        f"- 题量：{request.question_count}\n"
        f"- 题型：{', '.join(request.question_types)}\n"
        f"- 难度分布：简单 {request.difficulty_distribution.easy}%, "
        f"中等 {request.difficulty_distribution.medium}%, 困难 {request.difficulty_distribution.hard}%\n"
        f"- 试卷总分：{request.total_score}\n"
        f"- 教材范围：{', '.join(request.textbook_scope) if request.textbook_scope else '全部已索引教材'}\n\n"
        f"可用教材标签：{', '.join(labels) if labels else '无'}\n\n"
        f"教材片段：\n{context_text}\n\n"
        "请严格输出结构化题目，并确保返回合法 json。"
    )

    # 四层防御：
    # 第1层 手动 json_object 模式 (不用 with_structured_output, 避免其内部重置 bind)
    # 第2层 prompt 严格格式约束 (开头 + 结尾)
    # 第3层 Pydantic validators 自动转 list→str / 容器解包
    # 第4层 try_parse_with_fix: 失败时调用 qwen-turbo 修复
    llm = skill_llm.bind(response_format={"type": "json_object"})
    constrained_system = build_format_constrained_system_prompt(
        base_system_prompt, schema=GeneratedQuestionSet
    )
    human_content = f"{base_human_prompt}\n\n{build_format_constrained_human_suffix()}"

    llm_started_at = time.time()
    try:
        raw_response = await llm.ainvoke([
            SystemMessage(content=constrained_system),
            HumanMessage(content=human_content),
        ])
        question_set = await try_parse_with_fix(
            raw_response.content,
            GeneratedQuestionSet,
            context_label="question_generation",
        )
    except Exception as exc:
        logger.error(
            "question_pipeline_llm_failed",
            trace_id=trace,
            elapsed_ms=round((time.time() - llm_started_at) * 1000, 1),
            error=str(exc),
            exc_info=True,
        )
        raise LLMError(f"出题 LLM 调用失败: {exc}", detail={"trace_id": trace}) from exc
    logger.info(
        "question_pipeline_llm_done",
        trace_id=trace,
        elapsed_ms=round((time.time() - llm_started_at) * 1000, 1),
    )

    if not question_set.title.strip():
        mode_text = "试卷" if request.output_mode == "paper" else "练习题"
        question_set.title = f"{request.subject}-{request.topic}-{mode_text}"
    question_set.subject = request.subject
    question_set.output_mode = request.output_mode

    validate_started_at = time.time()
    try:
        notes = _validate_questions(question_set, request, retrieved_docs)
    except ValueError as exc:
        logger.error(
            "question_pipeline_validation_failed",
            trace_id=trace,
            error=str(exc),
        )
        raise PlatformValidationError(f"题目校验失败: {exc}", detail={"trace_id": trace}) from exc
    logger.info(
        "question_pipeline_validation_done",
        trace_id=trace,
        elapsed_ms=round((time.time() - validate_started_at) * 1000, 1),
        validated_question_count=question_set.question_count,
        validation_note_count=len(notes),
    )

    _normalize_score(question_set, request.output_mode, request.total_score)
    logger.info(
        "question_pipeline_completed",
        trace_id=trace,
        total_elapsed_ms=round((time.time() - started_at) * 1000, 1),
        final_question_count=question_set.question_count,
        final_total_score=question_set.total_score,
        source_count=len(sources),
        book_label_count=len(labels),
    )

    return QuestionGenerationResult(
        question_set=question_set,
        book_labels=labels,
        sources=sources,
        validation_notes=notes,
    )


class QuestionGenerationService:
    """智能出题入口服务。"""

    async def generate(
        self,
        request: QuestionGenerateInput,
        *,
        trace_id: str | None = None,
    ) -> QuestionGenerationResult:
        return await _run_question_generation_pipeline(request, trace_id=trace_id)
