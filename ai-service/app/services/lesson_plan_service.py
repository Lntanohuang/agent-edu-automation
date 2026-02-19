"""
教案生成服务
"""
import json
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.llm.model_factory import ollama_qwen_llm
from app.models.schemas import LessonPlanGenerateRequest

logger = get_logger(__name__)

CLASS_MINUTES = 45


class LessonPlanService:
    """教案生成服务"""

    def __init__(self):
        self.llm = ollama_qwen_llm

    async def generate(self, request: LessonPlanGenerateRequest) -> dict:
        """生成教案"""
        total_minutes = request.duration * CLASS_MINUTES
        output_hint = {
            "detailed": "流程建议 5-7 个环节，每个环节内容更细致。",
            "standard": "流程建议 4-6 个环节，内容清晰完整。",
            "simple": "流程建议 3-5 个环节，简洁可执行。",
        }.get(request.output_format, "流程建议 4-6 个环节，内容清晰完整。")

        system_prompt = (
            "你是一位资深教学设计专家，请根据用户输入生成可直接上课的教案。"
            "必须只返回 JSON 对象，不要返回 Markdown，不要加任何解释文字。"
        )

        user_prompt = f"""
请生成教案，严格返回一个 JSON 对象，结构如下：
{{
  "title": "教案标题",
  "subject": "学科",
  "grade": "年级",
  "duration": 课时数(整数),
  "objectives": ["目标1", "目标2", "目标3"],
  "key_points": ["重点1", "重点2"],
  "difficulties": ["难点1", "难点2"],
  "teaching_methods": ["方法1", "方法2"],
  "teaching_aids": ["教具1", "教具2"],
  "procedures": [
    {{
      "stage": "环节名称",
      "duration": 分钟数(整数),
      "content": "教学内容",
      "activities": "师生活动",
      "design_intent": "设计意图"
    }}
  ],
  "homework": "作业布置",
  "blackboard_design": "板书设计",
  "reflection_guide": "课后反思建议",
  "resources": [
    {{
      "title": "资源名称",
      "type": "资源类型",
      "description": "资源说明"
    }}
  ]
}}

约束：
1. 学科：{request.subject}
2. 年级：{request.grade}
3. 课题：{request.topic}
4. 课时：{request.duration}
5. 班级人数：{request.class_size}
6. 教材版本：{request.textbook_version or "未指定"}
7. 难度：{request.difficulty or "中等"}
8. 特殊要求：{request.requirements or "无"}
9. 教学目标补充：{request.teaching_goals or "无"}
10. 教学流程总时长必须等于 {total_minutes} 分钟
11. {output_hint}
12. 字段必须齐全，不能为空数组的字段至少给 1 项
"""

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            raw = self._extract_json_obj(response.content)
            return self._normalize_plan(
                raw=raw,
                subject=request.subject,
                grade=request.grade,
                topic=request.topic,
                duration=request.duration,
            )
        except Exception as exc:
            logger.error("Lesson plan generation failed, fallback used", error=str(exc))
            return self._build_default_plan(
                subject=request.subject,
                grade=request.grade,
                topic=request.topic,
                duration=request.duration,
            )

    async def enhance(self, request: dict) -> dict:
        """优化教案"""
        original = request.get("original_plan", {}) if isinstance(request, dict) else {}
        enhancement_type = str(request.get("enhancement_type", "improve")).strip() or "improve"
        target = str(request.get("target", "")).strip()

        subject = self._to_text(original.get("subject"), "未指定学科")
        grade = self._to_text(original.get("grade"), "未指定年级")
        duration = self._to_int(original.get("duration"), 1)
        title = self._to_text(original.get("title"), f"{grade}{subject}教案")

        base_plan = self._normalize_plan(
            raw=original,
            subject=subject,
            grade=grade,
            topic=title,
            duration=duration,
        )

        system_prompt = (
            "你是一位教学设计优化专家。请基于原教案做针对性改进。"
            "必须只返回 JSON 对象，不要返回 Markdown 和解释。"
        )

        user_prompt = f"""
请优化以下教案，并返回 JSON：
{{
  "enhanced_plan": <完整教案对象，字段同输入教案>,
  "changes": ["改动说明1", "改动说明2"]
}}

优化类型：{enhancement_type}
优化目标：{target or "未指定，请自动做合理增强"}
原教案：
{json.dumps(base_plan, ensure_ascii=False)}
"""

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            raw = self._extract_json_obj(response.content)
            enhanced_raw = raw.get("enhanced_plan", raw) if isinstance(raw, dict) else base_plan
            enhanced_plan = self._normalize_plan(
                raw=enhanced_raw,
                subject=subject,
                grade=grade,
                topic=title,
                duration=duration,
            )
            changes = self._normalize_str_list(raw.get("changes")) if isinstance(raw, dict) else []
            if not changes:
                changes = [f"已按 {enhancement_type} 优化教案结构与活动设计"]
            return {
                "enhanced_plan": enhanced_plan,
                "changes": changes,
            }
        except Exception as exc:
            logger.error("Lesson plan enhancement failed, fallback used", error=str(exc))
            return {
                "enhanced_plan": base_plan,
                "changes": [f"优化失败，已返回原教案: {str(exc)}"],
            }

    def _extract_json_obj(self, content: Any) -> Dict[str, Any]:
        text = str(content or "").strip()
        if not text:
            raise ValueError("LLM 返回为空")

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("未找到合法 JSON 对象")

        candidate = text[start : end + 1]
        data = json.loads(candidate)
        if not isinstance(data, dict):
            raise ValueError("JSON 根节点必须是对象")
        return data

    def _normalize_plan(
        self,
        raw: Dict[str, Any],
        *,
        subject: str,
        grade: str,
        topic: str,
        duration: int,
    ) -> Dict[str, Any]:
        total_minutes = max(1, duration) * CLASS_MINUTES

        objectives = self._normalize_str_list(raw.get("objectives"))
        if not objectives:
            objectives = [
                "知识与技能：掌握本课核心概念与方法。",
                "过程与方法：通过探究与练习提升分析和解决问题能力。",
                "情感态度与价值观：形成积极学习态度与合作意识。",
            ]

        key_points = self._normalize_str_list(raw.get("key_points") or raw.get("keyPoints"))
        if not key_points:
            key_points = ["理解并掌握本课核心知识点。"]

        difficulties = self._normalize_str_list(raw.get("difficulties"))
        if not difficulties:
            difficulties = ["将核心知识迁移到具体问题情境。"]

        teaching_methods = self._normalize_str_list(raw.get("teaching_methods") or raw.get("teachingMethods"))
        if not teaching_methods:
            teaching_methods = ["讲授法", "讨论法", "任务驱动法"]

        teaching_aids = self._normalize_str_list(raw.get("teaching_aids") or raw.get("teachingAids"))
        if not teaching_aids:
            teaching_aids = ["多媒体课件", "板书", "练习单"]

        procedures = self._normalize_procedures(raw.get("procedures"), total_minutes)

        resources = self._normalize_resources(raw.get("resources"))

        return {
            "title": self._to_text(raw.get("title"), f"{grade}{subject}《{topic}》教案"),
            "subject": self._to_text(raw.get("subject"), subject),
            "grade": self._to_text(raw.get("grade"), grade),
            "duration": self._to_int(raw.get("duration"), duration),
            "objectives": objectives,
            "key_points": key_points,
            "difficulties": difficulties,
            "teaching_methods": teaching_methods,
            "teaching_aids": teaching_aids,
            "procedures": procedures,
            "homework": self._to_text(
                raw.get("homework"),
                "1. 完成课后基础练习。\n2. 梳理本课知识框架。\n3. 预习下一课内容。",
            ),
            "blackboard_design": self._to_text(
                raw.get("blackboard_design") or raw.get("blackboardDesign"),
                "主板书：课题、核心概念、关键方法；副板书：典型例题与易错点。",
            ),
            "reflection_guide": self._to_text(
                raw.get("reflection_guide") or raw.get("reflectionGuide"),
                "反思目标达成情况、课堂互动效果与后续分层改进策略。",
            ),
            "resources": resources,
        }

    def _normalize_procedures(self, value: Any, total_minutes: int) -> List[Dict[str, Any]]:
        procedures: List[Dict[str, Any]] = []
        if isinstance(value, list):
            for idx, item in enumerate(value):
                if not isinstance(item, dict):
                    continue
                procedures.append(
                    {
                        "stage": self._to_text(item.get("stage"), f"教学环节{idx + 1}"),
                        "duration": max(1, self._to_int(item.get("duration"), 8)),
                        "content": self._to_text(item.get("content"), "围绕教学目标开展本环节学习。"),
                        "activities": self._to_text(item.get("activities"), "教师组织，学生参与互动与练习。"),
                        "design_intent": self._to_text(
                            item.get("design_intent") or item.get("designIntent"),
                            "服务教学目标达成并促进学生能力发展。",
                        ),
                    }
                )

        if not procedures:
            procedures = self._build_default_procedures(total_minutes)

        self._rebalance_procedure_duration(procedures, total_minutes)
        return procedures

    def _build_default_procedures(self, total_minutes: int) -> List[Dict[str, Any]]:
        return [
            {
                "stage": "导入与目标呈现",
                "duration": 6,
                "content": "创设情境，引出课题并明确学习目标。",
                "activities": "教师提问引导，学生联系已有经验回答。",
                "design_intent": "激活先备知识，建立学习动机。",
            },
            {
                "stage": "新知建构",
                "duration": 20,
                "content": "讲解核心概念与方法，配合示例进行分析。",
                "activities": "教师讲解示范，学生思考、记录并回应问题。",
                "design_intent": "帮助学生形成系统的知识结构。",
            },
            {
                "stage": "巩固练习",
                "duration": 14,
                "content": "设置分层练习，强化知识迁移与应用。",
                "activities": "学生独立/合作完成任务，教师巡视点拨。",
                "design_intent": "通过练习及时巩固与纠偏。",
            },
            {
                "stage": "总结与作业",
                "duration": 5,
                "content": "回顾重点难点，布置分层作业。",
                "activities": "师生共同总结，明确课后任务。",
                "design_intent": "促进知识内化并衔接后续学习。",
            },
        ][:4]

    def _rebalance_procedure_duration(self, procedures: List[Dict[str, Any]], total_minutes: int) -> None:
        durations = [max(1, self._to_int(item.get("duration"), 1)) for item in procedures]
        current_total = sum(durations)
        if current_total <= 0:
            durations = [1 for _ in procedures]
            current_total = len(durations)

        scaled = [max(1, round(d * total_minutes / current_total)) for d in durations]
        diff = total_minutes - sum(scaled)
        idx = 0
        safety = 0
        while diff != 0 and safety < 10000 and scaled:
            pos = idx % len(scaled)
            if diff > 0:
                scaled[pos] += 1
                diff -= 1
            else:
                if scaled[pos] > 1:
                    scaled[pos] -= 1
                    diff += 1
            idx += 1
            safety += 1

        for i, item in enumerate(procedures):
            item["duration"] = scaled[i]

    def _normalize_resources(self, value: Any) -> List[Dict[str, str]]:
        if not isinstance(value, list):
            return []
        resources: List[Dict[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                resources.append(
                    {
                        "title": self._to_text(item.get("title"), "未命名资源"),
                        "type": self._to_text(item.get("type"), "资料"),
                        "description": self._to_text(item.get("description"), ""),
                    }
                )
            elif isinstance(item, str) and item.strip():
                resources.append(
                    {
                        "title": item.strip(),
                        "type": "资料",
                        "description": "",
                    }
                )
        return resources

    def _normalize_str_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return items
        if isinstance(value, str) and value.strip():
            items = [x.strip() for x in re.split(r"[，,；;\n]+", value) if x.strip()]
            return items
        return []

    def _to_text(self, value: Any, default: str) -> str:
        text = str(value).strip() if value is not None else ""
        return text if text else default

    def _to_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_default_plan(
        self,
        *,
        subject: str,
        grade: str,
        topic: str,
        duration: int,
    ) -> Dict[str, Any]:
        return self._normalize_plan(
            raw={},
            subject=subject,
            grade=grade,
            topic=topic,
            duration=duration,
        )

    def build_default_plan(
        self,
        *,
        subject: str,
        grade: str,
        topic: str,
        duration: int,
    ) -> Dict[str, Any]:
        return self._build_default_plan(
            subject=subject,
            grade=grade,
            topic=topic,
            duration=duration,
        )
