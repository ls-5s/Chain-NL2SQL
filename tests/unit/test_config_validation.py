import pytest

from app.config.settings import Settings
from app.config.validation import validate_settings


def test_production_rejects_default_session_secret() -> None:
    with pytest.raises(ValueError, match="SESSION_SECRET"):
        validate_settings(Settings(app_env="production", host="0.0.0.0", port=8000, max_iterations=3, query_timeout_seconds=15, result_row_limit=100))


def test_production_rejects_default_password() -> None:
    with pytest.raises(ValueError, match="AUTH_PASSWORD"):
        validate_settings(
            Settings(
                app_env="production",
                host="0.0.0.0",
                port=8000,
                max_iterations=3,
                query_timeout_seconds=15,
                result_row_limit=100,
                session_secret="a-real-secret",
            )
        )
