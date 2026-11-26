"""The concrete API contract consumed by the React application.

Authentication is declared per endpoint: catalogue reads accept anonymous
visitors, while every write keeps an explicit role or ownership dependency.
"""
from fastapi import APIRouter

from routers.application import curation, ethno, multimedia, occurrences, taxa, users

router = APIRouter()
router.include_router(users.router)
router.include_router(taxa.router)
router.include_router(occurrences.router)
router.include_router(multimedia.router)
router.include_router(curation.router)
router.include_router(ethno.router)
