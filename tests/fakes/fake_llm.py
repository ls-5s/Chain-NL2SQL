from app.llm.client import ModelResponse
from langchain_core.prompt_values import PromptValue


class FakeLLM:
    """为 Graph 测试提供固定模型响应，避免依赖真实模型服务。"""

    def __init__(self, content: str) -> None:
        self.content = content

    def generate(self, prompt: PromptValue, timeout_seconds: float) -> ModelResponse:
        # 参数保留以匹配真实 LLMClient 协议，响应始终由测试用例控制。
        # Fake 不读取 Prompt 内容，也不产生网络请求，便于稳定覆盖 Graph 分支。
        return ModelResponse(content=self.content, model_name="fake")
