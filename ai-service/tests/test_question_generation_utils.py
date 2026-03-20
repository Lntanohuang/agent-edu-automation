"""
Tests for question_generation_service pure utility functions.
No LLM or external deps needed.
"""
import pytest
from langchain_core.documents import Document

from app.services.question_generation_service import (
    DifficultyDistribution,
    GeneratedQuestion,
    GeneratedQuestionSet,
    QuestionGenerateInput,
    _build_context_text,
    _collect_labels_and_sources,
    _extract_choice_tokens,
    _is_fill_blank_answer_deterministic,
    _is_multiple_choice_answer_deterministic,
    _is_single_choice_answer_deterministic,
    _is_true_false_answer_deterministic,
    _normalize_question_type,
    _normalize_score,
    _resolve_book_label,
    _validate_objective_answer,
    _validate_questions,
)


# ── DifficultyDistribution validation ──


class TestDifficultyDistribution:

    def test_valid(self):
        d = DifficultyDistribution(easy=30, medium=50, hard=20)
        assert d.easy + d.medium + d.hard == 100

    def test_all_zero_raises(self):
        with pytest.raises(ValueError, match="总和必须大于 0"):
            DifficultyDistribution(easy=0, medium=0, hard=0)

    def test_partial_sum_ok(self):
        d = DifficultyDistribution(easy=0, medium=0, hard=1)
        assert d.hard == 1


# ── _resolve_book_label ──


class TestResolveBookLabel:

    def test_has_label(self):
        assert _resolve_book_label({"book_label": "数据结构"}) == "数据结构"

    def test_fallback_file_name(self):
        assert _resolve_book_label({"file_name": "algo.pdf"}) == "algo.pdf"

    def test_fallback_source(self):
        assert _resolve_book_label({"source": "/tmp/os.txt"}) == "/tmp/os.txt"

    def test_default(self):
        assert _resolve_book_label({}) == "未知教材"


# ── _normalize_question_type ──


class TestNormalizeQuestionType:

    @pytest.mark.parametrize("raw,expected", [
        ("单选题", "单选题"),
        ("多选题", "多选题"),
        ("判断题", "判断题"),
        ("填空题", "填空题"),
        ("single", "single_choice"),
        ("single-choice", "single_choice"),
        ("multiple", "multiple_choice"),
        ("truefalse", "true_false"),
        ("true-false", "true_false"),
        ("fillblank", "fill_blank"),
        ("fill-blank", "fill_blank"),
        ("简答题", "简答题"),  # passthrough
        ("编程题", "编程题"),  # passthrough
    ])
    def test_mapping(self, raw, expected):
        assert _normalize_question_type(raw) == expected

    def test_empty(self):
        assert _normalize_question_type("") == ""


# ── _extract_choice_tokens ──


class TestExtractChoiceTokens:

    def test_single_letter(self):
        assert _extract_choice_tokens("A") == ["A"]

    def test_multiple_continuous(self):
        assert _extract_choice_tokens("ABD") == ["A", "B", "D"]

    def test_comma_separated(self):
        assert _extract_choice_tokens("A,B,D") == ["A", "B", "D"]

    def test_chinese_comma(self):
        assert _extract_choice_tokens("A，C") == ["A", "C"]

    def test_empty(self):
        assert _extract_choice_tokens("") == []

    def test_text_answer(self):
        assert _extract_choice_tokens("这是文字答案") == []


# ── _is_single_choice_answer_deterministic ──


class TestSingleChoiceDeterministic:

    def test_letter(self):
        assert _is_single_choice_answer_deterministic("B", ["A选项", "B选项"])

    def test_exact_option_match(self):
        assert _is_single_choice_answer_deterministic("B选项", ["A选项", "B选项"])

    def test_empty(self):
        assert not _is_single_choice_answer_deterministic("", [])

    def test_multiple_letters_not_single(self):
        assert not _is_single_choice_answer_deterministic("AB", ["A", "B"])


# ── _is_multiple_choice_answer_deterministic ──


class TestMultipleChoiceDeterministic:

    def test_multiple_letters(self):
        assert _is_multiple_choice_answer_deterministic("ACD", [])

    def test_single_letter_ok(self):
        assert _is_multiple_choice_answer_deterministic("A", [])

    def test_duplicate_letters(self):
        assert not _is_multiple_choice_answer_deterministic("AA", [])

    def test_empty(self):
        assert not _is_multiple_choice_answer_deterministic("", [])


# ── _is_true_false_answer_deterministic ──


class TestTrueFalseDeterministic:

    @pytest.mark.parametrize("answer", ["True", "False", "对", "错", "正确", "错误", "T", "F", "yes", "no"])
    def test_valid(self, answer):
        assert _is_true_false_answer_deterministic(answer)

    def test_invalid(self):
        assert not _is_true_false_answer_deterministic("也许")


# ── _is_fill_blank_answer_deterministic ──


class TestFillBlankDeterministic:

    def test_valid(self):
        assert _is_fill_blank_answer_deterministic("TCP/IP")

    def test_empty(self):
        assert not _is_fill_blank_answer_deterministic("")

    @pytest.mark.parametrize("ambiguous", ["言之成理即可", "合理即可", "答案不唯一"])
    def test_ambiguous(self, ambiguous):
        assert not _is_fill_blank_answer_deterministic(ambiguous)


# ── _validate_objective_answer ──


