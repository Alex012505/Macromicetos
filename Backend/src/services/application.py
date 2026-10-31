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
from models.EthnoSource import EthnoSource
from models.EthnoTaxonKnowledge import EthnoTaxonKnowledge
from models.EthnoUse import EthnoUse
from models.Event import Event, EVENT_TYPE_ENUM, SAMPLING_PROTOCOL_ENUM
from models.Location import Location
from models.MorphologyFact import MorphologyFact, MORPHOLOGY_TYPE_ENUM
from models.Multimedia import Multimedia, PHOTO_TYPE_ENUM
from models.MeasurementOrFact import MeasurementOrFact
from models.Occurrence import Occurrence, BASIS_OF_RECORD_ENUM, OCCURRENCE_STATUS_ENUM, ID_QUALIFIER_ENUM
from models.Party import EventParty, MediaParty, OccurrenceParty, Party, TaxonParty
from models.ScientificSource import ScientificSource
from models.ScientificTaxonLink import ScientificTaxonLink
from models.TaxonRef import TaxonRef
from models.UserWeb import UserWeb
from schemas.bibliographic_schema import SourceData
from schemas.socioecological_schema import (
    EthnoKnowledgeData, EthnoSourceData, EthnoSurveyData, EthnoUseData,
)
from settings import MEDIA_ROOT

MAX_PHOTO_BYTES = 10 * 1024 * 1024
PHOTO_TYPES = {"habitus": "voucher", "pileus": "cap"}
PHOTO_TYPES_REVERSE = {stored: sent for sent, stored in PHOTO_TYPES.items()}


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


# ---------------------------------------------------------------------------
# Capas normalizadas: lectura (bibliographic.* y socioecological.*)
# ---------------------------------------------------------------------------

def _source_payload(source):
    """Devuelve una referencia con la misma forma que SourceData."""
    return SourceData(
        source_id=source.source_id,
        source_type=source.source_type,
        title=source.title,
        authors=source.authors,
        year=source.pub_year,
        doi=source.doi,
        citation_apa=source.citation_apa,
        journal_or_publisher=source.journal_or_publisher,
        url=source.url,
        region_scope=source.region_scope,
        quality_level=source.quality_level,
        notes=source.notes,
    ).model_dump(mode="json")


def _survey_payload(source, knowledge, uses):
    """Devuelve una entrevista con la misma forma que EthnoSurveyData."""
    return EthnoSurveyData(
        source=EthnoSourceData(
            ethno_source_id=source.ethno_source_id,
            interview_date=source.interview_date,
            interviewer=source.interviewer,
            consent_given=source.consent_given,
            consent_type=source.consent_type,
            anonymity_level=source.anonymity_level,
            state_province=source.state_province,
            municipality=source.municipality,
            village=source.village,
            occupation=source.occupation,
            age_range=source.age_range,
            gender=source.gender,
            remarks=source.remarks,
        ),
        knowledge=EthnoKnowledgeData(
            knowledge_id=knowledge.ethno_know_id,
            ethno_source_id=knowledge.ethno_source_id,
            taxon_id=knowledge.taxon_id,
            knows_fungi=knowledge.knows_fungi,
            local_name=knowledge.local_name,
            learning_source=knowledge.learning_source,
            recognition_cues=knowledge.recognition_cues,
            found_in_places=knowledge.found_in_places,
            seasonality=knowledge.seasonality,
            months=knowledge.months,
            safety_practices=knowledge.safety_practices,
            myths_stories=knowledge.myths_stories,
            cultural_identity=knowledge.cultural_identity,
            recommendations=knowledge.recommendations,
        ),
        uses=[
            EthnoUseData(
                use_id=use.ethno_use_id,
                knowledge_id=use.ethno_know_id,
                taxon_id=use.taxon_id,
                uses_fungi=use.uses_fungi,
                use_category=use.use_category,
                preparation_method=use.preparation_method,
                ailment=use.ailment,
                dosage=use.dosage,
                contraindications=use.contraindications,
                importance=use.importance,
            )
            for use in uses
        ],
    ).model_dump(mode="json")


def taxon_sources(db, taxon_id):
    """Referencias vinculadas al taxón (cualquier tipo de mención)."""
    source_ids = db.scalars(
        select(ScientificTaxonLink.source_id).where(ScientificTaxonLink.taxon_id == taxon_id)
    ).all()
    if not source_ids:
        return []
    rows = db.scalars(
        select(ScientificSource)
        .where(ScientificSource.source_id.in_(set(source_ids)))
        .order_by(ScientificSource.pub_year.nulls_last(), ScientificSource.title)
    ).all()
    return [_source_payload(row) for row in rows]


