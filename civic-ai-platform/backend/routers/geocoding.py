"""Geocoding proxy endpoints backed by OpenStreetMap Nominatim."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/geocode", tags=["geocoding"])
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_TIMEOUT_SECONDS = 8.0
NOMINATIM_HEADERS = {
    "User-Agent": "CivicLens/1.0 (civic-ai-platform geocoding proxy)",
    "Accept": "application/json",
}


class GeocodeResult(BaseModel):
    """The small location payload exposed to the frontend."""

    display_name: str
    latitude: float
    longitude: float


def _simplify_result(item: Any) -> GeocodeResult | None:
    """Convert one Nominatim result into the public response shape."""

    if not isinstance(item, dict):
        return None

    display_name = item.get("display_name")
    raw_latitude = item.get("lat")
    raw_longitude = item.get("lon")
    if not display_name or raw_latitude is None or raw_longitude is None:
        return None

    try:
        latitude = float(raw_latitude)
        longitude = float(raw_longitude)
    except (TypeError, ValueError):
        return None

    return GeocodeResult(
        display_name=str(display_name),
        latitude=latitude,
        longitude=longitude,
    )


@router.get("/search", response_model=list[GeocodeResult])
async def search_locations(
    query: str = Query(..., min_length=2, max_length=200),
) -> list[GeocodeResult]:
    """Search for roads, areas, and addresses through Nominatim."""

    normalized_query = query.strip()
    if len(normalized_query) < 2:
        raise HTTPException(
            status_code=422,
            detail="query must contain at least two non-whitespace characters.",
        )

    try:
        async with httpx.AsyncClient(
            timeout=NOMINATIM_TIMEOUT_SECONDS,
            headers=NOMINATIM_HEADERS,
        ) as client:
            response = await client.get(
                NOMINATIM_SEARCH_URL,
                params={
                    "q": normalized_query,
                    "format": "json",
                    "limit": 5,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The geocoding service timed out. Please try again.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="The geocoding service returned an error.",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not contact the geocoding service.",
        ) from exc

    if not isinstance(payload, list):
        raise HTTPException(
            status_code=502,
            detail="The geocoding service returned an unexpected response.",
        )

    return [
        result
        for item in payload
        if (result := _simplify_result(item)) is not None
    ]
