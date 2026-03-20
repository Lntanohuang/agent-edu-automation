"""
Tests for app.memory.conversation_summary — pure functions + ConversationSummaryStore.
"""
import time

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.memory.conversation_summary import (
    ConversationSummaryState,
    ConversationSummaryStore,
    compose_history_context,
    count_user_turns,
    history_to_text,
    message_content_to_text,
    should_summarize_stateful,
    should_summarize_stateless,
)


# ── history_to_text ──


class TestHistoryToText:

    def test_basic_conversation(self):
        msgs = [HumanMessage(content="你好"), AIMessage(content="你好！")]
        text = history_to_text(msgs)
        assert "[user] 你好" in text
        assert "[assistant] 你好！" in text

    def test_system_and_tool(self):
        msgs = [
            SystemMessage(content="系统消息"),
            ToolMessage(content="工具结果", tool_call_id="t1"),
        ]
        text = history_to_text(msgs)
        assert "[system] 系统消息" in text
        assert "[tool] 工具结果" in text

    def test_empty_content_skipped(self):
        msgs = [HumanMessage(content=""), AIMessage(content="有内容")]
        text = history_to_text(msgs)
        assert "[user]" not in text
        assert "[assistant] 有内容" in text

    def test_empty_list(self):
        assert history_to_text([]) == ""


# ── message_content_to_text ──


class TestMessageContentToText:

    def test_string(self):
        assert message_content_to_text("hello") == "hello"

    def test_list_of_strings(self):
        assert message_content_to_text(["a", "b"]) == "a\nb"

    def test_list_of_dicts(self):
        content = [{"text": "part1"}, {"text": "part2"}]
        assert message_content_to_text(content) == "part1\npart2"

    def test_mixed_list(self):
        content = ["plain", {"text": "rich"}, {"image": "skip"}]
        result = message_content_to_text(content)
        assert "plain" in result
        assert "rich" in result

    def test_none(self):
        assert message_content_to_text(None) == ""

    def test_whitespace_stripped(self):
        assert message_content_to_text("  hello  ") == "hello"


# ── count_user_turns ──


class TestCountUserTurns:

    def test_mixed_messages(self):
        msgs = [HumanMessage(content="1"), AIMessage(content="r"), HumanMessage(content="2")]
        assert count_user_turns(msgs) == 2

    def test_no_human(self):
        assert count_user_turns([AIMessage(content="x")]) == 0

    def test_empty(self):
        assert count_user_turns([]) == 0


# ── should_summarize_stateful ──


class TestShouldSummarizeStateful:

    def test_trigger_when_enough_new_turns(self):
        state = ConversationSummaryState(last_summarized_user_turns=2)
        assert should_summarize_stateful(
            state=state, user_turn_count=7, summarization_interval_turns=5
        )

    def test_not_trigger_when_below_interval(self):
        state = ConversationSummaryState(last_summarized_user_turns=3)
        assert not should_summarize_stateful(
            state=state, user_turn_count=5, summarization_interval_turns=5
        )

    def test_zero_interval_never_triggers(self):
        state = ConversationSummaryState(last_summarized_user_turns=0)
        assert not should_summarize_stateful(
            state=state, user_turn_count=100, summarization_interval_turns=0
        )


# ── should_summarize_stateless ──


class TestShouldSummarizeStateless:

    def test_trigger(self):
        assert should_summarize_stateless(user_turn_count=5, summarization_interval_turns=5)

    def test_not_trigger(self):
        assert not should_summarize_stateless(user_turn_count=3, summarization_interval_turns=5)

    def test_zero_interval(self):
        assert not should_summarize_stateless(user_turn_count=10, summarization_interval_turns=0)


# ── compose_history_context ──


class TestComposeHistoryContext:

    def test_both_parts(self):
        result = compose_history_context("摘要内容", "最近对话")
        assert "会话摘要" in result
        assert "摘要内容" in result
        assert "最近对话" in result

    def test_summary_only(self):
        result = compose_history_context("摘要", "")
        assert "摘要" in result
        assert "最近对话" not in result

    def test_history_only(self):
        result = compose_history_context("", "对话文本")
        assert "对话文本" in result
        assert "会话摘要" not in result

    def test_both_empty(self):
        assert compose_history_context("", "") == ""


# ── ConversationSummaryStore ──


class TestConversationSummaryStore:

    def test_get_or_create_new(self):
        store = ConversationSummaryStore(max_conversations=5)
        state = store.get_or_create("conv-1")
        assert isinstance(state, ConversationSummaryState)
        assert state.summary == ""

    def test_get_or_create_existing(self):
        store = ConversationSummaryStore()
        s1 = store.get_or_create("conv-1")
        s1.summary = "已有摘要"
        s2 = store.get_or_create("conv-1")
        assert s2.summary == "已有摘要"
        assert s1 is s2

    def test_eviction_when_max_reached(self):
        store = ConversationSummaryStore(max_conversations=2)
        s1 = store.get_or_create("old")
        s1.updated_at = time.time() - 1000  # make it old
        store.get_or_create("new1")
        store.get_or_create("new2")  # should evict "old"
        s_old = store.get_or_create("old")
        assert s_old.summary == ""  # freshly created, old was evicted

    def test_reset_if_history_restarted(self):
        store = ConversationSummaryStore()
        state = store.get_or_create("conv-1")
        state.summary = "some summary"
        state.last_seen_message_count = 10
        state.last_summarized_message_count = 8

        # Simulate history restart (fewer messages than last time)
        store.reset_if_history_restarted(state, current_history_count=3)
        assert state.summary == ""
        assert state.last_summarized_message_count == 0

    def test_no_reset_if_history_grows(self):
        store = ConversationSummaryStore()
        state = store.get_or_create("conv-1")
        state.summary = "existing"
        state.last_seen_message_count = 5

        store.reset_if_history_restarted(state, current_history_count=8)
        assert state.summary == "existing"  # not reset
