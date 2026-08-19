from app.llm.client import ModelResponse
from langchain_core.prompt_values import PromptValue


class FakeLLM:
    """为 Graph 测试提供固定模型响应，避免依赖真实模型服务。"""

    def __init__(self, outcomes: str | Exception | list[str | Exception]) -> None:
        self.outcomes = [outcomes] if isinstance(outcomes, (str, Exception)) else list(outcomes)
        self.prompts: list[PromptValue] = []

    def generate(self, prompt: PromptValue, timeout_seconds: float) -> ModelResponse:
        # 参数保留以匹配真实 LLMClient 协议，响应始终由测试用例控制。
        # Fake 不产生网络请求，并记录 Prompt 以验证各分支没有携带 Schema。
        self.prompts.append(prompt)
        if not self.outcomes:
            raise AssertionError("FakeLLM ran out of configured outcomes.")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return ModelResponse(content=outcome, model_name="fake")
