"""Anthropic-backed natural-language understanding for citizen complaints."""

from __future__ import annotations

import json
import logging
import re

from anthropic import AsyncAnthropic

try:
    from ..config import ANTHROPIC_API_KEY, ENABLE_LOCAL_NLU_FALLBACK
except ImportError:  # Supports imports when running from the backend directory.
    from config import ANTHROPIC_API_KEY, ENABLE_LOCAL_NLU_FALLBACK


MODEL_NAME = "claude-sonnet-4-6"
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You convert code-mixed Indian-language citizen complaints into structured JSON.
Detect the language mixture and preserve meaningful details without inventing
facts. Return exactly these fields:

{
  "language": "string, for example Bengali+English",
  "problem": "concise description of the reported problem",
  "category": "one of Road, Water, Healthcare, Electricity, Garbage, Public Transport, Safety, Drainage, Other",
  "urgency": "number from 0 to 10",
  "location_hint": "location mentioned by the citizen, or an empty string"
}

Respond with ONLY valid JSON. Do not include a preamble, explanation,
Markdown, or code fences.
""".strip()


def _local_nlu_response(raw_text: str) -> str:
    """Return a deterministic fallback response for local demos."""

    normalized = raw_text.lower()
    selected_category = re.search(
        r"issue category:\s*(road|water|healthcare|electricity|garbage|public transport|safety|drainage|other)\\b",
        normalized,
    )
    if selected_category:
        category = {
            "public transport": "Public Transport",
        }.get(selected_category.group(1), selected_category.group(1).title())
    elif any(
        keyword in normalized
        for keyword in (
            "hospital", "clinic", "doctor", "medicine", "nurse", "ambulance", "health"
        )
    ):
        category = "Healthcare"
    elif any(keyword in normalized for keyword in ("garbage", "waste", "trash", "rubbish", "overflow")):
        category = "Garbage"
    elif any(keyword in normalized for keyword in ("public transport", "transport", "bus", "metro", "train")):
        category = "Public Transport"
    elif any(keyword in normalized for keyword in ("safety", "unsafe", "security", "harassment", "crime")):
        category = "Safety"
    elif any(keyword in normalized for keyword in ("drainage", "drain", "sewer", "waterlogging")):
        category = "Drainage"
    elif any(
        keyword in normalized
        for keyword in (
            "electricity", "bijli", "current", "transformer", "power", "load shedding",
            "streetlight", "street light", "light pole"
        )
    ):
        category = "Electricity"
    elif any(
        keyword in normalized
        for keyword in (
            "water", "paani", "pani", "jol", "drinking", "flood", "flooding"
        )
    ):
        category = "Water"
    elif any(
        keyword in normalized
        for keyword in ("road", "pothole", "streetlight", "bridge", "gali", "rasta")
    ):
        category = "Road"
    else:
        category = "Other"

    urgency = 5.0
    if any(
        keyword in normalized
        for keyword in ("urgent", "emergency", "dangerous", "accident", "unsafe")
    ):
        urgency = 9.0
    elif any(
        keyword in normalized
        for keyword in ("three days", "3 days", "cannot", "not available", "very bad")
    ):
        urgency = 8.0

    language_parts: list[str] = []
    if re.search(r"[\u0900-\u097f]", raw_text) or any(
        word in normalized.split()
        for word in ("hamare", "paani", "bijli", "gaon", "sarkari")
    ):
        language_parts.append("Hindi")
    if re.search(r"[\u0980-\u09ff]", raw_text) or any(
        word in normalized.split()
        for word in ("amar", "para", "jol", "korun", "brishti")
    ):
        language_parts.append("Bengali")
    if re.search(r"[\u0b80-\u0bff]", raw_text) or any(
        word in normalized.split()
        for word in ("enga", "romba", "pannunga", "irukku", "illai")
    ):
        language_parts.append("Tamil")
    if re.search(r"[a-zA-Z]", raw_text):
        language_parts.append("English")
    if not language_parts:
        language_parts.append("Unknown")

    return json.dumps(
        {
            "language": "+".join(dict.fromkeys(language_parts)),
            "problem": raw_text.strip(),
            "category": category,
            "urgency": urgency,
            "location_hint": "",
        },
        ensure_ascii=False,
    )


async def run(raw_text: str) -> str:
    """Send one raw citizen complaint to Claude and return its raw text response."""

    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text must contain a non-empty complaint.")
    if not ANTHROPIC_API_KEY:
        if ENABLE_LOCAL_NLU_FALLBACK:
            logger.warning("Using local NLU fallback because no Anthropic API key is configured.")
            return _local_nlu_response(raw_text)
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        try:
            response = await client.messages.create(
                model=MODEL_NAME,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": raw_text}],
            )
        except Exception as exc:
            # Local development must remain usable when the provider is
            # unavailable, the key is invalid/expired, the model name changes,
            # or the machine has no outbound network access. Production can
            # disable this behavior with ENABLE_LOCAL_NLU_FALLBACK=false.
            if ENABLE_LOCAL_NLU_FALLBACK:
                logger.warning(
                    "Using local NLU fallback because Claude was unavailable: %s",
                    exc,
                )
                return _local_nlu_response(raw_text)
            raise
        text_blocks = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        response_text = "".join(text_blocks).strip()
        if not response_text:
            raise RuntimeError("Claude returned an empty NLU response.")
        return response_text
    finally:
        await client.close()
