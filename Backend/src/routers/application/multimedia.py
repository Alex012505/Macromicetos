"""Photo bundles and simple uploads for an occurrence."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from Security import require_writer, user_profile
from database.Base import get_db
from models.Occurrence import Occurrence
from models.UserWeb import UserWeb
from routers.application.common import find, multipart, mutation
from schemas.bundles import MediaBundle
from schemas.multimedia_schema import PhotoData
from services.application import complete, media_data, save_photos

router = APIRouter(tags=["multimedia"])


@router.put("/occurrences/{occurrence_id}/media-bundle")
async def put_photos(occurrence_id: uuid.UUID, request: Request,
                     db: Session = Depends(get_db), user: UserWeb = Depends(require_writer)):
    body, files = await multipart(request, MediaBundle)
    if occurrence_id != body.occurrence_id:
        raise HTTPException(422, "El ID de la ruta y el del hallazgo no coinciden.")
    row = find(db, Occurrence, occurrence_id)
    with mutation(db) as written:
        await save_photos(db, row, body.multimedia, files, user, written)
    return complete(db, "occurrence", row, user, str(request.base_url))


@router.post("/occurrences/{occurrence_id}/photos", status_code=201)
async def add_photos(occurrence_id: uuid.UUID, request: Request, files: list[UploadFile] = File(...),
                     db: Session = Depends(get_db), user: UserWeb = Depends(require_writer)):
    if not 1 <= len(files) <= 10:
        raise HTTPException(422, "Selecciona entre 1 y 10 fotografías.")
    row = find(db, Occurrence, occurrence_id)
    metadata = [PhotoData(media_id=uuid.uuid4(), photo_type="habitus", file_name=photo.filename or "photo",
                          photographer=user_profile(user)["name"]) for photo in files]
    uploads = {str(item.media_id): photo for item, photo in zip(metadata, files)}
    with mutation(db) as written:
        saved = await save_photos(db, row, metadata, uploads, user, written)
    return [media_data(db, photo, user, str(request.base_url)) for photo in saved]
