"""Provider-neutral LLM interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelResponse:
    """统一封装不同模型提供商返回的文本和模型标识。"""

    content: str
    model_name: str


class LLMClient(Protocol):
    """生成节点依赖的最小模型协议，便于替换真实服务和 fake。"""

    def generate(self, prompt: str, timeout_seconds: int) -> ModelResponse: ...
