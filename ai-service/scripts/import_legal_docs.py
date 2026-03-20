"""批量导入法律文档到 ChromaDB。

用法:
    conda run -n Langchain-sgg python scripts/import_legal_docs.py data/labor_law/
    conda run -n Langchain-sgg python scripts/import_legal_docs.py data/labor_law/statutes/劳动法.md
"""

from __future__ import annotations

import sys
from hashlib import sha1
from pathlib import Path

# 将项目根目录加入 sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from app.llm.vector_store import get_rag_vector_store  # noqa: E402
from app.rag.frontmatter_parser import parse_frontmatter  # noqa: E402
from app.rag.legal_splitter import split_legal_document  # noqa: E402
from app.rag.rag_service import _store_documents_in_batches  # noqa: E402


def import_file(file_path: Path, vector_store) -> int:
    """导入单个 Markdown 文件，返回 chunk 数量。"""
    text = file_path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(text)

    if not body.strip():
        print(f"  [跳过] {file_path.name}: 正文为空")
        return 0

    # 补充文件信息
    metadata["file_name"] = file_path.name
    metadata["book_label"] = metadata.get("law_name", file_path.stem)
    book_id = f"book_{sha1(metadata['book_label'].encode('utf-8')).hexdigest()[:12]}"
    metadata["book_id"] = book_id

    # ChromaDB 不支持 list 类型 metadata，转为逗号分隔字符串
    for key, val in list(metadata.items()):
        if isinstance(val, list):
            metadata[key] = ", ".join(str(v) for v in val)

    # 按文档类型切块
    docs = split_legal_document(body, metadata)

    # 为每个 chunk 补全 book_id 和 chunk_index；同时扁平化 metadata
    for idx, doc in enumerate(docs):
        for k, v in list(doc.metadata.items()):
            if isinstance(v, list):
                doc.metadata[k] = ", ".join(str(x) for x in v)
        doc.metadata["book_id"] = book_id
        doc.metadata["chunk_index"] = idx

    # 生成稳定 chunk ID（内容哈希，重复导入不会重复写入）
    ids = [
        f"{book_id}_{idx}_{sha1(doc.page_content.encode('utf-8')).hexdigest()[:12]}"
        for idx, doc in enumerate(docs)
    ]

    _store_documents_in_batches(vector_store, docs, ids=ids, batch_size=32)
    print(f"  [OK] {file_path.name}: {len(docs)} chunks (book_id={book_id})")
    return len(docs)


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/import_legal_docs.py <path>")
        print("  <path> 可以是单个 .md 文件或包含 .md 文件的目录")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"路径不存在: {target}")
        sys.exit(1)

    vector_store = get_rag_vector_store()

    # 导入前统计
    try:
        before_count = vector_store._collection.count()
    except Exception:
        before_count = 0

    files: list[Path] = []
    if target.is_file():
        files = [target]
    else:
        files = sorted(target.rglob("*.md"))

    if not files:
        print(f"未找到 .md 文件: {target}")
        sys.exit(1)

    print(f"准备导入 {len(files)} 个文件...\n")

    total_chunks = 0
    for f in files:
        try:
            total_chunks += import_file(f, vector_store)
        except Exception as exc:
            print(f"  [失败] {f.name}: {exc}")

    # 导入后统计
    try:
        after_count = vector_store._collection.count()
    except Exception:
        after_count = 0

    print(f"\n导入完成:")
    print(f"  文件数: {len(files)}")
    print(f"  新增 chunks: {total_chunks}")
    print(f"  ChromaDB 总 chunks: {before_count} → {after_count}")


if __name__ == "__main__":
    main()
