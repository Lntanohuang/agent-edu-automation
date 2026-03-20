"""MLX-backed local chat model implemented as a LangChain BaseChatModel."""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


def _message_content_to_text(content: Any) -> str:
    """Flatten message content into plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "\n".join(part for part in parts if part).strip()
    return str(content or "")


def _to_chat_template_messages(messages: list[BaseMessage]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for message in messages:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, ToolMessage):
            role = "tool"
        else:
            role = "user"
        payload.append(
            {
                "role": role,
                "content": _message_content_to_text(getattr(message, "content", "")),
            }
        )
    return payload


def _fallback_prompt(messages: list[dict[str, str]]) -> str:
    blocks = [f"{item['role'].upper()}: {item['content']}" for item in messages if item["content"]]
    blocks.append("ASSISTANT:")
    return "\n\n".join(blocks)


@lru_cache(maxsize=2)
def _load_mlx_model(model_path: str):
    from mlx_lm import load

    return load(model_path)


class MLXChatModel(BaseChatModel):
    """Local MLX chat model that follows LangChain's BaseChatModel contract."""

    model_path: str = Field(default="")
    max_tokens: int = Field(default=2000, ge=1, le=8192)

    @property
    def _llm_type(self) -> str:
        return "mlx-chat"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model_path": self.model_path,
            "max_tokens": self.max_tokens,
        }

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = self._generate_text(messages, stop=stop)
        generation = ChatGeneration(message=AIMessage(content=text))
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return await asyncio.to_thread(self._generate, messages, stop, None, **kwargs)

    def _generate_text(self, messages: list[BaseMessage], stop: list[str] | None = None) -> str:
        try:
            from mlx_lm import generate
        except ImportError as exc:
            raise RuntimeError("当前配置使用 MLX 本地模型，但未安装 `mlx-lm`。") from exc

        if not self.model_path:
            raise RuntimeError("未配置 MLX_MODEL_PATH，无法加载本地模型。")

        model, tokenizer = _load_mlx_model(self.model_path)
        prompt_messages = _to_chat_template_messages(messages)

        if hasattr(tokenizer, "apply_chat_template"):
            prompt = tokenizer.apply_chat_template(
                prompt_messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            prompt = _fallback_prompt(prompt_messages)

        try:
            output = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=self.max_tokens,
                verbose=False,
            )
        except TypeError:
            output = generate(model, tokenizer, prompt=prompt, verbose=False)

        text = output if isinstance(output, str) else getattr(output, "text", str(output))
        cleaned = (text or "").strip()

        if stop:
            for token in stop:
                if token and token in cleaned:
                    cleaned = cleaned.split(token, 1)[0]
                    break

        return cleaned

    def with_structured_output(self, schema: Any, **kwargs: Any):
        """Fallback structured output via prompted JSON plus local parsing and retry."""
        if schema is None:
            raise ValueError("schema 不能为空")

        try:
            from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
        except ImportError as exc:
            raise RuntimeError("当前 LangChain 版本缺少结构化输出所需组件。") from exc

        if isinstance(schema, type):
            parser = PydanticOutputParser(pydantic_object=schema)
            schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        else:
            parser = JsonOutputParser()
            schema_json = json.dumps(schema, ensure_ascii=False, indent=2)

        instruction = (
            "请严格输出一个 JSON 对象，且必须满足以下 JSON Schema。\n"
            "不要输出解释、不要输出 Markdown 代码块、不要补充额外文本。\n"
            f"{schema_json}"
        )

        return MLXStructuredOutputRunnable(
            base_model=self,
            parser=parser,
            instruction=instruction,
            max_retries=1,
        )


class MLXStructuredOutputRunnable:
    """Structured-output wrapper with one repair retry when JSON parsing fails."""

    def __init__(self, *, base_model: MLXChatModel, parser: Any, instruction: str, max_retries: int = 1):
        self.base_model = base_model
        self.parser = parser
        self.instruction = instruction
        self.max_retries = max_retries

    def invoke(self, messages: list[BaseMessage], config: Any | None = None):
        return self._invoke_sync(messages)

    async def ainvoke(self, messages: list[BaseMessage], config: Any | None = None):
        return await self._invoke_async(messages)

    def _augment_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        augmented_messages = list(messages)
        if augmented_messages and isinstance(augmented_messages[0], SystemMessage):
            first = augmented_messages[0]
            augmented_messages[0] = SystemMessage(
                content=f"{_message_content_to_text(first.content)}\n\n{self.instruction}"
            )
        else:
            augmented_messages.insert(0, SystemMessage(content=self.instruction))
        return augmented_messages

    def _repair_messages(self, raw_text: str) -> list[BaseMessage]:
        repair_instruction = (
            f"{self.instruction}\n\n"
            "上一次输出未能被正确解析。请只返回修复后的 JSON 对象。"
        )
        return [
            SystemMessage(content=repair_instruction),
            ToolMessage(content=raw_text, tool_call_id="mlx-structured-output-repair"),
        ]

    def _parse_text(self, text: str):
        try:
            return self.parser.parse(text)
        except AttributeError:
            return self.parser.invoke(text)

    def _invoke_sync(self, messages: list[BaseMessage]):
        prompt_messages = self._augment_messages(messages)
        response = self.base_model.invoke(prompt_messages)
        raw_text = _message_content_to_text(getattr(response, "content", response))
        try:
            return self._parse_text(raw_text)
        except Exception:
            if self.max_retries <= 0:
                raise
        repair_response = self.base_model.invoke(self._repair_messages(raw_text))
        repaired_text = _message_content_to_text(getattr(repair_response, "content", repair_response))
        return self._parse_text(repaired_text)

    async def _invoke_async(self, messages: list[BaseMessage]):
        prompt_messages = self._augment_messages(messages)
        response = await self.base_model.ainvoke(prompt_messages)
        raw_text = _message_content_to_text(getattr(response, "content", response))
        try:
            return self._parse_text(raw_text)
        except Exception:
            if self.max_retries <= 0:
                raise
        repair_response = await self.base_model.ainvoke(self._repair_messages(raw_text))
        repaired_text = _message_content_to_text(getattr(repair_response, "content", repair_response))
        return self._parse_text(repaired_text)
