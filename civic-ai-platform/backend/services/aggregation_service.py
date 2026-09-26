"""Pure-code aggregation of complaint metrics by district."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

try:
    from ..models.db_models import Complaint, District, DistrictStats
except ImportError:
    from models.db_models import Complaint, District, DistrictStats


def compute_district_stats(db: Session, district_id: int) -> dict[str, Any]:
    """Compute and upsert complaint statistics for one district.

    The calculation uses only persisted Complaint fields and performs no AI or
    external-service calls.
    """

    district = db.get(District, district_id)
    if district is None:
        raise ValueError(f"District {district_id} does not exist.")

    complaints = db.scalars(
        select(Complaint)
        .where(Complaint.district_id == district_id)
        .order_by(Complaint.id)
    ).all()

    complaint_count = len(complaints)
    avg_urgency = (
        sum(complaint.urgency_score for complaint in complaints) / complaint_count
        if complaint_count
        else 0.0
    )
    verified_count = sum(
        complaint.evidence_file_path is not None for complaint in complaints
    )
    evidence_verified_pct = (
        verified_count / complaint_count * 100 if complaint_count else 0.0
    )
    category_breakdown = dict(
        sorted(Counter(complaint.category for complaint in complaints).items())
    )
    updated_at = datetime.now(timezone.utc)

    stats_row = db.scalar(
        select(DistrictStats)
        .where(DistrictStats.district_id == district_id)
        .order_by(DistrictStats.id)
        .limit(1)
    )
    if stats_row is None:
        stats_row = DistrictStats(
            district_id=district_id,
            complaint_count=complaint_count,
            avg_urgency=avg_urgency,
            evidence_verified_pct=evidence_verified_pct,
            category_breakdown=category_breakdown,
            updated_at=updated_at,
        )
        db.add(stats_row)
    else:
        stats_row.complaint_count = complaint_count
        stats_row.avg_urgency = avg_urgency
        stats_row.evidence_verified_pct = evidence_verified_pct
        stats_row.category_breakdown = category_breakdown
        stats_row.updated_at = updated_at

    try:
        db.commit()
        db.refresh(stats_row)
    except SQLAlchemyError:
        db.rollback()
        raise

    return {
        "district_id": district_id,
        "district_name": district.name,
        "complaint_count": complaint_count,
        "avg_urgency": avg_urgency,
        "evidence_verified_pct": evidence_verified_pct,
        "category_breakdown": category_breakdown,
    }


def compute_all_district_stats(db: Session) -> list[dict[str, Any]]:
    """Compute and upsert statistics for every district in the database."""

    districts = db.scalars(select(District).order_by(District.id)).all()
    return [compute_district_stats(db, district.id) for district in districts]