def taxon_knowledge(db, taxon_id):
    """Entrevistas del taxón, cada una con sus usos."""
    rows = db.scalars(
        select(EthnoTaxonKnowledge)
        .where(EthnoTaxonKnowledge.taxon_id == taxon_id)
        .order_by(EthnoTaxonKnowledge.created_at, EthnoTaxonKnowledge.ethno_know_id)
    ).all()
    payloads = []
    for knowledge in rows:
        source = db.get(EthnoSource, knowledge.ethno_source_id)
        if source is None:
            continue
        uses = db.scalars(
            select(EthnoUse)
            .where(EthnoUse.ethno_know_id == knowledge.ethno_know_id)
            .order_by(EthnoUse.created_at, EthnoUse.ethno_use_id)
        ).all()
        payloads.append(_survey_payload(source, knowledge, uses))
    return payloads


def _party_payload(party):
    return {
        "party_id": str(party.party_id),
        "given_name": party.given_name,
        "family_name": party.family_name,
        "display_name": (party.display_name or "").strip() or None,
        "orcid": party.orcid,
        "affiliation": party.affiliation,
        "contact_email": party.contact_email,
    }


def taxon_participants(db, taxon_id):
    """Responsables del taxón desde shared.party + shared.taxon_party."""
    rows = db.execute(
        select(Party)
        .join(TaxonParty, TaxonParty.party_id == Party.party_id)
        .where(TaxonParty.taxon_id == taxon_id)
        .order_by(TaxonParty.created_at, Party.display_name)
    ).scalars().all()
    return [
        {
            "party": _party_payload(party),
            # shared.taxon_party no guarda rol.
            "party_role": None,
            "scope": "taxon",
            "is_primary": False,
        }
        for party in rows
    ]


def _party_rows(db, model, column, entity_id, scope):
    """Vínculos de una entidad con su rol y su ámbito."""
    rows = db.execute(
        select(model, Party)
        .join(Party, Party.party_id == model.party_id)
        .where(column == entity_id)
        .order_by(model.created_at, Party.display_name)
    ).all()
    return [
        {
            "party": _party_payload(party),
            "party_role": link.party_role,
            "scope": scope,
            "is_primary": bool(link.is_primary),
        }
        for link, party in rows
    ]


def record_participants(db, occurrence_id, event_id):
    """Participantes del hallazgo y de su salida de campo."""
    return (_party_rows(db, OccurrenceParty, OccurrenceParty.occurrence_id, occurrence_id, "occurrence")
            + _party_rows(db, EventParty, EventParty.event_id, event_id, "event"))


def media_credits(db, media_id):
    """Créditos de una fotografía con la forma del contrato PhotoCredit."""
    rows = db.execute(
        select(MediaParty, Party)
        .join(Party, Party.party_id == MediaParty.party_id)
        .where(MediaParty.media_id == media_id)
        .order_by(MediaParty.created_at, Party.display_name)
    ).all()
    return [
        {
            "party": _party_payload(party),
            "credit_role": link.party_role,
            "is_primary": bool(link.is_primary),
        }
        for link, party in rows
    ]


# ---------------------------------------------------------------------------
# Capas normalizadas: escritura
# ---------------------------------------------------------------------------

def _sync_parties(db, model, column, entity_id, links):
    """Sincroniza una tabla shared.*_party.

    ``links`` es una secuencia de ``(PartyData, rol, is_primary)``. Las filas
    vacías que el formulario deja al pulsar "añadir" se ignoran en vez de
    romper el guardado.
    """
    existing = db.scalars(select(model).where(column == entity_id)).all()
    by_party = {row.party_id: row for row in existing}
    kept = set()
    for data, role, is_primary in links:
        if not any((data.given_name, data.family_name, data.display_name)):
            continue
        party = _upsert_party(db, data)
        row = by_party.get(party.party_id)
        if row is None:
            row = model(**{column.key: entity_id, "party_id": party.party_id})
            db.add(row)
        row.party_role = role
        row.is_primary = bool(is_primary)
        kept.add(party.party_id)
    for row in existing:
        if row.party_id not in kept:
            db.delete(row)
    db.flush()

