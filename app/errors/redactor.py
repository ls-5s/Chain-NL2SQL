"""Small shared redaction helpers; expand rules with database adapters."""

from __future__ import annotations

import re


# 先覆盖最常见的连接 URL；数据库适配器可继续追加方言相关脱敏规则。
_CONNECTION_URL = re.compile(r"\b\w+://[^\s]+")
_CREDENTIAL = re.compile(
    r"(?i)\b(api[-_ ]?key|authorization|x-api-key|token)\s*[:=]\s*[^\s,;]+"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
_SECRET_TOKEN = re.compile(r"\b(?:sk|lsv2)_[A-Za-z0-9_-]+\b")


def redact_error(message: str) -> str:
    # 返回给 API/Trace 的错误必须经过该边界，避免泄露凭据。
    redacted = _CONNECTION_URL.sub("[redacted-connection]", message)
    redacted = _CREDENTIAL.sub(lambda match: f"{match.group(1)}=[redacted-credential]", redacted)
    redacted = _BEARER.sub("Bearer [redacted-credential]", redacted)
    return _SECRET_TOKEN.sub("[redacted-token]", redacted)
