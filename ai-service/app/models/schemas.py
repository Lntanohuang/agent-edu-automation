"""
Pydantic 数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 通用模型 ====================

class ResponseBase(BaseModel):
    """通用响应基类"""
    success: bool = Field(default=True, description="是否成功")
    message: Optional[str] = Field(default=None, description="消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")


# ==================== 聊天模型 ====================

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色: system/user/assistant")
    content: str = Field(..., description="消息内容")


class ChatCompletionRequest(BaseModel):
    """聊天完成请求"""
    messages: List[ChatMessage] = Field(..., description="消息列表")
    model: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2000, ge=1)
    stream: bool = Field(default=False, description="是否流式返回")


class ChatCompletionResponse(ResponseBase):
    """聊天完成响应"""
    content: str = Field(..., description="回复内容")
    usage: Optional[Dict[str, int]] = Field(default=None, description="Token 使用量")


class EducationChatRequest(BaseModel):
    """教育领域聊天请求（带 RAG）"""
    query: str = Field(..., description="用户问题")
    context: Optional[Dict[str, str]] = Field(default=None, description="上下文信息")
    use_knowledge_base: bool = Field(default=True, description="是否使用知识库")
    knowledge_base_ids: Optional[List[str]] = Field(default=None, description="指定知识库ID")


class EducationChatResponse(ResponseBase):
    """教育领域聊天响应"""
    answer: str = Field(..., description="回答")
    sources: Optional[List[Dict[str, Any]]] = Field(default=None, description="参考来源")
    suggested_questions: Optional[List[str]] = Field(default=None, description="建议追问")


# ==================== 教案模型 ====================

class LessonPlanGenerateRequest(BaseModel):
    """教案生成请求"""
    subject: str = Field(..., description="学科")
    grade: str = Field(..., description="年级")
    topic: str = Field(..., description="课题")
    duration: int = Field(default=1, ge=1, le=4, description="课时数")
    class_size: int = Field(default=40, ge=1, le=100, description="班级人数")
    teaching_goals: Optional[str] = Field(default=None, description="教学目标")
    requirements: Optional[str] = Field(default=None, description="特殊要求")
    textbook_version: Optional[str] = Field(default=None, description="教材版本")
    difficulty: Optional[str] = Field(default="中等", description="难度")
    output_format: str = Field(default="detailed", description="输出格式: detailed/standard/simple")


class TeachingProcedure(BaseModel):
    """教学环节"""
    stage: str = Field(..., description="环节名称")
    duration: int = Field(..., description="时长(分钟)")
    content: str = Field(..., description="教学内容")
    activities: str = Field(..., description="师生活动")
    design_intent: str = Field(..., description="设计意图")


class LessonPlanResponse(ResponseBase):
    """教案响应"""
    title: str = Field(..., description="教案标题")
    subject: str = Field(..., description="学科")
    grade: str = Field(..., description="年级")
    duration: int = Field(..., description="课时数")
    objectives: List[str] = Field(..., description="教学目标")
    key_points: List[str] = Field(..., description="教学重点")
    difficulties: List[str] = Field(..., description="教学难点")
    teaching_methods: List[str] = Field(..., description="教学方法")
    teaching_aids: List[str] = Field(..., description="教学用具")
    procedures: List[TeachingProcedure] = Field(..., description="教学过程")
    homework: str = Field(..., description="作业布置")
    blackboard_design: Optional[str] = Field(default=None, description="板书设计")
    reflection_guide: Optional[str] = Field(default=None, description="教学反思指导")
    resources: Optional[List[Dict[str, str]]] = Field(default=None, description="推荐资源")


# ==================== 批阅模型 ====================

class GradingType(str, Enum):
    """批阅类型"""
    ESSAY = "essay"
    CODE = "code"
    MATH = "math"
    ENGLISH = "english"
    OTHER = "other"


class RubricItem(BaseModel):
    """评分标准项"""
    criteria: str = Field(..., description="评分项")
    weight: int = Field(..., ge=0, le=100, description="权重(%)")
    description: str = Field(..., description="描述")


class EssayGradingRequest(BaseModel):
    """作文批阅请求"""
    content: str = Field(..., description="作文内容")
    title: Optional[str] = Field(default=None, description="作文题目")
    rubric: List[RubricItem] = Field(..., description="评分标准")
    grade: Optional[str] = Field(default=None, description="年级")
    word_count: Optional[int] = Field(default=None, description="字数要求")
    check_plagiarism: bool = Field(default=False, description="是否查重")


class CriteriaScore(BaseModel):
    """分项得分"""
    criteria_id: str = Field(..., description="评分项ID")
    score: int = Field(..., description="得分")
    comment: str = Field(..., description="评语")


class EssayGradingResponse(ResponseBase):
    """作文批阅响应"""
    overall_score: int = Field(..., description="总评分")
    overall_comment: str = Field(..., description="总评评语")
    strengths: List[str] = Field(..., description="优点")
    weaknesses: List[str] = Field(..., description="不足")
    suggestions: List[str] = Field(..., description="建议")
    criteria_scores: List[CriteriaScore] = Field(..., description="分项评分")
    detailed_comments: str = Field(..., description="详细点评")
    spelling_errors: Optional[List[Dict[str, Any]]] = Field(default=None, description="错别字")
    word_count: Optional[int] = Field(default=None, description="实际字数")
    plagiarism_check: Optional[Dict[str, Any]] = Field(default=None, description="查重结果")


class CodeGradingRequest(BaseModel):
    """代码批阅请求"""
    code: str = Field(..., description="代码内容")
    language: str = Field(..., description="编程语言")
    problem: str = Field(..., description="题目描述")
    test_cases: Optional[List[Dict[str, str]]] = Field(default=None, description="测试用例")


class CodeGradingResponse(ResponseBase):
    """代码批阅响应"""
    score: int = Field(..., description="得分")
    compilation_result: Optional[Dict[str, Any]] = Field(default=None, description="编译结果")
    test_results: Optional[List[Dict[str, Any]]] = Field(default=None, description="测试结果")
    code_quality: Dict[str, int] = Field(..., description="代码质量评分")
    suggestions: List[str] = Field(..., description="改进建议")
    improved_code: Optional[str] = Field(default=None, description="优化后的代码")


# ==================== 知识库模型 ====================

class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    metadata: Optional[Dict[str, str]] = Field(default=None, description="元数据")


class DocumentUploadResponse(ResponseBase):
    """文档上传响应"""
    document_id: str = Field(..., description="文档ID")
    chunks: int = Field(..., description="切分成的文本块数")
    status: str = Field(..., description="状态")
    draft_id: Optional[str] = Field(default=None, description="待确认草稿ID")
    markdown_preview: Optional[str] = Field(default=None, description="Markdown预览")


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求"""
    query: str = Field(..., description="搜索查询")
    filters: Optional[Dict[str, str]] = Field(default=None, description="过滤条件")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数")


class KnowledgeSearchResponse(ResponseBase):
    """知识库搜索响应"""
    results: List[Dict[str, Any]] = Field(..., description="搜索结果")
