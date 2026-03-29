"""法条引用关系图 — 解析法条间的交叉引用，支持检索时自动扩展。

例如：第87条 引用了 第47条 → 检索87条时自动补充47条。
"""

import re
from collections import defaultdict
from typing import Any

# ── 中文数字转换（本地实现，避免循环导入 query_analyzer） ──
_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3,
    "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000,
}


def _cn_to_int(cn: str) -> int | None:
    """中文数字转阿拉伯数字（支持到千位）。"""
    if not cn:
        return None
    if cn.isdigit():
        return int(cn)
    result = 0
    cur = 0
    for ch in cn:
        v = _CN_DIGITS.get(ch)
        if v is None:
            return None
        if v >= 10:
            result += max(cur, 1) * v
            cur = 0
        else:
            cur = cur * 10 + v if cur else v
    total = result + cur
    return total if total > 0 else None


# ── 引用模式 ──
# 匹配 "依照/按照/根据/违反 + 本法/《法律名》 + 第X条"
_REF_PATTERN = re.compile(
    r"(?:依照|按照|依据|根据|违反|符合|适用|参照|参见)?"
    r"\s*"
    r"(?:本法|本条例|本规定|《(.+?)》)"
    r"\s*"
    r"第([一二三四五六七八九十百千零两\d]+)条"
)


class LegalReferenceGraph:
    """法条间交叉引用关系图。

    离线构建：从已切分的法条 chunks 中解析引用关系。
    在线查询：给定一个法条，返回它引用的 + 引用它的所有关联法条。
    """

    def __init__(self) -> None:
        # (law_name, article_no_str) -> [(ref_law, ref_article_str), ...]
        self.references: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        self.cited_by: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        self._built = False

    @property
    def is_built(self) -> bool:
        return self._built

    def build_from_chunks(self, chunks: list[Any]) -> int:
        """从法条 chunks 构建引用图。

        Args:
            chunks: 对象列表，需有 page_content 和 metadata 属性。

        Returns:
            解析到的引用关系数量。
        """
        self.references.clear()
        self.cited_by.clear()
        ref_count = 0

        for chunk in chunks:
            meta = getattr(chunk, "metadata", {})
            content = getattr(chunk, "page_content", "")

            law_name = meta.get("law_name", "")
            article_no = str(meta.get("article_no", ""))
            if not article_no or not law_name:
                continue

            source_key = (law_name, article_no)

            for match in _REF_PATTERN.finditer(content):
                ref_law = match.group(1) or law_name  # "本法" → 当前法律名
                ref_art_cn = match.group(2)
                ref_art = _cn_to_int(ref_art_cn)
                if ref_art is None:
                    continue

                target_key = (ref_law, str(ref_art))
                if target_key == source_key:
                    continue

                if target_key not in self.references[source_key]:
                    self.references[source_key].append(target_key)
                    ref_count += 1
                if source_key not in self.cited_by[target_key]:
                    self.cited_by[target_key].append(source_key)

        self._built = True
        return ref_count

    def get_references(self, law_name: str, article_no: str | int) -> list[tuple[str, str]]:
        """获取某法条引用的其他法条。"""
        return list(self.references.get((law_name, str(article_no)), []))

    def get_cited_by(self, law_name: str, article_no: str | int) -> list[tuple[str, str]]:
        """获取引用了某法条的其他法条。"""
        return list(self.cited_by.get((law_name, str(article_no)), []))

    def expand(self, law_name: str, article_no: str | int, depth: int = 1) -> list[tuple[str, str]]:
        """扩展查找：返回直接引用 + 被引用的所有关联法条。

        Args:
            law_name: 法律名称
            article_no: 条号
            depth: 扩展深度（默认1，只看直接关联）
        """
        key = (law_name, str(article_no))
        result: set[tuple[str, str]] = set()
        visited: set[tuple[str, str]] = {key}
        frontier: set[tuple[str, str]] = {key}

        for _ in range(depth):
            next_frontier: set[tuple[str, str]] = set()
            for node in frontier:
                for ref in self.references.get(node, []):
                    if ref not in visited:
                        result.add(ref)
                        next_frontier.add(ref)
                        visited.add(ref)
                for ref in self.cited_by.get(node, []):
                    if ref not in visited:
                        result.add(ref)
                        next_frontier.add(ref)
                        visited.add(ref)
            frontier = next_frontier
            if not frontier:
                break

        return list(result)

    def stats(self) -> dict[str, int]:
        """返回引用图统计信息。"""
        all_sources = set(self.references.keys())
        all_targets: set[tuple[str, str]] = set()
        total_edges = 0
        for targets in self.references.values():
            total_edges += len(targets)
            all_targets.update(targets)
        return {
            "source_articles": len(all_sources),
            "target_articles": len(all_targets),
            "total_references": total_edges,
            "unique_articles": len(all_sources | all_targets),
        }


# ── 单例 ──
_graph_instance: LegalReferenceGraph | None = None


def get_reference_graph() -> LegalReferenceGraph:
    """获取全局引用图单例。"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = LegalReferenceGraph()
    return _graph_instance


def build_reference_graph_from_vectorstore(vector_store: Any) -> LegalReferenceGraph:
    """从 ChromaDB vector store 构建引用图。在应用启动或文档导入后调用一次。"""
    graph = get_reference_graph()
    try:
        collection = vector_store._collection
        result = collection.get(include=["documents", "metadatas"])

        class _Chunk:
            def __init__(self, content: str, metadata: dict):
                self.page_content = content
                self.metadata = metadata

        chunks = []
        docs = result.get("documents", []) or []
        metas = result.get("metadatas", []) or []
        for doc, meta in zip(docs, metas):
            if doc and meta:
                chunks.append(_Chunk(doc, meta))

        ref_count = graph.build_from_chunks(chunks)
        stats = graph.stats()
        print(
            f"[LegalReferenceGraph] 构建完成: {ref_count} 条引用关系, "
            f"{stats['unique_articles']} 个法条节点"
        )
    except Exception as e:
        print(f"[LegalReferenceGraph] 构建失败: {e}")

    return graph
