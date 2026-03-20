"""
SkillAgent：独立技能 Agent，每个 Skill 拥有独立的检索策略和执行上下文。

相比原有 Skill 基类的改进：
1. 每个 Agent 可定义自己的检索参数（k 值、意图过滤、BM25 权重等）
2. 支持 pre-retrieval hook（检索前的查询预处理）
3. 支持 post-retrieval hook（检索后的结果过滤）
4. System prompt 分层设计，支持 prefix caching
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.model_factory import chat_llm
from app.skills.base import build_context_text, build_sources, collect_book_labels
from app.skills.schemas import SkillResponse

if TYPE_CHECKING:
    from app.skills.skill_config import SkillConfig

logger = logging.getLogger(__name__)


class RetrievalStrategy:
    """技能专属检索策略配置。"""

    def __init__(
        self,
        k: int = 6,
        bm25_weight_override: Optional[float] = None,
        intent_filter: Optional[List[str]] = None,
        metadata_filters: Optional[dict] = None,
        use_hyde: bool = False,
        pre_retrieval_hook: Optional[Callable[[str], str]] = None,
        post_retrieval_hook: Optional[Callable[[str, List[Document]], List[Document]]] = None,
    ):
        self.k = k
        self.bm25_weight_override = bm25_weight_override
        self.intent_filter = intent_filter
        self.metadata_filters = metadata_filters
        self.use_hyde = use_hyde
        self.pre_retrieval_hook = pre_retrieval_hook
        self.post_retrieval_hook = post_retrieval_hook


# ── Prefix-cacheable system prompt 分层设计 ──
# 第一层：固定前缀（所有 skill 共享，LLM 可以缓存这部分的 KV）
_SHARED_PREFIX = """你是智能教育平台的 AI 助教，专注于法学教育和劳动法领域。

通用工作规则：
1. 只使用检索上下文中的信息回答问题，不编造事实
2. 若证据不足，明确告知"信息不足以确定结论"
3. 回答需要结构化：结论 → 依据 → 建议
4. 必须列出依据来源（书名/文件名）
5. 给出 2-3 条探索任务引导学生继续学习
"""


class SkillAgent:
    """由 SkillConfig + RetrievalStrategy 驱动的独立技能 Agent。

    与原 Skill 基类的区别：
    - 拥有独立的 RetrievalStrategy
    - System prompt 分为共享前缀 + 技能专属后缀，利于 prefix caching
    - 支持 pre/post retrieval hooks
    """

    def __init__(
        self,
        config: "SkillConfig",
        retrieval_strategy: Optional[RetrievalStrategy] = None,
    ) -> None:
        self.config = config
        self.name = config.name
        self.strategy = retrieval_strategy or RetrievalStrategy()
        # 分层 prompt：共享前缀 + 技能专属指令
        self._system_prompt = f"{_SHARED_PREFIX}\n\n专属角色指令：\n{config.system_prompt}"

    def preprocess_query(self, query: str) -> str:
        """检索前的查询预处理。"""
        if self.strategy.pre_retrieval_hook:
            return self.strategy.pre_retrieval_hook(query)
        return query

    def filter_docs(self, query: str, docs: List[Document]) -> List[Document]:
        """检索后的结果过滤。"""
        if self.strategy.post_retrieval_hook:
            return self.strategy.post_retrieval_hook(query, docs)
        return docs

    async def run(self, query: str, retrieved_docs: List[Document]) -> SkillResponse:
        """执行技能 Agent：预处理 → 过滤文档 → LLM 生成 → 格式化。"""
        # 1. 后处理检索结果
        filtered_docs = self.filter_docs(query, retrieved_docs)
        context_text = build_context_text(filtered_docs)

        # 2. LLM 结构化输出（使用分层 prompt）
        llm = chat_llm.with_structured_output(
            self.config.output_schema, method="json_schema",
        )
        output = await llm.ainvoke([
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=f"用户问题：{query}\n\n检索上下文：\n{context_text}\n\n请输出结构化结果。"),
        ])

        parsed = (
            output
            if isinstance(output, self.config.output_schema)
            else self.config.output_schema.model_validate(output)
        )

        answer = self.config.format_answer(parsed)
        tasks = getattr(parsed, "exploration_tasks", [])
        tasks = tasks[:3] if tasks else self.config.default_tasks

        confidence = (
            self.config.confidence_with_docs if filtered_docs
            else self.config.confidence_without_docs
        )

        return SkillResponse(
            skill_used=self.name,
            answer=answer,
            sources=build_sources(filtered_docs),
            book_labels=collect_book_labels(filtered_docs),
            exploration_tasks=tasks,
            confidence=confidence,
            structured_data=parsed.model_dump(),
        )
