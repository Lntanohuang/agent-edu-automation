"""法律文档领域化切块器。

根据 doc_type 选择不同切块策略：
- statute / interpretation → 按"条"分割，保留章节层级上下文
- case → 按结构段落（事实摘要、争议焦点、裁判要旨等）分割
- contract → 按条款分割
- 其他 → 兜底通用 RecursiveCharacterTextSplitter
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from langchain_core.documents import Document

# ---------------------------------------------------------------------------
# 中文数字 → 阿拉伯数字
# ---------------------------------------------------------------------------

_CN_NUM_MAP = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000,
}


def _cn_to_int(cn: str) -> int:
    """将中文数字字符串转为整数，如 '四十七' → 47。支持阿拉伯数字直接返回。"""
    cn = cn.strip()
    if cn.isdigit():
        return int(cn)
    result = 0
    current = 0
    for ch in cn:
        val = _CN_NUM_MAP.get(ch)
        if val is None:
            continue
        if val >= 10:
            if current == 0:
                current = 1
            result += current * val
            current = 0
        else:
            current = val
    result += current
    return result


# ---------------------------------------------------------------------------
# 正则模式
# ---------------------------------------------------------------------------

_ARTICLE_PATTERN = re.compile(
    r"(第[一二三四五六七八九十百千零\d]+条)"
)
_CHAPTER_PATTERN = re.compile(
    r"第[一二三四五六七八九十百千零\d]+章\s+(.+)"
)
_SECTION_PATTERN = re.compile(
    r"第[一二三四五六七八九十百千零\d]+节\s+(.+)"
)
_ARTICLE_NO_EXTRACT = re.compile(
    r"第([一二三四五六七八九十百千零\d]+)条"
)

# 判例文书常见结构段落标题
_CASE_SECTION_HEADERS = [
    "案件基本信息", "基本信息",
    "当事人", "原告", "被告", "上诉人", "被上诉人",
    "案由",
    "诉讼请求", "原告诉称", "被告辩称",
    "事实摘要", "经审理查明", "审理查明", "本院查明",
    "争议焦点",
    "裁判要旨",
    "裁判理由", "本院认为",
    "裁判结果", "判决如下", "裁定如下",
    "引用法条", "法律依据",
]

_CASE_HEADER_PATTERN = re.compile(
    r"^(?:#+\s*)?(?:" + "|".join(re.escape(h) for h in _CASE_SECTION_HEADERS) + r")[:：]?\s*$",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# 法条类切块（statute / interpretation）
# ---------------------------------------------------------------------------

def split_statute(text: str, metadata: Dict[str, Any]) -> List[Document]:
    """按条分割法规文本。每条一个 chunk，metadata 标注条号和所属章节。"""
    law_name = metadata.get("law_name", "")
    current_chapter = ""
    current_section = ""
    docs: List[Document] = []

    parts = _ARTICLE_PATTERN.split(text)

    # parts[0]: 第一条之前的前言/目录/标题
    preamble = parts[0].strip()
    if preamble and len(preamble) > 30:
        # 从前言中提取章节标题
        for line in preamble.split("\n"):
            line = line.strip()
            ch = _CHAPTER_PATTERN.match(line)
            sec = _SECTION_PATTERN.match(line)
            if ch:
                current_chapter = ch.group(1)
            if sec:
                current_section = sec.group(1)

        docs.append(Document(
            page_content=f"【{law_name}】前言\n\n{preamble}",
            metadata={
                **metadata,
                "chunk_type": "preamble",
                "article_no": "0",
                "chapter": current_chapter,
                "section": current_section,
            },
        ))

    for i in range(1, len(parts), 2):
        article_header = parts[i]  # e.g. "第四十七条"
        article_body = parts[i + 1].strip() if i + 1 < len(parts) else ""

        # 提取条号
        no_match = _ARTICLE_NO_EXTRACT.search(article_header)
        article_no = str(_cn_to_int(no_match.group(1))) if no_match else "?"

        # 在 article_body 中追踪章节变化
        for line in article_body.split("\n"):
            line = line.strip()
            ch = _CHAPTER_PATTERN.match(line)
            sec = _SECTION_PATTERN.match(line)
            if ch:
                current_chapter = ch.group(1)
            if sec:
                current_section = sec.group(1)

        # 构建 chunk 内容：带法律名和章节上下文前缀
        prefix = f"【{law_name}】"
        if current_chapter:
            prefix += f" {current_chapter}"
        if current_section:
            prefix += f" > {current_section}"

        chunk_text = f"{prefix}\n\n{article_header} {article_body}"

        docs.append(Document(
            page_content=chunk_text,
            metadata={
                **metadata,
                "chunk_type": "article",
                "article_no": article_no,
                "chapter": current_chapter,
                "section": current_section,
            },
        ))

    # 如果按条分割失败（没有匹配到条文），走通用兜底
    if len(docs) <= 1 and len(text) > 500:
        return _fallback_split(text, metadata)

    return docs


# ---------------------------------------------------------------------------
# 判例类切块（case）
# ---------------------------------------------------------------------------

def split_case(text: str, metadata: Dict[str, Any]) -> List[Document]:
    """按判例结构段落分割。每段一个 chunk。"""
    case_id = metadata.get("case_id", "")
    case_label = case_id or metadata.get("law_name", "判例")
    docs: List[Document] = []

    # 按标题行分割
    sections = _split_by_headers(text, _CASE_SECTION_HEADERS)

    if not sections:
        # 无法识别结构，整体作为一个 chunk（或走通用分割）
        return _fallback_split(text, metadata)

    for section_name, section_content in sections:
        content = section_content.strip()
        if not content:
            continue
        chunk_text = f"【{case_label}】{section_name}\n\n{content}"
        docs.append(Document(
            page_content=chunk_text,
            metadata={
                **metadata,
                "chunk_type": "case_section",
                "case_section": section_name,
            },
        ))

    return docs


def _split_by_headers(
    text: str, headers: List[str]
) -> List[tuple[str, str]]:
    """按段落标题分割文本，返回 [(标题, 内容), ...]。"""
    # 构建匹配模式：标题行可能有 # 前缀和 : 后缀
    pattern = re.compile(
        r"^(?:#+\s*)?(" + "|".join(re.escape(h) for h in headers) + r")[:：]?\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return []

    sections = []
    # 第一个标题之前的内容
    if matches[0].start() > 0:
        pre_content = text[: matches[0].start()].strip()
        if pre_content:
            sections.append(("概述", pre_content))

    for idx, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append((name, text[start:end].strip()))

    return sections


# ---------------------------------------------------------------------------
# 合同类切块（contract）
# ---------------------------------------------------------------------------

def split_contract(text: str, metadata: Dict[str, Any]) -> List[Document]:
    """按合同条款分割。每个条款一个 chunk。"""
    contract_name = metadata.get("law_name", "") or metadata.get("contract_type", "合同")
    docs: List[Document] = []

    # 合同条款通常是 "第X条 标题\n内容"
    clause_pattern = re.compile(
        r"(第[一二三四五六七八九十\d]+条)\s+(.+?)(?=\n第[一二三四五六七八九十\d]+条\s|\Z)",
        re.DOTALL,
    )
    matches = list(clause_pattern.finditer(text))

    if not matches:
        return _fallback_split(text, metadata)

    # 合同开头（签约双方信息等）
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble and len(preamble) > 20:
            docs.append(Document(
                page_content=f"【{contract_name}】合同信息\n\n{preamble}",
                metadata={**metadata, "chunk_type": "contract_preamble"},
            ))

    for match in matches:
        clause_no = match.group(1)
        clause_body = match.group(2).strip()
        # 第一行通常是条款标题
        first_line = clause_body.split("\n")[0].strip()
        chunk_text = f"【{contract_name}】{clause_no} {clause_body}"

        no_match = _ARTICLE_NO_EXTRACT.search(clause_no)
        article_no = str(_cn_to_int(no_match.group(1))) if no_match else "?"

        docs.append(Document(
            page_content=chunk_text,
            metadata={
                **metadata,
                "chunk_type": "contract_clause",
                "article_no": article_no,
                "clause_title": first_line[:50],
            },
        ))

    return docs


# ---------------------------------------------------------------------------
# 通用兜底
# ---------------------------------------------------------------------------

def _fallback_split(text: str, metadata: Dict[str, Any]) -> List[Document]:
    """通用 RecursiveCharacterTextSplitter 兜底。"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )
    return splitter.create_documents([text], metadatas=[metadata])


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------

def split_legal_document(text: str, metadata: Dict[str, Any]) -> List[Document]:
    """根据 doc_type 选择切块策略。

    Parameters
    ----------
    text : str
        文档正文（不含 frontmatter）。
    metadata : dict
        从 frontmatter 解析出的元数据，必须包含 ``doc_type`` 字段。
    """
    doc_type = metadata.get("doc_type", "")
    if doc_type in ("statute", "interpretation"):
        return split_statute(text, metadata)
    elif doc_type == "case":
        return split_case(text, metadata)
    elif doc_type == "contract":
        return split_contract(text, metadata)
    else:
        return _fallback_split(text, metadata)
