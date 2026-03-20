"""解析 Markdown 文件开头的 YAML frontmatter，提取结构化元数据。"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import yaml


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """解析 YAML frontmatter，返回 (metadata, body)。

    如果文件不以 ``---`` 开头或 frontmatter 格式不合法，
    返回空 dict 和原始全文。
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    try:
        frontmatter = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return {}, text
    body = text[end + 3:].strip()
    return frontmatter or {}, body
