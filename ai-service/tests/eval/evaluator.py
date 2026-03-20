from __future__ import annotations
import json
import math
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from langchain_core.documents import Document


@dataclass
class EvalSample:
    id: str
    query: str
    intent: str
    difficulty: str
    expected_keywords: List[str]
    relevant_snippets: List[str]
    reference_answer: str
    notes: str = ""


@dataclass
class SampleResult:
    sample_id: str
    hit_at_k: bool
    mrr_at_k: float
    ndcg_at_k: float
    precision_at_k: float
    recall_at_k: float
    map_at_k: float


@dataclass
class EvalReport:
    retriever_name: str
    k: int
    hit_rate: float
    mrr: float
    ndcg: float
    precision: float
    recall: float
    mean_ap: float
    per_intent: dict   # intent -> {hit_rate, mrr, ndcg, count}
    per_difficulty: dict  # difficulty -> {hit_rate, ndcg, count}
    sample_results: List[SampleResult]


DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")


def load_dataset(path: str = DATASET_PATH) -> List[EvalSample]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [EvalSample(**item) for item in data]


def _relevance_score(doc_content: str, sample: EvalSample) -> float:
    """
    Token-overlap based relevance score (0.0 ~ 1.0).
    - keyword hit: +0.5/len(keywords) per hit, capped at 0.5
    - snippet substring hit (first 30 chars): +0.5
    """
    content = doc_content.lower()

    # keyword score
    kw_score = 0.0
    if sample.expected_keywords:
        hits = sum(1 for kw in sample.expected_keywords if kw.lower() in content)
        kw_score = min(0.5, 0.5 * hits / len(sample.expected_keywords))

    # snippet score
    snippet_score = 0.0
    for snippet in sample.relevant_snippets:
        # Use first 30 chars to avoid formatting mismatches
        key_part = snippet[:30].lower().strip()
        if key_part and key_part in content:
            snippet_score = 0.5
            break

    return min(1.0, kw_score + snippet_score)


def _is_relevant(doc_content: str, sample: EvalSample, threshold: float = 0.1) -> bool:
    return _relevance_score(doc_content, sample) >= threshold


def hit_at_k(docs: List[Document], sample: EvalSample, k: int) -> bool:
    return any(_is_relevant(d.page_content, sample) for d in docs[:k])


def mrr_at_k(docs: List[Document], sample: EvalSample, k: int) -> float:
    for i, doc in enumerate(docs[:k]):
        if _is_relevant(doc.page_content, sample):
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(docs: List[Document], sample: EvalSample, k: int) -> float:
    """Normalized Discounted Cumulative Gain @ k (graded relevance)."""
    gains = [_relevance_score(d.page_content, sample) for d in docs[:k]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))

    # Ideal DCG: sort gains descending
    ideal_gains = sorted(gains, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_gains))

    # If no gains found, assume at least 1 perfectly relevant doc exists
    if idcg == 0:
        idcg = 1.0 / math.log2(2)  # = 1.0

    return dcg / idcg if idcg > 0 else 0.0


def precision_at_k(docs: List[Document], sample: EvalSample, k: int) -> float:
    if not docs[:k]:
        return 0.0
    relevant = sum(1 for d in docs[:k] if _is_relevant(d.page_content, sample))
    return relevant / min(k, len(docs))


def recall_at_k(docs: List[Document], sample: EvalSample, k: int) -> float:
    """Recall @ k: relevant in top-k / estimated total relevant."""
    relevant_in_topk = sum(1 for d in docs[:k] if _is_relevant(d.page_content, sample))
    # Estimate total relevant = len(relevant_snippets) or at least 1
    total_relevant = max(1, len(sample.relevant_snippets))
    return min(1.0, relevant_in_topk / total_relevant)


def map_at_k(docs: List[Document], sample: EvalSample, k: int) -> float:
    """Mean Average Precision @ k."""
    precisions = []
    relevant_count = 0
    for i, doc in enumerate(docs[:k]):
        if _is_relevant(doc.page_content, sample):
            relevant_count += 1
            precisions.append(relevant_count / (i + 1))
    if not precisions:
        return 0.0
    return sum(precisions) / max(1, len(sample.relevant_snippets))


