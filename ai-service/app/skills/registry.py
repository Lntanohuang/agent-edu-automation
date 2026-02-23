"""Skills 注册中心。"""

from typing import List

from app.skills.base import SkillBase
from app.skills.case_analysis.skill import CaseAnalysisSkill
from app.skills.law_article.skill import LawArticleSkill
from app.skills.law_explain.skill import LawExplainSkill


def get_registered_skills() -> List[SkillBase]:
    """返回技能列表（顺序即匹配优先级）。"""
    # Order matters: more specific skills should be checked first.
    return [
        LawArticleSkill(),
        CaseAnalysisSkill(),
        LawExplainSkill(),
    ]