def _upsert_source(db, item):
    title = (item.title or "").strip()
    if not title:
        raise HTTPException(422, "Cada referencia bibliográfica requiere un título.")
    source_id = item.source_id or uuid.uuid4()
    if item.doi:
        clash = db.scalar(select(ScientificSource.source_id).where(
            ScientificSource.doi == item.doi, ScientificSource.source_id != source_id
        ))
        if clash:
            raise HTTPException(409, "Ese DOI ya está registrado en otra referencia.")
    row = db.get(ScientificSource, source_id)
    if row is None:
        row = ScientificSource(source_id=source_id)
        db.add(row)
    # El formulario siempre envía un tipo; si un cliente antiguo lo omite, la
    # columna NOT NULL necesita un valor y "other" es el menos engañoso.
    row.source_type = item.source_type or "other"
    row.title = title
    row.authors = item.authors
    row.pub_year = item.year
    row.doi = item.doi
    row.citation_apa = item.citation_apa
    row.journal_or_publisher = item.journal_or_publisher
    row.url = item.url
    row.region_scope = item.region_scope
    row.quality_level = item.quality_level
    row.notes = item.notes
    db.flush()
    return row


def _replace_sources(db, taxon_id, sources):
    """Sincroniza las referencias del taxón.

    scientific_source es compartida entre taxones, así que no se borra: solo se
    retiran los vínculos de tipo 'taxonomy', que son los que gestiona el
    formulario. Los vínculos importados (ecology, use, distribution...) se
    conservan.
    """
    links = db.scalars(
        select(ScientificTaxonLink).where(ScientificTaxonLink.taxon_id == taxon_id)
    ).all()
    linked = {link.source_id for link in links}
    kept = set()
    for item in sources:
        row = _upsert_source(db, item)
        kept.add(row.source_id)
        if row.source_id not in linked:
            db.add(ScientificTaxonLink(
                taxon_source_link_id=uuid.uuid4(),
                taxon_id=taxon_id,
                source_id=row.source_id,
                mention_type="taxonomy",
            ))
            linked.add(row.source_id)
    for link in links:
        if link.mention_type == "taxonomy" and link.source_id not in kept:
            db.delete(link)


def _upsert_ethno_source(db, item):
    interviewer = (item.interviewer or "").strip()
    if not interviewer:
        raise HTTPException(422, "Cada entrevista requiere el nombre del entrevistador.")
    source_id = item.ethno_source_id or uuid.uuid4()
    row = db.get(EthnoSource, source_id)
    if row is None:
        row = EthnoSource(ethno_source_id=source_id)
        db.add(row)
    row.interviewer = interviewer
    row.interview_date = item.interview_date or dt.datetime.now(dt.timezone.utc)
    row.consent_given = item.consent_given is True
    row.consent_type = item.consent_type
    row.anonymity_level = item.anonymity_level or "anonymous"
    row.state_province = item.state_province
    row.municipality = item.municipality
    row.village = item.village
    row.occupation = item.occupation
    row.age_range = item.age_range
    row.gender = item.gender
    row.remarks = item.remarks
    db.flush()
    return row


def _apply_knowledge(row, item):
    row.knows_fungi = item.knows_fungi
    row.local_name = item.local_name
    row.learning_source = item.learning_source
    row.recognition_cues = item.recognition_cues
    row.found_in_places = item.found_in_places
    row.seasonality = item.seasonality
    row.months = item.months
    row.safety_practices = item.safety_practices
    row.myths_stories = item.myths_stories
    row.cultural_identity = item.cultural_identity
    row.recommendations = item.recommendations


def _replace_uses(db, knowledge, uses):
    existing = db.scalars(
        select(EthnoUse).where(EthnoUse.ethno_know_id == knowledge.ethno_know_id)
    ).all()
    kept = set()
    for item in uses:
        if item.use_category is None:
            raise HTTPException(422, "Cada uso reportado necesita una categoría.")
        row = None
        if item.use_id:
            candidate = db.get(EthnoUse, item.use_id)
            if candidate is not None and candidate.ethno_know_id == knowledge.ethno_know_id:
                row = candidate
            elif candidate is None:
                row = EthnoUse(ethno_use_id=item.use_id, ethno_know_id=knowledge.ethno_know_id)
                db.add(row)
        if row is None:
            row = EthnoUse(ethno_know_id=knowledge.ethno_know_id)
            db.add(row)
        row.taxon_id = knowledge.taxon_id
        row.use_category = item.use_category
        row.uses_fungi = item.uses_fungi
        row.preparation_method = item.preparation_method
        row.ailment = item.ailment
        row.dosage = item.dosage
        row.contraindications = item.contraindications
        row.importance = item.importance
        kept.add(row.ethno_use_id)
    for row in existing:
        if row.ethno_use_id not in kept:
            db.delete(row)
    db.flush()


