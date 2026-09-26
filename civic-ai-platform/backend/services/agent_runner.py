"""Retry, parse, and normalize wrapper for AI agent calls."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Type

from pydantic import BaseModel

try:
    from ..models.agent_schemas import AgentOutputParseError, parse_agent_response
except ImportError:
    from models.agent_schemas import AgentOutputParseError, parse_agent_response


logger = logging.getLogger(__name__)
AgentFunction = Callable[[dict[str, Any]], Awaitable[str]]


def _model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Convert a Pydantic model to a plain dictionary across Pydantic versions."""

    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()


async def run_agent_with_retry(
    agent_fn: AgentFunction,
    input_data: dict[str, Any],
    schema: Type[BaseModel],
    agent_name: str,
    max_retries: int = 1,
) -> dict[str, Any]:
    """Run an agent, validate its JSON response, and retry parse failures.

    max_retries is the number of attempts after the initial call. Agent
    execution errors are returned immediately; malformed or schema-invalid
    responses are retried up to the configured limit.
    """

    if max_retries < 0:
        raise ValueError("max_retries must be zero or greater.")

    total_attempts = max_retries + 1
    last_parse_error: AgentOutputParseError | None = None

    for attempt in range(1, total_attempts + 1):
        logger.info(
            "Running agent=%s attempt=%d/%d",
            agent_name,
            attempt,
            total_attempts,
        )
        try:
            raw_response = await agent_fn(input_data)
        except Exception as exc:
            logger.exception(
                "Agent=%s raised an exception on attempt=%d",
                agent_name,
                attempt,
            )
            return {
                "agent": agent_name,
                "status": "failed",
                "error": f"Agent call failed: {exc}",
            }

        try:
            validated = parse_agent_response(raw_response, schema)
            logger.info("Agent=%s succeeded on attempt=%d", agent_name, attempt)
            return {
                "agent": agent_name,
                "status": "success",
                "data": _model_to_dict(validated),
            }
        except AgentOutputParseError as exc:
            last_parse_error = exc
            logger.warning(
                "Agent=%s returned invalid output on attempt=%d: %s",
                agent_name,
                attempt,
                exc,
            )

    error_message = (
        str(last_parse_error)
        if last_parse_error is not None
        else "Agent output could not be validated."
    )
    return {
        "agent": agent_name,
        "status": "failed",
        "error": error_message,
    }
