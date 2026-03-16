"""探索任务生成技能：补全可执行的学习任务。"""

from typing import List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm.model_factory import chat_llm
from app.skills.base import build_context_text, collect_book_labels


class TeachingTasksOutput(BaseModel):
    """探索任务生成的结构化输出。"""

    tasks: List[str] = Field(default_factory=list, description="Exploration/learning tasks")


class TeachingTaskGeneratorSkill:
    """
    Post-processing skill:
    generate exploration tasks that guide users back to books/materials.
    """

    name = "teaching_task_generator"

    async def run(
        self,
        *,
        query: str,
        answer: str,
        retrieved_docs: List[Document],
        existing_tasks: List[str],
    ) -> List[str]:
        """基于问题与检索结果生成 2-3 条探索任务。"""
        if existing_tasks and len(existing_tasks) >= 2:
            return existing_tasks[:3]

        context_text = build_context_text(retrieved_docs, max_docs=3, max_chars=2600)
        labels = collect_book_labels(retrieved_docs)
        label_text = ", ".join(labels) if labels else "当前未识别书本标签"

        llm = chat_llm.with_structured_output(
            TeachingTasksOutput,
            method="json_schema",
        )

        try:
            output = await llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "你是课程助教。请根据问题所属学科领域，为学生生成2-3条可执行的探索任务。"
                            "任务必须引导学生回到教材或检索资料，具体且有针对性，不要空泛。"
                        )
                    ),
                    HumanMessage(
                        content=(
                            f"用户问题：{query}\n\n"
                            f"当前回答：{answer}\n\n"
                            f"书本标签：{label_text}\n\n"
                            f"检索片段：\n{context_text}\n\n"
                            "请输出结构化 tasks。"
                        )
                    ),
                ]
            )
            parsed = output if isinstance(output, TeachingTasksOutput) else TeachingTasksOutput.model_validate(output)
            tasks = [task.strip() for task in parsed.tasks if task and task.strip()]
            if tasks:
                return tasks[:3]
        except Exception:
            pass

        fallback_label = labels[0] if labels else "教材"
        return [
            f"回看《{fallback_label}》中与该问题相关的章节，整理3个关键概念并写出定义。",
            "选取一个相近概念做对比表（定义、构成要件、适用边界）。",
            "基于本次结论设计1个反例，说明为什么不适用当前规则。",
        ]