def _compute_sample_result(docs: List[Document], sample: EvalSample, k: int) -> SampleResult:
    return SampleResult(
        sample_id=sample.id,
        hit_at_k=hit_at_k(docs, sample, k),
        mrr_at_k=mrr_at_k(docs, sample, k),
        ndcg_at_k=ndcg_at_k(docs, sample, k),
        precision_at_k=precision_at_k(docs, sample, k),
        recall_at_k=recall_at_k(docs, sample, k),
        map_at_k=map_at_k(docs, sample, k),
    )


def _aggregate(results: List[SampleResult]) -> dict:
    n = len(results)
    if n == 0:
        return {"hit_rate": 0, "mrr": 0, "ndcg": 0, "precision": 0, "recall": 0, "mean_ap": 0, "count": 0}
    return {
        "hit_rate": sum(r.hit_at_k for r in results) / n,
        "mrr": sum(r.mrr_at_k for r in results) / n,
        "ndcg": sum(r.ndcg_at_k for r in results) / n,
        "precision": sum(r.precision_at_k for r in results) / n,
        "recall": sum(r.recall_at_k for r in results) / n,
        "mean_ap": sum(r.map_at_k for r in results) / n,
        "count": n,
    }


def evaluate_retriever(
    retriever_fn: Callable[[str], List[Document]],
    dataset: List[EvalSample],
    k: int = 6,
    retriever_name: str = "retriever",
) -> EvalReport:
    """
    Evaluate a retriever function against the golden dataset.

    Args:
        retriever_fn: Accepts a query string, returns List[Document].
        dataset: Evaluation dataset.
        k: Evaluation depth (top-k results).
        retriever_name: Name used in the report.
    """
    sample_results: List[SampleResult] = []
    for sample in dataset:
        docs = retriever_fn(sample.query)
        sr = _compute_sample_result(docs, sample, k)
        sample_results.append(sr)

    agg = _aggregate(sample_results)

    # Group by intent
    intents = {s.intent for s in dataset}
    per_intent = {}
    for intent in intents:
        intent_results = [
            sr for sr, s in zip(sample_results, dataset) if s.intent == intent
        ]
        per_intent[intent] = _aggregate(intent_results)

    # Group by difficulty
    difficulties = {s.difficulty for s in dataset}
    per_difficulty = {}
    for diff in difficulties:
        diff_results = [
            sr for sr, s in zip(sample_results, dataset) if s.difficulty == diff
        ]
        per_difficulty[diff] = _aggregate(diff_results)

    return EvalReport(
        retriever_name=retriever_name,
        k=k,
        hit_rate=agg["hit_rate"],
        mrr=agg["mrr"],
        ndcg=agg["ndcg"],
        precision=agg["precision"],
        recall=agg["recall"],
        mean_ap=agg["mean_ap"],
        per_intent=per_intent,
        per_difficulty=per_difficulty,
        sample_results=sample_results,
    )


def compare_retrievers(
    dataset: List[EvalSample],
    k: int = 6,
) -> dict:
    """
    Compare old (similarity_search) vs new (hybrid_retriever) retrievers.
    Requires real ChromaDB online (marked as integration test).

    Returns:
        {"baseline": EvalReport, "hybrid": EvalReport}
    """
    from app.llm.vector_store import get_rag_vector_store
    from app.retrieval.hybrid_retriever import get_hybrid_retriever
    from app.retrieval.query_analyzer import analyze_query

    vector_store = get_rag_vector_store()
    hr = get_hybrid_retriever()

    def baseline_fn(query: str) -> List[Document]:
        return vector_store.similarity_search(query, k=k)

    def hybrid_fn(query: str) -> List[Document]:
        analysis = analyze_query(query)
        return hr.retrieve(query, analysis, k=k)

    baseline_report = evaluate_retriever(baseline_fn, dataset, k, "similarity_search")
    hybrid_report = evaluate_retriever(hybrid_fn, dataset, k, "hybrid_retriever")

    return {"baseline": baseline_report, "hybrid": hybrid_report}
