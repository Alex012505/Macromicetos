"""Complete occurrence records."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from Security import get_current_user, require_writer
from database.Base import get_db
from models.Occurrence import Occurrence
from models.UserWeb import UserWeb
from routers.application.common import find, multipart, mutation
from schemas.bundles import RecordBundle
from services.application import complete, save_photos, save_record

router = APIRouter(tags=["occurrences"])


@router.get("/occurrences")
def occurrences(request: Request, db: Session = Depends(get_db), user: UserWeb = Depends(get_current_user)):
    return [complete(db, "occurrence", row, user, str(request.base_url)) for row in db.scalars(
        select(Occurrence).order_by(Occurrence.created_at.desc(), Occurrence.occurrence_id)
    ).all()]


@router.get("/occurrences/{occurrence_id}")
def occurrence(occurrence_id: uuid.UUID, request: Request,
               db: Session = Depends(get_db), user: UserWeb = Depends(get_current_user)):
    return complete(db, "occurrence", find(db, Occurrence, occurrence_id), user, str(request.base_url))


@router.put("/record-bundles/{occurrence_id}")
async def put_occurrence(occurrence_id: uuid.UUID, request: Request,
                         db: Session = Depends(get_db), user: UserWeb = Depends(require_writer)):
    body, files = await multipart(request, RecordBundle)
    if occurrence_id != body.occurrence.occurrence_id:
        raise HTTPException(422, "El ID de la ruta y el del hallazgo no coinciden.")
    with mutation(db) as written:
        row = save_record(db, body, user)
        if body.multimedia:
            await save_photos(db, row, body.multimedia, files, user, written)
    return complete(db, "occurrence", row, user, str(request.base_url))
