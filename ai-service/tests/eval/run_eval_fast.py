#!/usr/bin/env python3
"""快速评测脚本 — 跳过 MongoDB 写入和 HyDE LLM 调用，专注核心指标。"""

import json
import sys
import time
import os
from pathlib import Path

# 项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.retrieval.query_analyzer import analyze_query
from app.retrieval.hybrid_retriever import get_hybrid_retriever

# Patch AFTER import — 替换已加载模块中的函数引用
import app.retrieval.metrics as metrics_mod
metrics_mod.log_retrieval_metrics = lambda *a, **kw: None  # type: ignore

import app.retrieval.hyde as hyde_mod
hyde_mod.generate_hypothetical_document_sync = lambda *a, **kw: None  # type: ignore

# 同时 patch hybrid_retriever 中的引用
import app.retrieval.hybrid_retriever as hr_mod
hr_mod.log_retrieval_metrics = lambda *a, **kw: None  # type: ignore
if hasattr(hr_mod, 'generate_hypothetical_document_sync'):
    hr_mod.generate_hypothetical_document_sync = lambda *a, **kw: None  # type: ignore


def main():
    dataset_path = Path("tests/eval/eval_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    total = len(dataset)
    print(f"加载评测数据集: {total} 条")
    print("初始化检索器 (HyDE/MongoDB 已禁用)...")
    retriever = get_hybrid_retriever()
    print("检索器就绪\n")

    correct_intent = 0
    total_kw_hit = 0.0
    total_mrr = 0.0
    recall3_count = 0
    recall6_count = 0
    by_intent: dict = {}
    misses: list = []
    total_latency = 0.0

    for i, item in enumerate(dataset):
        q = item["query"]
        expected_intent = item.get("intent", "general")
        expected_kw = item.get("expected_keywords", [])

        t0 = time.time()
        analysis = analyze_query(q)
        docs = retriever.retrieve(q, analysis, k=6)
        latency = round((time.time() - t0) * 1000, 1)
        total_latency += latency

        # Intent
        intent_ok = analysis.intent == expected_intent
        if intent_ok:
            correct_intent += 1
        else:
            misses.append((q[:45], expected_intent, analysis.intent))

        # Keywords
        if expected_kw:
            found = sum(
                1
                for kw in expected_kw
                if any(kw.lower() in (d.page_content or "").lower() for d in docs)
            )
            kw_rate = found / len(expected_kw)
        else:
            kw_rate = 1.0
        total_kw_hit += kw_rate

        # MRR
        mrr = 0.0
        if expected_kw:
            for rank, d in enumerate(docs, 1):
                if any(kw.lower() in (d.page_content or "").lower() for kw in expected_kw):
                    mrr = 1.0 / rank
                    break
        else:
            mrr = 1.0
        total_mrr += mrr

        # Recall
        has_rel_3 = (
            any(
                any(kw.lower() in (d.page_content or "").lower() for kw in expected_kw)
                for d in docs[:3]
            )
            if expected_kw
            else True
        )
        has_rel_6 = (
            any(
                any(kw.lower() in (d.page_content or "").lower() for kw in expected_kw)
                for d in docs
            )
            if expected_kw
            else True
        )
        if has_rel_3:
            recall3_count += 1
        if has_rel_6:
            recall6_count += 1

        # By intent
        if expected_intent not in by_intent:
            by_intent[expected_intent] = {"n": 0, "ok": 0, "kw": 0.0, "mrr": 0.0, "r6": 0}
        g = by_intent[expected_intent]
        g["n"] += 1
        if intent_ok:
            g["ok"] += 1
        g["kw"] += kw_rate
        g["mrr"] += mrr
        if has_rel_6:
            g["r6"] += 1

        tag = "OK" if intent_ok else "FAIL"
        print(
            f"[{i+1:2d}/{total}] {q[:40]:40s} intent={tag:4s} kw={kw_rate:.0%} mrr={mrr:.2f} {latency:.0f}ms"
        )

    # Summary
    print()
    print("=" * 60)
    print("评测结果汇总 (v2 — 修复后)")
    print("=" * 60)
    print(f"总数:             {total}")
    print(f"意图识别准确率:   {correct_intent}/{total} = {correct_intent/total:.1%}")
    print(f"关键词命中率:     {total_kw_hit/total:.1%}")
    print(f"MRR:              {total_mrr/total:.3f}")
    print(f"Recall@3:         {recall3_count}/{total} = {recall3_count/total:.1%}")
    print(f"Recall@6:         {recall6_count}/{total} = {recall6_count/total:.1%}")
    print(f"平均延迟:         {total_latency/total:.0f}ms")

    print("\n按意图分组:")
    for intent in ["law_article", "case_lookup", "concept_explain", "general"]:
        g = by_intent.get(intent)
        if g:
            n = g["n"]
            print(
                f"  {intent:20s}: n={n:2d}  intent={g['ok']/n:.0%}  kw={g['kw']/n:.0%}  "
                f"mrr={g['mrr']/n:.3f}  r@6={g['r6']/n:.0%}"
            )

    if misses:
        print(f"\n意图未命中 ({len(misses)}条):")
        for q, exp, got in misses:
            print(f'  "{q}" expected={exp} got={got}')

    # v1 对比
    print("\n" + "=" * 60)
    print("v1 vs v2 对比")
    print("=" * 60)
    print(f"{'指标':<20s} {'v1':>10s} {'v2':>10s} {'变化':>10s}")
    print("-" * 52)
    v1 = {"intent": 56.9, "kw": 75.9, "mrr": 0.743, "r3": 84.6, "r6": 92.3}
    v2_intent = correct_intent / total * 100
    v2_kw = total_kw_hit / total * 100
    v2_mrr = total_mrr / total
    v2_r3 = recall3_count / total * 100
    v2_r6 = recall6_count / total * 100
    print(f"{'意图准确率':<20s} {v1['intent']:>9.1f}% {v2_intent:>9.1f}% {v2_intent-v1['intent']:>+9.1f}%")
    print(f"{'关键词命中率':<20s} {v1['kw']:>9.1f}% {v2_kw:>9.1f}% {v2_kw-v1['kw']:>+9.1f}%")
    print(f"{'MRR':<20s} {v1['mrr']:>10.3f} {v2_mrr:>10.3f} {v2_mrr-v1['mrr']:>+10.3f}")
    print(f"{'Recall@3':<20s} {v1['r3']:>9.1f}% {v2_r3:>9.1f}% {v2_r3-v1['r3']:>+9.1f}%")
    print(f"{'Recall@6':<20s} {v1['r6']:>9.1f}% {v2_r6:>9.1f}% {v2_r6-v1['r6']:>+9.1f}%")


if __name__ == "__main__":
    main()
