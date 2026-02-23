"""
MongoDB-backed chat message store for RAG conversations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from pymongo import ASCENDING, DESCENDING, MongoClient  # type: ignore
except Exception:
    ASCENDING = 1
    DESCENDING = -1
    MongoClient = None


class MongoChatStore:
    """MongoDB 会话消息存储，连接失败时自动降级。"""

    def __init__(self) -> None:
        """初始化 Mongo 连接、集合和索引。"""
        self.enabled = bool(settings.mongodb_enabled)
        self._collection = None

        if not self.enabled:
            logger.info("Mongo chat store disabled by config")
            return
        if MongoClient is None:
            logger.warning("Mongo chat store unavailable: pymongo is not installed")
            self.enabled = False
            return

        try:
            client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
            db = client[settings.mongodb_database]
            collection = db[settings.mongodb_chat_collection]
            collection.create_index(
                [("conversation_id", ASCENDING), ("created_at", ASCENDING)],
                name="idx_conversation_created_at",
            )
            collection.create_index([("created_at", DESCENDING)], name="idx_created_at")
            # Ping once so init can fail fast if server is unavailable.
            client.admin.command("ping")
            self._collection = collection
            logger.info(
                "Mongo chat store initialized",
                database=settings.mongodb_database,
                collection=settings.mongodb_chat_collection,
            )
        except Exception as exc:
            logger.warning("Mongo chat store init failed, fallback to no-op", error=str(exc))
            self.enabled = False
            self._collection = None

    def list_recent_messages(self, conversation_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        """按会话读取最近消息（时间升序返回）。"""
        if not self.enabled or self._collection is None or not conversation_id:
            return []
        effective_limit = max(1, min(limit or settings.mongodb_history_limit, 200))
        try:
            cursor = (
                self._collection.find({"conversation_id": conversation_id})
                .sort("created_at", DESCENDING)
                .limit(effective_limit)
            )
            docs = list(cursor)
            docs.reverse()
            return docs
        except Exception as exc:
            logger.warning("Mongo list_recent_messages failed", error=str(exc), conversation_id=conversation_id)
            return []

    def append_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """向会话追加一条消息。"""
        if not self.enabled or self._collection is None or not conversation_id or not content:
            return
        doc = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc),
        }
        try:
            self._collection.insert_one(doc)
        except Exception as exc:
            logger.warning("Mongo append_message failed", error=str(exc), conversation_id=conversation_id, role=role)
