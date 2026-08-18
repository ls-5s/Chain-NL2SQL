from app.llm.client import ModelResponse


class FakeLLM:
    """为 Graph 测试提供固定模型响应，避免依赖真实模型服务。"""

    def __init__(self, content: str) -> None:
        self.content = content

    def generate(self, prompt: str, timeout_seconds: int) -> ModelResponse:
        # 参数保留以匹配真实 LLMClient 协议，响应始终由测试用例控制。
        return ModelResponse(content=self.content, model_name="fake")
