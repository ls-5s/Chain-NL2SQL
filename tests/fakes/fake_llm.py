from app.llm.client import ModelResponse
from langchain_core.prompt_values import PromptValue

import json


class FakeLLM:
    """为 Graph 测试提供固定模型响应，避免依赖真实模型服务。"""

    def __init__(self, outcomes: str | Exception | list[str | Exception]) -> None:
        self.outcomes = [outcomes] if isinstance(outcomes, (str, Exception)) else list(outcomes)
        self.prompts: list[PromptValue] = []

    def generate(self, prompt: PromptValue, timeout_seconds: float) -> ModelResponse:
        # 参数保留以匹配真实 LLMClient 协议，响应始终由测试用例控制。
        # Fake 不产生网络请求，并记录 Prompt 以验证各分支没有携带 Schema。
        if _is_projection_review(prompt) and not _next_outcome_is_review_decision(self.outcomes):
            # Existing tests model SQL generation and answer generation. Give
            # their unrelated data-query fixtures the standard approval while
            # allowing review-focused tests to supply an explicit decision.
            return ModelResponse(content='{"valid":true}', model_name="fake")
        self.prompts.append(prompt)
        if not self.outcomes:
            raise AssertionError("FakeLLM ran out of configured outcomes.")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return ModelResponse(content=outcome, model_name="fake")


def _is_projection_review(prompt: PromptValue) -> bool:
    return "SQL 字段相关性审查器" in prompt.to_string()


def _next_outcome_is_review_decision(outcomes: list[str | Exception]) -> bool:
    if not outcomes or isinstance(outcomes[0], Exception):
        return bool(outcomes)
    try:
        decision = json.loads(outcomes[0])
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(decision, dict) and "valid" in decision
