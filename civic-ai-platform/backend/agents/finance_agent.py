"""Finance Agent implementation."""

from __future__ import annotations

from typing import Any

try:
    from ._claude_agent import run_claude
except ImportError:
    from _claude_agent import run_claude


SYSTEM_PROMPT = """
You are the Finance Agent in a civic-tech policy simulation. Perform only
arithmetic using the supplied proposals and total budget. Amounts are in the
same units as the input, namely ₹ crore. Calculate total_requested as the sum
of proposal amounts, total_available from total_budget, and
shortfall_or_surplus as total_available minus total_requested (negative means
shortfall). If requests exceed the budget, suggest proportional adjustments
by cluster without judging need or fairness. Return exactly:
{
  "total_requested": 0.0,
  "total_available": 0.0,
  "shortfall_or_surplus": 0.0,
  "suggested_adjustment_per_cluster": {},
  "justification": "1-2 sentences describing the arithmetic"
}
Do not invent clusters or proposals. Respond with ONLY valid JSON.
""".strip()


async def run(input_data: dict[str, Any]) -> str:
    """Calculate budget totals and arithmetic adjustments for supplied proposals."""

    return await run_claude(SYSTEM_PROMPT, input_data)
