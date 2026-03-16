"""
结构化检索日志：每次检索写入 MongoDB retrieval_logs collection。
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalMetrics:
    """检索指标数据。"""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query: str = ""
    intent: str = "general"
    bm25_doc_count: int = 0
    vector_doc_count: int = 0
    rule_doc_count: int = 0
    merged_doc_count: int = 0
    rerank_top3_scores: List[float] = field(default_factory=list)
    final_confidence: str = ""
    latency_ms: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))


def log_retrieval_metrics(metrics: RetrievalMetrics) -> None:
    """
    将检索指标写入 MongoDB ai_service.retrieval_logs。

    MongoDB 连接失败时仅 log warning，不抛异常。
    """
    try:
        from pymongo import MongoClient

        client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
        db = client[settings.mongodb_database]
        collection = db["retrieval_logs"]
        collection.insert_one({
            "trace_id": metrics.trace_id,
            "query": metrics.query,
            "intent": metrics.intent,
            "bm25_doc_count": metrics.bm25_doc_count,
            "vector_doc_count": metrics.vector_doc_count,
            "rule_doc_count": metrics.rule_doc_count,
            "merged_doc_count": metrics.merged_doc_count,
            "rerank_top3_scores": metrics.rerank_top3_scores,
            "final_confidence": metrics.final_confidence,
            "latency_ms": metrics.latency_ms,
            "timestamp": metrics.timestamp,
        })
        logger.debug("检索指标已写入 MongoDB", trace_id=metrics.trace_id)
    except Exception as exc:
        logger.warning("检索指标写入 MongoDB 失败", error=str(exc), trace_id=metrics.trace_id)
