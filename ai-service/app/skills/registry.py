from typing import List

from app.skills.base import SkillBase
from app.skills.case_analysis.skill import CaseAnalysisSkill
from app.skills.law_article.skill import LawArticleSkill
from app.skills.law_explain.skill import LawExplainSkill


def get_registered_skills() -> List[SkillBase]:
    # Order matters: more specific skills should be checked first.
    return [
        LawArticleSkill(),
        CaseAnalysisSkill(),
        LawExplainSkill(),
    ]
