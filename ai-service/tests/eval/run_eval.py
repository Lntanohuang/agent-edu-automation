#!/usr/bin/env python3
"""
RAG 检索质量评测脚本。

用法：
    cd ai-service
    python -m tests.eval.run_eval [--dataset tests/eval/eval_dataset.json] [--output tests/eval/results.json]

评测指标：
1. 意图识别准确率 — query_analyzer 是否正确识别 intent
2. 关键词命中率 — 检索结果中包含 expected_keywords 的比例
3. 来源准确率 — 检索结果的 source/file_name 是否匹配 expected_source
4. MRR (Mean Reciprocal Rank) — 第一个相关文档的位置倒数的均值
5. 召回率@k — 前 k 个结果中包含至少一个相关文档的比例
6. 按难度/意图分组的细分指标
"""

import json
import sys
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.retrieval.query_analyzer import analyze_query
from app.retrieval.hybrid_retriever import get_hybrid_retriever


@dataclass
class EvalResult:
    """单条评测结果。"""
    id: str
    query: str
    intent_expected: str
    intent_predicted: str
    intent_correct: bool
    keywords_expected: List[str] = field(default_factory=list)
    keywords_found: List[str] = field(default_factory=list)
    keyword_hit_rate: float = 0.0
    expected_source: str = ""
    source_found: bool = False
    mrr: float = 0.0  # Mean Reciprocal Rank for this query
    recall_at_3: bool = False
    recall_at_6: bool = False
    num_docs_retrieved: int = 0
    latency_ms: float = 0.0
    difficulty: str = "medium"
    error: Optional[str] = None


@dataclass
class EvalSummary:
    """评测总结。"""
    total: int = 0
    intent_accuracy: float = 0.0
    avg_keyword_hit_rate: float = 0.0
    source_accuracy: float = 0.0
    mean_mrr: float = 0.0
    recall_at_3: float = 0.0
    recall_at_6: float = 0.0
    avg_latency_ms: float = 0.0
    by_intent: Dict[str, Dict] = field(default_factory=dict)
    by_difficulty: Dict[str, Dict] = field(default_factory=dict)


def _check_keyword_in_docs(keyword: str, docs) -> bool:
    """检查关键词是否出现在任一文档中。"""
    keyword_lower = keyword.lower()
    for doc in docs:
        if keyword_lower in (doc.page_content or "").lower():
            return True
    return False


def _check_source_in_docs(expected_source: str, docs) -> bool:
    """检查期望来源是否出现在检索结果中。"""
    if not expected_source:
        return True  # 未指定来源时默认通过
    for doc in docs:
        meta = doc.metadata or {}
        file_name = str(meta.get("file_name", ""))
        source = str(meta.get("source", ""))
        book_label = str(meta.get("book_label", ""))
        if expected_source in file_name or expected_source in source or expected_source in book_label:
            return True
    return False


def _compute_mrr(expected_keywords: List[str], docs) -> float:
    """计算 MRR：第一个包含任一关键词的文档的位置倒数。"""
    if not expected_keywords:
        return 1.0
    for rank, doc in enumerate(docs, start=1):
        content = (doc.page_content or "").lower()
        if any(kw.lower() in content for kw in expected_keywords):
            return 1.0 / rank
    return 0.0


def evaluate_single(item: dict, retriever) -> EvalResult:
    """评测单个 QA 对。"""
    query = item["query"]
    result = EvalResult(
        id=item["id"],
        query=query,
        intent_expected=item.get("intent", "general"),
        intent_predicted="",
        intent_correct=False,
        keywords_expected=item.get("expected_keywords", []),
        expected_source=item.get("expected_source", ""),
        difficulty=item.get("difficulty", "medium"),
    )

    try:
        t0 = time.time()

        # 1. 意图识别
        analysis = analyze_query(query)
        result.intent_predicted = analysis.intent
        result.intent_correct = (analysis.intent == result.intent_expected)

        # 2. 检索
        docs = retriever.retrieve(query, analysis, k=6)
        result.latency_ms = round((time.time() - t0) * 1000, 1)
        result.num_docs_retrieved = len(docs)

        # 3. 关键词命中
        if result.keywords_expected:
            found = [kw for kw in result.keywords_expected if _check_keyword_in_docs(kw, docs)]
            result.keywords_found = found
            result.keyword_hit_rate = len(found) / len(result.keywords_expected) if result.keywords_expected else 0

        # 4. 来源准确率
        result.source_found = _check_source_in_docs(result.expected_source, docs)

        # 5. MRR
        result.mrr = _compute_mrr(result.keywords_expected, docs)

        # 6. Recall@k
        has_relevant = any(
            any(kw.lower() in (d.page_content or "").lower() for kw in result.keywords_expected)
            for d in docs
        ) if result.keywords_expected else True
        result.recall_at_3 = any(
            any(kw.lower() in (d.page_content or "").lower() for kw in result.keywords_expected)
            for d in docs[:3]
        ) if result.keywords_expected else True
        result.recall_at_6 = has_relevant

    except Exception as exc:
        result.error = str(exc)

    return result


