"""Observaciones: create en ecological.occurrence."""
import uuid
import datetime as dt

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status,Query
from sqlalchemy import func,select
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.Event import Event
from models.Location import Location
from models.Occurrence import Occurrence
from models.TaxonRef import TaxonRef
from schemas.occurrence_schema import OccurrenceInput, OccurrenceResponse, OccurrenceMapItem



router = APIRouter(prefix="/occurrences", tags=["occurrences"])

ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


@router.post("", response_model=OccurrenceResponse, status_code=status.HTTP_201_CREATED)
def create_occurrence(
    body: OccurrenceInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Crea una observación individual dentro de un evento existente."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para crear ocurrencias")

    if not db.get(Event, body.event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El evento indicado no existe")

    if body.taxon_id and not db.get(TaxonRef, body.taxon_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El taxón indicado no existe")

    if body.external_occurrence_id:
        duplicada = db.scalar(
            select(Occurrence).where(Occurrence.external_occurrence_id == body.external_occurrence_id)
        )
        if duplicada:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una ocurrencia con ese ID externo")

    nueva = Occurrence(
        occurrence_id=uuid.uuid4(),
        event_id=body.event_id,
        taxon_id=body.taxon_id,
        external_occurrence_id=body.external_occurrence_id,
        basis_of_record=body.basis_of_record,
        recorded_by=body.recorded_by,
        event_date=body.event_date,
        occurrence_status=body.occurrence_status,
        individual_count=body.individual_count,
        occurrence_remarks=body.occurrence_remarks,
        verbatim_scientific_name=body.verbatim_scientific_name,
        identification_qualifier=body.identification_qualifier,
        identified_by=body.identified_by,
        date_identified=body.date_identified,
        substrate=body.substrate,
        associated_organisms=body.associated_organisms,
        associated_references=body.associated_references,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.get("/map", response_model=list[OccurrenceMapItem])
def get_occurrence_map(
    
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
    state_province: Optional[str] = Query(None, description="Departamento"),
    family: Optional[str] = Query(None, description="Familia del taxón"),
    date_from: Optional[dt.date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    date_to: Optional[dt.date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    
    ):
    """Puntos para el mapa: ocurrencia + sitio + taxón, en una sola fila."""
    stmt = (
        select(Occurrence, Location, TaxonRef.scientific_name)
        .join(Event, Occurrence.event_id == Event.event_id)
        .join(Location, Event.location_id == Location.location_id)
        # LEFT JOIN: el taxón es nullable y el frontend pinta 'Sin identificar'
        .outerjoin(TaxonRef, Occurrence.taxon_id == TaxonRef.taxon_id)
    )

    if state_province:
        stmt = stmt.where(func.lower(Location.state_province) == state_province.lower())
    if family:
        stmt = stmt.where(func.lower(TaxonRef.family) == family.lower())
    if date_from:
        stmt = stmt.where(Event.event_date >= date_from)
    if date_to:
        stmt = stmt.where(Event.event_date <= date_to)

    filas = db.execute(stmt).all()
    return [
        OccurrenceMapItem(
            occurrence_id=occ.occurrence_id,
            event_id=occ.event_id,
            taxon_id=occ.taxon_id,
            decimal_latitude=float(loc.decimal_latitude) if loc.decimal_latitude is not None else None,
            decimal_longitude=float(loc.decimal_longitude) if loc.decimal_longitude is not None else None,
            locality=loc.locality,
            scientific_name=sci,
        )
        for occ, loc, sci in filas
    ]




    