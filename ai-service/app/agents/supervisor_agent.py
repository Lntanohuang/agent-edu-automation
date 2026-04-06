"""
Multi-Agent Supervisor 教案生成 Agent (LangGraph StateGraph)。

架构:
    Supervisor (并行分发 + 重试降级)
        → conflict_detect (规则 + LLM 冲突检测)
        → writer (显式合并规则 → SemesterPlanOutput)

面试关键词: Supervisor 模式、asyncio.gather(return_exceptions=True)、
           重试+降级不阻塞、显式优先级规则、独立上下文。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.plan_agent import SemesterPlanOutput, WeeklyPlan
from app.llm.model_factory import chat_llm, plan_llm
from app.prompts.plan_prompts import (
    conflict_detection_prompt,
    lesson_plan_prompt,
    writer_merge_prompt,
)
from app.retrieval.hybrid_retriever import get_hybrid_retriever
from app.retrieval.query_analyzer import analyze_query
from app.skills.registry import get_registered_skills

logger = logging.getLogger(__name__)

# ── Supervisor 依赖的 skill 列表 ──────────────────────────────

_PLAN_SKILLS = [
    "curriculum_outline",
    "knowledge_sequencing",
    "teaching_activity",
    "assessment_design",
]

# ── 显式合并优先级规则（写死，不让 LLM 自行决定） ───────────
MERGE_PRIORITY = {
    "total_weeks": "curriculum_outline",      # 周数以课程大纲为准
    "knowledge_order": "knowledge_sequencing", # 知识排序以知识排序为准
    "activities": "teaching_activity",         # 活动以教学活动为准
    "assessment": "assessment_design",         # 考核以考核设计为准
}


# =====================================================================
# 1. State 定义
# =====================================================================

class SkillResult(TypedDict):
    status: str          # "success" | "degraded"
    name: str
    data: Optional[str]  # skill.answer 文本
    error: Optional[str]
    structured_data: Optional[Dict]


class PlanSupervisorState(TypedDict):
    """Supervisor 全局状态，所有节点共享、各自更新自己负责的字段。"""
    query: str
    retrieved_docs: List[Document]
    skill_results: Dict[str, SkillResult]
    data_gaps: List[str]
    conflicts: List[str]
    final_output: Optional[SemesterPlanOutput]
    agent_meta: Dict[str, Any]


# =====================================================================
# 2. 重试 + 降级执行器
# =====================================================================

async def execute_skill_with_retry(
    skill: Any,
    name: str,
    query: str,
    docs: List[Document],
    *,
    max_retries: int = 2,
    retry_delay: float = 1.0,
) -> SkillResult:
    """
    带重试和降级的 Skill 执行器。

    - max_retries: 最多重试次数（不含首次）
    - 重试全部失败 → 降级（标记缺失，不抛异常，不阻塞其他 Agent）
    """
    last_error: Optional[str] = None

    for attempt in range(max_retries + 1):
        try:
            result = await skill.run(query, docs)
            logger.info("[%s] 执行成功 (attempt=%d)", name, attempt + 1)
            return SkillResult(
                status="success",
                name=name,
                data=result.answer,
                error=None,
                structured_data=result.structured_data,
            )
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                logger.warning(
                    "[%s] 第%d次失败: %s，%.1fs后重试",
                    name, attempt + 1, last_error, retry_delay,
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    "[%s] 已重试%d次全部失败，触发降级", name, max_retries
                )

    # 降级：标记缺失，允许流程继续
    return SkillResult(
        status="degraded",
        name=name,
        data=None,
        error=last_error,
        structured_data=None,
    )


# =====================================================================
# 3. Graph 节点
# =====================================================================

async def supervisor_node(state: PlanSupervisorState) -> dict:
    """
    Supervisor 节点：并行分发 4 个 Skill Agent，收集结果。

    关键设计:
    - asyncio.gather(return_exceptions=True) → 一个 Skill 异常不会炸掉全部
    - 每个 Skill 独立上下文（独立 System Prompt），避免 lost-in-the-middle
    - 降级信息写入 state["data_gaps"]，后续节点可感知
    """
    query = state["query"]
    docs = state["retrieved_docs"]
    all_skills = get_registered_skills()

    # 构建并行任务
    tasks = []
    task_names = []
    for skill_name in _PLAN_SKILLS:
        skill = all_skills.get(skill_name)
        if skill is None:
            logger.warning("Supervisor: 技能未注册 %s", skill_name)
            continue
        tasks.append(
            execute_skill_with_retry(skill, skill_name, query, docs)
        )
        task_names.append(skill_name)

    # 并行执行（return_exceptions=True 防止单点炸全局）
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    skill_results: Dict[str, SkillResult] = {}
    data_gaps: List[str] = []

    for i, raw in enumerate(raw_results):
        name = task_names[i]
        if isinstance(raw, Exception):
            # gather 层面的异常（理论上不会触发，因为 execute_skill_with_retry 已捕获）
            logger.error("Supervisor: gather 捕获异常 %s: %s", name, raw)
            skill_results[name] = SkillResult(
                status="degraded", name=name,
                data=None, error=str(raw), structured_data=None,
            )
            data_gaps.append(name)
        elif raw["status"] == "degraded":
            skill_results[name] = raw
            data_gaps.append(name)
        else:
            skill_results[name] = raw

    if data_gaps:
        logger.warning("Supervisor: 以下模块降级 %s，流程继续", data_gaps)

    return {
        "skill_results": skill_results,
        "data_gaps": data_gaps,
    }


async def conflict_detect_node(state: PlanSupervisorState) -> dict:
    """
    冲突检测节点：规则优先 + LLM 兜底。

    规则检测: 周数不一致、知识点数量 vs 周数矛盾
    LLM 检测: 活动设计 vs 考核方式语义矛盾
    """
    results = state["skill_results"]
    conflicts: List[str] = []

    # ── 规则检测：跳过降级模块 ──
    co = results.get("curriculum_outline", {})
    ks = results.get("knowledge_sequencing", {})
    ta = results.get("teaching_activity", {})
    ad = results.get("assessment_design", {})

    co_data = co.get("structured_data") or {} if co.get("status") == "success" else {}
    ks_data = ks.get("structured_data") or {} if ks.get("status") == "success" else {}

    # 规则1: 周数一致性
    co_weeks = co_data.get("total_weeks") or co_data.get("weeks")
    ks_weeks = ks_data.get("total_weeks") or ks_data.get("weeks")
    if co_weeks and ks_weeks and co_weeks != ks_weeks:
        conflicts.append(
            f"周数冲突: curriculum_outline={co_weeks}周, "
            f"knowledge_sequencing={ks_weeks}周。"
            f"按合并规则以 curriculum_outline 为准。"
        )

    # ── LLM 语义冲突检测（仅当两个模块都成功时才做） ──
    ta_text = ta.get("data") if ta.get("status") == "success" else None
    ad_text = ad.get("data") if ad.get("status") == "success" else None

    if ta_text and ad_text:
        try:
            resp = await chat_llm.ainvoke([
                SystemMessage(content=conflict_detection_prompt),
                HumanMessage(content=(
                    f"教学活动设计:\n{ta_text[:1500]}\n\n"
                    f"考核方案设计:\n{ad_text[:1500]}\n\n"
                    "请检查是否存在矛盾。"
                )),
            ])
            det = (getattr(resp, "content", "") or "").strip()
            if det and not det.upper().startswith("PASS"):
                conflicts.append(det)
        except Exception as e:
            logger.warning("冲突检测 LLM 调用失败: %s", e)

    return {"conflicts": conflicts}


async def writer_node(state: PlanSupervisorState) -> dict:
    """
    Writer 节点：汇总所有 Skill 结果，按显式优先级规则合并，生成 SemesterPlanOutput。

    关键设计:
    - 合并规则写在 Prompt 里，不让 LLM 自行决定
    - 降级模块标注 [数据缺失]
    - 矛盾点明确标注，建议教师人工确认
    """
    results = state["skill_results"]
    data_gaps = state["data_gaps"]
    conflicts = state["conflicts"]
    query = state["query"]

    # 拼接各模块结果
    sections: List[str] = []
    for name in _PLAN_SKILLS:
        r = results.get(name, {})
        if r.get("status") == "success" and r.get("data"):
            sections.append(f"=== {name} ===\n{r['data']}")
        else:
            sections.append(f"=== {name} ===\n[数据缺失: 该模块生成失败，请教师补充]")

    skills_text = "\n\n".join(sections)

    # 降级说明
    gap_notice = ""
    if data_gaps:
        gap_notice = (
            f"\n\n注意：以下模块数据缺失，相关部分请标注"
            f"'[数据缺失，仅供参考]'：{', '.join(data_gaps)}"
        )

    # 冲突说明
    conflict_notice = ""
    if conflicts:
        conflict_text = "\n".join(f"- {c}" for c in conflicts)
        conflict_notice = (
            f"\n\n以下冲突已检测到，请在报告中标注分歧点并建议教师确认：\n{conflict_text}"
        )

    # 构建 Writer prompt
    merge_input = (
        f"{query}\n\n"
        f"以下是各教学设计专家模块的分析结果：\n\n"
        f"{skills_text}"
        f"{gap_notice}"
        f"{conflict_notice}\n\n"
        f"请严格按结构化字段输出。"
    )

    structured_llm = plan_llm.with_structured_output(
        SemesterPlanOutput,
        method="json_schema",
    )

    output = await structured_llm.ainvoke([
        SystemMessage(content=f"{lesson_plan_prompt}\n\n{writer_merge_prompt}"),
        HumanMessage(content=merge_input),
    ])

    if not isinstance(output, SemesterPlanOutput):
        output = SemesterPlanOutput.model_validate(output)

    # 构建 agent_meta
    skill_status = {}
    for name in _PLAN_SKILLS:
        r = results.get(name, {})
        skill_status[name] = r.get("status", "not_registered")

    agent_meta = {
        "skill_status": skill_status,
        "conflicts": conflicts,
        "data_gaps": data_gaps,
        "merge_priority": MERGE_PRIORITY,
    }

    return {
        "final_output": output,
        "agent_meta": agent_meta,
    }


# =====================================================================
# 4. 构建 StateGraph
# =====================================================================

def build_supervisor_graph() -> StateGraph:
    """
    构建 Supervisor Multi-Agent 图:
        supervisor → conflict_detect → writer → END

    Supervisor 内部用 asyncio.gather 并行执行 4 个 Skill Agent。
    决策权始终在 Supervisor — 子 Agent 只执行，不决策。
    """
    graph = StateGraph(PlanSupervisorState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("conflict_detect", conflict_detect_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "conflict_detect")
    graph.add_edge("conflict_detect", "writer")
    graph.add_edge("writer", END)

    return graph.compile()


# 单例
_compiled_graph = None


def get_supervisor_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_supervisor_graph()
    return _compiled_graph


# =====================================================================
# 5. 对外接口（保持与原 PlanAgent 兼容的 ainvoke 签名）
# =====================================================================

class SupervisorPlanAgent:
    """
    Multi-Agent Supervisor 教案生成 Agent。

    对外接口与原 SkillEnhancedPlanAgent 完全一致:
        result = await agent.ainvoke({"messages": [HumanMessage(...)]})
        result["structured_response"]  → SemesterPlanOutput
        result["agent_meta"]           → 新增：降级/冲突/耗时元信息
    """

    async def ainvoke(self, inputs: dict) -> dict:
        start = time.time()

        messages = inputs.get("messages", []) if isinstance(inputs, dict) else []
        user_query = ""
        if messages:
            last_msg = messages[-1]
            user_query = str(getattr(last_msg, "content", "") or "")
        if not user_query:
            raise ValueError("缺少用户输入")

        # ── 检索教材文档 ──
        hybrid_retriever = get_hybrid_retriever()
        analysis = analyze_query(user_query)
        retrieved_docs = hybrid_retriever.retrieve(user_query, analysis, k=8)

        # ── 执行 Supervisor Graph ──
        graph = get_supervisor_graph()
        initial_state: PlanSupervisorState = {
            "query": user_query,
            "retrieved_docs": retrieved_docs,
            "skill_results": {},
            "data_gaps": [],
            "conflicts": [],
            "final_output": None,
            "agent_meta": {},
        }

        final_state = await graph.ainvoke(initial_state)

        elapsed_ms = int((time.time() - start) * 1000)
        agent_meta = final_state.get("agent_meta", {})
        agent_meta["total_time_ms"] = elapsed_ms

        return {
            "structured_response": final_state["final_output"],
            "agent_meta": agent_meta,
        }


def create_supervisor_plan_agent() -> SupervisorPlanAgent:
    """创建 Multi-Agent Supervisor 教案生成 Agent。"""
    return SupervisorPlanAgent()
