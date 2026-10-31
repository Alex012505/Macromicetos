"""Curation queue and review decisions for occurrences.

The legacy polymorphic router (``routers/curation.py``) keeps the shared
``CurationDecision`` table and schemas. These endpoints expose the same data
under the application contract used by the React client, without the
admin-only ``/legacy`` prefix.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from Security import require_curator
from database.Base import get_db
from models.CurationDecision import CurationDecision
from models.Occurrence import Occurrence
from models.TaxonRef import TaxonRef
from models.UserWeb import UserWeb
from routers.application.common import find, mutation
from schemas.curation_schema import QueueStatus, ReviewInput
from services.application import audit, complete, current_decision

router = APIRouter(tags=["curation"])

# Estados técnicos que el aplicativo presenta como «en revisión».
PENDING_STATUSES = ("draft", "submitted", "in_review")
REJECTED_STATUSES = ("needs_adjustment", "rejected")


def bucket(decision: CurationDecision | None) -> QueueStatus:
    """Translate the latest technical status into a queue tab."""
    status = decision.new_status if decision else "submitted"
    if status == "verified":
        return "verified"
    if status in REJECTED_STATUSES:
        return "rejected"
    return "pending"


def reviewable(decision: CurationDecision | None) -> bool:
    """Only an observation still awaiting a curator decision can be reviewed."""
    return decision is None or decision.new_status in PENDING_STATUSES


def history(db: Session, occurrence_id: uuid.UUID) -> list[CurationDecision]:
    return list(db.scalars(select(CurationDecision).where(
        CurationDecision.entity_type == "occurrence",
        CurationDecision.entity_id == occurrence_id,
    ).order_by(CurationDecision.created_at.desc(), CurationDecision.decision_id.desc())).all())


def decision_data(decision: CurationDecision | None) -> dict:
    return {
        "decision_id": str(decision.decision_id) if decision else None,
        "decision_status": decision.new_status if decision else "submitted",
        "review_note": decision.comment if decision else None,
        "decided_by": str(decision.decided_by) if decision and decision.decided_by else None,
        "decided_at": decision.created_at if decision else None,
        "editable": reviewable(decision),
    }


def history_data(decision: CurationDecision) -> dict:
    return {
        "decision_id": str(decision.decision_id),
        "decision_status": decision.new_status,
        "previous_status": decision.previous_status,
        "review_note": decision.comment,
        "decided_by": str(decision.decided_by) if decision.decided_by else None,
        "decided_at": decision.created_at,
    }


@router.get("/curation/queue")
def queue(request: Request, status: QueueStatus = Query("pending"),
          search: str = Query("", max_length=200), limit: int = Query(50, ge=1, le=200),
          offset: int = Query(0, ge=0), db: Session = Depends(get_db),
          user: UserWeb = Depends(require_curator)):
    """Observations grouped by their current curation state.

    ``pending`` includes observations never reviewed and those sent back after
    an edit. ``verified`` is read-only. ``rejected`` means the observation was
    returned and is waiting for the researcher's changes.
    """
    names = {taxon.taxon_id: taxon.scientific_name for taxon in db.scalars(select(TaxonRef)).all()}
    items = []
    for row in db.scalars(select(Occurrence).order_by(
            Occurrence.created_at.desc(), Occurrence.occurrence_id)).all():
        decision = current_decision(db, "occurrence", row.occurrence_id)
        if bucket(decision) != status:
            continue
        data = complete(db, "occurrence", row, user, str(request.base_url))
        data.update(decision_data(decision))
        data["scientific_name"] = names.get(row.taxon_id)
        items.append(data)
    if search.strip():
        needle = search.casefold().strip()
        items = [item for item in items if needle in " ".join(str(value) for value in (
            item.get("scientific_name"), item.get("identified_by"), item.get("recorded_by"),
            item.get("event", {}).get("location", {}).get("locality"),
            item.get("event", {}).get("location", {}).get("state_province"),
        ) if value).casefold()]
    return {"total": len(items), "items": items[offset:offset + limit]}


@router.get("/occurrences/{occurrence_id}/curation")
def occurrence_curation(occurrence_id: uuid.UUID, request: Request,
                        db: Session = Depends(get_db), user: UserWeb = Depends(require_curator)):
    """Current review state plus the full decision history for one occurrence."""
    row = find(db, Occurrence, occurrence_id)
    decisions = history(db, occurrence_id)
    data = complete(db, "occurrence", row, user, str(request.base_url))
    current = decisions[0] if decisions else None
    data["curation"] = {**decision_data(current), "history": [history_data(decision) for decision in decisions]}
    return data


@router.patch("/occurrences/{occurrence_id}/curation")
def curate(occurrence_id: uuid.UUID, body: ReviewInput, request: Request,
           db: Session = Depends(get_db), user: UserWeb = Depends(require_curator)):
    """Record a curator decision for an observation that is still pending."""
    row = find(db, Occurrence, occurrence_id)
    decision = current_decision(db, "occurrence", occurrence_id)
    if not reviewable(decision):
        raise HTTPException(409, "Esta observación ya fue revisada y no admite cambios de curaduría.")
    with mutation(db):
        audit(db, "occurrence", row.occurrence_id, user, body.status, body.review_note.strip() or None)
    return complete(db, "occurrence", row, user, str(request.base_url))


@router.patch("/curations/{decision_id}")
def update_decision(decision_id: uuid.UUID, body: ReviewInput, request: Request,
                    db: Session = Depends(get_db), user: UserWeb = Depends(require_curator)):
    """Update the review identified by its curation id.

    The original decision is preserved as audit history; a new decision is
    appended with the new status and comment. Only the latest pending decision
    of an occurrence can be updated.
    """
    decision = find(db, CurationDecision, decision_id)
    if decision.entity_type != "occurrence":
        raise HTTPException(422, "Solo las decisiones sobre observaciones se actualizan desde esta ruta.")
    latest = current_decision(db, decision.entity_type, decision.entity_id)
    if latest is None or latest.decision_id != decision.decision_id:
        raise HTTPException(409, "Esa decisión ya fue reemplazada por una revisión más reciente.")
    if not reviewable(decision):
        raise HTTPException(409, "Esta revisión ya fue resuelta y no admite cambios.")
    row = find(db, Occurrence, decision.entity_id)
    with mutation(db):
        audit(db, "occurrence", row.occurrence_id, user, body.status, body.review_note.strip() or None)
    return complete(db, "occurrence", row, user, str(request.base_url))
