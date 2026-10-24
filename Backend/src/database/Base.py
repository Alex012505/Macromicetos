import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL"
   
)

if not DATABASE_URL:
    raise ValueError("La variable de entorno DATABASE_URL no está configurada en el archivo .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)



class Base(DeclarativeBase):
    pass
    """Base declarativa de todos los modelos."""


def get_db():
    """Entrega una sesión por petición y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
