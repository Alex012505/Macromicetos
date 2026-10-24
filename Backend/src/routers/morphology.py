"""Morfología: create en ecological.morphology_fact."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.MorphologyFact import MorphologyFact
from models.Occurrence import Occurrence
from models.TaxonRef import TaxonRef
from schemas.morphology_schema import MorphologyInput, MorphologyResponse

router = APIRouter(prefix="/morphology", tags=["morphology"])

ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


@router.post("", response_model=MorphologyResponse, status_code=status.HTTP_201_CREATED)
def create_morphology(
    body: MorphologyInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Registra una característica morfológica de un taxón (descripción
    general) o de un espécimen concreto (medida en campo). Existentemente
    mutuamente útiles: mandar ambos anclajes también funciona, pero decide
    aquí si queréis prohibirlo con un 422."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para registrar morfología")

    # FK existentes (los índices parciales dependen del anclaje correcto)
    if body.taxon_id and not db.get(TaxonRef, body.taxon_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El taxón indicado no existe")
    if body.occurrence_id and not db.get(Occurrence, body.occurrence_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La ocurrencia indicada no existe")

    # Índice parcial uq_morphology_occurrence: una medida por individuo
    if body.occurrence_id:
        duplicado = db.scalar(
            select(MorphologyFact).where(
                MorphologyFact.occurrence_id == body.occurrence_id,
                MorphologyFact.measurement_type == body.measurement_type,
                MorphologyFact.occurrence_id.is_not(None),
            )
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La ocurrencia ya registra '{body.measurement_type}'",
            )

    # Índice parcial uq_morphology_taxon: una característica por especie
    if body.taxon_id:
        duplicado = db.scalar(
            select(MorphologyFact).where(
                MorphologyFact.taxon_id == body.taxon_id,
                MorphologyFact.measurement_type == body.measurement_type,
                MorphologyFact.taxon_id.is_not(None),
            )
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El taxón ya registra '{body.measurement_type}'",
            )

    nueva = MorphologyFact(
        morphology_id=uuid.uuid4(),
        taxon_id=body.taxon_id,
        occurrence_id=body.occurrence_id,
        measurement_type=body.measurement_type,
        measurement_value=body.measurement_value,
        measurement_unit=body.measurement_unit,
        measurement_determined_date=body.measurement_determined_date,
        measurement_remarks=body.measurement_remarks,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva