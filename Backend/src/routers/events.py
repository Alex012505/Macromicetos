"""Salidas de campo: create en ecological.event."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select , func
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.Event import Event
from models.Location import Location
from schemas.event_schema import EventInput, EventResponse

router = APIRouter(prefix="/events", tags=["events"])

ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Crea una salida de campo asociada a un sitio existente."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para crear eventos")

    if not db.get(Location, body.location_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La ubicación indicada no existe")

    # La BD impone UNIQUE (location_id, event_date, recorded_by); verificamos
    # con coalesce porque recorded_by es nullable y NULL no dispara el UNIQUE.
    duplicado = db.scalar(
        select(Event).where(
            Event.location_id == body.location_id,
            Event.event_date == body.event_date,
            func.coalesce(Event.recorded_by, "") == (body.recorded_by or ""),
        )
    )
    if duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un evento en ese sitio con esa fecha y observador",
        )

    nuevo = Event(
        event_id=uuid.uuid4(),
        location_id=body.location_id,
        event_type=body.event_type,
        field_number=body.field_number,
        event_date=body.event_date,
        event_time=body.event_time,
        recorded_by=body.recorded_by,
        sampling_protocol=body.sampling_protocol,
        sampling_effort=body.sampling_effort,
        event_remarks=body.event_remarks,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo