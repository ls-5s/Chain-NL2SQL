"""Global test isolation for external observability integrations."""

import os


# Tests must never emit traces or depend on credentials from a developer's .env.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
