"""Fotografías: create de metadatos en ecological.multimedia."""
from typing import Optional
import uuid
import os
from pathlib import Path as FsPath
import hashlib


from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session

from models.Event import Event
from models.Location import Location
from models.Occurrence import Occurrence
from models.TaxonRef import TaxonRef
from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.Multimedia import Multimedia
from models.Occurrence import Occurrence
from schemas.multimedia_schema import MultimediaInput, MultimediaResponse, PhotoArchiveItem

router = APIRouter(prefix="/multimedia", tags=["multimedia"])

ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


UPLOAD_DIR = FsPath(os.getenv("MULTIMEDIA_ROOT", "data/images"))
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 2 * 1024 * 1024      # 2 MB por foto, igual que el frontend


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

@router.get("", response_model=list[PhotoArchiveItem])
def list_photo_archive(
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Especie, nombre común o departamento"),
):
    """Archivo fotográfico: una fila por foto con contexto de observación."""
    stmt = (
        select(
            Multimedia,
            TaxonRef.scientific_name,
            TaxonRef.common_name_es,
            Event.event_date,
            Location.state_province,
            Location.locality,
        )
        .join(Occurrence, Multimedia.occurrence_id == Occurrence.occurrence_id)
        .join(Event, Occurrence.event_id == Event.event_id)
        .join(Location, Event.location_id == Location.location_id)
        .outerjoin(TaxonRef, Occurrence.taxon_id == TaxonRef.taxon_id)
    )

    if search:
        patron = f"%{search.lower()}%"
        stmt = stmt.where(or_(
            func.lower(TaxonRef.scientific_name).like(patron),
            func.lower(TaxonRef.common_name_es).ilike(patron),
            func.lower(Location.state_province).ilike(patron),
        ))

    filas = db.execute(stmt).all()
    return [
        PhotoArchiveItem(
            media_id=m.media_id,
            occurrence_id=m.occurrence_id,
            photo_type=m.photo_type,
            file_name=m.file_name,
            file_path=m.file_path,
            scientific_name=sci,
            common_name_es=common,
            state_province=depto,
            locality=localidad,
            event_date=fecha,
            sha256_hash=m.sha256_hash,
        )
        for m, sci, common, fecha, depto, localidad in filas
    ]


import hashlib
from pathlib import Path as FsPath
from fastapi import File, UploadFile

UPLOAD_DIR = FsPath(os.getenv("MULTIMEDIA_ROOT", "data/images"))  # configurable en .env
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 2 * 1024 * 1024          # 2 MB, igual que el frontend
MAX_FILES = 10

@router.post("/occurrences/{occurrence_id}/photos", response_model=list[MultimediaResponse],
             status_code=status.HTTP_201_CREATED)
async def upload_photos(
    occurrence_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
    files: list[UploadFile] = File(...),
):
    """Sube hasta 10 fotos (2 MB c/u) y crea sus filas de metadatos."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos")

    occ = db.get(Occurrence, occurrence_id)
    if not occ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La ocurrencia no existe")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Máximo 10 fotos por carga")

    creadas = []
    for f in files:
        if f.content_type not in ALLOWED:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                detail=f"Formato no permitido: {f.content_type}")
        contenido = await f.read()
        if len(contenido) > MAX_SIZE:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail=f"{f.filename} supera 2 MB")

        sha = hashlib.sha256(contenido).hexdigest()
        if db.scalar(select(Multimedia).where(Multimedia.sha256_hash == sha)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{f.filename} ya existe (hash)")

        # ruta estructurada idéntica a la del pipeline: <occ>/<nombre-orig>
        destino = UPLOAD_DIR / str(occurrence_id)
        destino.mkdir(parents=True, exist_ok=True)
        ruta = destino / f.filename
        ruta.write_bytes(contenido)

        nueva = Multimedia(
            media_id=uuid.uuid4(),
            occurrence_id=occurrence_id,
            photo_type="voucher",          # o un campo extra del form si el modal lo pide
            file_name=f.filename,
            file_path=str(ruta).replace("\\", "/"),
            sha256_hash=sha,
            captured_with="phone",         # ajusta si el modal pregunta el dispositivo
            photographer=usuario.first_name + (" " + usuario.last_name if usuario.last_name else ""),
            capture_date=occ.event_date,
            rights_holder="Grupo Virtus",
        )
        db.add(nueva)
        creadas.append(nueva)

    db.commit()
    for n in creadas:
        db.refresh(n)
    return creadas