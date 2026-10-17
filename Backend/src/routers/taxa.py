"""Catálogo de taxones: creación en el diccionario shared.taxon_ref."""
import uuid
import csv
import io
from urllib.parse import quote

from fastapi.responses import StreamingResponse

from typing import Optional
from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from Security import get_current_user
from database.Base import get_db
from models import UserWeb
from models.TaxonRef import TaxonRef
from schemas.taxon_schema import TaxonRefInput, TaxonRefResponse

def get_taxa_rows(
    db: Session, *,
    taxon_rank: Optional[str] = None,
    family: Optional[str] = None,
    search: Optional[str] = None,
    kingdom: Optional[str] = None,
    phylum: Optional[str] = None,
    class_name: Optional[str] = None,
    order_name: Optional[str] = None,
    genus: Optional[str] = None,
    species: Optional[str] = None,
    common_name_es: Optional[str] = None,
    taxon_remarks: Optional[str] = None,
):
    """Construye el listado de taxones con filtros — compartido por vista y export."""
    stmt = select(TaxonRef).order_by(TaxonRef.scientific_name)

    if taxon_rank:
        stmt = stmt.where(TaxonRef.taxon_rank == taxon_rank)
    if family:
        stmt = stmt.where(func.lower(TaxonRef.family) == family.lower())
    if search:
        stmt = stmt.where(TaxonRef.scientific_name.ilike(f"%{search}%"))
    if kingdom:
        stmt = stmt.where(func.lower(TaxonRef.kingdom) == kingdom.lower())
    if phylum:
        stmt = stmt.where(func.lower(TaxonRef.phylum) == phylum.lower())
    if class_name:
        stmt = stmt.where(func.lower(TaxonRef.class_name) == class_name.lower())
    if order_name:
        stmt = stmt.where(func.lower(TaxonRef.order_name) == order_name.lower())
    if genus:
        stmt = stmt.where(func.lower(TaxonRef.genus) == genus.lower())
    if species:
        stmt = stmt.where(TaxonRef.specific_epithet == species)
    if common_name_es:
        stmt = stmt.where(func.lower(TaxonRef.common_name_es).ilike(f"%{common_name_es.lower()}%"))
    if taxon_remarks:
        stmt = stmt.where(TaxonRef.taxon_remarks.ilike(f"%{taxon_remarks}%"))

    return db.scalars(stmt).all()


####function of extract info in csv

def _taxa_a_csv(rows) -> StreamingResponse:
    """Arma el CSV de taxones filtrados y lo devuelve como descarga."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "taxon_id", "scientific_name", "taxon_rank", "kingdom", "phylum",
        "class", "order", "family", "genus", "specific_epithet",
        "external_taxon_id", "common_name_es", "taxon_remarks",
        "created_at", "updated_at",
    ])
    for t in rows:
        writer.writerow([
            t.taxon_id, t.scientific_name, t.taxon_rank, t.kingdom, t.phylum,
            t.class_name, t.order_name, t.family, t.genus, t.specific_epithet,
            t.external_taxon_id, t.common_name_es, t.taxon_remarks,
            t.created_at, t.updated_at,
        ])

    buffer.seek(0)
    content = buffer.getvalue().encode("utf-8-sig")   # BOM: Excel lo detecta como UTF-8
    filename = "taxa.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        },
    )


router = APIRouter(prefix="/taxa", tags=["taxa"])

# Solo el biólogo/curador y el admin pueden ampliar el diccionario.
ROLES_AUTORIZADOS = {"admin", "curator", "analyst"}


@router.post("", response_model=TaxonRefResponse, status_code=status.HTTP_201_CREATED)
def create_taxon(
    body: TaxonRefInput,
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
):
    """Crea un taxón aceptado. La BD aplica UNIQUE (scientific_name, taxon_rank)."""
    if usuario.role not in ROLES_AUTORIZADOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para crear taxones")

    existe = db.scalar(
        select(TaxonRef).where(
            func.lower(TaxonRef.scientific_name) == body.scientific_name.lower(),
            TaxonRef.taxon_rank == body.taxon_rank,
        )
    )
    if existe:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El taxón ya está registrado")

    nuevo = TaxonRef(
        taxon_id=uuid.uuid4(),
        scientific_name=body.scientific_name,
        taxon_rank=body.taxon_rank,
        kingdom=body.kingdom,
        phylum=body.phylum,
        class_name=body.class_name,
        order_name=body.order_name,
        family=body.family,
        genus=body.genus,
        specific_epithet=body.specific_epithet,
        external_taxon_id=body.external_taxon_id,
        common_name_es=body.common_name_es,
        taxon_remarks=body.taxon_remarks,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo



#=====================

@router.get("/export", response_class=StreamingResponse)
def export_taxa(
    db: Session = Depends(get_db),
    usuario: UserWeb = Depends(get_current_user),
    format: str = Query("csv", pattern="^(csv)$"),  # futuro: json|xlsx
    taxon_rank: Optional[str] = Query(None),
    family: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    kingdom: Optional[str] = Query(None),
    phylum: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None, alias="class"),
    order_name: Optional[str] = Query(None, alias="order"),
    genus: Optional[str] = Query(None),
    species: Optional[str] = Query(None),
    common_name_es: Optional[str] = Query(None, alias="common_name"),
    taxon_remarks: Optional[str] = Query(None),
):
    """Descarga los taxones con los mismos filtros del listado."""
    rows = get_taxa_rows(
        db=db, taxon_rank=taxon_rank, family=family, search=search,
        kingdom=kingdom, phylum=phylum, class_name=class_name,
        order_name=order_name, genus=genus, species=species,
        common_name_es=common_name_es, taxon_remarks=taxon_remarks,
    )

    if format == "csv":
        return _taxa_a_csv(rows)

    # formato no soportado — que sea explícito si mañana se agrega otro
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Formato no soportado: {format}")

#====================

@router.get("", response_model=list[TaxonRefResponse])
def get_all_taxa(
    db: Session = Depends(get_db),
    
    taxon_rank: Optional[str] = Query(None, description="Filtrar por rango (kingdom, family, species...)"),
    family: Optional[str] = Query(None, description="Filtrar por familia"),
    search: Optional[str] = Query(None, description="Búsqueda de texto en scientific_name"),
    kingdom: Optional[str] = Query(None, description="Filtrar por reino"),
    phylum: Optional[str] = Query(None, description="Filtrar por filo"),
    class_name: Optional[str] = Query(None, alias="class", description="Filtrar por clase"),
    order_name: Optional[str] = Query(None, alias="order", description="Filtrar por orden"),
    genus: Optional[str] = Query(None, description="Filtrar por género"),
    species: Optional[str] = Query(None, description="Filtrar por especie (nombre científico exacto)"),
    common_name_es: Optional[str] = Query(None, alias="common_name", description="Filtrar por nombre común en español"),
    taxon_remarks: Optional[str] = Query(None, description="Texto contenido en las notas de curación")
):
    return get_taxa_rows(
        db=db, taxon_rank=taxon_rank, family=family, search=search,
        kingdom=kingdom, phylum=phylum, class_name=class_name,
        order_name=order_name, genus=genus, species=species,
        common_name_es=common_name_es, taxon_remarks=taxon_remarks,
    )

@router.get("/{taxon_id}", response_model=TaxonRefResponse)
def get_taxon(taxon_id: uuid.UUID, db: Session = Depends(get_db)):
    taxon = db.get(TaxonRef, taxon_id)
    if not taxon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taxon no encontrado")
    return taxon