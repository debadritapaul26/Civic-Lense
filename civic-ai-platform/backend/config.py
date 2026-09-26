"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "civic.db"


def _get_budget() -> float:
    """Read the total policy-cycle budget in crore rupees from the environment."""

    raw_budget = os.getenv("TOTAL_BUDGET", "10.0")
    try:
        budget = float(raw_budget)
    except ValueError as exc:
        raise ValueError("TOTAL_BUDGET must be a valid number in INR crore.") from exc

    if budget < 0:
        raise ValueError("TOTAL_BUDGET cannot be negative.")
    return budget


ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ENABLE_LOCAL_NLU_FALLBACK: bool = os.getenv(
    "ENABLE_LOCAL_NLU_FALLBACK",
    "false",
).lower() in {"1", "true", "yes", "on"}
ENABLE_LOCAL_AGENT_FALLBACK: bool = os.getenv(
    "ENABLE_LOCAL_AGENT_FALLBACK",
    str(ENABLE_LOCAL_NLU_FALLBACK),
).lower() in {"1", "true", "yes", "on"}

_configured_database_url = os.getenv("DATABASE_URL", "sqlite:///./civic.db")
DATABASE_URL: str = (
    f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    if _configured_database_url == "sqlite:///./civic.db"
    else _configured_database_url
)
TOTAL_BUDGET: float = _get_budget()
