import copy
import base64
import datetime as dt
import io
import json
import uuid

from PIL import Image
from sqlalchemy import func, select

from conftest import PASSWORD
from database.Base import SessionLocal, engine
from models.CurationDecision import CurationDecision
from models.Event import Event
from models.Location import Location
from models.Multimedia import Multimedia
from models.Occurrence import Occurrence
from models.UserWeb import UserWeb
from Security import create_access_token
from settings import MEDIA_ROOT


def uid():
    return str(uuid.uuid4())


def taxon_bundle():
    taxon_id = uid()
    return {"taxon": {"taxon_id": taxon_id, "scientific_name": "Pleurotus ostreatus", "taxon_rank": "species",
                      "kingdom": "Fungi", "class": "Agaricomycetes", "order": "Agaricales", "family": "Pleurotaceae"},
            "morphology": [{"taxon_id": taxon_id, "measurement_type": "color_sombrero", "measurement_value": "Gris"}],
            "sources": [{"source_id": uid(), "title": "Manual científico", "year": 2026}],
            "participants": [{"party": {"party_id": uid(), "display_name": "Ana", "contact_email": "private@example.org"}, "party_role": "author"}],
            "knowledge": [{"source": {"ethno_source_id": uid(), "interview_date": "2026-10-22T12:00:00-05:00", "consent_given": True},
                           "knowledge": {"knows_fungi": False}, "uses": [{"use_category": "cultural"}]}]}


def record_bundle(taxon_id=None):
    occurrence_id, event_id, location_id = uid(), uid(), uid()
    return {"location": {"location_id": location_id, "country": "CO", "locality": "Bosque de prueba", "state_province": "Meta",
                         "decimal_latitude": 0, "decimal_longitude": 0, "coordinate_uncertainty_m": 0, "habitat": "Bosque de galería"},
            "event": {"event_id": event_id, "location_id": location_id, "event_date": "2026-10-20", "recorded_by": "Nombre manipulado",
                      "event_type": "Observation", "sampling_protocol": "OpportunisticSearch", "sampling_effort": "Tres horas"},
            "occurrence": {"occurrence_id": occurrence_id, "event_id": event_id, "taxon_id": taxon_id,
                           "event_date": "2026-10-20T13:00:00-05:00", "date_identified": "2026-10-22", "identified_by": "Especialista", "substrate": "Madera muerta"},
            "morphology": [{"occurrence_id": occurrence_id, "measurement_type": "diametro_sombrero", "measurement_value": "5–8", "measurement_unit": "cm"}],
            "measurements": [{"occurrence_id": occurrence_id, "event_id": None, "measurement_type": "Temperatura", "measurement_value": "24", "measurement_unit": "°C"}],
            "participants": [{"party": {"party_id": uid(), "display_name": "Participante", "contact_email": "private@example.org"}, "party_role": "collector"}],
            "multimedia": []}


def picture(color="red"):
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), color=color).save(stream, format="PNG")
    return stream.getvalue()


def put_record(client, body, account, photos=None):
    files = {"payload": (None, json.dumps(body), "application/json")}
    for key, content in (photos or {}).items():
        files[f"file_{key}"] = ("photo.png", content, "image/png")
    return client.put(f"/record-bundles/{body['occurrence']['occurrence_id']}", headers=account["headers"], files=files)


def test_registration_login_and_real_profile(client):
    response = client.post("/auth/register", json={"email": "New@Example.org", "password": PASSWORD, "first_name": "Nueva", "last_name": "Cuenta", "role": "admin"})
    assert response.status_code == 201
    login = client.post("/auth/login-json", json={"email": "new@example.org", "password": PASSWORD})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/auth/me", headers=headers).json()["role"] == "viewer"
    assert client.post("/auth/login-json", json={"email": "new@example.org", "password": "incorrect"}).status_code == 401
    assert client.post("/auth/register", json={"email": "new@example.org", "password": PASSWORD, "first_name": "Otra"}).status_code == 409
    with SessionLocal() as db:
        user = db.scalar(select(UserWeb))
        assert user.password_hash != PASSWORD and user.role == "viewer"


