"""
Conversation summary memory and history utilities for RAG chat.
"""
import logging
import time
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages

logger = logging.getLogger(__name__)


@dataclass
class ConversationSummaryState:
    """单个会话的摘要状态。"""

    summary: str = ""
    last_summarized_message_count: int = 0
    last_summarized_user_turns: int = 0
    last_seen_message_count: int = 0
    updated_at: float = field(default_factory=time.time)


class ConversationSummaryStore:
    """会话摘要存储：内存缓存 + MongoDB 持久化。

    读取顺序：内存 → MongoDB → 新建空状态。
    写入时同时更新内存和 MongoDB（MongoDB 失败不影响运行）。
    """

    MONGO_COLLECTION = "conversation_summaries"

    def __init__(self, max_conversations: int = 500, mongo_client=None):
        """初始化摘要存储，可选注入 MongoDB 客户端。"""
        self._max_conversations = max_conversations
        self._summaries: dict[str, ConversationSummaryState] = {}
        self._mongo_collection = None
        self._init_mongo(mongo_client)

    def _init_mongo(self, mongo_client=None) -> None:
        """初始化 MongoDB 持久化（可选）。"""
        if mongo_client is not None:
            try:
                from app.core.config import settings
                db = mongo_client[settings.mongodb_database]
                self._mongo_collection = db[self.MONGO_COLLECTION]
                self._mongo_collection.create_index("conversation_id", unique=True)
                logger.info("Summary store MongoDB persistence enabled")
            except Exception as exc:
                logger.warning("Summary store MongoDB init failed, memory-only mode", exc_info=exc)
                self._mongo_collection = None
        else:
            # 尝试自动连接
            try:
                from app.core.config import settings
                if not settings.mongodb_enabled:
                    return
                from pymongo import MongoClient
                client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
                client.admin.command("ping")
                db = client[settings.mongodb_database]
                self._mongo_collection = db[self.MONGO_COLLECTION]
                self._mongo_collection.create_index("conversation_id", unique=True)
                logger.info("Summary store MongoDB persistence enabled (auto-connect)")
            except Exception:
                self._mongo_collection = None

    def get_or_create(self, conversation_id: str) -> ConversationSummaryState:
        """获取会话摘要状态；不存在则从 MongoDB 加载或新建。"""
        state = self._summaries.get(conversation_id)
        if state is not None:
            return state

        # 尝试从 MongoDB 恢复
        state = self._load_from_mongo(conversation_id)
        if state is not None:
            self._summaries[conversation_id] = state
            return state

        if len(self._summaries) >= self._max_conversations:
            oldest_id = min(
                self._summaries.items(),
                key=lambda item: item[1].updated_at,
            )[0]
            self._summaries.pop(oldest_id, None)

        state = ConversationSummaryState()
        self._summaries[conversation_id] = state
        return state

    def reset_if_history_restarted(self, state: ConversationSummaryState, current_history_count: int) -> None:
        """当历史消息数量回退时，判定会话重开并重置摘要。"""
        if current_history_count < state.last_seen_message_count:
            state.summary = ""
            state.last_summarized_message_count = 0
            state.last_summarized_user_turns = 0
        state.last_seen_message_count = current_history_count
        state.updated_at = time.time()

    def persist(self, conversation_id: str, state: ConversationSummaryState) -> None:
        """将摘要状态持久化到 MongoDB（由调用方在摘要更新后调用）。"""
        if self._mongo_collection is None:
            return
        try:
            self._mongo_collection.update_one(
                {"conversation_id": conversation_id},
                {"$set": {
                    "conversation_id": conversation_id,
                    "summary": state.summary,
                    "last_summarized_message_count": state.last_summarized_message_count,
                    "last_summarized_user_turns": state.last_summarized_user_turns,
                    "last_seen_message_count": state.last_seen_message_count,
                    "updated_at": state.updated_at,
                }},
                upsert=True,
            )
        except Exception as exc:
            logger.warning("Summary persist to MongoDB failed", exc_info=exc)

    def _load_from_mongo(self, conversation_id: str) -> ConversationSummaryState | None:
        """从 MongoDB 加载摘要状态。"""
        if self._mongo_collection is None:
            return None
        try:
            doc = self._mongo_collection.find_one({"conversation_id": conversation_id})
            if doc is None:
                return None
            return ConversationSummaryState(
                summary=doc.get("summary", ""),
                last_summarized_message_count=doc.get("last_summarized_message_count", 0),
                last_summarized_user_turns=doc.get("last_summarized_user_turns", 0),
                last_seen_message_count=doc.get("last_seen_message_count", 0),
                updated_at=doc.get("updated_at", time.time()),
            )
        except Exception as exc:
            logger.warning("Summary load from MongoDB failed", exc_info=exc)
            return None


def trim_history_messages(messages: list[BaseMessage], max_tokens: int) -> list[BaseMessage]:
    """按 token 预算裁剪历史消息，优先保留最近上下文。"""
    if not messages:
        return []
    try:
        return trim_messages(
            messages,
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=max_tokens,
            start_on="human",
            end_on=("human", "tool"),
            include_system=True,
        )
    except Exception:
        return messages[-8:]


def history_to_text(messages: list[BaseMessage]) -> str:
    """把消息对象列表转换为统一文本表示。"""
    lines: list[str] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, ToolMessage):
            role = "tool"
        else:
            role = "user"
        content = str(msg.content or "").strip()
        if content:
            lines.append(f"[{role}] {content}")
    return "\n".join(lines).strip()


def message_content_to_text(content: object) -> str:
    """把模型 content（str/list/dict）标准化为纯文本。"""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text).strip())
        return "\n".join(part for part in parts if part).strip()
    return str(content or "").strip()


def count_user_turns(messages: list[BaseMessage]) -> int:
    """统计用户消息轮次。"""
    return sum(1 for message in messages if isinstance(message, HumanMessage))


def should_summarize_stateful(
    *,
    state: ConversationSummaryState,
    user_turn_count: int,
    summarization_interval_turns: int,
) -> bool:
    """有状态模式下，判断是否触发一次增量摘要。"""
    new_user_turns = max(user_turn_count - state.last_summarized_user_turns, 0)
    return summarization_interval_turns > 0 and new_user_turns >= summarization_interval_turns


def should_summarize_stateless(
    *,
    user_turn_count: int,
    summarization_interval_turns: int,
) -> bool:
    """无状态模式下，判断是否触发一次整体摘要。"""
    return summarization_interval_turns > 0 and user_turn_count >= summarization_interval_turns


def compose_history_context(summary: str, recent_history_text: str) -> str:
    """拼接长期摘要和近期对话，供后续检索/生成使用。"""
    parts: list[str] = []
    summary = summary.strip()
    recent_history_text = recent_history_text.strip()
    if summary:
        parts.append(f"会话摘要（长期记忆）:\n{summary}")
    if recent_history_text:
        parts.append(f"最近对话（短期上下文）:\n{recent_history_text}")
    return "\n\n".join(parts).strip()
