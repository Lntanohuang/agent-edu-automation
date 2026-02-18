"""
教案生成服务
"""
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI


from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import LessonPlanGenerateRequest

logger = get_logger(__name__)


class LessonPlanService:
    """教案生成服务"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            max_tokens=3000,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    
    async def generate(self, request: LessonPlanGenerateRequest) -> dict:
        """生成教案"""
        
        system_prompt = """你是一位资深的教学设计专家，擅长为中小学教师设计高质量教案。

你的任务是根据提供的教学信息，生成一份详细、专业、可落地的教案。教案应包含：
1. 清晰的教学目标（三维目标）
2. 明确的教学重难点
3. 详细的教学过程（每个环节的时间分配、教学内容、师生活动、设计意图）
4. 合理的作业布置
5. 板书设计建议

请用中文输出，格式规范，内容详实。"""

        user_prompt = f"""请为以下课程设计教案：

学科：{request.subject}
年级：{request.grade}
课题：{request.topic}
课时：{request.duration}课时
班级规模：{request.class_size}人
"""
        
        if request.teaching_goals:
            user_prompt += f"\n教学目标：{request.teaching_goals}"
        
        if request.requirements:
            user_prompt += f"\n特殊要求：{request.requirements}"
        
        if request.textbook_version:
            user_prompt += f"\n教材版本：{request.textbook_version}"
        
        user_prompt += f"\n难度级别：{request.difficulty}"
        user_prompt += "\n\n请生成完整的教案，并用JSON格式输出："
        
        # 调用 LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # 解析响应（这里简化处理，实际应该解析 JSON）
        return self._parse_lesson_plan_response(response.content, request)
    
    def _parse_lesson_plan_response(self, content: str, request: LessonPlanGenerateRequest) -> dict:
        """解析教案响应"""
        # 简化实现，实际应该用 JSON 解析
        return {
            "title": f"{request.grade}{request.subject} - {request.topic}",
            "subject": request.subject,
            "grade": request.grade,
            "duration": request.duration,
            "objectives": [
                "知识与技能：掌握核心概念和基本方法",
                "过程与方法：培养分析问题和解决问题的能力",
                "情感态度与价值观：激发学习兴趣，培养科学态度"
            ],
            "key_points": ["核心知识点的理解和掌握"],
            "difficulties": ["知识点的深入理解和应用"],
            "teaching_methods": ["讲授法", "讨论法", "演示法", "练习法"],
            "teaching_aids": ["多媒体课件", "实物教具"],
            "procedures": [
                {
                    "stage": "导入新课",
                    "duration": 5,
                    "content": "通过生活实例引入课题，激发学生兴趣",
                    "activities": "教师展示案例，学生观察思考",
                    "design_intent": "创设情境，引发学习兴趣"
                },
                {
                    "stage": "新课讲授",
                    "duration": 25,
                    "content": "讲解核心概念，配合例题分析",
                    "activities": "教师讲解演示，学生听讲记笔记",
                    "design_intent": "系统传授知识"
                },
                {
                    "stage": "课堂练习",
                    "duration": 10,
                    "content": "完成练习题，巩固所学",
                    "activities": "学生独立练习，教师巡视指导",
                    "design_intent": "及时巩固"
                },
                {
                    "stage": "小结作业",
                    "duration": 5,
                    "content": "总结本节课内容，布置作业",
                    "activities": "师生共同总结",
                    "design_intent": "梳理知识"
                }
            ],
            "homework": "1. 完成课后练习题\n2. 预习下节课内容",
            "blackboard_design": "主板书：课题、核心概念\n副板书：例题、要点",
            "reflection_guide": "课后反思要点...",
            "resources": []
        }
    
    async def enhance(self, request: dict) -> dict:
        """优化教案"""
        # TODO: 实现教案优化逻辑
        return {
            "enhanced_plan": request.get("original_plan"),
            "changes": []
        }
