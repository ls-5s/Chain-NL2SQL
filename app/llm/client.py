"""Provider-neutral LLM interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from langchain_core.prompt_values import PromptValue


@dataclass(frozen=True)
class ModelResponse:
    """统一封装不同模型提供商返回的文本和模型标识。"""

    # 只向 Graph 暴露文本和模型名，不暴露供应商响应对象或原始元数据。
    content: str
    model_name: str


class LLMClient(Protocol):
    """生成节点依赖的最小模型协议，便于替换真实服务和 fake。"""

    # PromptValue 保留系统消息和用户消息边界，避免调用方拼接纯文本 Prompt。
    def generate(self, prompt: PromptValue, timeout_seconds: float) -> ModelResponse: ...
