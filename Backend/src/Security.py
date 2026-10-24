"""Authentication and server-side permissions for every application operation."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database.Base import get_db
from models.UserWeb import UserWeb
from settings import SECRET_KEY, TOKEN_MINUTES

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(password, hashed_password)
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=TOKEN_MINUTES))}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserWeb:
    invalid = HTTPException(401, "La sesión no es válida o ha vencido.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require_exp": True, "require_sub": True})
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, TypeError, KeyError):
        raise invalid
    user = db.get(UserWeb, user_id)
    if user is None or payload.get("role") != user.role:
        raise invalid
    return user


def require_roles(*roles):
    def authorize(user: UserWeb = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Tu perfil no permite realizar esta acción.")
        return user
    return authorize


require_writer = require_roles("analyst", "admin")
require_curator = require_roles("curator", "admin")
require_admin = require_roles("admin")


def user_profile(user: UserWeb) -> dict:
    return {"user_web_id": str(user.user_web_id), "email": user.email, "first_name": user.first_name,
            "last_name": user.last_name, "name": " ".join(part for part in (user.first_name, user.last_name) if part),
            "role": user.role}















