"""Exclusive socioecological interview section.

One record links an interview session (``ethno_source``) to one species
(``ethno_taxon_knowledge``) and its reported uses (``ethno_use``). Reads are
open to researchers, curators and admins; writes require ownership of the
species or the admin role.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from Security import require_researcher, require_writer
from database.Base import get_db
from models.UserWeb import UserWeb
from routers.application.common import mutation
from schemas.socioecological_schema import EthnoSurveyData
from services.application import delete_ethno_knowledge, ethno_surveys, save_ethno_survey

router = APIRouter(tags=["ethno"])


@router.get("/ethno-surveys")
def list_surveys(taxon_id: uuid.UUID | None = None, db: Session = Depends(get_db),
                 user: UserWeb = Depends(require_researcher)):
    return ethno_surveys(db, user, taxon_id)


@router.put("/ethno-surveys/{source_id}")
def put_survey(source_id: uuid.UUID, body: EthnoSurveyData, db: Session = Depends(get_db),
               user: UserWeb = Depends(require_writer)):
    if body.source.ethno_source_id is None:
        body.source.ethno_source_id = source_id
    elif body.source.ethno_source_id != source_id:
        raise HTTPException(422, "El identificador de la ruta y el de la entrevista no coinciden.")
    body.knowledge.ethno_source_id = source_id
    with mutation(db):
        survey = save_ethno_survey(db, body, user)
    if survey is None:
        raise HTTPException(409, "No fue posible reconstruir la entrevista guardada.")
    return survey


@router.delete("/ethno-surveys/knowledge/{knowledge_id}", status_code=204)
def delete_knowledge(knowledge_id: uuid.UUID, db: Session = Depends(get_db),
                     user: UserWeb = Depends(require_writer)):
    with mutation(db):
        delete_ethno_knowledge(db, knowledge_id, user)