class TestValidateObjectiveAnswer:

    def test_valid_single_choice(self):
        _validate_objective_answer("单选题", "A", ["A选项", "B选项"], 1)

    def test_invalid_single_choice(self):
        with pytest.raises(ValueError, match="单选答案不可判定"):
            _validate_objective_answer("单选题", "AB", ["A", "B"], 1)

    def test_valid_true_false(self):
        _validate_objective_answer("判断题", "对", [], 1)

    def test_invalid_true_false(self):
        with pytest.raises(ValueError, match="判断题答案"):
            _validate_objective_answer("判断题", "不确定", [], 1)

    def test_valid_fill_blank(self):
        _validate_objective_answer("填空题", "HTTP", [], 1)

    def test_invalid_fill_blank(self):
        with pytest.raises(ValueError, match="填空答案不可判定"):
            _validate_objective_answer("填空题", "言之成理即可", [], 1)


# ── _normalize_score ──


class TestNormalizeScore:

    def test_paper_mode_rescale(self):
        qs = GeneratedQuestionSet(
            questions=[
                GeneratedQuestion(stem="Q1", answer="A", explanation="...", score=10),
                GeneratedQuestion(stem="Q2", answer="B", explanation="...", score=10),
            ]
        )
        _normalize_score(qs, "paper", 100)
        assert qs.total_score == pytest.approx(100.0)
        assert qs.questions[0].score == pytest.approx(50.0)

    def test_paper_mode_zero_scores(self):
        qs = GeneratedQuestionSet(
            questions=[
                GeneratedQuestion(stem="Q1", answer="A", explanation="...", score=0),
                GeneratedQuestion(stem="Q2", answer="B", explanation="...", score=0),
            ]
        )
        _normalize_score(qs, "paper", 100)
        assert qs.total_score == pytest.approx(100.0)
        assert qs.questions[0].score == pytest.approx(50.0)

    def test_practice_mode_keeps_scores(self):
        qs = GeneratedQuestionSet(
            questions=[
                GeneratedQuestion(stem="Q1", answer="A", explanation="...", score=5),
                GeneratedQuestion(stem="Q2", answer="B", explanation="...", score=15),
            ]
        )
        _normalize_score(qs, "practice", 100)
        assert qs.total_score == pytest.approx(20.0)

    def test_empty_questions(self):
        qs = GeneratedQuestionSet(questions=[])
        _normalize_score(qs, "paper", 100)
        assert qs.total_score == 0.0


# ── _validate_questions ──


class TestValidateQuestions:

    def test_auto_fill_question_id(self):
        qs = GeneratedQuestionSet(
            questions=[
                GeneratedQuestion(stem="什么是TCP?", answer="传输控制协议", explanation="略述"),
            ]
        )
        req = QuestionGenerateInput(question_count=5)
        notes = _validate_questions(qs, req, [])
        assert qs.questions[0].question_id == "Q001"

    def test_missing_stem_raises(self):
        qs = GeneratedQuestionSet(
            questions=[GeneratedQuestion(stem="", answer="A", explanation="x")]
        )
        req = QuestionGenerateInput()
        with pytest.raises(ValueError, match="缺少题干"):
            _validate_questions(qs, req, [])

    def test_missing_answer_raises(self):
        qs = GeneratedQuestionSet(
            questions=[GeneratedQuestion(stem="题目", answer="", explanation="x")]
        )
        req = QuestionGenerateInput()
        with pytest.raises(ValueError, match="缺少答案"):
            _validate_questions(qs, req, [])

    def test_truncate_excess_questions(self):
        questions = [
            GeneratedQuestion(stem=f"Q{i}", answer="A", explanation="x")
            for i in range(8)
        ]
        qs = GeneratedQuestionSet(questions=questions)
        req = QuestionGenerateInput(question_count=3)
        notes = _validate_questions(qs, req, [])
        assert len(qs.questions) == 3
        assert any("裁剪" in n for n in notes)

    def test_fallback_source_citation(self):
        doc = Document(page_content="教材内容", metadata={"book_label": "操作系统", "source": "os.pdf"})
        qs = GeneratedQuestionSet(
            questions=[GeneratedQuestion(stem="进程是什么", answer="执行中的程序", explanation="解析")]
        )
        req = QuestionGenerateInput(question_count=5)
        notes = _validate_questions(qs, req, [doc])
        assert qs.questions[0].source_citations[0].book_label == "操作系统"
        assert any("默认引用" in n for n in notes)

    def test_choice_question_needs_options(self):
        qs = GeneratedQuestionSet(
            questions=[
                GeneratedQuestion(
                    stem="单选题", question_type="单选题",
                    answer="A", explanation="x", options=["只有一个选项"],
                )
            ]
        )
        req = QuestionGenerateInput()
        with pytest.raises(ValueError, match="选项不足"):
            _validate_questions(qs, req, [])


# ── _collect_labels_and_sources ──


class TestCollectLabelsAndSources:

    def test_basic(self):
        docs = [
            Document(page_content="a", metadata={"book_label": "教材B", "source": "b.pdf"}),
            Document(page_content="b", metadata={"book_label": "教材A", "file_name": "a.pdf"}),
        ]
        labels, sources = _collect_labels_and_sources(docs)
        assert labels == ["教材A", "教材B"]
        assert "a.pdf" in sources
        assert "b.pdf" in sources

    def test_empty(self):
        labels, sources = _collect_labels_and_sources([])
        assert labels == []
        assert sources == []


# ── _build_context_text ──


class TestBuildContextText:

    def test_includes_metadata(self):
        doc = Document(
            page_content="知识点内容",
            metadata={"book_label": "数据结构", "source": "ds.pdf", "page": "15"},
        )
        text = _build_context_text([doc])
        assert "数据结构" in text
        assert "知识点内容" in text

    def test_max_chars_truncation(self):
        doc = Document(page_content="A" * 10000, metadata={"book_label": "Big"})
        text = _build_context_text([doc], max_chars=100)
        assert len(text) <= 500  # content itself gets truncated to 320 + metadata

    def test_empty(self):
        assert _build_context_text([]) == ""
