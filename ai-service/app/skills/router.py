"""根据用户问题选择最匹配的技能。"""

from app.skills.base import SkillBase
from app.skills.registry import get_registered_skills


_SKILLS = get_registered_skills()


def select_skill(query: str) -> SkillBase:
    """按注册顺序选择首个命中的技能。"""
    for skill in _SKILLS:
        if skill.can_handle(query):
            return skill
    # Fallback to the last skill as default explainer.
    return _SKILLS[-1]
