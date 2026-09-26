"""Pydantic request and response schemas for the API foundation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response returned by the service health endpoint."""

    status: str


class DistrictCreate(BaseModel):
    """Payload for creating a district."""

    name: str
    population: int = Field(..., ge=0)
    income_level: str
    existing_infra_score: float = Field(..., ge=0, le=10)


class ComplaintCreate(BaseModel):
    """Payload for storing a complaint."""

    raw_text: str
    language_detected: str
    category: str
    urgency_score: float = Field(..., ge=0, le=10)
    district_id: Optional[int] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    formatted_address: Optional[str] = None
    evidence_file_path: Optional[str] = None


class ComplaintResponse(BaseModel):
    """Complaint response including evidence recency metadata."""

    id: int
    raw_text: str
    language_detected: str
    problem: Optional[str] = None
    category: str
    urgency_score: float
    location_hint: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None
    district_id: Optional[int] = None
    evidence_file_path: Optional[str] = None
    created_at: datetime
    evidence_uploaded_at: Optional[datetime] = None
    evidence_age_hours: Optional[float] = None


class ProposalCreate(BaseModel):
    """Payload for creating a location-cluster funding proposal."""

    cluster_id: str
    project_name: str
    requested_amount: float = Field(..., ge=0)


class ProposalCreateRequest(BaseModel):
    """Request body for a proposal route scoped to a cluster path parameter."""

    project_name: str
    requested_amount: float = Field(..., ge=0)


class SimulationRequest(BaseModel):
    """Request body for starting a cluster-based multi-agent simulation."""

    cluster_ids: list[str] | None = Field(default=None, min_length=1)
    total_budget: float = Field(..., ge=0)
    equity_context: dict[str, dict[str, Any]] | None = None


class SimulationSummary(BaseModel):
    """Minimal persisted simulation response."""

    id: int
    total_budget: float
    status: str
    created_at: datetime
    agent_outputs: dict[str, Any] = Field(default_factory=dict)
