"""Endpoints de autenticación: registro, login y cambio de contraseña."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from Security import hash_password,verify_password
from database.Base import get_db,engine
from models.UserWeb import  UserWeb
from schemas.user_schema import (ChangePasswordInput, MessageResponse,
                     UserLoginInput, UserRegisterInput)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserRegisterInput, db: Session = Depends(get_db)):# acá si está usando el mismo objeto?
    """Crea una cuenta con el rol de menor privilegio ('viewer')."""
    #logic of email already registred
    #___________________________________________________________________________________________________
    existe = db.scalar(
        select(UserWeb).where(func.lower(UserWeb.email) == body.email.lower())
    )
    if existe:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Correo ya registrado")
    #___________________________________________________________________________________________________
   
    
    
    # 2. Creación del nuevo usuario público con rol 'viewer'
    nuevo_usuario = UserWeb(
        user_web_id=uuid.uuid4(),
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        first_name=getattr(body, "first_name", None),
        last_name=getattr(body, "last_name", None),
        role="viewer",  # Forzado por RBAC para evitar elevación de privilegios
        
    )
    
    db.add(nuevo_usuario)
    db.commit()
    return MessageResponse(message="Cuenta creada correctamente")


# Asegúrate de importar verify_password y create_access_token desde tu módulo Security
from Security import hash_password, verify_password, create_access_token
# Asegúrate de incluir TokenResponse en la importación de schemas.user_schema
from schemas.user_schema import (ChangePasswordInput, MessageResponse,
                     UserLoginInput, UserRegisterInput, TokenResponse)

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(body: UserLoginInput, db: Session = Depends(get_db)):
    """Verifica las credenciales y devuelve un token JWT (Access Token)."""
    
    # 1. Buscar al usuario por correo electrónico (Case Insensitive)
    usuario = db.scalar(
        select(UserWeb).where(func.lower(UserWeb.email) == body.email.lower())
    )
    
    # 2. Verificar que el usuario exista y la contraseña sea correcta
    if not usuario or not verify_password(body.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Generar el Access Token
    # Se incluye el ID del usuario (sub) y su rol en el payload del JWT
    access_token = create_access_token(
        data={"sub": str(usuario.user_web_id), "role": usuario.role}
    )
    
    # 4. Retornar la respuesta estructurada
    return {"access_token": access_token, "token_type": "Bearer"}

