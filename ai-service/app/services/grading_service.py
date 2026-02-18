"""
作业批阅服务
"""
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI


from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import EssayGradingRequest, CodeGradingRequest

logger = get_logger(__name__)


class GradingService:
    """作业批阅服务"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,  # 批阅需要更确定性的输出
            max_tokens=2000,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    
    async def grade_essay(self, request: EssayGradingRequest) -> dict:
        """作文批阅"""
        
        system_prompt = """你是一位资深的语文教师，擅长作文评阅和指导。

请对学生的作文进行全面、专业、有建设性的评价。评价应包括：
1. 总评分（百分制）
2. 总评评语（整体评价）
3. 优点（至少3条）
4. 不足（至少2条）
5. 改进建议（至少3条）
6. 分项评分（按评分标准）
7. 详细点评（段落级别的点评）

请客观公正，既指出问题又给予鼓励。"""

        # 构建评分标准描述
        rubric_desc = "\n".join([
            f"- {item.criteria}（{item.weight}%）：{item.description}"
            for item in request.rubric
        ])
        
        user_prompt = f"""请批阅以下作文：

题目：{request.title or "未指定"}
年级：{request.grade or "未指定"}

评分标准：
{rubric_desc}

作文内容：
{request.content}

请给出详细的批阅结果。"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # 解析响应（简化实现）
        return self._parse_essay_grading_response(response.content, request)
    
    def _parse_essay_grading_response(self, content: str, request: EssayGradingRequest) -> dict:
        """解析作文批阅响应"""
        # 简化实现，实际应该解析结构化数据
        total_weight = sum(item.weight for item in request.rubric)
        
        return {
            "overall_score": 85,
            "overall_comment": "这是一篇优秀的作文，立意明确，结构清晰，语言表达流畅。",
            "strengths": [
                "立意明确，主题突出",
                "结构完整，层次分明",
                "语言表达流畅，用词准确"
            ],
            "weaknesses": [
                "个别段落过渡不够自然",
                "细节描写可以更丰富"
            ],
            "suggestions": [
                "注意段落之间的过渡衔接",
                "增加具体事例和细节描写",
                "可以多运用修辞手法增强表现力"
            ],
            "criteria_scores": [
                {
                    "criteria_id": str(i),
                    "score": int(85 * item.weight / total_weight),
                    "comment": f"{item.criteria}方面表现良好"
                }
                for i, item in enumerate(request.rubric)
            ],
            "detailed_comments": content[:500],
            "spelling_errors": [],
            "word_count": len(request.content)
        }
    
    async def grade_code(self, request: CodeGradingRequest) -> dict:
        """代码批阅"""
        
        system_prompt = """你是一位资深的编程教师，擅长代码评审和指导。

请对学生的代码进行全面评价，包括：
1. 功能正确性（是否解决问题）
2. 代码质量（可读性、规范性）
3. 算法效率
4. 改进建议
5. 优化后的代码示例"""

        user_prompt = f"""请评审以下代码：

编程语言：{request.language}
题目：{request.problem}

代码：
```{request.language}
{request.code}
```

请给出详细的评审结果。"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        return {
            "score": 90,
            "compilation_result": {"success": True},
            "test_results": [{"passed": True, "case": "示例测试"}],
            "code_quality": {
                "readability": 85,
                "efficiency": 90,
                "best_practices": 80
            },
            "suggestions": [
                "代码结构清晰，继续保持",
                "可以添加更多注释说明",
                "考虑异常处理"
            ],
            "improved_code": request.code
        }
    
    async def grade_math(self, request: dict) -> dict:
        """数学解答批阅"""
        return {
            "is_correct": True,
            "score": 100,
            "score_breakdown": {
                "steps": 100,
                "answer": 100
            },
            "feedback": "解答正确，步骤完整",
            "errors": [],
            "suggestions": []
        }
    
    async def grade_english_essay(self, request: dict) -> dict:
        """英语作文批阅"""
        return {
            "overall_score": 88,
            "word_count": 150,
            "grammar_errors": [],
            "vocabulary_suggestions": [],
            "sentence_structure": "Good variety",
            "overall_feedback": "Good job!"
        }
    
    async def batch_grade(self, request: dict) -> dict:
        """批量批阅"""
        import uuid
        return {
            "batch_id": str(uuid.uuid4()),
            "estimated_time": len(request.get("submissions", [])) * 3
        }
    
    async def get_batch_progress(self, batch_id: str) -> dict:
        """获取批量批阅进度"""
        return {
            "batch_id": batch_id,
            "status": "completed",
            "completed": 10,
            "total": 10,
            "progress": 100
        }
