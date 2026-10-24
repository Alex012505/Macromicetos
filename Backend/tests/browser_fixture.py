"""Local browser-test accounts and read-only verification of artificial records.

Never changes an existing person's account. Only a uniquely identified temporary
QA administrator is removed on cleanup; the three QA profiles and two requested
artificial records remain available for the repository owner's manual testing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sys
import uuid

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))

from sqlalchemy import func, select
from database.Base import SessionLocal, engine
from models.ApplicationState import ApplicationState
from models.CurationDecision import CurationDecision
from models.Multimedia import Multimedia
from models.Occurrence import Occurrence
from models.UserWeb import UserWeb
from Security import hash_password
from settings import ENVIRONMENT, MEDIA_ROOT

MANIFEST = BACKEND / "data" / "web-test-accounts.json"
MARKER = "macromicetos-local-browser-test-v1"
ARTIFICIAL_IDS = ("PRUEBA-WEB-01", "PRUEBA-WEB-02")


def manifest():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("marker") != MARKER:
        raise RuntimeError("El archivo de pruebas no tiene el identificador esperado.")
    for role, account in data["accounts"].items():
        if role not in ("admin", "analyst", "curator", "viewer") or not account["email"].startswith(f"qa-{role}-") or not account["email"].endswith("@example.org"):
            raise RuntimeError("Cuenta fuera del espacio reservado a estas pruebas.")
    return data


def save(data):
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def prepare():
    if MANIFEST.exists():
        data = manifest()
    else:
        tag = uuid.uuid4().hex[:12]
        names = {"admin": "QA Administrador temporal", "analyst": "QA Investigador", "curator": "QA Curador", "viewer": "QA Visitante"}
        data = {"marker": MARKER, "accounts": {role: {"id": str(uuid.uuid4()), "email": f"qa-{role}-{tag}@example.org",
                "firstName": name, "lastName": "Ficticio", "password": secrets.token_urlsafe(20)} for role, name in names.items()}}
    admin_data = data["accounts"]["admin"]
    admin_data["password"] = secrets.token_urlsafe(24)
    with SessionLocal() as db:
        real_admins = db.scalar(select(func.count()).select_from(UserWeb).where(UserWeb.role == "admin", UserWeb.email != admin_data["email"]))
        if not real_admins:
            raise RuntimeError("Primero crea tu cuenta administradora real con Backend/manage.py create-admin.")
        existing = db.get(UserWeb, uuid.UUID(admin_data["id"]))
        if existing:
            if existing.email != admin_data["email"] or existing.first_name != admin_data["firstName"]:
                raise RuntimeError("No se modificó una cuenta que no pertenece a la prueba.")
            existing.password_hash = hash_password(admin_data["password"])
            existing.role = "admin"
        else:
            db.add(UserWeb(user_web_id=uuid.UUID(admin_data["id"]), email=admin_data["email"], first_name=admin_data["firstName"],
                           last_name=admin_data["lastName"], role="admin", password_hash=hash_password(admin_data["password"])))
        for role in ("analyst", "curator", "viewer"):
            account = data["accounts"][role]
            existing = db.scalar(select(UserWeb).where(UserWeb.email == account["email"]))
            if existing and (existing.first_name != account["firstName"] or existing.last_name != account["lastName"]):
                raise RuntimeError("La cuenta encontrada no pertenece a estas pruebas; no se modificó.")
            account["registered"] = bool(existing)
        data["records"] = []
        for external_id in ARTIFICIAL_IDS:
            row = db.scalar(select(Occurrence).where(Occurrence.external_occurrence_id == external_id))
            if row:
                state = db.get(ApplicationState, ("occurrence", row.occurrence_id))
                owner = db.get(UserWeb, state.owner_id) if state else None
                if not owner or owner.email != data["accounts"]["analyst"]["email"] or "ARTIFICIAL" not in (row.occurrence_remarks or ""):
                    raise RuntimeError("Un identificador de prueba ya pertenece a otro registro; no se modificó.")
                data["records"].append({"externalId": external_id, "id": str(row.occurrence_id)})
        # Persist the generated administrator credential before committing its
        # account, so a browser startup failure can still clean up precisely.
        save(data)
        db.commit()
    print("Cuentas de prueba preparadas; credenciales guardadas solo en Backend/data/web-test-accounts.json.")


def verify():
    data = manifest()
    with SessionLocal() as db:
        owner = db.scalar(select(UserWeb).where(UserWeb.email == data["accounts"]["analyst"]["email"]))
        if not owner:
            raise RuntimeError("No se encontró el investigador de pruebas.")
        result = []
        for external_id in ARTIFICIAL_IDS:
            rows = db.scalars(select(Occurrence).where(Occurrence.external_occurrence_id == external_id)).all()
            if len(rows) != 1:
                raise RuntimeError(f"{external_id}: se esperaba exactamente un registro persistido.")
            row = rows[0]
            state = db.get(ApplicationState, ("occurrence", row.occurrence_id))
            assert state and state.owner_id == owner.user_web_id
            assert "ARTIFICIAL" in row.occurrence_remarks
            photos = db.scalars(select(Multimedia).where(Multimedia.occurrence_id == row.occurrence_id)).all()
            assert len(photos) == 1
            for photo in photos:
                path = (MEDIA_ROOT / photo.file_path).resolve()
                assert path.is_relative_to(MEDIA_ROOT) and path.is_file()
                assert hashlib.sha256(path.read_bytes()).hexdigest() == photo.sha256_hash
            decision = db.scalar(select(CurationDecision).where(CurationDecision.entity_type == "occurrence", CurationDecision.entity_id == row.occurrence_id)
                                 .order_by(CurationDecision.created_at.desc()).limit(1))
            assert decision and decision.new_status == ("verified" if external_id == "PRUEBA-WEB-01" else "submitted"), f"Estado de curaduría inesperado para {external_id}."
            assert state.payload["measurements"][0]["measurement_value"] == "0"
            assert state.payload["location"]["coordinate_uncertainty_m"] == 0
            result.append({"id": str(row.occurrence_id), "externalId": external_id, "photos": len(photos), "status": decision.new_status})
        data["records"] = result
        save(data)
    print(json.dumps({"database": engine.dialect.name, "records": result}, ensure_ascii=False))


def cleanup():
    if not MANIFEST.exists():
        return
    data = manifest()
    account = data["accounts"]["admin"]
    with SessionLocal() as db:
        row = db.get(UserWeb, uuid.UUID(account["id"]))
        if row:
            assert row.email == account["email"] and row.first_name == account["firstName"]
            assert not db.scalar(select(ApplicationState.entity_id).where((ApplicationState.owner_id == row.user_web_id) | (ApplicationState.created_by_id == row.user_web_id)).limit(1))
            assert not db.scalar(select(CurationDecision.decision_id).where(CurationDecision.decided_by == row.user_web_id).limit(1))
            assert db.scalar(select(func.count()).select_from(UserWeb).where(UserWeb.role == "admin", UserWeb.user_web_id != row.user_web_id)) > 0
            db.delete(row)
            db.commit()
    account.pop("password", None)
    account["active"] = False
    save(data)
    print("Administrador temporal de QA eliminado. Tus usuarios reales no se modificaron.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "verify", "cleanup"])
    command = parser.parse_args().command
    if ENVIRONMENT != "development" or engine.dialect.name != "postgresql" or engine.url.host not in ("localhost", "127.0.0.1"):
        raise RuntimeError("Estas pruebas persistentes solo se permiten en PostgreSQL de desarrollo local.")
    {"prepare": prepare, "verify": verify, "cleanup": cleanup}[command]()
