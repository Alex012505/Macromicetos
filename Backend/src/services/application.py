"""Persistence and permissions for complete taxon, occurrence and photo forms."""
import copy
import datetime as dt
import hashlib
import io
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, inspect, select

from models.ApplicationState import ApplicationState
from models.CurationDecision import CurationDecision
from models.Event import Event, EVENT_TYPE_ENUM, SAMPLING_PROTOCOL_ENUM, SAMPLING_EFFORT_ENUM
from models.Location import Location, HABITAT_ENUM
from models.MorphologyFact import MorphologyFact, MORPHOLOGY_TYPE_ENUM
from models.Multimedia import Multimedia, PHOTO_TYPE_ENUM
from models.MeasurementOrFact import MeasurementOrFact
from models.Occurrence import Occurrence, SUBSTRATE_ENUM, BASIS_OF_RECORD_ENUM, OCCURRENCE_STATUS_ENUM, ID_QUALIFIER_ENUM
from models.TaxonRef import TaxonRef
from models.UserWeb import UserWeb
from settings import MEDIA_ROOT

MAX_PHOTO_BYTES = 10 * 1024 * 1024
PHOTO_TYPES = {"habitus": "voucher", "pileus": "cap"}


def as_dict(row):
    data = {attr.key: getattr(row, attr.key) for attr in inspect(row).mapper.column_attrs}
    if isinstance(row, TaxonRef):
        data["class"] = data.pop("class_name")
        data["order"] = data.pop("order_name")
    return jsonable_encoder(data)


def state_for(db, kind, entity_id):
    return db.get(ApplicationState, (kind, entity_id))


def require_edit(db, kind, entity_id, user):
    state = state_for(db, kind, entity_id)
    if user.role != "admin" and (user.role != "analyst" or not state or state.owner_id != user.user_web_id):
        raise HTTPException(403, "Solo puedes editar registros de tu propia cuenta.")
    return state


def current_decision(db, kind, entity_id):
    return db.scalar(select(CurationDecision).where(
        CurationDecision.entity_type == kind, CurationDecision.entity_id == entity_id
    ).order_by(CurationDecision.created_at.desc(), CurationDecision.decision_id.desc()).limit(1))


def audit(db, kind, entity_id, user, status="submitted", note=None):
    previous = current_decision(db, kind, entity_id)
    db.add(CurationDecision(decision_id=uuid.uuid4(), entity_type=kind, entity_id=entity_id,
                           decided_by=user.user_web_id, previous_status=previous.new_status if previous else None,
                           new_status=status, comment=note, created_at=dt.datetime.now(dt.timezone.utc)))


def ownership(db, kind, entity_id, user, owner_id=None):
    state = state_for(db, kind, entity_id)
    if state:
        require_edit(db, kind, entity_id, user)
    if user.role != "admin":
        owner_id = user.user_web_id
    else:
        owner_id = owner_id or (state.owner_id if state else user.user_web_id)
    owner = db.get(UserWeb, owner_id)
    historical_owner = state and state.owner_id == owner_id
    if not owner or (not historical_owner and owner.user_web_id != user.user_web_id and owner.role != "analyst"):
        raise HTTPException(422, "Selecciona un investigador válido como responsable.")
    if not state:
        state = ApplicationState(entity_type=kind, entity_id=entity_id,
                                 owner_id=owner_id, created_by_id=user.user_web_id, payload={})
        db.add(state)
    state.owner_id = owner_id
    return state, owner


def private_fields(data):
    """Remove private contact addresses at every nested participant level."""
    if isinstance(data, dict):
        return {key: private_fields(value) for key, value in data.items() if key not in ("contact_email", "contactEmail")}
    if isinstance(data, list):
        return [private_fields(item) for item in data]
    return data


