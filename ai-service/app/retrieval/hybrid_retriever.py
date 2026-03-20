"""
多路混合检索器：BM25 + Dense 向量 + 规则召回 + Metadata Filter。

路 1: BM25        — 法条名、术语、案号精确匹配
路 2: Dense 向量   — 语义相似表达
路 3: Metadata filter — 特定 doc_type / 法域
路 4: 规则召回     — "劳动合同法第47条" 直接查 chunk metadata
"""

import hashlib
import time
import threading
from functools import lru_cache
from typing import List, Optional

import jieba
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

from app.core.logging import get_logger
from app.llm.vector_store import get_rag_vector_store
from app.retrieval.query_analyzer import QueryAnalysis
from app.retrieval.reranker import rerank
from app.retrieval.metrics import RetrievalMetrics, log_retrieval_metrics
from app.retrieval.hyde import generate_hypothetical_document_sync

logger = get_logger(__name__)


class HybridRetriever:
    """
    多路混合检索器。

    首次调用时从 ChromaDB 加载全部文档构建 BM25 索引。
    文档更新后调用 invalidate() 重建索引。
    """

    def __init__(self):
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_docs: List[Document] = []
        self._bm25_corpus: List[List[str]] = []
        self._lock = threading.Lock()
        self._index_hash: Optional[str] = None

    def _build_bm25_index(self) -> None:
        """从 ChromaDB 加载全部文档，构建 BM25 索引。"""
        start = time.time()
        vector_store = get_rag_vector_store()

        try:
            collection = vector_store._collection
            result = collection.get(include=["documents", "metadatas"])
        except Exception:
            # fallback: 通过 Chroma 的 get() 方法
            result = vector_store.get(include=["documents", "metadatas"])

        documents_text = result.get("documents", []) or []
        metadatas = result.get("metadatas", []) or []
        ids = result.get("ids", []) or []

        docs: List[Document] = []
        corpus: List[List[str]] = []

        for i, text in enumerate(documents_text):
            if not text:
                continue
            meta = metadatas[i] if i < len(metadatas) else {}
            doc = Document(page_content=text, metadata={**meta, "_chroma_id": ids[i] if i < len(ids) else ""})
            docs.append(doc)
            # jieba 分词用于 BM25
            tokens = list(jieba.cut(text))
            corpus.append(tokens)

        if corpus:
            self._bm25 = BM25Okapi(corpus)
        else:
            self._bm25 = None

        self._bm25_docs = docs
        self._bm25_corpus = corpus
        self._index_hash = hashlib.md5(str(len(docs)).encode()).hexdigest()

        elapsed = (time.time() - start) * 1000
        logger.info(
            "BM25 索引构建完成",
            doc_count=len(docs),
            elapsed_ms=round(elapsed, 1),
        )

    def _ensure_bm25(self) -> None:
        """确保 BM25 索引已构建。"""
        if self._bm25 is None:
            with self._lock:
                if self._bm25 is None:
                    self._build_bm25_index()

    def invalidate(self) -> None:
        """文档更新后重建 BM25 索引。"""
        with self._lock:
            self._bm25 = None
            self._bm25_docs = []
            self._bm25_corpus = []
            self._index_hash = None
        logger.info("BM25 索引已失效，下次检索时重建")

    def _bm25_search(self, query: str, k: int) -> List[Document]:
        """BM25 检索。"""
        self._ensure_bm25()
        if self._bm25 is None or not self._bm25_docs:
            return []

        tokens = list(jieba.cut(query))
        scores = self._bm25.get_scores(tokens)

        # 取 top-k
        scored_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        results = []
        for idx in scored_indices:
            if scores[idx] > 0:
                doc = self._bm25_docs[idx]
                # 在 metadata 中记录 BM25 分数
                doc_copy = Document(
                    page_content=doc.page_content,
                    metadata={**doc.metadata, "_bm25_score": float(scores[idx])},
                )
                results.append(doc_copy)
        return results

    def _dense_search(self, query: str, k: int) -> List[Document]:
        """Dense 向量检索（ChromaDB similarity_search）。"""
        vector_store = get_rag_vector_store()
        return vector_store.similarity_search(query, k=k)

    def _hyde_dense_search(self, hypothesis: str, k: int) -> List[Document]:
        """用 HyDE 假设文档做向量检索。"""
        vector_store = get_rag_vector_store()
        docs = vector_store.similarity_search(hypothesis, k=k)
        # 标记来源为 HyDE
        for doc in docs:
            doc.metadata["_retrieval_source"] = "hyde"
        return docs

    def _metadata_filter_search(self, query: str, analysis: QueryAnalysis, k: int) -> List[Document]:
        """基于 metadata 过滤的检索。"""
        if not analysis.metadata_filters:
            return []

        vector_store = get_rag_vector_store()
        try:
            return vector_store.similarity_search(query, k=k, filter=analysis.metadata_filters)
        except Exception as exc:
            logger.warning("Metadata filter 检索失败", error=str(exc), filters=analysis.metadata_filters)
            return []

    def _rule_recall(self, analysis: QueryAnalysis) -> List[Document]:
        """
        规则召回：根据实体精确匹配 chunk metadata。

        例如 "劳动合同法第47条" → 查找 metadata 中包含 article_no=47 的 chunks。
        """
        entities = analysis.entities
        if not entities.get("law_name") and not entities.get("article_no"):
            return []

        self._ensure_bm25()
        results = []
        law_name = entities.get("law_name", "")
        article_no = entities.get("article_no", "")

        for doc in self._bm25_docs:
            content = doc.page_content or ""
            meta = doc.metadata or {}

            # 精确匹配：metadata 或内容中包含法律名和条号
            name_match = law_name and (
                law_name in str(meta.get("law_name", ""))
                or law_name in str(meta.get("filename", ""))
                or law_name in content[:200]
            )
            article_match = article_no and (
                str(meta.get("article_no", "")) == article_no
                or f"第{article_no}条" in content
                or f"第 {article_no} 条" in content
            )

            if name_match and article_match:
                results.append(doc)
            elif article_match and not law_name:
                results.append(doc)
            elif name_match and not article_no:
                # 仅匹配法律名但无条号，降低优先级，只取前几条
                if len(results) < 3:
                    results.append(doc)

        return results

    def _dedup_docs(self, all_docs: List[Document]) -> List[Document]:
        """基于内容 hash 去重。"""
        seen = set()
        unique = []
        for doc in all_docs:
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(doc)
        return unique

    def _rrf_fusion(self, doc_lists: list[list[Document]], weights: list[float], k_rrf: int = 60) -> list[Document]:
        """
        RRF 融合多路召回结果。

        RRF_score(d) = Σ weight_i / (k + rank_i(d))
        k=60 是业界常用值。
        """
        scores: dict[str, float] = {}  # content_hash -> score
        doc_map: dict[str, Document] = {}  # content_hash -> Document

        for doc_list, weight in zip(doc_lists, weights):
            for rank, doc in enumerate(doc_list):
                content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
                if content_hash not in doc_map:
                    doc_map[content_hash] = doc
                scores[content_hash] = scores.get(content_hash, 0.0) + weight / (k_rrf + rank + 1)

        sorted_hashes = sorted(scores, key=scores.get, reverse=True)
        return [doc_map[h] for h in sorted_hashes]

    def retrieve(
        self,
        query: str,
        analysis: QueryAnalysis,
        k: int = 6,
    ) -> List[Document]:
        """
        多路混合检索主入口。

        1. 并行执行 BM25 / Dense / Metadata / Rule 四路召回
        2. RRF 风格融合（按 bm25_boost 调权）
        3. 去重
        4. Rerank 重排序
        5. 记录检索指标

        Args:
            query: 用户查询
            analysis: QueryAnalysis 分析结果
            k: 最终返回文档数

        Returns:
            排序后的 Document 列表
        """
        metrics = RetrievalMetrics(query=query, intent=analysis.intent)
        latency: dict = {}

        # ── 路 1: BM25 ──
        t0 = time.time()
        bm25_weight = 0.4 + analysis.bm25_boost
        bm25_k = max(k, int(k * bm25_weight * 2))
        bm25_docs = self._bm25_search(query, k=bm25_k)
        latency["bm25_ms"] = round((time.time() - t0) * 1000, 1)
        metrics.bm25_doc_count = len(bm25_docs)

        # ── 路 2: Dense 向量 ──
        t0 = time.time()
        dense_k = max(k, int(k * (1 - bm25_weight) * 2 + 2))
        dense_docs = self._dense_search(query, k=dense_k)
        latency["dense_ms"] = round((time.time() - t0) * 1000, 1)
        metrics.vector_doc_count = len(dense_docs)

        # ── 路 2b: HyDE Dense（仅 concept_explain / general 意图） ──
        if analysis.intent in ("concept_explain", "general"):
            try:
                hypothesis = generate_hypothetical_document_sync(query)
                if hypothesis:
                    t0 = time.time()
                    hyde_docs = self._hyde_dense_search(hypothesis, k=dense_k)
                    latency["hyde_ms"] = round((time.time() - t0) * 1000, 1)
                    # 把 HyDE 结果追加到 dense_docs
                    dense_docs = dense_docs + hyde_docs
                    metrics.vector_doc_count = len(dense_docs)
            except Exception as exc:
                logger.warning("HyDE 检索失败，跳过 error=%s", str(exc))

        # ── 路 3: Metadata filter ──
        t0 = time.time()
        meta_docs = self._metadata_filter_search(query, analysis, k=k)
        latency["metadata_ms"] = round((time.time() - t0) * 1000, 1)

        # ── 路 4: 规则召回 ──
        t0 = time.time()
        rule_docs = self._rule_recall(analysis)
        latency["rule_ms"] = round((time.time() - t0) * 1000, 1)
        metrics.rule_doc_count = len(rule_docs)

        # ── RRF 真融合：规则召回优先 > BM25(动态权重) > Metadata > Dense ──
        weights = [2.0, 1.0 + analysis.bm25_boost, 0.8, 0.6]
        unique_docs = self._rrf_fusion(
            [rule_docs, bm25_docs, meta_docs, dense_docs],
            weights,
        )
        metrics.merged_doc_count = len(unique_docs)
        metrics.fusion_method = "rrf"
        metrics.rrf_weights = weights

        # ── Rerank ──
        t0 = time.time()
        reranked = rerank(query, unique_docs, top_k=k)
        latency["rerank_ms"] = round((time.time() - t0) * 1000, 1)

        final_docs = [doc for doc, _ in reranked]
        metrics.rerank_top3_scores = [round(s, 4) for _, s in reranked[:3]]
        metrics.latency_ms = latency

        # ── 异步记录指标（不阻塞主流程） ──
        try:
            log_retrieval_metrics(metrics)
        except Exception:
            pass

        logger.info(
            "混合检索完成",
            intent=analysis.intent,
            bm25=len(bm25_docs),
            dense=len(dense_docs),
            meta=len(meta_docs),
            rule=len(rule_docs),
            merged=len(unique_docs),
            final=len(final_docs),
        )

        return final_docs


# ── 单例 ──
_hybrid_retriever: Optional[HybridRetriever] = None
_retriever_lock = threading.Lock()


def get_hybrid_retriever() -> HybridRetriever:
    """获取 HybridRetriever 单例。"""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        with _retriever_lock:
            if _hybrid_retriever is None:
                _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever
