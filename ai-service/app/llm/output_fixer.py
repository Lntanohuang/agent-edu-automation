"""
结构化输出修复器：主模型输出的 JSON 无法通过验证时，调用小模型修复。

四层防御的第 4 层：作为最后的容错手段。
"""

from __future__ import annotations

import json
import time
from typing import Type

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.logging import get_traced_logger
from app.llm.structured_output import schema_to_field_description

# 复用 model_factory 的 httpx 客户端（延迟导入避免循环）
_fixer_llm: ChatOpenAI | None = None


def _get_fixer_llm() -> ChatOpenAI:
    """懒加载修复用小模型（qwen-turbo，便宜快速）。"""
    global _fixer_llm
    if _fixer_llm is None:
        from app.llm.model_factory import _httpx_client, _httpx_async_client
        _fixer_llm = ChatOpenAI(
            model=settings.fixer_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            max_tokens=settings.skill_max_tokens,
            temperature=0,
            max_retries=1,
            http_client=_httpx_client,
            http_async_client=_httpx_async_client,
            timeout=60,
        )
    return _fixer_llm


async def try_parse_with_fix(
    raw_json: str,
    target_schema: Type[BaseModel],
    *,
    context_label: str = "",
) -> BaseModel:
    """尝试解析 JSON，失败则调用小模型修复。

    Args:
        raw_json: LLM 返回的原始 JSON 字符串
        target_schema: 目标 Pydantic BaseModel 类
        context_label: 日志标识（如 skill 名称）

    Returns:
        解析成功的 Pydantic 实例

    Raises:
        ValidationError: 修复后仍无法解析
    """
    logger = get_traced_logger("output_fixer")

    # 第一次：直接解析（会触发 model_validator 和 field_validator）
    try:
        return target_schema.model_validate_json(raw_json)
    except ValidationError as first_error:
        logger.warning(
            "output_parse_failed_attempting_fix",
            label=context_label,
            error_count=first_error.error_count(),
            raw_len=len(raw_json),
        )

    # 也尝试 dict 解析（处理已被 json.loads 过的情况）
    try:
        data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        return target_schema.model_validate(data)
    except (ValidationError, json.JSONDecodeError):
        pass

    # 第 4 层：调用小模型修复
    t0 = time.perf_counter()
    schema_desc = schema_to_field_description(target_schema)

    fix_system = (
        "你是 JSON 格式修复器。用户给你一段不符合 schema 的 JSON 和验证错误信息。\n"
        "你的任务是修复 JSON 使其完全符合目标 schema。\n"
        "规则：\n"
        "1) 只输出修复后的 JSON，不要任何其他文本\n"
        "2) 如果某个 list 字段的元素是字符串而非对象，将其转为符合子 schema 的对象\n"
        "3) 如果 JSON 被包裹在容器对象中，展开到顶层\n"
        "4) 缺失的必填字段用合理默认值填充\n"
        "5) 输出必须是合法 JSON"
    )

    fix_human = (
        f"原始 JSON：\n{raw_json}\n\n"
        f"验证错误：\n{str(first_error)}\n\n"
        f"目标 Schema：\n{schema_desc}\n\n"
        "请修复 JSON，只输出结果。"
    )

    try:
        fixer = _get_fixer_llm()
        response = await fixer.ainvoke([
            SystemMessage(content=fix_system),
            HumanMessage(content=fix_human),
        ])
        fixed_text = response.content.strip()
        # 去除可能的 markdown 代码块包裹
        if fixed_text.startswith("```"):
            fixed_text = fixed_text.split("\n", 1)[-1]
        if fixed_text.endswith("```"):
            fixed_text = fixed_text.rsplit("```", 1)[0]
        fixed_text = fixed_text.strip()

        result = target_schema.model_validate_json(fixed_text)
        elapsed = round(time.perf_counter() - t0, 3)
        logger.info(
            "output_fix_succeeded",
            label=context_label,
            elapsed_s=elapsed,
            fixer_model=settings.fixer_model,
        )
        return result
    except Exception as fix_error:
        elapsed = round(time.perf_counter() - t0, 3)
        logger.error(
            "output_fix_failed",
            label=context_label,
            elapsed_s=elapsed,
            fix_error=str(fix_error),
            original_error=str(first_error),
        )
        # 抛出原始错误，不是修复器的错误
        raise first_error from fix_error
