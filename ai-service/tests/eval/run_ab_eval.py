"""
Retrieval quality A/B comparison script.

Usage:
    conda run -n Langchain-sgg python -m tests.eval.run_ab_eval

Requires ChromaDB + vector data online (marked as integration test).
"""
import sys
import os

# Ensure ai-service root is in sys.path
AI_SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if AI_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, AI_SERVICE_ROOT)

import pytest


def _fmt(val: float) -> str:
    return f"{val:.3f}"


def _pct_change(old: float, new: float) -> str:
    if old == 0:
        return "N/A"
    change = (new - old) / old * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def _abs_change(old: float, new: float) -> str:
    diff = new - old
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.3f}"


def print_comparison(baseline, hybrid):
    """Print comparison table."""
    SEP = "-" * 72

    print()
    print("=" * 72)
    print(f"  Retrieval Quality A/B Comparison (k={baseline.k})")
    print("=" * 72)

    metrics = [
        ("Hit@k",       baseline.hit_rate,  hybrid.hit_rate),
        ("MRR@k",       baseline.mrr,       hybrid.mrr),
        ("nDCG@k",      baseline.ndcg,      hybrid.ndcg),
        ("Precision@k", baseline.precision, hybrid.precision),
        ("Recall@k",    baseline.recall,    hybrid.recall),
        ("MAP@k",       baseline.mean_ap,   hybrid.mean_ap),
    ]

    header = f"  {'Metric':<14} {'Baseline(sim)':>14} {'New(hybrid)':>12} {'Abs Gain':>10} {'Rel Gain':>10}"
    print(header)
    print(f"  {SEP}")

    for name, old_val, new_val in metrics:
        note = "  <- industry standard" if name == "nDCG@k" else ""
        print(f"  {name:<14} {_fmt(old_val):>14} {_fmt(new_val):>12} "
              f"{_abs_change(old_val, new_val):>10} {_pct_change(old_val, new_val):>10}{note}")

    # Group by intent
    print()
    print("  -- By Intent (nDCG@k) --")
    all_intents = sorted(set(baseline.per_intent) | set(hybrid.per_intent))
    for intent in all_intents:
        b_ndcg = baseline.per_intent.get(intent, {}).get("ndcg", 0)
        h_ndcg = hybrid.per_intent.get(intent, {}).get("ndcg", 0)
        count = hybrid.per_intent.get(intent, {}).get("count", 0)
        note = "  <- rule recall most impactful" if intent == "law_article" else ""
        print(f"  {intent:<16} {_fmt(b_ndcg):>14} {_fmt(h_ndcg):>12} "
              f"{_abs_change(b_ndcg, h_ndcg):>10} {_pct_change(b_ndcg, h_ndcg):>10}  (n={count}){note}")

    # Group by difficulty
    print()
    print("  -- By Difficulty (nDCG@k) --")
    for diff in ["easy", "medium", "hard"]:
        if diff not in baseline.per_difficulty:
            continue
        b_ndcg = baseline.per_difficulty[diff].get("ndcg", 0)
        h_ndcg = hybrid.per_difficulty.get(diff, {}).get("ndcg", 0)
        count = hybrid.per_difficulty.get(diff, {}).get("count", 0)
        print(f"  {diff:<16} {_fmt(b_ndcg):>14} {_fmt(h_ndcg):>12} "
              f"{_abs_change(b_ndcg, h_ndcg):>10}  (n={count})")

    print()


@pytest.mark.integration
def test_ab_comparison():
    """Integration test: requires ChromaDB + vector data online."""
    from tests.eval.evaluator import load_dataset, compare_retrievers

    dataset = load_dataset()
    results = compare_retrievers(dataset, k=6)
    baseline = results["baseline"]
    hybrid = results["hybrid"]

    print_comparison(baseline, hybrid)

    # Basic assertion: hybrid should outperform baseline
    assert hybrid.ndcg >= baseline.ndcg, (
        f"hybrid nDCG {hybrid.ndcg:.3f} < baseline {baseline.ndcg:.3f}"
    )
    assert hybrid.hit_rate >= baseline.hit_rate


if __name__ == "__main__":
    from tests.eval.evaluator import load_dataset, compare_retrievers

    print("Loading evaluation dataset...")
    dataset = load_dataset()
    print(f"Total {len(dataset)} evaluation samples")

    print("Running retrieval evaluation (requires ChromaDB online)...")
    results = compare_retrievers(dataset, k=6)

    print_comparison(results["baseline"], results["hybrid"])
