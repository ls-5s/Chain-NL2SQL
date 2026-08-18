"""Structured logging setup without logging raw errors by default."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    # 统一由应用配置日志 handler；此处不私自添加可能重复的 handler。
    return logging.getLogger(name)
