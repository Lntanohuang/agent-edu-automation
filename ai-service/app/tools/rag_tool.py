from pathlib import Path

from langchain_core.tools import tool

from app.llm.vector_store import get_rag_vector_store


def _resolve_book_label(metadata: dict) -> str:
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


# 检索工具
@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Retrieve information to help answer a query."""
    vector_store = get_rag_vector_store()
    retrieved_docs = vector_store.similarity_search(query, k=2)
    labels = sorted(
        {
            _resolve_book_label(doc.metadata or {})
            for doc in retrieved_docs
            if _resolve_book_label(doc.metadata or {})
        }
    )
    serialized = "\n\n".join(
        (
            "BookLabel: "
            f"{_resolve_book_label(doc.metadata or {})}\n"
            f"Source: {doc.metadata}\n"
            f"Content: {doc.page_content}"
        )
        for doc in retrieved_docs
    )
    if labels:
        serialized = f"RetrievedBookLabels: {', '.join(labels)}\n\n{serialized}"
    return serialized, retrieved_docs
