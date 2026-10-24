"""Application entry point: integrated API, local development DB and public media."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from Security import require_admin
from database.Base import SessionLocal, initialize_database
from routers import ALL_ROUTERS, auth, application
from settings import CORS_ORIGINS, MEDIA_ROOT


@asynccontextmanager
async def lifespan(app):
    initialize_database()
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Macromicetos API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", "Accept"])
app.include_router(auth.router)
app.include_router(application.router)

# Keep the original scientific API for administrative imports. Its raw write
# operations cannot bypass the ownership rules of the new application endpoints.
for router in ALL_ROUTERS:
    if router is not auth.router:
        app.include_router(router, prefix="/legacy", dependencies=[Depends(require_admin)])

app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT), check_dir=False), name="media")


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": db.get_bind().dialect.name}


@app.middleware("http")
async def upload_limit(request: Request, call_next):
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        return JSONResponse({"detail": "Content-Length inválido."}, status_code=400)
    if length > 110 * 1024 * 1024:
        return JSONResponse({"detail": "La carga supera 110 MB."}, status_code=413)
    return await call_next(request)
