"""The concrete API contract consumed by the React application."""
from fastapi import APIRouter, Depends

from Security import get_current_user
from routers.application import curation, multimedia, occurrences, taxa, users

router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(users.router)
router.include_router(taxa.router)
router.include_router(occurrences.router)
router.include_router(multimedia.router)
router.include_router(curation.router)
