"""Coordinator for dynamic location-cluster multi-agent simulations."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Type

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from ..models.agent_schemas import (
        ArbiterOutput,
        CitizenAdvocateOutput,
        EquityAgentOutput,
        EvidenceAgentOutput,
        FinanceAgentOutput,
    )
    from ..models.db_models import Proposal, Simulation
    from ..services.location_cluster_service import (
        get_all_location_clusters,
        get_cluster_by_id,
    )
    from .agent_runner import AgentFunction, run_agent_with_retry
    from .urgency_ranking_service import get_top_urgency_locations
except ImportError:
    from models.agent_schemas import (
        ArbiterOutput,
        CitizenAdvocateOutput,
        EquityAgentOutput,
        EvidenceAgentOutput,
        FinanceAgentOutput,
    )
    from models.db_models import Proposal, Simulation
    from services.location_cluster_service import (
        get_all_location_clusters,
        get_cluster_by_id,
    )
    from services.agent_runner import AgentFunction, run_agent_with_retry
    from services.urgency_ranking_service import get_top_urgency_locations


logger = logging.getLogger(__name__)


def _load_agent_functions() -> tuple[
    AgentFunction,
    AgentFunction,
    AgentFunction,
    AgentFunction,
    AgentFunction,
]:
    """Load the five existing agent run functions without modifying them."""

    try:
        from ..agents import (
            arbiter_agent,
            citizen_advocate,
            equity_agent,
            evidence_agent,
            finance_agent,
        )
    except ImportError:
        from agents import (
            arbiter_agent,
            citizen_advocate,
            equity_agent,
            evidence_agent,
            finance_agent,
        )

    return (
        citizen_advocate.run,
        evidence_agent.run,
        finance_agent.run,
        equity_agent.run,
        arbiter_agent.run,
    )


def _cluster_metadata(cluster: dict[str, Any]) -> dict[str, Any]:
    """Keep only the shared aggregate fields supplied to specialist agents."""

    return {
        "cluster_id": cluster["cluster_id"],
        "representative_location": cluster["representative_location"],
        "latitude": cluster["latitude"],
        "longitude": cluster["longitude"],
        "complaint_count": cluster["complaint_count"],
        "avg_urgency_score": cluster["avg_urgency_score"],
        "evidence_verified_pct": cluster["evidence_verified_pct"],
        "category_breakdown": cluster["category_breakdown"],
        "most_recent_evidence_age_hours": cluster[
            "most_recent_evidence_age_hours"
        ],
    }


def _proposal_data(proposal: Proposal) -> dict[str, Any]:
    """Convert a cluster proposal ORM object into agent-safe JSON data."""

    return {
        "id": proposal.id,
        "cluster_id": proposal.cluster_id,
        "project_name": proposal.project_name,
        "requested_amount": proposal.requested_amount,
    }


def _result_with_cluster(
    cluster_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Attach a dynamic cluster identifier to a specialist result."""

    return {"cluster_id": cluster_id, **result}


async def _run_cluster_agent(
    agent_fn: AgentFunction,
    input_data: dict[str, Any],
    schema: Type[BaseModel],
    agent_name: str,
    cluster_id: str,
) -> dict[str, Any]:
    """Run one per-cluster agent and attach its cluster identifier."""

    result = await run_agent_with_retry(
        agent_fn=agent_fn,
        input_data=input_data,
        schema=schema,
        agent_name=agent_name,
    )
    return _result_with_cluster(cluster_id, result)