def test_authentication_required_for_application_and_legacy_routes(client, accounts):
    assert client.get("/taxa").status_code == 401
    assert client.get("/occurrences").status_code == 401
    assert client.get("/users", headers=accounts["alice"]["headers"]).status_code == 403
    assert client.post("/legacy/locations", json={}, headers=accounts["alice"]["headers"]).status_code == 403
    expired = create_access_token({"sub": accounts["alice"]["id"], "role": "analyst"}, dt.timedelta(seconds=-1))
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    forged = expired.rsplit(".", 1)[0] + ".incorrectsignature"
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_taxon_full_form_survives_round_trip_and_redacts_interviews(client, accounts):
    body = taxon_bundle()
    path = f"/taxon-bundles/{body['taxon']['taxon_id']}"
    response = client.put(path, json=body, headers=accounts["alice"]["headers"])
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["class"] == "Agaricomycetes" and saved["sources"][0]["year"] == 2026
    assert saved["knowledge"][0]["knowledge"]["knows_fungi"] is False
    assert saved["morphology"][0]["measurement_value"] == "Gris"
    assert saved["owner_id"] == accounts["alice"]["id"]
    public = client.get(f"/taxa/{saved['taxon_id']}", headers=accounts["viewer"]["headers"]).json()
    assert not public.get("knowledge") and "private@example.org" not in json.dumps(public)
    assert "snapshot" not in public
    assert client.put(path, json=body, headers=accounts["bob"]["headers"]).status_code == 403
    assert client.put(path, json=body, headers=accounts["viewer"]["headers"]).status_code == 403
    assert client.put(path, json=body, headers=accounts["alice"]["headers"]).status_code == 200
    duplicate = taxon_bundle()
    assert client.put(f"/taxon-bundles/{duplicate['taxon']['taxon_id']}", json=duplicate, headers=accounts["alice"]["headers"]).status_code == 409


def test_full_record_identity_photos_and_idempotent_retry(client, accounts):
    body = record_bundle()
    body["owner_id"] = accounts["bob"]["id"]
    media_id = uid()
    body["multimedia"] = [{"media_id": media_id, "file_name": "../../photo.png", "photo_type": "pileus", "photographer": "Ana", "license": "CC BY 4.0",
                            "credits": [{"party": {"display_name": "Ana", "contact_email": "private@example.org"}, "credit_role": "photographer"}]}]
    response = put_record(client, body, accounts["alice"], {media_id: picture()})
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["owner_id"] == accounts["alice"]["id"] and saved["created_by_id"] == accounts["alice"]["id"]
    assert saved["event"]["recorded_by"] == saved["recorded_by"] == "Alice"
    assert saved["event"]["sampling_effort"] == "Tres horas"
    assert saved["substrate"] == "Madera muerta"
    assert saved["event"]["location"]["decimal_latitude"] == 0 and saved["event"]["location"]["coordinate_uncertainty_m"] == 0
    assert saved["date_identified"] == "2026-10-22" and saved["event"]["event_date"] == "2026-10-20"
    assert saved["measurements"][0]["measurement_value"] == "24"
    photo = saved["multimedia"][0]
    assert photo["photo_type"] == "pileus" and photo["file_name"] == "photo.png" and "file_path" not in photo
    assert client.get(photo["source_url"]).content == picture()
    assert put_record(client, body, accounts["alice"], {media_id: picture()}).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Multimedia)) == 1
        assert db.scalar(select(func.count()).select_from(Occurrence)) == 1
    public = client.get(f"/occurrences/{saved['occurrence_id']}", headers=accounts["viewer"]["headers"]).json()
    assert "private@example.org" not in json.dumps(public)
    assert "snapshot" not in public
    assert len(client.get("/occurrences", headers=accounts["viewer"]["headers"]).json()) == 1
    assert put_record(client, body, accounts["bob"], {media_id: picture()}).status_code == 403


def test_admin_assignment_and_curator_review(client, accounts):
    body = record_bundle()
    body["owner_id"] = accounts["bob"]["id"]
    response = put_record(client, body, accounts["admin"])
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["owner_id"] == accounts["bob"]["id"] and saved["created_by_id"] == accounts["admin"]["id"]
    assert put_record(client, body, accounts["bob"]).status_code == 200
    path = f"/occurrences/{saved['occurrence_id']}/curation"
    assert client.patch(path, json={"status": "verified"}, headers=accounts["bob"]["headers"]).status_code == 403
    assert client.patch(path, json={"status": "rejected", "review_note": "corto"}, headers=accounts["curator"]["headers"]).status_code == 422
    reviewed = client.patch(path, json={"status": "verified", "review_note": "Verificado por especialista"}, headers=accounts["curator"]["headers"])
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "verified"
    body["occurrence"]["occurrence_remarks"] = "Información adicional"
    updated = put_record(client, body, accounts["bob"])
    assert updated.status_code == 200 and updated.json()["status"] == "pending"


