"""Disposable HTTP server for the real TypeScript-client integration check.

Called only by frontend/scripts/check-integration.mjs, with an isolated DB path
and a random password supplied through environment variables.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn
from sqlalchemy.engine import make_url
from database.Base import SessionLocal, initialize_database
from models.UserWeb import UserWeb
from Security import hash_password

if __name__ == "__main__":
    password = os.environ["INTEGRATION_TEST_PASSWORD"]
    target = make_url(os.environ["DATABASE_URL"])
    if not os.environ.get("INTEGRATION_ISOLATED_DB") or os.environ.get("APP_ENV") != "test":
        raise RuntimeError("El servidor de prueba requiere una base aislada y APP_ENV=test.")
    if target.get_backend_name() == "postgresql":
        if not re.fullmatch(r"macromicetos_test_[0-9a-f]{32}", target.database or ""):
            raise RuntimeError("La base PostgreSQL de integración debe ser desechable.")
    elif target.get_backend_name() == "sqlite":
        test_root = Path(__file__).resolve().parents[1] / ".test-data"
        if Path(target.database).resolve().parent.parent != test_root.resolve():
            raise RuntimeError("La base SQLite de integración debe estar dentro de .test-data.")
    else:
        raise RuntimeError("Motor de pruebas no admitido.")
    initialize_database()
    with SessionLocal() as db:
        for role in ("admin", "analyst", "curator", "viewer"):
            db.add(UserWeb(first_name=role.title(), email=f"{role}@example.org", role=role, password_hash=hash_password(password)))
        db.commit()
    uvicorn.run("main:app", host="127.0.0.1", port=int(os.environ["INTEGRATION_TEST_PORT"]), log_level="error")