def complete(db, kind, row, user, base_url):
    data = as_dict(row)
    entity_id = row.taxon_id if kind == "taxon_ref" else row.occurrence_id
    state = state_for(db, kind, entity_id)
    extra = copy.deepcopy(state.payload if state else {})
    extra.pop("snapshot", None)
    extra.pop("morphology_snapshot", None)
    sensitive = user.role in ("admin", "curator") or (state and state.owner_id == user.user_web_id)
    if not sensitive:
        extra = private_fields(extra)
        extra.pop("knowledge", None)
    data.update(extra)
    decision = current_decision(db, kind, entity_id)
    raw_status = decision.new_status if decision else "submitted"
    data["status"] = {"verified": "verified", "rejected": "rejected", "needs_adjustment": "rejected"}.get(raw_status, "pending")
    data["review_note"] = decision.comment if decision else None
    data["owner_id"] = str(state.owner_id) if state and state.owner_id else None
    data["created_by_id"] = str(state.created_by_id) if state and state.created_by_id else None
    if kind == "occurrence":
        event = db.get(Event, row.event_id)
        location = db.get(Location, event.location_id)
        event_data = {**as_dict(event), **extra.get("event", {})}
        event_data["location"] = {**as_dict(location), **extra.get("location", {})}
        data["event"] = event_data
        if state and "snapshot" in state.payload:
            data["event_date"] = state.payload["snapshot"]["occurrence"].get("event_date")
        if not state or "measurements" not in state.payload:
            data["measurements"] = [as_dict(item) for item in db.scalars(select(MeasurementOrFact).where(MeasurementOrFact.event_id == row.event_id)).all()]
        data["multimedia"] = [media_data(db, photo, user, base_url) for photo in db.scalars(
            select(Multimedia).where(Multimedia.occurrence_id == row.occurrence_id).order_by(Multimedia.created_at, Multimedia.media_id)
        ).all()]
    else:
        photo = db.scalar(select(Multimedia).join(Occurrence, Multimedia.occurrence_id == Occurrence.occurrence_id)
                          .where(Occurrence.taxon_id == row.taxon_id).order_by(Multimedia.created_at, Multimedia.media_id).limit(1))
        if photo:
            data["image"] = media_data(db, photo, user, base_url).get("source_url")
    data["morphology"] = [as_dict(fact) for fact in db.scalars(select(MorphologyFact).where(
        MorphologyFact.taxon_id == entity_id if kind == "taxon_ref" else MorphologyFact.occurrence_id == entity_id
    )).all()]
    return data


def media_data(db, photo, user, base_url):
    data = as_dict(photo)
    state = state_for(db, "multimedia", photo.media_id)
    if state:
        data.update(copy.deepcopy(state.payload))
        if user.role not in ("admin", "curator") and state.owner_id != user.user_web_id:
            data = private_fields(data)
    path = Path(photo.file_path)
    if not path.is_absolute():
        path = MEDIA_ROOT / path
    if path.is_file() and path.resolve().is_relative_to(MEDIA_ROOT):
        relative = path.resolve().relative_to(MEDIA_ROOT).as_posix()
        data["source_url"] = f"{base_url.rstrip('/')}/media/{relative}"
    # Never disclose filesystem paths in API responses.
    data.pop("file_path", None)
    return data


def replace_morphology(db, kind, entity_id, facts):
    seen = set()
    for fact in facts:
        expected = fact.taxon_id if kind == "taxon_ref" else fact.occurrence_id
        other = fact.occurrence_id if kind == "taxon_ref" else fact.taxon_id
        if expected != entity_id or other is not None or fact.measurement_type not in MORPHOLOGY_TYPE_ENUM.enums:
            raise HTTPException(422, "El rasgo morfológico o su vínculo no es válido.")
        if fact.measurement_type in seen or not fact.measurement_value.strip():
            raise HTTPException(422, "Los rasgos deben tener valor y no repetirse.")
        if fact.measurement_type == "diametro_sombrero" and fact.measurement_unit not in ("cm", "mm"):
            raise HTTPException(422, "El diámetro del sombrero requiere cm o mm.")
        seen.add(fact.measurement_type)
    column = MorphologyFact.taxon_id if kind == "taxon_ref" else MorphologyFact.occurrence_id
    db.execute(delete(MorphologyFact).where(column == entity_id))
    for fact in facts:
        db.add(MorphologyFact(morphology_id=uuid.uuid4(), **fact.model_dump()))


