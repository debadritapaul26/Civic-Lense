"""Shared map-pin clustering and aggregation for civic complaints."""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from ..models.db_models import Complaint
except ImportError:  # Supports imports when running from the backend directory.
    from models.db_models import Complaint


CLUSTER_RADIUS_METERS = 200
"""Maximum distance between complaints in one location cluster."""

EARTH_RADIUS_METERS = 6_371_000.0


@dataclass
class _LocationCluster:
    """Mutable collection of complaints belonging to one nearby location."""

    complaints: list[Complaint] = field(default_factory=list)


def haversine_distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return the great-circle distance between two coordinates in meters."""

    latitude_a_rad = math.radians(latitude_a)
    latitude_b_rad = math.radians(latitude_b)
    delta_latitude = math.radians(latitude_b - latitude_a)
    delta_longitude = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_a_rad)
        * math.cos(latitude_b_rad)
        * math.sin(delta_longitude / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(
        math.sqrt(min(1.0, max(0.0, haversine)))
    )


def evidence_age_hours(
    uploaded_at: datetime | None,
    now: datetime | None = None,
) -> float | None:
    """Return the age of an evidence upload in hours, if it exists."""

    if uploaded_at is None:
        return None

    comparison_time = now or datetime.now(timezone.utc)
    if uploaded_at.tzinfo is None:
        uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
    if comparison_time.tzinfo is None:
        comparison_time = comparison_time.replace(tzinfo=timezone.utc)
    return max(0.0, (comparison_time - uploaded_at).total_seconds() / 3600)


def _has_valid_coordinates(complaint: Complaint) -> bool:
    """Return whether a complaint contains finite, valid map coordinates."""

    if complaint.latitude is None or complaint.longitude is None:
        return False
    latitude = float(complaint.latitude)
    longitude = float(complaint.longitude)
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def cluster_complaints(
    complaints: Sequence[Complaint],
    radius_meters: float = CLUSTER_RADIUS_METERS,
) -> list[list[Complaint]]:
    """Group all geotagged complaints by proximity, regardless of category.

    A complaint joins the nearest existing cluster when it is within the
    configured radius of any complaint already in that cluster. Legacy rows
    without valid coordinates are excluded because they cannot identify a
    map location.
    """

    clusters: list[_LocationCluster] = []
    for complaint in complaints:
        if not _has_valid_coordinates(complaint):
            continue

        matching_clusters: list[tuple[float, _LocationCluster]] = []
        for cluster in clusters:
            nearest_distance = min(
                haversine_distance_meters(
                    float(complaint.latitude),
                    float(complaint.longitude),
                    float(existing.latitude),
                    float(existing.longitude),
                )
                for existing in cluster.complaints
                if existing.latitude is not None and existing.longitude is not None
            )
            if nearest_distance <= radius_meters:
                matching_clusters.append((nearest_distance, cluster))

        if matching_clusters:
            _, nearest_cluster = min(matching_clusters, key=lambda item: item[0])
            nearest_cluster.complaints.append(complaint)
        else:
            clusters.append(_LocationCluster(complaints=[complaint]))

    return [cluster.complaints for cluster in clusters]


def _most_common_nonempty(values: Sequence[str | None], fallback: str) -> str:
    """Return the most common non-empty trimmed value."""

    cleaned_values = [value.strip() for value in values if value and value.strip()]
    return Counter(cleaned_values).most_common(1)[0][0] if cleaned_values else fallback


def _category_breakdown(complaints: Sequence[Complaint]) -> dict[str, int]:
    """Count complaints by normalized display category."""

    categories = [
        (complaint.category or "Other").strip() or "Other"
        for complaint in complaints
    ]
    return dict(sorted(Counter(categories).items(), key=lambda item: item[0].lower()))


def _stable_cluster_id(latitude: float, longitude: float) -> str:
    """Create a compact deterministic ID from rounded centroid coordinates."""

    coordinate_key = f"{latitude:.4f}:{longitude:.4f}".encode("utf-8")
    digest = hashlib.sha1(coordinate_key).hexdigest()[:12]
    return f"cluster-{digest}"


def _complaint_to_dict(
    complaint: Complaint,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Serialize one complaint for a cluster detail response."""

    return {
        "id": complaint.id,
        "raw_text": complaint.raw_text,
        "language_detected": complaint.language_detected,
        "problem": complaint.problem,
        "category": complaint.category,
        "urgency_score": complaint.urgency_score,
        "location_hint": complaint.location_hint,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "formatted_address": complaint.formatted_address,
        "district_id": complaint.district_id,
        "evidence_file_path": complaint.evidence_file_path,
        "evidence_uploaded_at": (
            complaint.evidence_uploaded_at.isoformat()
            if complaint.evidence_uploaded_at is not None
            else None
        ),
        "evidence_age_hours": evidence_age_hours(
            complaint.evidence_uploaded_at,
            now,
        ),
        "created_at": (
            complaint.created_at.isoformat()
            if complaint.created_at is not None
            else None
        ),
    }


