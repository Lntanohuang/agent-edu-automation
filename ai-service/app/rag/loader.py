from pathlib import Path
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)

# 上传文件 → 建立索引 → 持久化
# 查询时 → 只做检索
def load_document(file_path: str):
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    elif suffix == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif suffix == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return loader.load()