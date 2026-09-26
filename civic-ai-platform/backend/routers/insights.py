"""Insight endpoints built from persisted complaint evidence."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..services.urgency_ranking_service import get_top_urgency_locations
except ImportError:
    from database import get_db
    from services.urgency_ranking_service import get_top_urgency_locations


router = APIRouter(tags=["insights"])


@router.get("/insights/top-urgency-locations")
def get_top_urgency_location_insights(
    top_n: int = Query(default=3, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return the top evidence-backed urgency hotspots."""

    return get_top_urgency_locations(db, top_n=top_n)