def _summarize_cluster(
    complaints: Sequence[Complaint],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the shared aggregate representation for one cluster."""

    if not complaints:
        raise ValueError("A location cluster must contain at least one complaint.")

    latitude = sum(float(complaint.latitude) for complaint in complaints) / len(complaints)
    longitude = sum(float(complaint.longitude) for complaint in complaints) / len(complaints)
    evidence_ages = [
        age
        for complaint in complaints
        if complaint.evidence_file_path
        for age in [evidence_age_hours(complaint.evidence_uploaded_at, now)]
        if age is not None
    ]
    district_values = [
        complaint.district_id
        for complaint in complaints
        if complaint.district_id is not None
    ]
    district_id = Counter(district_values).most_common(1)[0][0] if district_values else None

    return {
        "cluster_id": _stable_cluster_id(latitude, longitude),
        "representative_location": _most_common_nonempty(
            [complaint.formatted_address for complaint in complaints],
            "the pinned location",
        ),
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "complaint_count": len(complaints),
        "avg_urgency_score": round(
            sum(float(complaint.urgency_score) for complaint in complaints)
            / len(complaints),
            2,
        ),
        "evidence_verified_pct": round(
            sum(bool(complaint.evidence_file_path) for complaint in complaints)
            / len(complaints)
            * 100,
            2,
        ),
        "category_breakdown": _category_breakdown(complaints),
        "most_recent_evidence_age_hours": (
            round(min(evidence_ages), 2) if evidence_ages else None
        ),
        # Kept as compatibility metadata for legacy district-aware consumers.
        "district_id": district_id,
    }


def _load_cluster_complaints(db: Session) -> list[list[Complaint]]:
    """Load all complaints and group the geotagged rows into clusters."""

    complaints = db.scalars(select(Complaint).order_by(Complaint.id)).all()
    return cluster_complaints(complaints)


def get_all_location_clusters(db: Session) -> list[dict[str, Any]]:
    """Return aggregate metrics for every map-pin-based complaint cluster."""

    summaries = [_summarize_cluster(cluster) for cluster in _load_cluster_complaints(db)]
    return sorted(
        summaries,
        key=lambda cluster: (
            -cluster["complaint_count"],
            -cluster["avg_urgency_score"],
            cluster["cluster_id"],
        ),
    )


def get_cluster_by_id(db: Session, cluster_id: str) -> dict[str, Any]:
    """Return one cluster's aggregate metrics and its individual complaints.

    Raises:
        LookupError: If ``cluster_id`` does not identify a current cluster.
    """

    now = datetime.now(timezone.utc)
    for complaints in _load_cluster_complaints(db):
        summary = _summarize_cluster(complaints, now=now)
        if summary["cluster_id"] == cluster_id:
            summary["complaints"] = [
                _complaint_to_dict(complaint, now=now)
                for complaint in complaints
            ]
            return summary

    raise LookupError(f"Location cluster '{cluster_id}' was not found.")
