"""声明式技能配置。"""

from dataclasses import dataclass, field
from typing import Callable, List, Type

from pydantic import BaseModel


@dataclass
class SkillConfig:
    """主技能的声明式定义，驱动通用 Skill runner。"""

    name: str
    """技能唯一标识，如 ``"law_article"``。"""

    description: str
    """供 LLM 路由使用的技能描述（一句话概括适用场景）。"""

    output_schema: Type[BaseModel]
    """LLM 结构化输出的 Pydantic 模型。"""

    system_prompt: str
    """传给 LLM 的 SystemMessage 内容。"""

    format_answer: Callable[[BaseModel], str]
    """将结构化输出转换为可读文本答案。"""

    default_tasks: List[str] = field(default_factory=list)
    """当 LLM 未生成探索任务时使用的兜底任务。"""

    confidence_with_docs: str = "high"
    """有检索文档时的置信度。"""

    confidence_without_docs: str = "low"
    """无检索文档时的置信度。"""