def _agent_result_payload(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap per-cluster results for JSON storage and Arbiter input."""

    return {"results": results}


def _unavailable_agent_notes(outputs: dict[str, Any]) -> list[str]:
    """List agent/cluster labels whose data is unavailable."""

    notes: list[str] = []
    for agent_name, output in outputs.items():
        if isinstance(output, dict) and "results" in output:
            for result in output["results"]:
                if result.get("status") != "success":
                    cluster_id = result.get("cluster_id", "unknown")
                    notes.append(f"{agent_name} for cluster {cluster_id}")
        elif isinstance(output, dict) and output.get("status") != "success":
            notes.append(agent_name)
    return notes


def _simulation_status(
    agent_outputs: dict[str, Any],
    arbiter_output: dict[str, Any],
) -> str:
    """Derive complete, partial_failure, or failed simulation status."""

    if arbiter_output.get("status") != "success":
        return "failed"
    if _unavailable_agent_notes(agent_outputs):
        return "partial_failure"
    return "complete"


def _save_simulation(
    db: Session,
    total_budget: float,
    outputs: dict[str, Any],
    status: str,
) -> Simulation:
    """Persist all agent outputs and return the refreshed Simulation row."""

    simulation = Simulation(
        total_budget=total_budget,
        citizen_agent_output=outputs.get("citizen_advocate"),
        evidence_agent_output=outputs.get("evidence_agent"),
        finance_agent_output=outputs.get("finance_agent"),
        equity_agent_output=outputs.get("equity_agent"),
        arbiter_output=outputs.get("arbiter"),
        status=status,
    )
    db.add(simulation)
    db.commit()
    db.refresh(simulation)
    return simulation


def _equity_context_for_cluster(
    cluster_id: str,
    equity_context: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    """Return supplied socioeconomic context or an explicit unavailable note."""

    supplied = (equity_context or {}).get(cluster_id)
    if isinstance(supplied, dict) and (
        supplied.get("income_level") is not None
        or supplied.get("infra_score") is not None
        or supplied.get("existing_infra_score") is not None
    ):
        return {"available": True, **supplied}

    return {
        "available": False,
        "note": (
            "socioeconomic data not available for this location — reason from "
            "complaint density and category mix only"
        ),
    }


async def run_simulation(
    db: Session,
    cluster_ids: list[str] | None = None,
    total_budget: float = 0.0,
    equity_context: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run all five agents for selected or automatically discovered clusters.

    When ``cluster_ids`` is omitted or empty, all current map-based clusters
    are selected. Specialist agents run once per cluster; Finance and Arbiter
    receive the complete selected-cluster context.
    """

    outputs: dict[str, Any] = {
        "citizen_advocate": {"results": []},
        "evidence_agent": {"results": []},
        "finance_agent": None,
        "equity_agent": {"results": []},
        "arbiter": None,
    }
    simulation: Simulation | None = None

    try:
        if total_budget < 0:
            raise ValueError("total_budget cannot be negative.")

        all_clusters = get_all_location_clusters(db)
        clusters_by_id = {
            str(cluster["cluster_id"]): cluster for cluster in all_clusters
        }
        selected_ids = list(dict.fromkeys(cluster_ids or clusters_by_id.keys()))
        if not selected_ids:
            raise ValueError("No location clusters are available for simulation.")

        for selected_id in selected_ids:
            if selected_id not in clusters_by_id:
                raise ValueError(f"Location cluster {selected_id} does not exist.")

        (
            citizen_run,
            evidence_run,
            finance_run,
            equity_run,
            arbiter_run,
        ) = _load_agent_functions()

        top_urgency_locations = get_top_urgency_locations(db)
        contexts: list[dict[str, Any]] = []
        for cluster_id in selected_ids:
            cluster = clusters_by_id[cluster_id]
            detail = get_cluster_by_id(db, cluster_id)
            proposals = db.scalars(
                select(Proposal)
                .where(Proposal.cluster_id == cluster_id)
                .order_by(Proposal.id)
            ).all()
            contexts.append(
                {
                    "cluster": _cluster_metadata(cluster),
                    "complaints": detail["complaints"],
                    "proposals": [_proposal_data(proposal) for proposal in proposals],
                    "equity_context": _equity_context_for_cluster(
                        cluster_id,
                        equity_context,
                    ),
                    "top_urgency_locations": top_urgency_locations,
                    "total_budget": total_budget,
                }
            )

        finance_input = {
            "clusters": contexts,
            "total_budget": total_budget,
        }
        tasks: list[Any] = [
            run_agent_with_retry(
                agent_fn=finance_run,
                input_data=finance_input,
                schema=FinanceAgentOutput,
                agent_name="finance_agent",
            )
        ]
        for context in contexts:
            cluster_id = context["cluster"]["cluster_id"]
            tasks.extend(
                [
                    _run_cluster_agent(
                        citizen_run,
                        context,
                        CitizenAdvocateOutput,
                        "citizen_advocate",
                        cluster_id,
                    ),
                    _run_cluster_agent(
                        evidence_run,
                        context,
                        EvidenceAgentOutput,
                        "evidence_agent",
                        cluster_id,
                    ),
                    _run_cluster_agent(
                        equity_run,
                        context,
                        EquityAgentOutput,
                        "equity_agent",
                        cluster_id,
                    ),
                ]
            )

        gathered_results = await asyncio.gather(*tasks)
        outputs["finance_agent"] = gathered_results[0]

        result_index = 1
        citizen_results: list[dict[str, Any]] = []
        evidence_results: list[dict[str, Any]] = []
        equity_results: list[dict[str, Any]] = []
        for _ in contexts:
            citizen_results.append(gathered_results[result_index])
            evidence_results.append(gathered_results[result_index + 1])
            equity_results.append(gathered_results[result_index + 2])
            result_index += 3

        outputs["citizen_advocate"] = _agent_result_payload(citizen_results)
        outputs["evidence_agent"] = _agent_result_payload(evidence_results)
        outputs["equity_agent"] = _agent_result_payload(equity_results)

        arbiter_input = {
            "total_budget": total_budget,
            "clusters": contexts,
            "citizen_advocate": outputs["citizen_advocate"],
            "evidence_agent": outputs["evidence_agent"],
            "finance_agent": outputs["finance_agent"],
            "equity_agent": outputs["equity_agent"],
            "top_urgency_locations": top_urgency_locations,
            "unavailable_agent_data": _unavailable_agent_notes(outputs),
        }
        arbiter_result = await run_agent_with_retry(
            agent_fn=arbiter_run,
            input_data=arbiter_input,
            schema=ArbiterOutput,
            agent_name="arbiter",
        )
        outputs["arbiter"] = arbiter_result

        status = _simulation_status(outputs, arbiter_result)
        simulation = _save_simulation(db, total_budget, outputs, status)
        return {
            **outputs,
            "simulation_status": status,
            "simulation_id": simulation.id,
        }
    except Exception as exc:
        logger.exception("Simulation failed")
        try:
            db.rollback()
            simulation = _save_simulation(db, total_budget, outputs, "failed")
        except Exception:
            logger.exception("Could not persist failed simulation")
            db.rollback()

        return {
            **outputs,
            "simulation_status": "failed",
            "simulation_id": simulation.id if simulation is not None else None,
            "error": str(exc),
        }