def _replace_knowledge(db, taxon_id, surveys):
    """Sincroniza entrevistas y usos del taxón.

    La clave natural es (ethno_source_id, taxon_id): una entrevista no puede
    repetirse para el mismo taxón. Si el cliente manda un knowledge_id libre se
    respeta; si ya está en uso se genera otro.
    """
    existing = db.scalars(
        select(EthnoTaxonKnowledge).where(EthnoTaxonKnowledge.taxon_id == taxon_id)
    ).all()
    by_source = {row.ethno_source_id: row for row in existing}
    kept, seen = set(), set()
    for survey in surveys:
        source = _upsert_ethno_source(db, survey.source)
        if source.ethno_source_id in seen:
            raise HTTPException(422, "Una entrevista no puede repetirse para el mismo taxón.")
        seen.add(source.ethno_source_id)
        row = by_source.get(source.ethno_source_id)
        if row is None and survey.knowledge.knowledge_id:
            candidate = db.get(EthnoTaxonKnowledge, survey.knowledge.knowledge_id)
            if candidate is not None and candidate.taxon_id == taxon_id \
                    and candidate.ethno_source_id == source.ethno_source_id:
                row = candidate
        if row is None:
            knowledge_id = survey.knowledge.knowledge_id
            if knowledge_id and db.get(EthnoTaxonKnowledge, knowledge_id) is not None:
                knowledge_id = None  # ya pertenece a otro par entrevista/taxón
            row = EthnoTaxonKnowledge(
                ethno_know_id=knowledge_id or uuid.uuid4(),
                ethno_source_id=source.ethno_source_id,
                taxon_id=taxon_id,
            )
            db.add(row)
        _apply_knowledge(row, survey.knowledge)
        # El formulario pone "recomendaciones" en cada uso; la columna vive en
        # el conocimiento. Se conserva el texto de los usos si no hay uno propio.
        extras = [use.recommendations.strip() for use in survey.uses
                  if use.recommendations and use.recommendations.strip()]
        if not row.recommendations and extras:
            row.recommendations = "\n".join(dict.fromkeys(extras))
        db.flush()
        kept.add(row.ethno_know_id)
        _replace_uses(db, row, survey.uses)
    for row in existing:
        if row.ethno_know_id not in kept:
            db.delete(row)
    db.flush()


def _upsert_party(db, data):
    given = (data.given_name or "").strip()
    family = (data.family_name or "").strip() or None
    display = (data.display_name or "").strip()
    if not given and display:
        parts = display.split(None, 1)
        given = parts[0]
        family = family or (parts[1] if len(parts) > 1 else None)
    if not given:
        raise HTTPException(422, "Cada participante requiere un nombre.")
    party_id = data.party_id or uuid.uuid4()
    row = db.get(Party, party_id)
    if row is None:
        row = Party(party_id=party_id)
        db.add(row)
    row.given_name = given
    row.family_name = family
    row.orcid = data.orcid
    row.affiliation = data.affiliation
    row.contact_email = data.contact_email
    # display_name es GENERATED ALWAYS: nunca se asigna.
    db.flush()
    return row


def _replace_participants(db, taxon_id, participants):
    existing = db.scalars(
        select(TaxonParty).where(TaxonParty.taxon_id == taxon_id)
    ).all()
    linked = {row.party_id for row in existing}
    kept = set()
    for item in participants:
        party = _upsert_party(db, item.party)
        kept.add(party.party_id)
        if party.party_id not in linked:
            db.add(TaxonParty(taxon_id=taxon_id, party_id=party.party_id))
            linked.add(party.party_id)
    for row in existing:
        if row.party_id not in kept:
            db.delete(row)


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
        # Los participantes viven en shared.occurrence_party y shared.event_party.
        data["participants"] = record_participants(db, row.occurrence_id, row.event_id) or extra.get("participants", [])
        if not sensitive:
            data["participants"] = private_fields(data["participants"])
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
        # Las tablas normalizadas son la fuente de verdad. El JSON queda solo
        # como respaldo para fichas guardadas antes de esta versión.
        data["sources"] = taxon_sources(db, row.taxon_id) or extra.get("sources", [])
        data["knowledge"] = taxon_knowledge(db, row.taxon_id) or extra.get("knowledge", [])
        data["participants"] = taxon_participants(db, row.taxon_id) or extra.get("participants", [])
        if not sensitive:
            data["participants"] = private_fields(data["participants"])
            data.pop("knowledge", None)
    data["morphology"] = [as_dict(fact) for fact in db.scalars(select(MorphologyFact).where(
        MorphologyFact.taxon_id == entity_id if kind == "taxon_ref" else MorphologyFact.occurrence_id == entity_id
    )).all()]
    return data


