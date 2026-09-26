"""Shared Claude invocation and local demo fallbacks for specialist agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

try:
    from ..config import ANTHROPIC_API_KEY, ENABLE_LOCAL_AGENT_FALLBACK
except ImportError:
    from config import ANTHROPIC_API_KEY, ENABLE_LOCAL_AGENT_FALLBACK


MODEL_NAME = "claude-sonnet-4-6"
logger = logging.getLogger(__name__)


def _number(value: Any, default: float = 0.0) -> float:
    """Convert a value to a finite float for deterministic demo calculations."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _cluster_context(input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Extract a cluster identifier and aggregate cluster data."""

    cluster = input_data.get("cluster")
    if not isinstance(cluster, dict):
        cluster = {}
    name = str(
        cluster.get("representative_location")
        or cluster.get("cluster_id")
        or "Location cluster"
    )
    return name, cluster


def _local_agent_response(
    system_prompt: str,
    input_data: dict[str, Any],
) -> str:
    """Create schema-compatible local reports when Claude is unavailable."""

    prompt = system_prompt.lower()
    if "citizen advocate agent" in prompt:
        name, cluster = _cluster_context(input_data)
        complaint_count = _number(cluster.get("complaint_count"))
        urgency = _number(cluster.get("avg_urgency_score"))
        score = max(1.0, min(10.0, round(urgency * 0.8 + complaint_count / 10, 1)))
        return json.dumps(
            {
                "cluster": name,
                "priority_score": score,
                "justification": (
                    f"{name} has {int(complaint_count)} complaints with average urgency "
                    f"{urgency:.1f}/10, so the location-level citizen-need signal is material."
                ),
                "key_stats_cited": (
                    f"complaint_count={int(complaint_count)}, avg_urgency={urgency:.1f}, "
                    f"evidence_verified_pct={_number(cluster.get('evidence_verified_pct')):.1f}"
                ),
            },
            ensure_ascii=False,
        )

    if "evidence agent" in prompt:
        name, cluster = _cluster_context(input_data)
        complaint_count = _number(cluster.get("complaint_count"))
        urgency = max(0.0, min(10.0, _number(cluster.get("avg_urgency_score"))))
        evidence_pct = max(0.0, min(100.0, _number(cluster.get("evidence_verified_pct"))))
        return json.dumps(
            {
                "cluster_or_complaint_id": name,
                "severity_score": round(urgency, 1),
                "confidence_percent": round(max(20.0, evidence_pct), 1),
                "justification": (
                    f"The location cluster has {int(complaint_count)} complaints at average urgency "
                    f"{urgency:.1f}/10, with {evidence_pct:.1f}% marked as evidence-verified."
                ),
                "mismatch_flag": complaint_count > 0 and evidence_pct < 25,
            },
            ensure_ascii=False,
        )

    if "finance agent" in prompt:
        clusters = input_data.get("clusters")
        if not isinstance(clusters, list):
            clusters = []
        budget = max(0.0, _number(input_data.get("total_budget")))
        requested_by_cluster: dict[str, float] = {}
        for context in clusters:
            if not isinstance(context, dict):
                continue
            cluster = context.get("cluster")
            name = (
                str(cluster.get("cluster_id") or cluster.get("representative_location"))
                if isinstance(cluster, dict)
                else "Location cluster"
            )
            proposals = context.get("proposals")
            if not isinstance(proposals, list):
                proposals = []
            requested_by_cluster[name] = round(
                sum(_number(item.get("requested_amount")) for item in proposals if isinstance(item, dict)),
                2,
            )
        total_requested = round(sum(requested_by_cluster.values()), 2)
        factor = budget / total_requested if total_requested > budget and total_requested else 1.0
        adjustments = {
            name: round(amount * factor, 2)
            for name, amount in requested_by_cluster.items()
        }
        return json.dumps(
            {
                "total_requested": total_requested,
                "total_available": budget,
                "shortfall_or_surplus": round(budget - total_requested, 2),
                "suggested_adjustment_per_cluster": adjustments,
                "justification": (
                    f"The proposals request INR {total_requested:.2f} crore against "
                    f"an available INR {budget:.2f} crore. "
                    + (
                        "Amounts were reduced proportionally to fit the budget."
                        if total_requested > budget
                        else "The requests fit within the stated budget."
                    )
                ),
            },
            ensure_ascii=False,
        )

    if "regional equity agent" in prompt:
        name, cluster = _cluster_context(input_data)
        equity_context = input_data.get("equity_context")
        if not isinstance(equity_context, dict):
            equity_context = {}
        income = str(equity_context.get("income_level", "")).lower()
        infra_score = equity_context.get("infra_score", equity_context.get("existing_infra_score"))
        demand = _number(cluster.get("complaint_count"))
        urgency = _number(cluster.get("avg_urgency_score"))
        evidence_pct = _number(cluster.get("evidence_verified_pct"))
        category_mix = cluster.get("category_breakdown")
        healthcare_count = (
            _number(category_mix.get("Healthcare"))
            if isinstance(category_mix, dict)
            else 0.0
        )
        context_available = bool(equity_context.get("available"))
        if context_available:
            income_need = {"low": 9.0, "medium": 6.0, "high": 3.0}.get(income, 5.0)
            infrastructure_need = 10.0 - _number(infra_score, 5.0)
            score = max(1.0, min(10.0, round((income_need + infrastructure_need + urgency) / 3, 1)))
        else:
            score = max(1.0, min(10.0, round(urgency * 0.55 + demand / 10 + healthcare_count / 5 + evidence_pct / 100, 1)))
        conflict = (
            "Equity priority uses the supplied socioeconomic context and may exceed raw demand."
            if context_available and score >= 7 and demand < 10
            else "Socioeconomic data is unavailable; equity priority is an approximate demand-and-category signal."
            if not context_available
            else "No material conflict is visible from the supplied indicators."
        )
        return json.dumps(
            {
                "cluster": name,
                "equity_priority_score": score,
                "justification": (
                    f"The location has {int(demand)} complaints, average urgency {urgency:.1f}/10, "
                    f"and {evidence_pct:.1f}% evidence coverage. "
                    + (
                        f"Supplied income level is '{income or 'not specified'}' and infrastructure score is "
                        f"{_number(infra_score, 5.0):.1f}/10."
                        if context_available
                        else "Socioeconomic data is unavailable for this location, so complaint density, category mix, and evidence patterns are being used as a weaker approximate substitute."
                    )
                ),
                "conflict_with_other_agents": conflict,
            },
            ensure_ascii=False,
        )

    if "final arbiter agent" in prompt:
        clusters = input_data.get("clusters")
        if not isinstance(clusters, list):
            clusters = []
        budget = max(0.0, _number(input_data.get("total_budget")))
        weights: list[tuple[str, float]] = []
        for context in clusters:
            if not isinstance(context, dict):
                continue
            cluster = context.get("cluster")
            if not isinstance(cluster, dict):
                cluster = {}
            name = str(cluster.get("cluster_id") or cluster.get("representative_location", "Location cluster"))
            weight = max(1.0, _number(cluster.get("complaint_count"))) * max(
                1.0, _number(cluster.get("avg_urgency_score"))
            )
            equity_context = context.get("equity_context")
            if isinstance(equity_context, dict) and str(equity_context.get("income_level", "")).lower() == "low":
                weight *= 1.15
            weights.append((name, weight))
        total_weight = sum(weight for _, weight in weights)
        allocations: dict[str, float] = {}
        allocated = 0.0
        for index, (name, weight) in enumerate(weights):
            amount = budget - allocated if index == len(weights) - 1 else round(budget * weight / total_weight, 2)
            allocations[name] = max(0.0, round(amount, 2))
            allocated += allocations[name]
        cluster_names = ", ".join(allocations) or "the selected clusters"
        return json.dumps(
            {
                "allocations": allocations,
                "confidence_score": 65.0,
                "explanation": (
                    f"Citizen Advocate demand signals and Evidence severity were balanced across {cluster_names}. "
                    "Finance constrained the recommendation to the stated total budget. "
                    "Equity increased attention to clusters with supplied socioeconomic need; unavailable socioeconomic data was treated as a weaker signal. "
                    "This is a recommendation for human policymakers, not a final spending decision."
                ),
            },
            ensure_ascii=False,
        )

    raise RuntimeError("No local fallback is defined for this agent prompt.")


