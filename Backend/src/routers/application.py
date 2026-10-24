"""The concrete API contract consumed by the React application."""
import csv
import io
import uuid
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from Security import get_current_user, require_admin, require_curator, require_writer, user_profile
from database.Base import get_db
from models.Occurrence import Occurrence
from models.TaxonRef import TaxonRef
from models.UserWeb import UserWeb
from schemas.application_schema import MediaBundle, PhotoData, RecordBundle, ReviewInput, RoleUpdate, TaxonBundle
from schemas.taxon_schema import TaxonRefInput
from services.application import audit, complete, media_data, save_photos, save_record, save_taxon

router = APIRouter(tags=["application"], dependencies=[Depends(get_current_user)])


@contextmanager
def mutation(db):
    written = []
    try:
        yield written
        db.commit()
    except Exception as error:
        db.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        if isinstance(error, IntegrityError):
            raise HTTPException(409, "Los datos entran en conflicto con un registro existente.") from error
        raise


async def multipart(request, schema):
    form = await request.form(max_files=10, max_fields=100, max_part_size=2 * 1024 * 1024)
    payload = form.get("payload")
    if not isinstance(payload, str) or len(payload) > 2 * 1024 * 1024:
        raise HTTPException(422, "Falta el campo JSON payload o supera el tamaño permitido.")
    try:
        body = schema.model_validate_json(payload)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    files = {}
    for key, value in form.multi_items():
        if key == "payload":
            continue
        if not key.startswith("file_") or not hasattr(value, "read") or key[5:] in files:
            raise HTTPException(422, "Campos de archivo inválidos o duplicados.")
        files[key[5:]] = value
    if set(files) != {str(photo.media_id) for photo in body.multimedia}:
        raise HTTPException(422, "Los archivos y sus metadatos no coinciden.")
    return body, files


def find(db, model, entity_id):
    row = db.get(model, entity_id)
    if row is None:
        raise HTTPException(404, "El registro solicitado no existe.")
    return row


@router.get("/users")
def users(db: Session = Depends(get_db), user: UserWeb = Depends(require_admin)):
    return [user_profile(account) for account in db.scalars(select(UserWeb).order_by(UserWeb.first_name, UserWeb.email)).all()]


@router.patch("/users/{user_id}")
def update_role(user_id: uuid.UUID, body: RoleUpdate, db: Session = Depends(get_db), user: UserWeb = Depends(require_admin)):
    with mutation(db):
        admins = db.scalars(select(UserWeb).where(UserWeb.role == "admin").order_by(UserWeb.user_web_id).with_for_update()).all()
        account = find(db, UserWeb, user_id)
        if account.role == "admin" and body.role != "admin" and len(admins) < 2:
            raise HTTPException(409, "Debe permanecer al menos una cuenta administradora.")
        account.role = body.role
    return user_profile(account)


@router.get("/taxa")
def taxa(request: Request, search: str = "", db: Session = Depends(get_db), user: UserWeb = Depends(get_current_user)):
    query = select(TaxonRef).order_by(TaxonRef.scientific_name)
    if search:
        query = query.where(TaxonRef.scientific_name.ilike(f"%{search}%") | TaxonRef.common_name_es.ilike(f"%{search}%"))
    return [complete(db, "taxon_ref", row, user, str(request.base_url)) for row in db.scalars(query).all()]


@router.get("/taxa/export")
def taxa_export(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["taxon_id", "scientific_name", "taxon_rank", "family", "genus"])
    for row in db.scalars(select(TaxonRef).order_by(TaxonRef.scientific_name)).all():
        safe_name = "'" + row.scientific_name if row.scientific_name.lstrip().startswith(("=", "+", "-", "@")) else row.scientific_name
        writer.writerow([row.taxon_id, safe_name, row.taxon_rank, row.family, row.genus])
    return Response("\ufeff" + output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="taxa.csv"'})


@router.get("/taxa/{taxon_id}")
def taxon(taxon_id: uuid.UUID, request: Request, db: Session = Depends(get_db), user: UserWeb = Depends(get_current_user)):
    return complete(db, "taxon_ref", find(db, TaxonRef, taxon_id), user, str(request.base_url))


@router.post("/taxa", status_code=201)
def create_taxon(body: TaxonRefInput, request: Request, db: Session = Depends(get_db), user: UserWeb = Depends(require_writer)):
    bundle = TaxonBundle(taxon={**body.model_dump(by_alias=True), "taxon_id": uuid.uuid4()})
    with mutation(db):
        row = save_taxon(db, bundle, user)
    return complete(db, "taxon_ref", row, user, str(request.base_url))


@router.put("/taxon-bundles/{taxon_id}")
def put_taxon(taxon_id: uuid.UUID, body: TaxonBundle, request: Request,
              db: Session = Depends(get_db), user: UserWeb = Depends(require_writer)):
    if taxon_id != body.taxon.taxon_id:
        raise HTTPException(422, "El ID de la ruta y el de la ficha no coinciden.")
    with mutation(db):
        row = save_taxon(db, body, user)
    return complete(db, "taxon_ref", row, user, str(request.base_url))


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


@router.patch("/occurrences/{occurrence_id}/curation")
def curate(occurrence_id: uuid.UUID, body: ReviewInput, request: Request,
           db: Session = Depends(get_db), user: UserWeb = Depends(require_curator)):
    row = find(db, Occurrence, occurrence_id)
    with mutation(db):
        audit(db, "occurrence", row.occurrence_id, user, body.status, body.review_note.strip() or None)
    return complete(db, "occurrence", row, user, str(request.base_url))
