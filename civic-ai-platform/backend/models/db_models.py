"""SQLAlchemy models for complaints, districts, proposals, and simulations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all application tables."""


class District(Base):
    """A geographic district participating in a policy simulation."""

    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False)
    income_level: Mapped[str] = mapped_column(String(100), nullable=False)
    existing_infra_score: Mapped[float] = mapped_column(Float, nullable=False)

    complaints: Mapped[list["Complaint"]] = relationship(
        back_populates="district",
        cascade="all, delete-orphan",
    )
    stats: Mapped[list["DistrictStats"]] = relationship(
        back_populates="district",
        cascade="all, delete-orphan",
    )


class Complaint(Base):
    """An individual complaint stored for processing and aggregation."""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    language_detected: Mapped[str] = mapped_column(String(50), nullable=False)
    problem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    urgency_score: Mapped[float] = mapped_column(Float, nullable=False)
    location_hint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    formatted_address: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    # Retained only for legacy records and district-level aggregation rollback.
    district_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("districts.id"),
        nullable=True,
        index=True,
    )
    evidence_file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    evidence_uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    district: Mapped[Optional[District]] = relationship(back_populates="complaints")


class DistrictStats(Base):
    """Aggregated complaint and evidence metrics for a district."""

    __tablename__ = "district_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(
        ForeignKey("districts.id"),
        nullable=False,
        index=True,
    )
    complaint_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_urgency: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_verified_pct: Mapped[float] = mapped_column(Float, nullable=False)
    category_breakdown: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    district: Mapped[District] = relationship(back_populates="stats")


class Proposal(Base):
    """A funding proposal associated with a computed location cluster."""

    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cluster_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_amount: Mapped[float] = mapped_column(Float, nullable=False)



class Simulation(Base):
    """Persisted inputs and outputs for one multi-agent policy simulation."""

    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    citizen_agent_output: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    evidence_agent_output: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    finance_agent_output: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    equity_agent_output: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    arbiter_output: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
