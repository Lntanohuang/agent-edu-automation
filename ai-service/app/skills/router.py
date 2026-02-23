from app.skills.base import SkillBase
from app.skills.registry import get_registered_skills


_SKILLS = get_registered_skills()


def select_skill(query: str) -> SkillBase:
    for skill in _SKILLS:
        if skill.can_handle(query):
            return skill
    # Fallback to the last skill as default explainer.
    return _SKILLS[-1]
