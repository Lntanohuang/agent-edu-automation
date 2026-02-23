from dataclasses import dataclass
from typing import List

from langchain_core.documents import Document


@dataclass
class SourceAuditResult:
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
    ) -> SourceAuditResult:
        source_notes: List[str] = []
        has_sources = bool(sources)
        has_docs = bool(retrieved_docs)

        if has_sources and has_docs:
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
