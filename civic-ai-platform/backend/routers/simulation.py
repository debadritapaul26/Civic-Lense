"""Simulation orchestration endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..models.db_models import Simulation
    from ..models.schemas import SimulationRequest
    from ..services.orchestrator import run_simulation
except ImportError:
    from database import get_db
    from models.db_models import Simulation
    from models.schemas import SimulationRequest
    from services.orchestrator import run_simulation


router = APIRouter(tags=["simulation"])


def _simulation_to_dict(simulation: Simulation) -> dict[str, Any]:
    """Convert a Simulation ORM object into a JSON response."""

    return {
        "id": simulation.id,
        "total_budget": simulation.total_budget,
        "citizen_advocate": simulation.citizen_agent_output,
        "evidence_agent": simulation.evidence_agent_output,
        "finance_agent": simulation.finance_agent_output,
        "equity_agent": simulation.equity_agent_output,
        "arbiter": simulation.arbiter_output,
        "status": simulation.status,
        "created_at": simulation.created_at,
    }


@router.post("/simulate")
async def simulate(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run a multi-agent simulation for selected or all location clusters."""

    return await run_simulation(
        db=db,
        cluster_ids=payload.cluster_ids,
        total_budget=payload.total_budget,
        equity_context=payload.equity_context,
    )


@router.get("/simulate")
def list_simulations(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return recent simulation summaries for the history screen."""

    simulations = db.scalars(
        select(Simulation)
        .order_by(Simulation.created_at.desc(), Simulation.id.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": simulation.id,
            "total_budget": simulation.total_budget,
            "status": simulation.status,
            "created_at": simulation.created_at,
        }
        for simulation in simulations
    ]


@router.get("/simulate/{simulation_id}")
def get_simulation(
    simulation_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return a previously persisted simulation by ID."""

    simulation = db.get(Simulation, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")
    return _simulation_to_dict(simulation)
