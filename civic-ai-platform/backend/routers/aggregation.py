"""Legacy district statistics and dynamic cluster proposal endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..models.db_models import District, Proposal
    from ..models.schemas import ProposalCreateRequest
    from ..services.aggregation_service import (
        compute_all_district_stats,
        compute_district_stats,
    )
    from ..services.location_cluster_service import get_cluster_by_id
except ImportError:
    from database import get_db
    from models.db_models import District, Proposal
    from models.schemas import ProposalCreateRequest
    from services.aggregation_service import (
        compute_all_district_stats,
        compute_district_stats,
    )
    from services.location_cluster_service import get_cluster_by_id


router = APIRouter(tags=["aggregation"])


def _proposal_to_dict(proposal: Proposal) -> dict[str, Any]:
    """Convert a Proposal ORM object into a JSON-serializable response."""

    return {
        "id": proposal.id,
        "cluster_id": proposal.cluster_id,
        "project_name": proposal.project_name,
        "requested_amount": proposal.requested_amount,
    }

# Deprecated for complaint location selection; retained for the legacy
# district dashboard and rollback compatibility. Use /api/clusters for
# map-pin-based aggregation instead.
@router.get("/districts/stats")
def get_all_district_stats(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Return legacy district statistics; complaint selection is map-based."""

    return compute_all_district_stats(db)


# Deprecated district endpoint; use /api/clusters for map-pin aggregation.
@router.get("/districts/{district_id}/stats")
def get_district_stats(
    district_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return legacy district statistics; prefer the /api/clusters endpoint."""

    try:
        return compute_district_stats(db, district_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/clusters/{cluster_id}/proposals", status_code=201)
def create_proposal(
    cluster_id: str,
    payload: ProposalCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a funding proposal for an existing computed location cluster."""

    try:
        get_cluster_by_id(db, cluster_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    proposal = Proposal(
        cluster_id=cluster_id,
        project_name=payload.project_name,
        requested_amount=payload.requested_amount,
    )
    db.add(proposal)
    try:
        db.commit()
        db.refresh(proposal)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the proposal.",
        ) from exc

    return _proposal_to_dict(proposal)


@router.get("/clusters/{cluster_id}/proposals")
def get_cluster_proposals(
    cluster_id: str,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all funding proposals for one computed location cluster."""

    proposals = db.scalars(
        select(Proposal)
        .where(Proposal.cluster_id == cluster_id)
        .order_by(Proposal.id)
    ).all()
    return [_proposal_to_dict(proposal) for proposal in proposals]