def _should_use_fallback(error: Exception) -> bool:
    """Return whether an Anthropic failure is suitable for local demo fallback."""

    message = str(error).lower()
    return any(
        marker in message
        for marker in ("credit balance", "rate limit", "overloaded", "timeout", "connection")
    )


async def run_claude(
    system_prompt: str,
    input_data: dict[str, Any],
    max_tokens: int = 1024,
) -> str:
    """Call Claude, or return a schema-compatible local report when configured."""

    if not ANTHROPIC_API_KEY:
        if ENABLE_LOCAL_AGENT_FALLBACK:
            logger.warning("Using local agent fallback because no Anthropic API key is configured.")
            return _local_agent_response(system_prompt, input_data)
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        try:
            response = await client.messages.create(
                model=MODEL_NAME,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(input_data, ensure_ascii=False),
                    }
                ],
            )
        except Exception as exc:
            if ENABLE_LOCAL_AGENT_FALLBACK and _should_use_fallback(exc):
                logger.warning("Using local agent fallback because Claude was unavailable: %s", exc)
                return _local_agent_response(system_prompt, input_data)
            raise

        text_blocks = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        response_text = "".join(text_blocks).strip()
        if not response_text:
            raise RuntimeError("Claude returned an empty agent response.")
        return response_text
    finally:
        await client.close()
