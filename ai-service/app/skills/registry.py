"""Skills 自动发现注册中心。

扫描 skills/ 子目录，导入每个 ``skill.py`` 中导出的 ``config: SkillConfig`` 对象，
自动生成 Skill 实例。新增技能只需创建子目录并定义 ``config``，无需修改此文件。
"""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict

from app.skills.base import Skill
from app.skills.skill_config import SkillConfig

logger = logging.getLogger(__name__)

_SKILL_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def discover_skill_configs() -> Dict[str, SkillConfig]:
    """遍历子目录，收集所有导出 ``config: SkillConfig`` 的模块。"""
    configs: Dict[str, SkillConfig] = {}
    for item in sorted(_SKILL_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith("_"):
            continue
        skill_module_path = item / "skill.py"
        if not skill_module_path.exists():
            continue
        module_name = f"app.skills.{item.name}.skill"
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            logger.warning("跳过无法导入的技能模块: %s", module_name)
            continue
        cfg = getattr(mod, "config", None)
        if isinstance(cfg, SkillConfig):
            configs[cfg.name] = cfg
            logger.debug("发现技能: %s (%s)", cfg.name, module_name)
    return configs


def get_registered_skills() -> Dict[str, Skill]:
    """返回已注册的 Skill 实例字典（按 name 索引）。"""
    return {name: Skill(cfg) for name, cfg in discover_skill_configs().items()}
