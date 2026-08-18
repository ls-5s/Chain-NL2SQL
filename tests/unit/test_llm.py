from __future__ import annotations

import httpx
import pytest
from langchain_core.messages import AIMessage, BaseMessage
from openai import APITimeoutError

from app.config.settings import Settings
from app.llm.factory import LLMConfigurationError, OpenAIChatClient, create_openai_client
from app.llm.prompts import build_sql_generation_prompt, build_sql_repair_prompt


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "local",
        "host": "127.0.0.1",
        "port": 8000,
        "max_iterations": 3,
        "query_timeout_seconds": 15,
        "result_row_limit": 100,
        "allowed_database_ids": frozenset({"demo"}),
        "openai_api_key": "test-key",
        "openai_base_url": "https://example.test/v1",
        "openai_model": "test-model",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


class StubModel:
    def __init__(self, outcome: BaseMessage | Exception) -> None:
        self.outcome = outcome
        self.messages: list[BaseMessage] | None = None

    def invoke(self, messages: list[BaseMessage]) -> BaseMessage:
        self.messages = messages
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class StubModelFactory:
    def __init__(self, outcomes: list[BaseMessage | Exception]) -> None:
        self.outcomes = outcomes
        self.options: list[dict[str, object]] = []
        self.models: list[StubModel] = []

    def __call__(self, **options: object) -> StubModel:
        self.options.append(options)
        model = StubModel(self.outcomes.pop(0))
        self.models.append(model)
        return model


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.delays: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)
        self.now += seconds


def generation_prompt():
    return build_sql_generation_prompt().invoke(
        {
            "dialect": "sqlite",
            "schema_context": "TABLE users(id INTEGER, name TEXT)",
            "question": "查询所有用户",
        }
    )


def timeout_error() -> APITimeoutError:
    return APITimeoutError(request=httpx.Request("POST", "https://example.test/v1/chat/completions"))


def test_client_requires_key_and_model() -> None:
    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY, OPENAI_MODEL"):
        create_openai_client(make_settings(openai_api_key=None, openai_model=None))


def test_client_invokes_chat_model_with_configured_options() -> None:
    factory = StubModelFactory([AIMessage(content="SELECT name FROM users")])
    client = OpenAIChatClient(make_settings(), chat_model_factory=factory)

    response = client.generate(generation_prompt(), timeout_seconds=3)

    assert response.content == "SELECT name FROM users"
    assert response.model_name == "test-model"
    assert factory.options == [
        {
            "model": "test-model",
            "api_key": "test-key",
            "temperature": 0,
            "max_retries": 0,
            "timeout": 3,
            "base_url": "https://example.test/v1",
        }
    ]
    assert factory.models[0].messages is not None


def test_client_uses_provider_model_name_when_available() -> None:
    factory = StubModelFactory(
        [AIMessage(content="SELECT 1", response_metadata={"model_name": "provider-model"})]
    )
    client = OpenAIChatClient(make_settings(), chat_model_factory=factory)

    assert client.generate(generation_prompt(), timeout_seconds=3).model_name == "provider-model"


def test_client_retries_transient_errors() -> None:
    factory = StubModelFactory([timeout_error(), AIMessage(content="SELECT 1")])
    clock = Clock()
    client = OpenAIChatClient(
        make_settings(),
        chat_model_factory=factory,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    assert client.generate(generation_prompt(), timeout_seconds=3).content == "SELECT 1"
    assert len(factory.options) == 2
    assert clock.delays == [0.25]


def test_client_does_not_retry_non_transient_errors() -> None:
    factory = StubModelFactory([ValueError("invalid request")])
    client = OpenAIChatClient(make_settings(), chat_model_factory=factory)

    with pytest.raises(ValueError, match="invalid request"):
        client.generate(generation_prompt(), timeout_seconds=3)
    assert len(factory.options) == 1


def test_client_preserves_transient_error_after_retry_budget_is_exhausted() -> None:
    factory = StubModelFactory([timeout_error(), timeout_error(), timeout_error()])
    clock = Clock()
    client = OpenAIChatClient(
        make_settings(),
        chat_model_factory=factory,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    with pytest.raises(APITimeoutError):
        client.generate(generation_prompt(), timeout_seconds=3)
    assert len(factory.options) == 3
    assert clock.delays == [0.25, 0.5]


def test_generation_prompt_enforces_single_readonly_sql_output() -> None:
    prompt = build_sql_generation_prompt().invoke(
        {"dialect": "sqlite", "schema_context": "TABLE users(id)", "question": "查询用户"}
    )
    content = "\n".join(message.content for message in prompt.to_messages() if isinstance(message.content, str))

    assert "仅返回一条只读 SQL" in content
    assert "不得返回 Markdown 围栏" in content
    assert "TABLE users(id)" in content


def test_repair_prompt_includes_the_sanitized_error_and_failed_sql() -> None:
    prompt = build_sql_repair_prompt().invoke(
        {
            "dialect": "sqlite",
            "schema_context": "TABLE users(id)",
            "question": "查询用户",
            "failed_sql": "SELECT missing FROM users",
            "error_message": "unknown column",
        }
    )
    content = "\n".join(message.content for message in prompt.to_messages() if isinstance(message.content, str))

    assert "SELECT missing FROM users" in content
    assert "unknown column" in content
    assert "已脱敏错误信息" in content
