"""Credential-based registration, login and authenticated account profile."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from Security import create_access_token, get_current_user, hash_password, user_profile, verify_password
from database.Base import get_db
from models.UserWeb import UserWeb
from schemas.user_schema import ChangePasswordInput, UserLoginInput, UserRegisterInput

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: UserRegisterInput, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(UserWeb).where(func.lower(UserWeb.email) == email)):
        raise HTTPException(409, "Correo ya registrado.")
    if not body.first_name.strip():
        raise HTTPException(422, "Completa tu nombre.")
    user = UserWeb(user_web_id=uuid.uuid4(), email=email, password_hash=hash_password(body.password),
                   first_name=body.first_name.strip(), last_name=(body.last_name or "").strip() or None, role="viewer")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Correo ya registrado.")
    return {"message": "Cuenta creada correctamente. Inicia sesión."}


def authenticate(email: str, password: str, db: Session):
    user = db.scalar(select(UserWeb).where(func.lower(UserWeb.email) == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Correo o contraseña incorrectos.", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token({"sub": str(user.user_web_id), "role": user.role}),
            "token_type": "Bearer", "user": user_profile(user)}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return authenticate(form.username, form.password, db)


@router.post("/login-json")
def login_json(body: UserLoginInput, db: Session = Depends(get_db)):
    return authenticate(body.email, body.password, db)


@router.get("/me")
def me(user: UserWeb = Depends(get_current_user)):
    return user_profile(user)


@router.post("/change-password")
def change_password(body: ChangePasswordInput, db: Session = Depends(get_db),
                    user: UserWeb = Depends(get_current_user)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(403, "Contraseña actual incorrecta.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Contraseña actualizada correctamente."}
