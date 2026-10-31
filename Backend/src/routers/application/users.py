"""User listing and role management."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from Security import require_admin, user_profile
from database.Base import get_db
from models.UserWeb import UserWeb
from routers.application.common import find, mutation
from schemas.user_schema import RoleUpdate

router = APIRouter(tags=["users"])


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
