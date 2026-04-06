"""Skills 通用工具方法与声明式技能 Runner。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_traced_logger
from app.core.exceptions import SkillError
from app.llm.model_factory import chat_llm
from app.skills.schemas import SkillResponse

if TYPE_CHECKING:
    from app.skills.skill_config import SkillConfig


# ── 工具函数（保持不变） ─────────────────────────────────────


def resolve_book_label(metadata: dict) -> str:
    """从 metadata 中解析书本标签。"""
    label = str(metadata.get("book_label") or "").strip()
    if label:
        return label
    file_name = str(metadata.get("file_name") or "").strip()
    if file_name:
        return Path(file_name).stem or file_name
    source = str(metadata.get("source") or "").strip()
    if source:
        return Path(source).stem or source
    return "未知资料"


def collect_book_labels(docs: List[Document]) -> List[str]:
    """收集检索文档的去重书本标签。"""
    return sorted({resolve_book_label(doc.metadata or {}) for doc in docs if doc is not None})


def build_sources(docs: List[Document]) -> List[str]:
    """生成可读来源列表（包含章/节/页）。"""
    sources: List[str] = []
    for doc in docs:
        if doc is None:
            continue
        metadata = doc.metadata or {}
        label = resolve_book_label(metadata)
        page = metadata.get("page")
        chapter = metadata.get("chapter")
        section = metadata.get("section")
        suffix_parts = []
        if chapter:
            suffix_parts.append(f"章:{chapter}")
        if section:
            suffix_parts.append(f"节:{section}")
        if page is not None:
            suffix_parts.append(f"页:{page}")
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        sources.append(f"{label}{suffix}")
    # Keep order and deduplicate.
    deduped = list(dict.fromkeys(sources))
    return deduped


def build_context_text(docs: List[Document], *, max_docs: int = 4, max_chars: int = 4200) -> str:
    """将检索文档压缩为可放入提示词的上下文文本。"""
    chunks: List[str] = []
    consumed = 0
    for idx, doc in enumerate(docs[:max_docs], start=1):
        if doc is None:
            continue
        meta = doc.metadata or {}
        label = resolve_book_label(meta)
        content = (doc.page_content or "").strip()
        chapter = meta.get("chapter", "")
        section = meta.get("section", "")
        page = meta.get("page", "")
        loc_parts = [f"章:{chapter}" if chapter else "", f"节:{section}" if section else "", f"页:{page}" if page else ""]
        loc = " ".join(p for p in loc_parts if p)
        item = f"参考文档{idx}（来自：{label}{' ' + loc if loc else ''}）：\n{content}\n"
        if consumed + len(item) > max_chars:
            break
        chunks.append(item)
        consumed += len(item)
    return "\n".join(chunks).strip()


# ── 通用 Skill Runner ───────────────────────────────────────


class Skill:
    """由 SkillConfig 驱动的通用技能执行器。

    所有主技能共用此实现，不再需要各自定义 class。
    """

    def __init__(self, config: SkillConfig) -> None:
        self.config = config
        self.name = config.name

    async def run(self, query: str, retrieved_docs: List[Document]) -> SkillResponse:
        """执行技能：构建上下文 → LLM 结构化输出 → 格式化 → 返回 SkillResponse。"""
        logger = get_traced_logger("skill").bind(skill=self.name)
        logger.info("skill_started", query_len=len(query), doc_count=len(retrieved_docs))
        t0 = time.perf_counter()
        try:
            context_text = build_context_text(retrieved_docs)

            llm = chat_llm.with_structured_output(
                self.config.output_schema, method="json_schema",
            )
            output = await llm.ainvoke([
                SystemMessage(content=self.config.system_prompt),
                HumanMessage(content=f"检索上下文：\n{context_text}\n\n用户问题：{query}\n\n请只基于以上检索上下文回答，未涵盖的内容请如实说明。输出结构化结果。"),
            ])

            parsed = (
                output
                if isinstance(output, self.config.output_schema)
                else self.config.output_schema.model_validate(output)
            )

            answer = self.config.format_answer(parsed)

            tasks = getattr(parsed, "exploration_tasks", [])
            tasks = tasks[:3] if tasks else self.config.default_tasks

            confidence = (
                self.config.confidence_with_docs if retrieved_docs
                else self.config.confidence_without_docs
            )

            result = SkillResponse(
                skill_used=self.name,
                answer=answer,
                sources=build_sources(retrieved_docs),
                book_labels=collect_book_labels(retrieved_docs),
                exploration_tasks=tasks,
                confidence=confidence,
                structured_data=parsed.model_dump(),
            )
            elapsed = round(time.perf_counter() - t0, 3)
            logger.info("skill_completed", elapsed_s=elapsed, answer_len=len(answer))
            return result
        except Exception as exc:
            elapsed = round(time.perf_counter() - t0, 3)
            logger.error("skill_failed", elapsed_s=elapsed, error=str(exc), exc_info=True)
            raise SkillError(
                f"Skill [{self.name}] 执行失败: {exc}",
                detail={"skill": self.name, "elapsed_s": elapsed},
            ) from exc
