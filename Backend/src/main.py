"""Punto de entrada de la API de la plataforma Virtus Macromycetes."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from database.Base import get_db,engine #here are the access to the database

from routers import ALL_ROUTERS

app = FastAPI(
    title="Virtus Macromycetes API",
    description=(
        "API de la Plataforma Web Macromicetos (Grupo Virtus). "
        "Pipeline de datos de macrohongos de la región Orinoquía colombiana."
    ),
    version="1.0.0",
)

for router in ALL_ROUTERS:
       app.include_router(router)

@app.on_event("startup")
def startup_db_check():
    try:
        db = next(get_db()) # Obtiene la sesión del generador
        db.execute(text("SELECT 1"))
        db.close()
        print(" Conexión exitosa a la base de datos PostgreSQL/PostGIS.")
    except Exception as e:
        print(f" Error al conectar a la base de datos al iniciar: {e}")
