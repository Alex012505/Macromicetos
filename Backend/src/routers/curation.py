"""Curaduría polimórfica: decisiones de revisión y lectura del audit log."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text, func, select
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.CurationDecision import CurationDecision

from models.Location import Location
from models.Event import Event
from models.Occurrence import Occurrence
from models.Multimedia import Multimedia
from models.MeasurementOrFact import MeasurementOrFact
from models.MorphologyFact import MorphologyFact
from models.TaxonRef import TaxonRef
from schemas.curation_schema import (
    CurationDecisionInput, CurationDecisionResponse, CurrentStatusItem, AuditLogItem,
    EntityType,
)

router = APIRouter(prefix="/curations", tags=["curations"])

# Mapa de polimorfismo: modelo SQLAlchemy y nombre de su PK.
# Al agregar capa 2/3: una línea aquí, una en el ENUM (SQL) y en el Literal (schema).
ENTITY_MAP: dict[str, tuple[type, str]] = {
    "taxon_ref": (TaxonRef, "taxon_id"),
    "location": (Location, "location_id"),
    "event": (Event, "event_id"),
    "occurrence": (Occurrence, "occurrence_id"),
    "multimedia": (Multimedia, "media_id"),
    "measurement_or_fact": (MeasurementOrFact, "measurement_id"),
    "morphology_fact": (MorphologyFact, "morphology_id"),
    "user_web": (UserWeb, "user_web_id"),
}

ROLES_DECIDIR = {"admin", "curator"}

def _modelo(entity_type: str):
    """Devuelve (Modelo, campo_pk) o lanza 422 si el tipo no existe en el mapa."""
    if entity_type not in ENTITY_MAP:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Entidad no curable: {entity_type}")
    return ENTITY_MAP[entity_type]



@router.post("", response_model=CurationDecisionResponse, status_code=status.HTTP_201_CREATED)
def create_curation_decision(
    body: CurationDecisionInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Registra una decisión de curaduría sobre cualquier entidad curable."""
    if usuario.role not in ROLES_DECIDIR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo curador o administrador")

    Modelo, _ = _modelo(body.entity_type)

    if not db.get(Modelo, body.entity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"La entidad {body.entity_type} {body.entity_id} no existe")

    # estado previo = última decisión registrada para esa entidad
    previa = db.scalar(
        select(CurationDecision.new_status)
        .where(CurationDecision.entity_type == body.entity_type,
               CurationDecision.entity_id == body.entity_id)
        .order_by(CurationDecision.created_at.desc())
        .limit(1)
    )

    decision = CurationDecision(
        decision_id=uuid.uuid4(),
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        decided_by=usuario.user_web_id,
        previous_status=previa,
        new_status=body.new_status,
        comment=body.comment,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@router.get("", response_model=list[CurationDecisionResponse])
def list_decisions(
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
    entity_type: Optional[EntityType] = Query(None),
    entity_id: Optional[uuid.UUID] = Query(None),
    current_status: Optional[str] = Query(None, alias="status"),
    decided_by: Optional[uuid.UUID] = Query(None),
):
    """Historial de decisiones (más reciente primero), filtrable."""
    stmt = select(CurationDecision).order_by(CurationDecision.created_at.desc())

    if entity_type:
        stmt = stmt.where(CurationDecision.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(CurationDecision.entity_id == entity_id)
    if current_status:
        stmt = stmt.where(CurationDecision.new_status == current_status)
    if decided_by:
        stmt = stmt.where(CurationDecision.decided_by == decided_by)

    return db.scalars(stmt).all()


@router.get("/current", response_model=list[CurrentStatusItem])
def list_current_status(
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
    entity_type: Optional[EntityType] = Query(None),
    current_status: Optional[str] = Query(None, alias="status"),
):
    """Estado vigente por entidad (lee la vista curaduria.current_status)."""
    sql = "SELECT * FROM curaduria.current_status"
    filtros, params = [], {}
    if entity_type:
        filtros.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    if current_status:
        filtros.append("current_status = :current_status")
        params["current_status"] = current_status
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    sql += " ORDER BY last_decision_at DESC"

    filas = db.execute(text(sql), params).mappings().all()
    return [CurrentStatusItem(**f) for f in filas]