def media_data(db, photo, user, base_url):
    data = as_dict(photo)
    state = state_for(db, "multimedia", photo.media_id)
    if state:
        data.update(copy.deepcopy(state.payload))
    # El formulario envía "habitus"/"pileus"; la columna guarda el valor del
    # enum. Se devuelve el valor original para que el select lo reconozca.
    data["photo_type"] = PHOTO_TYPES_REVERSE.get(photo.photo_type, photo.photo_type)
    # Los créditos viven en shared.media_party; el JSON solo respalda fichas
    # subidas antes de existir esa tabla.
    data["credits"] = media_credits(db, photo.media_id) or data.get("credits", [])
    if user.role not in ("admin", "curator") and not (state and state.owner_id == user.user_web_id):
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
        if knowledge.source.consent_given is not True:
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
    snapshot = body.model_dump(mode="json", exclude={"taxon", "morphology"})
    previous_snapshot = state.payload.get("snapshot")
    # sources/knowledge/participants se normalizan; el JSON solo conserva el
    # snapshot para detectar cambios y la morfología para el respaldo.
    _replace_sources(db, taxon_id, body.sources)
    _replace_knowledge(db, taxon_id, body.knowledge)
    _replace_participants(db, taxon_id, body.participants)
    state.payload = {
        "snapshot": snapshot,
        "morphology_snapshot": [fact.model_dump(mode="json") for fact in body.morphology],
    }
    db.flush()
    replace_morphology(db, "taxon_ref", taxon_id, body.morphology)
    changed = previous != as_dict(row) or previous_snapshot != snapshot
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
    for key, value in values.items():
        setattr(location, key, value)
    db.flush()
    if not event:
        event = Event(event_id=body.event.event_id)
        db.add(event)
    values = body.event.model_dump(exclude={"event_id"})
    values["recorded_by"] = recorded_by
    for key, enum in (("event_type", EVENT_TYPE_ENUM), ("sampling_protocol", SAMPLING_PROTOCOL_ENUM)):
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
        setattr(row, key, value)
    seen_measurements = set()
    for measurement in body.measurements:
        event_id, record_id = measurement.event_id, measurement.occurrence_id
        if not ((event_id == event.event_id and record_id is None) or (record_id == occurrence_id and event_id is None)):
            raise HTTPException(422, "Cada medida debe pertenecer al evento o al hallazgo actual.")
        key = (bool(event_id), measurement.measurement_type.strip().casefold())
        value = measurement.measurement_value
        if not key[1] or value is None or not str(value).strip() or key in seen_measurements:
            raise HTTPException(422, "Completa variable y valor de cada medida.")
        seen_measurements.add(key)
    snapshot = body.model_dump(mode="json", exclude={"multimedia", "owner_id"})
    snapshot["event"]["recorded_by"] = recorded_by
    snapshot["occurrence"]["recorded_by"] = recorded_by
    changed = state.payload.get("snapshot") != snapshot
    # Ubicación, evento, sustrato y participantes ya tienen tabla propia. El
    # JSON solo conserva el snapshot (para detectar cambios) y las medidas
    # libres, que no caben en ecological.measurement_or_fact (tipo enum y
    # valor numérico) y por eso siguen aquí.
    state.payload = {"snapshot": snapshot,
                     "measurements": [measurement.model_dump(mode="json") for measurement in body.measurements]}
    db.flush()
    _sync_parties(db, OccurrenceParty, OccurrenceParty.occurrence_id, occurrence_id,
                  [(person.party, person.party_role, person.is_primary)
                   for person in body.participants if person.scope != "event"])
    _sync_parties(db, EventParty, EventParty.event_id, event.event_id,
                  [(person.party, person.party_role, person.is_primary)
                   for person in body.participants if person.scope == "event"])
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
            _sync_parties(db, MediaParty, MediaParty.media_id, existing.media_id,
                          [(credit.party, credit.credit_role, credit.is_primary) for credit in item.credits])
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
                                payload={}))
        _sync_parties(db, MediaParty, MediaParty.media_id, item.media_id,
                      [(credit.party, credit.credit_role, credit.is_primary) for credit in item.credits])
        staged.append(photo)
    db.flush()
    return staged
