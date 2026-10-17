"""Fotografías: create de metadatos en ecological.multimedia."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.Multimedia import Multimedia
from models.Occurrence import Occurrence
from schemas.multimedia_schema import MultimediaInput, MultimediaResponse

router = APIRouter(prefix="/multimedia", tags=["multimedia"])

ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


@router.post("", response_model=MultimediaResponse, status_code=status.HTTP_201_CREATED)
def create_multimedia(
    body: MultimediaInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Registra los metadatos de una fotografía asociada a una ocurrencia."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para registrar fotografías")

    if not db.get(Occurrence, body.occurrence_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La ocurrencia indicada no existe")

    # UNIQUE (occurrence_id, photo_type, file_name)
    duplicada = db.scalar(
        select(Multimedia).where(
            Multimedia.occurrence_id == body.occurrence_id,
            Multimedia.photo_type == body.photo_type,
            Multimedia.file_name == body.file_name,
        )
    )
    if duplicada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esa ocurrencia ya tiene una foto con ese tipo y nombre de archivo",
        )

    # UNIQUE (sha256_hash): la misma foto no se registra dos veces, aunque cambie de nombre
    if body.sha256_hash:
        mismo_hash = db.scalar(select(Multimedia).where(Multimedia.sha256_hash == body.sha256_hash.lower()))
        if mismo_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El archivo ya está registrado (coincidencia SHA-256)",
            )

    nueva = Multimedia(
        media_id=uuid.uuid4(),
        occurrence_id=body.occurrence_id,
        photo_type=body.photo_type,
        file_name=body.file_name,
        file_path=body.file_path,
        source_url=body.source_url,
        sha256_hash=body.sha256_hash.lower() if body.sha256_hash else None,
        media_type=body.media_type,
        mime_format=body.mime_format,
        captured_with=body.captured_with,
        photographer=body.photographer,
        capture_date=body.capture_date,
        width_px=body.width_px,
        height_px=body.height_px,
        license=body.license,
        rights_holder=body.rights_holder,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva