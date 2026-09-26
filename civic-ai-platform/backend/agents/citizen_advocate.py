"""Citizen Advocate Agent implementation."""

from __future__ import annotations

from typing import Any

try:
    from ._claude_agent import run_claude
except ImportError:
    from _claude_agent import run_claude

try:
    from ..prompts.citizen_advocate_prompt import SYSTEM_PROMPT
except ImportError:
    from prompts.citizen_advocate_prompt import SYSTEM_PROMPT


async def run(input_data: dict[str, Any]) -> str:
    """Evaluate one district's citizen need from aggregated statistics."""

    return await run_claude(SYSTEM_PROMPT, input_data)
