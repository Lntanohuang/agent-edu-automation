"""LLM 技能路由：根据用户问题语义选择最匹配的技能。"""

from __future__ import annotations

import time
from difflib import SequenceMatcher
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.logging import get_traced_logger
from app.llm.model_factory import chat_llm
from app.llm.structured_output import get_structured_output_method
from app.skills.base import Skill
from app.skills.registry import get_registered_skills

# 懒加载缓存
_skills: Dict[str, Skill] = {}

_FALLBACK_SKILL = "law_explain"


class RouteDecision(BaseModel):
    """路由决策结构化输出。"""

    skill_name: str = Field(description="选中的技能名称")
    reason: str = Field(description="选择理由（一句话）")


def _get_skills() -> Dict[str, Skill]:
    global _skills
    if not _skills:
        _skills = get_registered_skills()
    return _skills


def _build_routing_prompt(skills: Dict[str, Skill]) -> str:
    skill_list = "\n".join(
        f"- {name}: {s.config.description}" for name, s in skills.items()
    )
    return (
        "你是技能路由器。根据用户问题选择最合适的技能。\n\n"
        f"可选技能：\n{skill_list}\n\n"
        "请选择最匹配的技能名称。skill_name 字段只能是上面列出的名称之一。\n"
        "请返回合法 json（小写 json），不要输出额外文本。"
    )


async def select_skill(query: str) -> Skill:
    """使用 LLM 将用户问题路由到最合适的技能。"""
    logger = get_traced_logger(__name__)
    t0 = time.perf_counter()
    logger.info("skill_routing_started", query_preview=query[:60])

    skills = _get_skills()

    if len(skills) == 1:
        return next(iter(skills.values()))

    llm = chat_llm.with_structured_output(RouteDecision, method=get_structured_output_method())
    try:
        decision = await llm.ainvoke([
            SystemMessage(content=_build_routing_prompt(skills)),
            HumanMessage(content=f"用户问题：{query}"),
        ])
        parsed = (
            decision
            if isinstance(decision, RouteDecision)
            else RouteDecision.model_validate(decision)
        )
        # 清理 Ollama json_schema 模式偶发的尾部残留字符（如 "law_explain'}"）
        clean_name = parsed.skill_name.strip().rstrip("'\"}")
        if clean_name in skills:
            elapsed_s = round(time.perf_counter() - t0, 3)
            logger.info("skill_routing_decided", skill=clean_name, reason=parsed.reason, elapsed_s=elapsed_s)
            return skills[clean_name]
        logger.warning("skill_routing_unknown_name_fallback", raw_skill_name=parsed.skill_name)
    except Exception as exc:
        logger.error("skill_routing_llm_failed_fallback", error=str(exc), exc_info=True)

    return _fallback_by_similarity(query, skills)


def _fallback_by_similarity(query: str, skills: Dict[str, Skill]) -> Skill:
    """路由 LLM 失败时，用技能描述的文本相似度选最相关技能。"""
    logger = get_traced_logger(__name__)
    best_name, best_ratio = None, 0.0
    for name, skill in skills.items():
        ratio = SequenceMatcher(None, query, skill.config.description).ratio()
        if ratio > best_ratio:
            best_name, best_ratio = name, ratio
    if best_name:
        logger.info("skill_routing_similarity_fallback", skill=best_name, ratio=round(best_ratio, 3))
        return skills[best_name]
    return next(iter(skills.values()))
