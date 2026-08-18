"""Build a configured OpenAI-compatible LLM client."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from langchain_core.messages import BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_openai import ChatOpenAI

from app.config.settings import Settings
from app.llm.client import ModelResponse
from app.llm.retry_policy import invoke_with_retry


class LLMConfigurationError(ValueError):
    """Raised only when a real model client is requested without its credentials."""


class ChatModel(Protocol):
    """The ChatModel surface required by this adapter and its offline test doubles."""

    def invoke(self, messages: list[BaseMessage]) -> BaseMessage: ...


ChatModelFactory = Callable[..., ChatModel]


class OpenAIChatClient:
    """Adapt LangChain's ChatOpenAI to the application's provider-neutral protocol."""

    def __init__(
        self,
        settings: Settings,
        *,
        chat_model_factory: ChatModelFactory = ChatOpenAI,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        # 依赖注入 ChatModel 工厂，使真实客户端和离线 Fake 都能复用同一适配逻辑。
        self._settings = settings
        self._chat_model_factory = chat_model_factory
        self._sleep = sleep
        self._monotonic = monotonic
        self._validate_configuration()

    def generate(self, prompt: PromptValue, timeout_seconds: float) -> ModelResponse:
        """Invoke the model with a per-request timeout and bounded transient retries."""

        # 拒绝无效预算，避免把零或负数 timeout 传入底层 HTTP 客户端。
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")

        # 该截止时间在重试之间共享，保证总耗时受单次调用预算限制。
        deadline = self._monotonic() + timeout_seconds

        def invoke_once() -> ModelResponse:
            # 每次重试都用剩余时间重新创建 ChatModel，避免请求使用过期 timeout。
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                raise TimeoutError("LLM call exceeded its timeout budget.")

            model = self._create_chat_model(remaining)
            # PromptValue 转成消息列表后交给 LangChain ChatModel，保持供应商无关。
            message = model.invoke(prompt.to_messages())
            return ModelResponse(
                content=_message_content(message),
                model_name=_model_name(message, self._settings.openai_model),
            )

        return invoke_with_retry(
            invoke_once,
            timeout_seconds=timeout_seconds,
            sleep=self._sleep,
            monotonic=self._monotonic,
        )

    def _validate_configuration(self) -> None:
        # 只校验真实调用必需字段；配置缺失不影响不使用模型的本地接口启动。
        missing = [
            name
            for name, value in {
                "OPENAI_API_KEY": self._settings.openai_api_key,
                "OPENAI_MODEL": self._settings.openai_model,
            }.items()
            if not value
        ]
        if missing:
            raise LLMConfigurationError(
                "Missing required LLM configuration: " + ", ".join(missing) + "."
            )

    def _create_chat_model(self, timeout_seconds: float) -> ChatModel:
        # SDK 自带重试关闭，由 retry_policy 统一控制重试次数和时间预算。
        options: dict[str, object] = {
            "model": self._settings.openai_model,
            "api_key": self._settings.openai_api_key,
            "temperature": 0,
            "max_retries": 0,
            "timeout": timeout_seconds,
        }
        if self._settings.openai_base_url:
            # Base URL 可切换到 DeepSeek、Qwen 等 OpenAI 兼容服务。
            options["base_url"] = self._settings.openai_base_url
        return self._chat_model_factory(**options)


def create_openai_client(settings: Settings) -> OpenAIChatClient:
    """Create the real client lazily so non-LLM endpoints can start without credentials."""

    # 工厂不在模块导入时创建网络客户端，只有真正需要模型时才校验凭证。
    return OpenAIChatClient(settings)


def _message_content(message: BaseMessage) -> str:
    # 常规 ChatModel 返回字符串；多模态响应则提取其中的文本块。
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_blocks = [
            block["text"]
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ]
        if text_blocks:
            return "".join(text_blocks)
    raise TypeError("ChatModel response must contain text content.")


def _model_name(message: BaseMessage, configured_model: str | None) -> str:
    # 优先使用供应商实际返回的模型名，兼容响应未携带模型元数据的服务。
    response_model = message.response_metadata.get("model_name")
    return response_model if isinstance(response_model, str) else configured_model or "unknown"
