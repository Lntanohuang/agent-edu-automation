"""
Provider-aware 结构化输出策略 + Prompt 格式约束注入。

qwen-plus 不支持严格 json_schema 模式，需要降级为 json_mode，
并通过 prompt 工程强制格式遵从。
"""

from __future__ import annotations

import json
from typing import Type

from pydantic import BaseModel

from app.core.config import settings


def get_structured_output_method() -> str:
    """根据 chat_provider 选择 with_structured_output 的 method 参数。

    - 原生 OpenAI (GPT-4o 等) 支持严格 json_schema
    - qwen_api / ollama / mlx 只支持松散 json_mode
    """
    provider = settings.chat_provider.strip().lower()
    if provider == "openai":
        return "json_schema"
    return "json_mode"


# ── Prompt 格式约束（严厉语气） ────────────────────────────────

_FORMAT_CONSTRAINT_PREFIX = """\
【严格格式要求 - 违反将导致系统解析失败】
你必须严格按照 JSON Schema 输出，不得有任何偏差。
- 所有字段名必须与 schema 完全一致，不得自行命名或重命名
- List 类型字段中的每个元素必须是完整对象（包含所有子字段），绝对不得简化为纯字符串
- 禁止在输出外层包裹任何容器对象（如 {"result": {...}} 或 {"data": {...}}）
- 输出必须是单个扁平 JSON 对象，顶层字段直接对应 schema 定义
- 禁止输出 JSON 以外的任何文本、注释或 markdown 标记
"""

_FORMAT_CONSTRAINT_SUFFIX = """\
【再次警告 - 格式不合规将导致完全失败】
输出必须是严格合法的扁平 JSON 对象。
列表中的每个元素必须是完整对象（包含所有子字段），不得简化为纯字符串。
不要在外面包裹任何容器，直接输出目标 schema 对应的 JSON。"""


def build_format_constrained_system_prompt(skill_prompt: str, schema: Type[BaseModel] | None = None) -> str:
    """在技能 system prompt 前后注入格式约束。"""
    parts = [_FORMAT_CONSTRAINT_PREFIX]
    if schema is not None:
        field_names = list(schema.model_fields.keys())
        parts.append(f"目标 JSON 顶层字段为：{', '.join(field_names)}。\n")
    parts.append(skill_prompt)
    return "\n\n".join(parts)


def build_format_constrained_human_suffix() -> str:
    """返回 human prompt 末尾的格式约束。"""
    return _FORMAT_CONSTRAINT_SUFFIX


def schema_to_field_description(schema: Type[BaseModel]) -> str:
    """将 Pydantic schema 转为可读的字段描述（供 fixer prompt 使用）。"""
    try:
        return json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    except Exception:
        return str(list(schema.model_fields.keys()))