def save_taxon(db, body, user):
    taxon_id = body.taxon.taxon_id
    row = db.get(TaxonRef, taxon_id)
    if row:
        require_edit(db, "taxon_ref", taxon_id, user)
    duplicate = db.scalar(select(TaxonRef).where(
        TaxonRef.scientific_name.ilike(body.taxon.scientific_name.strip()), TaxonRef.taxon_id != taxon_id
    ))
    if duplicate:
        raise HTTPException(409, "Este nombre científico ya está registrado.")
    if not body.taxon.scientific_name.strip() or not body.taxon.kingdom.strip():
        raise HTTPException(422, "Completa nombre científico y reino.")
    for knowledge in body.knowledge:
        if knowledge.get("source", {}).get("consent_given") is not True:
            raise HTTPException(422, "Una entrevista requiere consentimiento otorgado.")
    state, _ = ownership(db, "taxon_ref", taxon_id, user)
    values = body.taxon.model_dump(exclude={"taxon_id"})
    values["scientific_name"] = " ".join(values["scientific_name"].split())
    if row is None:
        row = TaxonRef(taxon_id=taxon_id)
        db.add(row)
    previous = as_dict(row) if row.scientific_name else None
    for key, value in values.items():
        setattr(row, key, value)
    extras = body.model_dump(mode="json", exclude={"taxon", "morphology"})
    extras["morphology_snapshot"] = [fact.model_dump(mode="json") for fact in body.morphology]
    changed = previous != as_dict(row) or state.payload != extras
    state.payload = extras
    db.flush()
    replace_morphology(db, "taxon_ref", taxon_id, body.morphology)
    # Edits return to the review queue. A repeated identical PUT remains safe.
    if changed or not current_decision(db, "taxon_ref", taxon_id):
        audit(db, "taxon_ref", taxon_id, user)
    return row


def save_record(db, body, user):
    occurrence_id = body.occurrence.occurrence_id
    for key, enum in (("basis_of_record", BASIS_OF_RECORD_ENUM), ("occurrence_status", OCCURRENCE_STATUS_ENUM), ("identification_qualifier", ID_QUALIFIER_ENUM)):
        value = getattr(body.occurrence, key)
        if value is not None and value not in enum.enums:
            raise HTTPException(422, f"Valor no válido para {key}.")
    row = db.get(Occurrence, occurrence_id)
    if row:
        require_edit(db, "occurrence", occurrence_id, user)
    if body.occurrence.taxon_id and not db.get(TaxonRef, body.occurrence.taxon_id):
        raise HTTPException(404, "El taxón seleccionado no existe.")
    event = db.get(Event, body.event.event_id)
    location = db.get(Location, body.location.location_id)
    # An aggregate must never overwrite a location/event belonging to another record.
    if (event and (not row or row.event_id != event.event_id)) or (location and (not event or event.location_id != location.location_id)):
        raise HTTPException(409, "Ese evento o ubicación pertenece a otro registro. Crea identificadores propios.")
    if event and db.scalar(select(Occurrence.occurrence_id).where(Occurrence.event_id == event.event_id, Occurrence.occurrence_id != occurrence_id)):
        raise HTTPException(409, "No se puede modificar un evento compartido desde este formulario.")
    if location and db.scalar(select(Event.event_id).where(Event.location_id == location.location_id, Event.event_id != body.event.event_id)):
        raise HTTPException(409, "No se puede modificar una ubicación compartida desde este formulario.")
    state, owner = ownership(db, "occurrence", occurrence_id, user, body.owner_id)
    recorded_by = " ".join(part for part in (owner.first_name, owner.last_name) if part)
    if not location:
        location = Location(location_id=body.location.location_id)
        db.add(location)
    values = body.location.model_dump(exclude={"location_id"})
    values["country_code"] = values["country"].upper()
    values["habitat"] = values["habitat"] if values["habitat"] in HABITAT_ENUM.enums else ("Other" if values["habitat"] else None)
    for key, value in values.items():
        setattr(location, key, value)
    db.flush()
    if not event:
        event = Event(event_id=body.event.event_id)
        db.add(event)
    values = body.event.model_dump(exclude={"event_id"})
    values["recorded_by"] = recorded_by
    for key, enum in (("event_type", EVENT_TYPE_ENUM), ("sampling_protocol", SAMPLING_PROTOCOL_ENUM), ("sampling_effort", SAMPLING_EFFORT_ENUM)):
        values[key] = values[key] if values[key] in enum.enums else None
    for key, value in values.items():
        setattr(event, key, value)
    db.flush()
    if row is None:
        row = Occurrence(occurrence_id=occurrence_id)
        db.add(row)
    values = body.occurrence.model_dump(exclude={"occurrence_id"})
    values["recorded_by"] = recorded_by
    for key, value in values.items():
        if key == "substrate":
            value = value if value in SUBSTRATE_ENUM.enums else ("Other" if value else None)
        setattr(row, key, value)
    seen_measurements = set()
    for measurement in body.measurements:
        event_id, record_id = measurement.get("event_id"), measurement.get("occurrence_id")
        if not ((event_id == str(event.event_id) and record_id is None) or (record_id == str(occurrence_id) and event_id is None)):
            raise HTTPException(422, "Cada medida debe pertenecer al evento o al hallazgo actual.")
        key = (bool(event_id), str(measurement.get("measurement_type") or "").strip().casefold())
        value = measurement.get("measurement_value")
        if not key[1] or value is None or not str(value).strip() or key in seen_measurements:
            raise HTTPException(422, "Completa variable y valor de cada medida.")
        seen_measurements.add(key)
    snapshot = body.model_dump(mode="json", exclude={"multimedia", "owner_id"})
    snapshot["event"]["recorded_by"] = recorded_by
    snapshot["occurrence"]["recorded_by"] = recorded_by
    changed = state.payload.get("snapshot") != snapshot
    state.payload = {"snapshot": snapshot, "location": body.location.model_dump(mode="json"),
                     "event": {**body.event.model_dump(mode="json"), "recorded_by": recorded_by},
                     "substrate": body.occurrence.substrate, "participants": body.participants,
                     "measurements": body.measurements}
    db.flush()
    replace_morphology(db, "occurrence", occurrence_id, body.morphology)
    if changed:
        audit(db, "occurrence", occurrence_id, user)
    return row


