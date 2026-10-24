"""Every test runs against an isolated disposable DB, never the user's DB."""
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
TEST_ROOT = BACKEND / ".test-data"
TEST_ROOT.mkdir(exist_ok=True)
temporary = tempfile.TemporaryDirectory(prefix="pytest-", dir=TEST_ROOT)
TEST_DIR = Path(temporary.name).resolve()
assert TEST_DIR.parent == TEST_ROOT.resolve()
postgres_url = os.environ.get("MACROMICETOS_TEST_POSTGRES_URL")
if postgres_url:
    from sqlalchemy.engine import make_url
    target = make_url(postgres_url)
    if target.get_backend_name() != "postgresql" or not re.fullmatch(r"macromicetos_test_[0-9a-f]{32}", target.database or ""):
        raise RuntimeError("Las pruebas PostgreSQL solo admiten bases desechables macromicetos_test_<UUID>.")
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = postgres_url or f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["MULTIMEDIA_ROOT"] = str(TEST_DIR / "images")
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
sys.path.insert(0, str(BACKEND / "src"))

from database.Base import Base, SessionLocal, engine
from main import app
from models.UserWeb import UserWeb
from Security import hash_password

PASSWORD = secrets.token_urlsafe(18)


@pytest.fixture
def client():
    # The exact database target was created above, inside this test-only folder.
    if postgres_url:
        assert re.fullmatch(r"macromicetos_test_[0-9a-f]{32}", engine.url.database)
    else:
        assert Path(engine.url.database).resolve() == TEST_DIR / "test.db"
    Base.metadata.drop_all(engine)
    with TestClient(app) as instance:
        yield instance


@pytest.fixture
def accounts(client):
    with SessionLocal() as db:
        people = {}
        for name, role in (("admin", "admin"), ("alice", "analyst"), ("bob", "analyst"), ("curator", "curator"), ("viewer", "viewer")):
            person = UserWeb(first_name=name.title(), email=f"{name}@example.org", password_hash=hash_password(PASSWORD), role=role)
            db.add(person)
            db.flush()
            people[name] = {"id": str(person.user_web_id), "role": role, "name": person.first_name}
        db.commit()
    for name, person in people.items():
        response = client.post("/auth/login-json", json={"email": f"{name}@example.org", "password": PASSWORD})
        assert response.status_code == 200, response.text
        person["headers"] = {"Authorization": f"Bearer {response.json()['access_token']}"}
    return people


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    temporary.cleanup()
