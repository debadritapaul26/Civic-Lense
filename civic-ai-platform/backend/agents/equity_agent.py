"""Regional Equity Agent implementation."""

from __future__ import annotations

from typing import Any

try:
    from ._claude_agent import run_claude
except ImportError:
    from _claude_agent import run_claude

try:
    from ..prompts.equity_prompt import SYSTEM_PROMPT
except ImportError:
    from prompts.equity_prompt import SYSTEM_PROMPT


async def run(input_data: dict[str, Any]) -> str:
    """Evaluate indicator-based regional equity for one cluster context."""

    return await run_claude(SYSTEM_PROMPT, input_data)
