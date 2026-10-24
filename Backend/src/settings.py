"""Configuration shared by the API, CLI and database initialization."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
ENVIRONMENT = os.getenv("APP_ENV", "development")
DATA_DIR = BACKEND_DIR / "data"
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Configura DATABASE_URL de PostgreSQL en Backend/.env. Ejecuta: python Backend/setup_postgres.py")
if not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
    if ENVIRONMENT != "test" or not DATABASE_URL.startswith("sqlite:///"):
        raise RuntimeError("El aplicativo requiere PostgreSQL. SQLite solo se admite en pruebas aisladas (APP_ENV=test).")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Configura una SECRET_KEY privada de al menos 32 caracteres en Backend/.env.")
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY debe contener al menos 32 caracteres.")

MEDIA_ROOT = Path(os.getenv("MULTIMEDIA_ROOT", str(DATA_DIR / "images"))).resolve()
CORS_ORIGINS = [value.strip() for value in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if value.strip()]
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
