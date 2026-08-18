"""Small shared redaction helpers; expand rules with database adapters."""

from __future__ import annotations

import re


# 先覆盖最常见的连接 URL；数据库适配器可继续追加方言相关脱敏规则。
_CONNECTION_URL = re.compile(r"\b\w+://[^\s]+")


def redact_error(message: str) -> str:
    # 返回给 API/Trace 的错误必须经过该边界，避免泄露凭据。
    return _CONNECTION_URL.sub("[redacted-connection]", message)
