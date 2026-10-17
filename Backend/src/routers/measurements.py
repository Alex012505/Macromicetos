"""Microclima: create en ecological.measurement_or_fact."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.Event import Event
from models.MeasurementOrFact import MeasurementOrFact
from schemas.measurement_schema import MeasurementInput, MeasurementResponse

router = APIRouter(prefix="/measurements", tags=["measurements"])

ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


@router.post("", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def create_measurement(
    body: MeasurementInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Registra una lectura de microclima para un evento existente."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para registrar mediciones")

    if not db.get(Event, body.event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El evento indicado no existe")

    # La BD impone UNIQUE (event_id, measurement_type): una lectura por variable.
    existe = db.scalar(
        select(MeasurementOrFact).where(
            MeasurementOrFact.event_id == body.event_id,
            MeasurementOrFact.measurement_type == body.measurement_type,
        )
    )
    if existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El evento ya tiene una lectura de {body.measurement_type}",
        )

    nueva = MeasurementOrFact(
        measurement_id=uuid.uuid4(),
        event_id=body.event_id,
        measurement_type=body.measurement_type,
        measurement_value=body.measurement_value,
        measurement_unit=body.measurement_unit,
        measurement_determined_date=body.measurement_determined_date,
        measurement_method=body.measurement_method,
        measurement_remarks=body.measurement_remarks,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva