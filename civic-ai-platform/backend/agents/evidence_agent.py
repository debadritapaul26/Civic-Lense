"""Evidence Agent implementation."""

from __future__ import annotations

from typing import Any

try:
    from ._claude_agent import run_claude
except ImportError:
    from _claude_agent import run_claude

try:
    from ..prompts.evidence_prompt import SYSTEM_PROMPT
except ImportError:
    from prompts.evidence_prompt import SYSTEM_PROMPT


async def run(input_data: dict[str, Any]) -> str:
    """Assess evidence-supported severity for one district context."""

    return await run_claude(SYSTEM_PROMPT, input_data)
