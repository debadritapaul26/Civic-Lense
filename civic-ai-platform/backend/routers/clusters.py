"""API endpoints for map-pin-based complaint clusters."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..services.location_cluster_service import (
        get_all_location_clusters,
        get_cluster_by_id,
    )
except ImportError:  # Supports imports when running from the backend directory.
    from database import get_db
    from services.location_cluster_service import (
        get_all_location_clusters,
        get_cluster_by_id,
    )


router = APIRouter(tags=["clusters"])


@router.get("/clusters")
def list_location_clusters(
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return aggregate metrics for all current map-pin clusters."""

    return get_all_location_clusters(db)


@router.get("/clusters/{cluster_id}")
def get_location_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return one cluster and the individual complaints inside it."""

    try:
        return get_cluster_by_id(db, cluster_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
