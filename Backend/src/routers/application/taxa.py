"""Complete taxon forms and catalogue exports."""
import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from Security import get_current_user, require_writer
from database.Base import get_db
from models.TaxonRef import TaxonRef
from models.UserWeb import UserWeb
from routers.application.common import find, mutation
from schemas.bundles import TaxonBundle
from schemas.taxon_schema import TaxonRefInput
from services.application import complete, save_taxon

router = APIRouter(tags=["taxa"])


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
