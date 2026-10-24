import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import UserWeb

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_por_defecto_cambiala")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    """Genera el hash argon2id. Nunca se guarda la contraseña en claro."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara la contraseña en texto plano contra el hash guardado en la base de datos."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Genera un Access Token JWT firmado con la información del usuario."""
    to_encode = data.copy()
    
    # Si no se define tiempo de expiración, por defecto dura 30 minutos
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        
    to_encode.update({"exp": expire})
    
    # Firmar el token con la llave secreta
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserWeb:
    """
    Middleware / Dependencia:
    Extrae el JWT de la cabecera HTTP, lo decodifica y busca al usuario en PostgreSQL.
    Si el token es inválido, expiró o el usuario no existe, levanta un 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales o el token ha expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decodificar el token usando la misma clave secreta
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2. Extraer el "sub" (subject), que en el login guardamos como el user_web_id
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        # Falla si la firma no coincide o el token ya expiró
        raise credentials_exception
        
    # 3. Buscar el usuario en la base de datos usando el ID extraído
    user = db.query(UserWeb).filter(UserWeb.user_web_id == user_id).first()
    
    if user is None:
        raise credentials_exception
        
    return user















