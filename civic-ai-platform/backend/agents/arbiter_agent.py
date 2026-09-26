"""Final Arbiter Agent implementation."""

from __future__ import annotations

from typing import Any

try:
    from ._claude_agent import run_claude
except ImportError:
    from _claude_agent import run_claude

try:
    from ..prompts.arbiter_prompt import SYSTEM_PROMPT
except ImportError:
    from prompts.arbiter_prompt import SYSTEM_PROMPT


async def run(input_data: dict[str, Any]) -> str:
    """Synthesize specialist reports into a budget-bounded recommendation."""

    return await run_claude(SYSTEM_PROMPT, input_data, max_tokens=1536)