def compute_summary(results: List[EvalResult]) -> EvalSummary:
    """计算评测汇总指标。"""
    summary = EvalSummary(total=len(results))

    if not results:
        return summary

    valid = [r for r in results if r.error is None]

    summary.intent_accuracy = sum(1 for r in valid if r.intent_correct) / len(valid) if valid else 0
    summary.avg_keyword_hit_rate = sum(r.keyword_hit_rate for r in valid) / len(valid) if valid else 0

    source_items = [r for r in valid if r.expected_source]
    summary.source_accuracy = sum(1 for r in source_items if r.source_found) / len(source_items) if source_items else 0

    summary.mean_mrr = sum(r.mrr for r in valid) / len(valid) if valid else 0
    summary.recall_at_3 = sum(1 for r in valid if r.recall_at_3) / len(valid) if valid else 0
    summary.recall_at_6 = sum(1 for r in valid if r.recall_at_6) / len(valid) if valid else 0
    summary.avg_latency_ms = sum(r.latency_ms for r in valid) / len(valid) if valid else 0

    # 按意图分组
    for intent in ["law_article", "case_lookup", "concept_explain", "general"]:
        group = [r for r in valid if r.intent_expected == intent]
        if group:
            summary.by_intent[intent] = {
                "count": len(group),
                "intent_accuracy": sum(1 for r in group if r.intent_correct) / len(group),
                "avg_keyword_hit_rate": sum(r.keyword_hit_rate for r in group) / len(group),
                "mean_mrr": sum(r.mrr for r in group) / len(group),
                "recall_at_6": sum(1 for r in group if r.recall_at_6) / len(group),
            }

    # 按难度分组
    for diff in ["easy", "medium", "hard"]:
        group = [r for r in valid if r.difficulty == diff]
        if group:
            summary.by_difficulty[diff] = {
                "count": len(group),
                "avg_keyword_hit_rate": sum(r.keyword_hit_rate for r in group) / len(group),
                "mean_mrr": sum(r.mrr for r in group) / len(group),
                "recall_at_6": sum(1 for r in group if r.recall_at_6) / len(group),
            }

    return summary


def main():
    parser = argparse.ArgumentParser(description="RAG 检索质量评测")
    parser.add_argument("--dataset", default="tests/eval/eval_dataset.json", help="评测数据集路径")
    parser.add_argument("--output", default="tests/eval/results.json", help="结果输出路径")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"评测数据集不存在: {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"加载评测数据集: {len(dataset)} 条")
    print("初始化检索器...")
    retriever = get_hybrid_retriever()

    results: List[EvalResult] = []
    for i, item in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] {item['query'][:40]}...", end=" ")
        result = evaluate_single(item, retriever)
        results.append(result)
        status = "OK" if result.error is None else f"ERROR: {result.error}"
        print(f"-> intent={'OK' if result.intent_correct else 'FAIL'} kw={result.keyword_hit_rate:.0%} mrr={result.mrr:.2f} {status}")

    summary = compute_summary(results)

    output = {
        "summary": asdict(summary),
        "results": [asdict(r) for r in results],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("评测结果汇总")
    print("=" * 60)
    print(f"总数: {summary.total}")
    print(f"意图识别准确率: {summary.intent_accuracy:.1%}")
    print(f"关键词命中率: {summary.avg_keyword_hit_rate:.1%}")
    print(f"来源准确率: {summary.source_accuracy:.1%}")
    print(f"MRR: {summary.mean_mrr:.3f}")
    print(f"Recall@3: {summary.recall_at_3:.1%}")
    print(f"Recall@6: {summary.recall_at_6:.1%}")
    print(f"平均延迟: {summary.avg_latency_ms:.0f}ms")

    print("\n按意图分组:")
    for intent, stats in summary.by_intent.items():
        print(f"  {intent}: n={stats['count']} intent_acc={stats['intent_accuracy']:.0%} kw={stats['avg_keyword_hit_rate']:.0%} mrr={stats['mean_mrr']:.3f}")

    print("\n按难度分组:")
    for diff, stats in summary.by_difficulty.items():
        print(f"  {diff}: n={stats['count']} kw={stats['avg_keyword_hit_rate']:.0%} mrr={stats['mean_mrr']:.3f}")

    print(f"\n详细结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
