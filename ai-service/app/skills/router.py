"""LLM 技能路由：根据用户问题语义选择最匹配的技能。"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm.model_factory import chat_llm
from app.skills.base import Skill
from app.skills.registry import get_registered_skills

logger = logging.getLogger(__name__)

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
        "请选择最匹配的技能名称。skill_name 字段只能是上面列出的名称之一。"
    )


async def select_skill(query: str) -> Skill:
    """使用 LLM 将用户问题路由到最合适的技能。"""
    skills = _get_skills()

    if len(skills) == 1:
        return next(iter(skills.values()))

    llm = chat_llm.with_structured_output(RouteDecision, method="json_schema")
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
            logger.info("路由决策: %s (理由: %s)", clean_name, parsed.reason)
            return skills[clean_name]
        logger.warning("LLM 返回了未知技能名: %s，回落到默认", parsed.skill_name)
    except Exception:
        logger.exception("技能路由 LLM 调用失败，回落到默认技能")

    return _fallback_by_similarity(query, skills)


def _fallback_by_similarity(query: str, skills: Dict[str, Skill]) -> Skill:
    """路由 LLM 失败时，用技能描述的文本相似度选最相关技能。"""
    best_name, best_ratio = None, 0.0
    for name, skill in skills.items():
        ratio = SequenceMatcher(None, query, skill.config.description).ratio()
        if ratio > best_ratio:
            best_name, best_ratio = name, ratio
    if best_name:
        logger.info("Fallback 相似度匹配: %s (%.2f)", best_name, best_ratio)
        return skills[best_name]
    return next(iter(skills.values()))
