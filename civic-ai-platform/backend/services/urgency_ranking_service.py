"""Urgency ranking built on the shared map-pin location clusters."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

try:
    from .location_cluster_service import (
        CLUSTER_RADIUS_METERS,
        cluster_complaints,
        evidence_age_hours,
        haversine_distance_meters,
        get_all_location_clusters,
    )
except ImportError:  # Supports imports when running from the backend directory.
    from services.location_cluster_service import (
        CLUSTER_RADIUS_METERS,
        cluster_complaints,
        evidence_age_hours,
        haversine_distance_meters,
        get_all_location_clusters,
    )


def _primary_category(category_breakdown: dict[str, int]) -> str:
    """Return the most frequently reported category in a cluster."""

    return max(
        category_breakdown.items(),
        key=lambda item: (item[1], item[0]),
    )[0] if category_breakdown else "Other"


def _format_evidence_age(age_hours: float | None) -> str:
    """Format the freshest evidence age for a human-readable explanation."""

    if age_hours is None:
        return "the most recent photo upload time is unavailable"
    if age_hours < 1:
        return "the most recent photo was uploaded less than 1 hour ago"
    if age_hours == 1:
        return "the most recent photo was uploaded 1 hour ago"
    if age_hours.is_integer():
        return f"the most recent photo was uploaded {int(age_hours)} hours ago"
    return f"the most recent photo was uploaded {age_hours:.1f} hours ago"


def _with_urgency_details(cluster: dict[str, Any]) -> dict[str, Any]:
    """Add the legacy urgency endpoint fields to a shared cluster summary."""

    evidence_pct = float(cluster["evidence_verified_pct"])
    urgency = float(cluster["avg_urgency_score"])
    category = _primary_category(cluster["category_breakdown"])
    cluster_with_details = dict(cluster)
    cluster_with_details.update(
        {
            "category": category,
            "representative_latitude": cluster["latitude"],
            "representative_longitude": cluster["longitude"],
            "reasoning": (
                f"{cluster['complaint_count']} complaints reported at "
                f"{cluster['representative_location']} within "
                f"{CLUSTER_RADIUS_METERS}m, average urgency {urgency:.1f}/10, "
                f"{round(evidence_pct)}% evidence-verified, "
                f"{_format_evidence_age(cluster['most_recent_evidence_age_hours'])}."
            ),
            # Keep urgency primary while evidence breaks close ties.
            "_combined_score": urgency + evidence_pct / 10_000,
        }
    )
    return cluster_with_details


def get_top_urgency_locations(
    db: Session,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """Return the highest-urgency clusters from the shared cluster service."""

    if top_n <= 0:
        return []

    summaries = [
        _with_urgency_details(cluster)
        for cluster in get_all_location_clusters(db)
    ]
    summaries.sort(
        key=lambda cluster: (
            -cluster["_combined_score"],
            -cluster["complaint_count"],
            cluster["representative_location"],
        )
    )
    for summary in summaries:
        summary.pop("_combined_score", None)
    return summaries[:top_n]


__all__ = [
    "CLUSTER_RADIUS_METERS",
    "cluster_complaints",
    "evidence_age_hours",
    "get_top_urgency_locations",
    "haversine_distance_meters",
]