def test_failed_photo_batch_rolls_back_all_entities_and_files(client, accounts):
    body = record_bundle()
    first, second = uid(), uid()
    body["multimedia"] = [{"media_id": key, "file_name": "photo.png", "photo_type": "habitus"} for key in (first, second)]
    before = set(MEDIA_ROOT.rglob("*.png"))
    response = put_record(client, body, accounts["alice"], {first: picture("blue"), second: b"this is not an image"})
    assert response.status_code == 415, response.text
    assert set(MEDIA_ROOT.rglob("*.png")) == before
    with SessionLocal() as db:
        for model in (Occurrence, Event, Location, Multimedia):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_record_validation_and_foreign_event_protection(client, accounts):
    first = record_bundle()
    assert put_record(client, first, accounts["alice"]).status_code == 200
    foreign = copy.deepcopy(first)
    foreign["occurrence"]["occurrence_id"] = uid()
    foreign["morphology"] = []
    foreign["measurements"] = []
    assert put_record(client, foreign, accounts["bob"]).status_code == 409
    for mutate in (lambda b: b["location"].update(decimal_latitude=91),
                   lambda b: b["location"].update(decimal_longitude=None),
                   lambda b: b["event"].update(location_id=uid()),
                   lambda b: b["occurrence"].update(basis_of_record="invented")):
        invalid = record_bundle()
        mutate(invalid)
        assert put_record(client, invalid, accounts["alice"]).status_code == 422


def test_role_management_protects_last_admin_and_invalidates_old_tokens(client, accounts):
    admin = accounts["admin"]
    assert len(client.get("/users", headers=admin["headers"]).json()) == 5
    assert client.patch(f"/users/{admin['id']}", json={"role": "viewer"}, headers=admin["headers"]).status_code == 409
    path = f"/users/{accounts['alice']['id']}"
    assert client.patch(path, json={"role": "curator"}, headers=accounts["alice"]["headers"]).status_code == 403
    assert client.patch(path, json={"role": "curator"}, headers=admin["headers"]).status_code == 200
    assert client.get("/auth/me", headers=accounts["alice"]["headers"]).status_code == 401
    login = client.post("/auth/login-json", json={"email": "alice@example.org", "password": PASSWORD})
    assert login.json()["user"]["role"] == "curator"


def test_additional_photo_endpoint_matches_frontend_route(client, accounts):
    body = record_bundle()
    saved = put_record(client, body, accounts["alice"]).json()
    path = f"/occurrences/{saved['occurrence_id']}/photos"
    assert client.post(path, files={"files": ("a.png", picture("green"), "image/png")}, headers=accounts["bob"]["headers"]).status_code == 403
    response = client.post(path, files={"files": ("a.png", picture("green"), "image/png")}, headers=accounts["alice"]["headers"])
    assert response.status_code == 201, response.text
    assert len(response.json()) == 1 and response.json()[0]["source_url"]


def test_corrupt_png_and_invalid_taxon_rank_return_validation_errors(client, accounts):
    body = record_bundle()
    saved = put_record(client, body, accounts["alice"]).json()
    bad_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aY0cAAAAASUVORK5CYII=")
    response = client.post(f"/occurrences/{saved['occurrence_id']}/photos", files={"files": ("bad.png", bad_png, "image/png")}, headers=accounts["alice"]["headers"])
    assert response.status_code == 415
    assert client.post("/taxa", json={"scientific_name": "Test species", "taxon_rank": "invented"}, headers=accounts["alice"]["headers"]).status_code == 422


def test_cors_and_persistent_restart(client, accounts):
    assert client.get("/health").json() == {"status": "ok", "database": engine.dialect.name}
    response = client.options("/auth/login-json", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert put_record(client, record_bundle(), accounts["alice"]).status_code == 200
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as restarted:
        assert len(restarted.get("/occurrences", headers=accounts["alice"]["headers"]).json()) == 1
