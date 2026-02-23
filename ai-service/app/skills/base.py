from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from app.skills.schemas import SkillResponse


def resolve_book_label(metadata: dict) -> str:
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
    return sorted({resolve_book_label(doc.metadata or {}) for doc in docs if doc is not None})


def build_sources(docs: List[Document]) -> List[str]:
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
    chunks: List[str] = []
    consumed = 0
    for idx, doc in enumerate(docs[:max_docs], start=1):
        if doc is None:
            continue
        label = resolve_book_label(doc.metadata or {})
        content = (doc.page_content or "").strip()
        item = f"[片段{idx}] 书本标签:{label}\n内容:{content}\n"
        if consumed + len(item) > max_chars:
            break
        chunks.append(item)
        consumed += len(item)
    return "\n".join(chunks).strip()


class SkillBase(ABC):
    name: str = "base"

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def run(self, query: str, retrieved_docs: List[Document]) -> SkillResponse:
        raise NotImplementedError