async def save_photos(db, occurrence, metadata, files, user, written):
    state = require_edit(db, "occurrence", occurrence.occurrence_id, user)
    ids = [item.media_id for item in metadata]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "No repitas el identificador de una fotografía.")
    staged = []
    for item in metadata:
        upload = files.get(str(item.media_id))
        if upload is None:
            raise HTTPException(422, "Falta el archivo de una fotografía.")
        content = await upload.read(MAX_PHOTO_BYTES + 1)
        if len(content) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "Cada fotografía debe pesar como máximo 10 MB.")
        try:
            with Image.open(io.BytesIO(content)) as image:
                image_format = image.format
                width, height = image.size
                if image_format not in ("JPEG", "PNG", "WEBP") or width > 32767 or height > 32767:
                    raise ValueError()
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            raise HTTPException(415, "El archivo no es una fotografía JPG, PNG o WebP válida.")
        sha = hashlib.sha256(content).hexdigest()
        existing = db.get(Multimedia, item.media_id)
        if existing:
            if existing.occurrence_id != occurrence.occurrence_id or existing.sha256_hash != sha:
                raise HTTPException(409, "El identificador de la fotografía ya está en uso.")
            staged.append(existing)
            continue
        if db.scalar(select(Multimedia.media_id).where(Multimedia.sha256_hash == sha)) or any(getattr(p, "sha256_hash", None) == sha for p in staged):
            raise HTTPException(409, "Esta fotografía ya está registrada.")
        photo_type = PHOTO_TYPES.get(item.photo_type, item.photo_type)
        if photo_type not in PHOTO_TYPE_ENUM.enums:
            raise HTTPException(422, "Tipo de fotografía inválido.")
        extension, mime = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}[image_format]
        relative = Path(str(occurrence.occurrence_id)) / f"{item.media_id}.{extension}"
        destination = MEDIA_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if hashlib.sha256(destination.read_bytes()).hexdigest() != sha:
                raise HTTPException(409, "Hay un archivo distinto con ese identificador.")
        else:
            with destination.open("xb") as output:
                output.write(content)
            written.append(destination)
        photo = Multimedia(media_id=item.media_id, occurrence_id=occurrence.occurrence_id, photo_type=photo_type,
                           file_name=Path(item.file_name.replace("\\", "/")).name, file_path=relative.as_posix(),
                           sha256_hash=sha, mime_format=mime, media_type="StillImage", photographer=item.photographer,
                           rights_holder=item.rights_holder, license=item.license, width_px=width, height_px=height,
                           capture_date=occurrence.event_date, created_at=dt.datetime.now(dt.timezone.utc))
        db.add(photo)
        db.add(ApplicationState(entity_type="multimedia", entity_id=item.media_id,
                                owner_id=state.owner_id if state else user.user_web_id, created_by_id=user.user_web_id,
                                payload={"photo_type": item.photo_type, "credits": item.credits}))
        staged.append(photo)
    db.flush()
    return staged
