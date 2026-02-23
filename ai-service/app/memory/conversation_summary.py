"""
Conversation summary memory and history utilities for RAG chat.
"""
import time
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages


@dataclass
class ConversationSummaryState:
    """单个会话的摘要状态。"""

    summary: str = ""
    last_summarized_message_count: int = 0
    last_summarized_user_turns: int = 0
    last_seen_message_count: int = 0
    updated_at: float = field(default_factory=time.time)


class ConversationSummaryStore:
    """会话摘要内存存储（进程内）。"""

    def __init__(self, max_conversations: int = 500):
        """初始化摘要存储，并设置最大会话数。"""
        self._max_conversations = max_conversations
        self._summaries: dict[str, ConversationSummaryState] = {}

    def get_or_create(self, conversation_id: str) -> ConversationSummaryState:
        """获取会话摘要状态；不存在则创建。"""
        state = self._summaries.get(conversation_id)
        if state is not None:
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
        # If the client sends fewer history messages than previous round,
        # treat it as a restarted timeline.
        if current_history_count < state.last_seen_message_count:
            state.summary = ""
            state.last_summarized_message_count = 0
            state.last_summarized_user_turns = 0
        state.last_seen_message_count = current_history_count
        state.updated_at = time.time()


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
