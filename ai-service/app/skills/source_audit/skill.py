"""来源审计技能：根据证据完整度修正回答与置信度。"""

from dataclasses import dataclass
from typing import List

from langchain_core.documents import Document


@dataclass
class SourceAuditResult:
    """来源审计结果。"""

    audited_answer: str
    confidence: str
    source_notes: List[str]


class SourceAuditSkill:
    """
    Post-processing skill:
    - check whether answer is backed by retrieved sources
    - append clear source disclaimer when evidence is weak
    """

    name = "source_audit"

    def run(
        self,
        *,
        answer: str,
        sources: List[str],
        retrieved_docs: List[Document],
        rerank_scores: List[float] | None = None,
    ) -> SourceAuditResult:
        """
        校验回答证据，并返回审计后的结果。

        置信度优先由 rerank 分数驱动（如果可用）：
        - avg(top3) > 0.7 → high
        - avg(top3) > 0.4 → medium
        - 否则 → low

        fallback 到旧逻辑（基于 sources/docs 是否存在）。
        """
        source_notes: List[str] = []
        has_sources = bool(sources)
        has_docs = bool(retrieved_docs)

        # ── 优先使用 rerank 分数驱动置信度 ──
        if rerank_scores and len(rerank_scores) > 0:
            avg_score = sum(rerank_scores[:3]) / min(len(rerank_scores), 3)
            if avg_score > 0.7 and has_docs:
                confidence = "high"
                audited_answer = answer
                source_notes.append(f"Rerank 均分 {avg_score:.2f}，已基于检索片段完成来源核对。")
            elif avg_score > 0.4 and has_docs:
                confidence = "medium"
                audited_answer = (
                    f"{answer}\n\n"
                    "【来源提示】检索片段相关度中等，建议结合原始教材核对。"
                )
                source_notes.append(f"Rerank 均分 {avg_score:.2f}，相关度中等。")
            else:
                confidence = "low"
                audited_answer = (
                    f"{answer}\n\n"
                    "【证据不足】检索片段相关度较低，结论仅供参考，请先补充教材或关键词后重试。"
                )
                source_notes.append(f"Rerank 均分 {avg_score:.2f}，相关度不足。")
        # ── fallback: 旧逻辑 ──
        elif has_sources and has_docs:
            confidence = "high"
            audited_answer = answer
            source_notes.append("已基于检索片段完成来源核对。")
        elif has_docs and not has_sources:
            confidence = "medium"
            audited_answer = (
                f"{answer}\n\n"
                "【来源提示】已检索到资料片段，但来源标签不完整，建议补充 book_label 或 file_name 元数据。"
            )
            source_notes.append("检索到片段但来源标签缺失。")
        else:
            confidence = "low"
            audited_answer = (
                f"{answer}\n\n"
                "【证据不足】当前未检索到可核对的资料片段，结论仅供参考，请先补充教材或关键词后重试。"
            )
            source_notes.append("未检索到有效证据。")

        return SourceAuditResult(
            audited_answer=audited_answer,
            confidence=confidence,
            source_notes=source_notes,
        )
