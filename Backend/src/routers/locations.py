"""Sitios de campo: create en ecological.location."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.Location import Location
from schemas.location_schema import LocationInput, LocationResponse

router = APIRouter(prefix="/locations", tags=["locations"])

ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    body: LocationInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Crea un sitio de campo. La BD aplica UNIQUE (locality, municipality, state_province)."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para crear sitios")

    # Ojo: la BD tiene UNIQUE (locality, municipality, state_province); si alguna
    # de las tres es NULL, Postgres no bloquea duplicados ahí — lo hacemos acá.
    existe = db.scalar(
        select(Location).where(
            func.coalesce(Location.locality, "") == (body.locality or ""),
            func.coalesce(Location.municipality, "") == (body.municipality or ""),
            func.coalesce(Location.state_province, "") == (body.state_province or ""),
        )
    )
    if existe:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El sitio ya está registrado")

    nueva = Location(
        location_id=uuid.uuid4(),
        state_province=body.state_province,
        municipality=body.municipality,
        locality=body.locality,
        decimal_latitude=body.decimal_latitude,
        decimal_longitude=body.decimal_longitude,
        coordinate_uncertainty_m=body.coordinate_uncertainty_m,
        elevation_m=body.elevation_m,
        habitat=body.habitat,
        location_remarks=body.location_remarks,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva