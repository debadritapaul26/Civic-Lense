"""Complaint submission and retrieval endpoints.

Migration note:
District-based location is deprecated in favor of map-pinned coordinates as of
the map-pinned-location upgrade. The District table is retained for
legacy/rollback only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

try:
    from ..agents import nlu_agent
    from ..database import get_db
    from ..models.agent_schemas import (
        AgentOutputParseError,
        NLUOutput,
        parse_agent_response,
    )
    from ..models.db_models import Complaint
    from ..models.schemas import ComplaintResponse
except ImportError:
    from agents import nlu_agent
    from database import get_db
    from models.agent_schemas import (
        AgentOutputParseError,
        NLUOutput,
        parse_agent_response,
    )
    from models.db_models import Complaint
    from models.schemas import ComplaintResponse


router = APIRouter(tags=["complaints"])
BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BACKEND_DIR / "uploads"
UPLOAD_CHUNK_SIZE = 1024 * 1024


def _complaint_to_dict(complaint: Complaint) -> dict[str, object]:
    """Convert a Complaint ORM object into a JSON-serializable response."""

    evidence_age_hours: Optional[float] = None
    if complaint.evidence_uploaded_at is not None:
        uploaded_at = complaint.evidence_uploaded_at
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        evidence_age_hours = max(
            0.0,
            (datetime.now(timezone.utc) - uploaded_at).total_seconds() / 3600,
        )

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
        "created_at": complaint.created_at,
        "evidence_uploaded_at": complaint.evidence_uploaded_at,
        "evidence_age_hours": evidence_age_hours,
    }


async def _save_upload(file: UploadFile) -> tuple[Path, str, datetime]:
    """Save an uploaded file with a generated name and return path metadata."""

    suffix = Path(file.filename or "").suffix.lower()
    if len(suffix) > 20:
        suffix = ""

    destination = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                output.write(chunk)
    except Exception as exc:
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(
            status_code=500,
            detail="Could not save the uploaded evidence file.",
        ) from exc
    finally:
        await file.close()

    relative_path = destination.relative_to(BACKEND_DIR).as_posix()
    return destination, relative_path, datetime.utcnow()


def _remove_saved_file(path: Optional[Path]) -> None:
    """Best-effort cleanup for an upload when complaint creation fails."""

    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


async def _run_nlu_with_retry(raw_text: str) -> NLUOutput:
    """Call the NLU Agent and retry once when its response fails validation."""

    parse_error: Optional[AgentOutputParseError] = None
    for attempt in range(2):
        try:
            raw_response = await nlu_agent.run(raw_text)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="The NLU service could not process the complaint.",
            ) from exc

        try:
            parsed = parse_agent_response(raw_response, NLUOutput)
            return parsed  # type: ignore[return-value]
        except AgentOutputParseError as exc:
            parse_error = exc
            if attempt == 0:
                continue

    raise HTTPException(
        status_code=500,
        detail="The NLU service returned invalid structured output twice.",
    ) from parse_error


@router.post("/complaints", status_code=201)
async def create_complaint(
    text: str = Form(...),
    latitude: Optional[float] = Form(default=None, ge=-90, le=90),
    longitude: Optional[float] = Form(default=None, ge=-180, le=180),
    formatted_address: Optional[str] = Form(default=None, max_length=500),
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Classify, persist, and return one citizen complaint submission."""

    if not text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty.")
    if latitude is None or longitude is None:
        raise HTTPException(
            status_code=400,
            detail="Please search and pin a location.",
        )

    saved_path: Optional[Path] = None
    relative_file_path: Optional[str] = None
    evidence_uploaded_at: Optional[datetime] = None
    try:
        if file is not None:
            saved_path, relative_file_path, evidence_uploaded_at = await _save_upload(file)

        nlu_output = await _run_nlu_with_retry(text)
        complaint = Complaint(
            raw_text=text,
            language_detected=nlu_output.language,
            problem=nlu_output.problem,
            category=nlu_output.category,
            urgency_score=nlu_output.urgency,
            location_hint=nlu_output.location_hint,
            latitude=latitude,
            longitude=longitude,
            formatted_address=formatted_address,
            evidence_file_path=relative_file_path,
            evidence_uploaded_at=evidence_uploaded_at,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        return _complaint_to_dict(complaint)
    except HTTPException:
        db.rollback()
        _remove_saved_file(saved_path)
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        _remove_saved_file(saved_path)
        raise HTTPException(
            status_code=500,
            detail="Could not save the complaint.",
        ) from exc
    except Exception as exc:
        db.rollback()
        _remove_saved_file(saved_path)
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while creating the complaint.",
        ) from exc


@router.post(
    "/complaints/{complaint_id}/evidence",
    response_model=ComplaintResponse,
    status_code=200,
)
async def attach_evidence(
    complaint_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Attach or replace evidence on an existing complaint."""

    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    saved_path: Optional[Path] = None
    try:
        saved_path, relative_file_path, evidence_uploaded_at = await _save_upload(file)
        complaint.evidence_file_path = relative_file_path
        complaint.evidence_uploaded_at = evidence_uploaded_at
        db.commit()
        db.refresh(complaint)
        return _complaint_to_dict(complaint)
    except HTTPException:
        db.rollback()
        _remove_saved_file(saved_path)
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        _remove_saved_file(saved_path)
        raise HTTPException(
            status_code=500,
            detail="Could not attach the evidence file.",
        ) from exc
    except Exception as exc:
        db.rollback()
        _remove_saved_file(saved_path)
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while attaching evidence.",
        ) from exc


@router.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return one complaint with evidence timestamp and age metadata."""

    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return _complaint_to_dict(complaint)


@router.get("/complaints", response_model=list[ComplaintResponse])
def list_complaints(
    district_id: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    """Return complaints, with district filtering retained for legacy data."""

    statement = select(Complaint).order_by(
        Complaint.created_at.desc(),
        Complaint.id.desc(),
    )
    if district_id is not None:
        statement = statement.where(Complaint.district_id == district_id)

    complaints = db.scalars(statement).all()
    return [_complaint_to_dict(complaint) for complaint in complaints]
