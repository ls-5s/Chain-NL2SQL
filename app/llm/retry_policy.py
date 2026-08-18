"""Own bounded retries for transient model-provider failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError


T = TypeVar("T")
# 只重试可由短暂网络或服务波动造成的错误，不重试参数和认证错误。
_RETRYABLE_ERRORS = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)


def invoke_with_retry(
    operation: Callable[[], T],
    *,
    timeout_seconds: float,
    max_attempts: int = 3,
    initial_backoff_seconds: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> T:
    """重试短暂模型故障，且不允许等待时间超过调用预算。"""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    # 总预算覆盖所有尝试和退避等待，而不是每次重试重新计时。
    deadline = monotonic() + timeout_seconds
    for attempt in range(max_attempts):
        # 在创建下一次请求前检查剩余预算，避免超时后继续访问供应商。
        if monotonic() >= deadline:
            raise TimeoutError("LLM call exceeded its timeout budget.")
        try:
            return operation()
        except _RETRYABLE_ERRORS:
            # 最后一次失败直接保留供应商异常，交由上层统一分类。
            if attempt == max_attempts - 1:
                raise

            remaining = deadline - monotonic()
            if remaining <= 0:
                raise
            # 指数退避降低连续重试压力，同时不能超过剩余时间预算。
            delay = min(initial_backoff_seconds * (2**attempt), remaining)
            sleep(delay)

    raise RuntimeError("Retry loop exited unexpectedly.")
