"""Validated output schemas and response parsing for all five AI agents."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Literal, Type

from pydantic import BaseModel, Field, ValidationError


class CitizenAdvocateOutput(BaseModel):
    """Expected structured output from the cluster-level Citizen Advocate."""

    cluster: str
    priority_score: float = Field(..., ge=1, le=10)
    justification: str
    key_stats_cited: str


class EvidenceAgentOutput(BaseModel):
    """Expected structured output from the cluster-level Evidence Agent."""

    cluster_or_complaint_id: str
    severity_score: float = Field(..., ge=0, le=10)
    confidence_percent: float = Field(..., ge=0, le=100)
    justification: str
    mismatch_flag: bool


class FinanceAgentOutput(BaseModel):
    """Expected structured output from the cluster-level Finance Agent."""

    total_requested: float
    total_available: float
    shortfall_or_surplus: float
    suggested_adjustment_per_cluster: Dict[str, Any]
    justification: str


class EquityAgentOutput(BaseModel):
    """Expected structured output from the cluster-level Regional Equity Agent."""

    cluster: str
    equity_priority_score: float = Field(..., ge=1, le=10)
    justification: str
    conflict_with_other_agents: str | None = None


class ArbiterOutput(BaseModel):
    """Expected output from the Final Arbiter, keyed by cluster ID or location."""

    allocations: Dict[str, float] = Field(
        ...,
        description="Budget allocations keyed by cluster_id or representative location.",
    )
    confidence_score: float = Field(..., ge=0, le=100)
    explanation: str


class NLUOutput(BaseModel):
    """Structured complaint interpretation returned by the NLU Agent."""

    language: str
    problem: str
    category: Literal["Road", "Water", "Healthcare", "Electricity", "Garbage", "Public Transport", "Safety", "Drainage", "Other"]
    urgency: float = Field(..., ge=0, le=10)
    location_hint: str


class AgentOutputParseError(ValueError):
    """Raised when an agent response cannot be parsed or schema-validated."""


_CODE_FENCE_RE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    flags=re.IGNORECASE | re.DOTALL,
)


def _remove_code_fences(raw_text: str) -> str:
    """Remove an optional Markdown JSON code fence from an agent response."""

    match = _CODE_FENCE_RE.search(raw_text)
    if match:
        return match.group(1).strip()

    without_opening_fence = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        raw_text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s*```\s*$", "", without_opening_fence).strip()


def _extract_json_object(cleaned_text: str) -> str:
    """Extract the first complete JSON object from surrounding agent text."""

    decoder = json.JSONDecoder()
    last_error: json.JSONDecodeError | None = None

    for start, character in enumerate(cleaned_text):
        if character != "{":
            continue
        try:
            _, end = decoder.raw_decode(cleaned_text[start:])
            return cleaned_text[start : start + end]
        except json.JSONDecodeError as error:
            last_error = error

    if last_error is not None:
        raise last_error
    raise json.JSONDecodeError(
        "No JSON object found",
        cleaned_text,
        0,
    )


def _validate_with_schema(
    payload: Any,
    schema: Type[BaseModel],
) -> BaseModel:
    """Validate a decoded JSON payload using Pydantic v1 or v2 APIs."""

    if hasattr(schema, "model_validate"):
        return schema.model_validate(payload)  # type: ignore[attr-defined]
    return schema.parse_obj(payload)


def parse_agent_response(
    raw_text: str,
    schema: Type[BaseModel],
) -> BaseModel:
    """Clean, decode, and validate one LLM response against a Pydantic schema.

    The helper tolerates Markdown JSON fences and explanatory text surrounding
    the JSON object. It raises AgentOutputParseError with a useful message for
    malformed JSON, unsupported input, or Pydantic validation failures.
    """

    if not isinstance(raw_text, str):
        raise AgentOutputParseError("Agent response must be a string.")
    if not isinstance(schema, type) or not issubclass(schema, BaseModel):
        raise AgentOutputParseError(
            "schema must be a Pydantic BaseModel subclass."
        )

    try:
        cleaned_text = _remove_code_fences(raw_text)
        json_object = _extract_json_object(cleaned_text)
        payload = json.loads(json_object)
    except json.JSONDecodeError as error:
        raise AgentOutputParseError(
            f"Agent response does not contain valid JSON: {error.msg}."
        ) from error

    try:
        return _validate_with_schema(payload, schema)
    except ValidationError as error:
        raise AgentOutputParseError(
            f"Agent response failed {schema.__name__} validation: {error}."
        ) from error
