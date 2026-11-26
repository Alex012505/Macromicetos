#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
import_corte1.py — Carga los datos reales del proyecto en la base del aplicativo Macromicetos.

Importa (por capas):
  1. Taxones        -> shared.taxon_ref (une la lista maestra GBIF con la lista curada)
  2. Ocurrencias GBIF -> ecological.location / event / occurrence (occurrence.txt)
  3. Multimedia      -> ecological.multimedia (multimedia.txt, solo URL, sin descarga)
  4. Morfología      -> ecological.morphology_fact (Capa_morfologica.xlsx)
  5. Bibliografía    -> bibliographic.* (Capa_bibliografica.xlsx)
  6. Etnomicología   -> socioecological.* (Capa_etnomicologica.xlsx)

Las capas 5 y 6 se importan en TABLAS NORMALIZADAS (no en JSON). Aplica primero
restore_capas.sql para crearlas; si no existen, la bibliografía cae a un respaldo
en application_state (JSON) y la etnomicológica se omite, con un aviso.

Requisito: ejecutar DESDE LA RAÍZ del repo Macromicetos (alex012505/Macromicetos),
con Backend/.env ya configurado (python Backend/setup_postgres.py) y, de preferencia,
un administrador creado (Backend/manage.py create-admin). El script reutiliza los
modelos SQLAlchemy del aplicativo para garantizar que el esquema coincida.

Opciones de taxones:
  --taxon-ref PATH            lista curada (ej. Lista_especies_macrohongos_orinoquia.xlsx),
                              primera hoja; puede repetirse.
  --taxon-sheet SHEET         hoja del --taxon-ref (por defecto la primera).
  --taxon-master PATH         lista maestra GBIF (ej. Base_Datos_Nuclear.xlsx).
  --taxon-master-sheet SHEET  hoja del --taxon-master (por defecto 'sp').
  Las listas se UNEN por nombre científico: la maestra aporta el grueso (802 especies)
  y la curada añade las especies de literatura y sus citas (Cita_...). Sin duplicados.

Modo simulación (sin tocar la BD, solo lee y valida los archivos):
    python import_corte1.py --dry-run --taxon-master ... --taxon-ref ... --occurrence ... --multimedia ... --biblio ...

Ejecución real (ver importar_datos_reales.ps1):
    .\\Backend\\.venv\\Scripts\\python.exe import_corte1.py ^
        --taxon-master "..\\03_Equipo_de_Trabajo\\KAREN\\BD\\Base_Datos_Nuclear.xlsx" --taxon-master-sheet sp ^
        --taxon-ref    "..\\03_Equipo_de_Trabajo\\WENDY\\Lista_especies_macrohongos_orinoquia.xlsx" ^
        --occurrence   "...\\occurrence.txt" ^
        --multimedia   "...\\multimedia.txt" ^
        --biblio       "...\\Capa_bibliografica.xlsx" ^
        --owner-email  "correo-del-admin@..."
"""

from __future__ import annotations

import argparse
import re
import sys
import uuid
from datetime import date as dt_date
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Utilidades escalares (independientes de la BD)
# ---------------------------------------------------------------------------

def _str_or_none(val):
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _safe_int(val):
    s = _str_or_none(val)
    if s is None:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _safe_float(val):
    s = _str_or_none(val)
    if s is None:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_date(val):
    dt = _parse_datetime(val)
    return dt.date() if dt else None


def _parse_datetime(val):
    s = _str_or_none(val)
    if s is None:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _extract_binomial(full_name):
    """'Macrocybe titans (H.E.Bigelow…) Pegler' -> 'Macrocybe titans'."""
    cleaned = re.sub(r"\(.*?\)", "", full_name).strip()
    parts = cleaned.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return parts[0] if parts else full_name


# ---------------------------------------------------------------------------
# Lectura de taxones (una o varias listas, unidas sin duplicados)
# ---------------------------------------------------------------------------

_CITA_COL = "Cita_dentro_de_la_carpeta_LITERATURA_(WENDY)"


def _read_taxon_file(path, sheet=None):
    kwargs = {} if sheet is None else {"sheet_name": sheet}
    df = pd.read_excel(path, dtype=str, keep_default_na=False, **kwargs)
    df.columns = [c.strip() for c in df.columns]
    rows: dict[str, dict] = {}
    for _, row in df.iterrows():
        species = _str_or_none(row.get("species"))
        if not species:
            continue
        species = " ".join(species.split())
        key = species.lower()
        parts = species.split()
        item = {
            "scientific_name": species,
            "taxon_rank": "species",
            "kingdom": "Fungi",
            "phylum": _str_or_none(row.get("phylum")),
            "class_name": _str_or_none(row.get("class")),
            "order_name": _str_or_none(row.get("order")),
            "family": _str_or_none(row.get("family")),
            "genus": _str_or_none(row.get("genus")),
            "specific_epithet": parts[1] if len(parts) >= 2 else None,
            "taxon_remarks": _str_or_none(row.get(_CITA_COL)),
        }
        if key in rows:
            for k, v in item.items():
                if not rows[key].get(k) and v:
                    rows[key][k] = v
        else:
            rows[key] = item
    return rows


def load_taxones(sources):
    """sources: lista de tuplas (path, sheet_or_None). Se unen por nombre científico."""
    merged: dict[str, dict] = {}
    for path, sheet in sources:
        for key, item in _read_taxon_file(path, sheet).items():
            if key in merged:
                for k, v in item.items():
                    if not merged[key].get(k) and v:
                        merged[key][k] = v
            else:
                merged[key] = item
    return list(merged.values())


# ---------------------------------------------------------------------------
# Lectura de ocurrencias y multimedia GBIF (independiente de la BD)
# ---------------------------------------------------------------------------

def load_occurrences(occ_path, mm_path):
    """occurrence.txt + multimedia.txt -> (ocurrencias, índice gbifID->fotos)."""
    occ = pd.read_csv(occ_path, sep="\t", dtype=str, keep_default_na=False,
                      encoding="utf-8", low_memory=False)
    mm = pd.read_csv(mm_path, sep="\t", dtype=str, keep_default_na=False,
                     encoding="utf-8", low_memory=False)

    media_index: dict[str, list[dict]] = {}
    if "gbifID" in mm.columns:
        for _, m in mm.iterrows():
            gid = _str_or_none(m.get("gbifID"))
            if not gid:
                continue
            media_index.setdefault(gid, []).append({
                "source_url": _str_or_none(m.get("identifier")),
                "creator": _str_or_none(m.get("creator")),
                "created": _parse_datetime(_str_or_none(m.get("created"))),
                "license": _str_or_none(m.get("license")),
                "rights_holder": _str_or_none(m.get("rightsHolder")),
                "mime_format": _str_or_none(m.get("format")),
            })

    ocurrencias = []
    for _, row in occ.iterrows():
        gid = _str_or_none(row.get("gbifID"))
        if not gid:
            continue
        year = _safe_int(row.get("year"))
        month = _safe_int(row.get("month")) or 1
        day = _safe_int(row.get("day")) or 1
        event_date = _parse_date(_str_or_none(row.get("eventDate")))
        if event_date is None and year:
            try:
                event_date = dt_date(year, month, day)
            except ValueError:
                event_date = dt_date(year, 1, 1)
        if event_date is None:
            event_date = dt_date(1900, 1, 1)

        lat = _safe_float(row.get("decimalLatitude"))
        lon = _safe_float(row.get("decimalLongitude"))
        locality = _str_or_none(row.get("locality"))
        if not locality and lat is not None and lon is not None:
            locality = f"coord_{round(lat, 4)}_{round(lon, 4)}"

        ocurrencias.append({
            "gbif_id": gid,
            "verbatim_scientific_name": _str_or_none(row.get("scientificName")),
            "binomial": _extract_binomial(_str_or_none(row.get("scientificName")) or ""),
            "basis_of_record_raw": (_str_or_none(row.get("basisOfRecord")) or "HUMAN_OBSERVATION").upper(),
            "occurrence_status_raw": (_str_or_none(row.get("occurrenceStatus")) or "PRESENT").upper(),
            "recorded_by": _str_or_none(row.get("recordedBy")),
            "identified_by": _str_or_none(row.get("identifiedBy")),
            "event_date_dt": event_date,
            "event_datetime": _parse_datetime(_str_or_none(row.get("eventDate"))),
            "individual_count": _safe_int(row.get("individualCount")),
            "occurrence_remarks": _str_or_none(row.get("occurrenceRemarks")),
            "state_province": _str_or_none(row.get("stateProvince")),
            "municipality": _str_or_none(row.get("municipality")),
            "locality": locality,
            "decimal_latitude": lat,
            "decimal_longitude": lon,
            "coordinate_uncertainty_m": _safe_float(row.get("coordinateUncertaintyInMeters")),
            "elevation_m": _safe_float(row.get("elevation")),
        })
    return ocurrencias, media_index


def load_biblio(path):
    """biblio_layer.xlsx / Capa_bibliografica.xlsx -> {taxon_name: [fuentes]}."""
    if not path or not Path(path).is_file():
        return {}
    xl = pd.ExcelFile(path)
    sheets = {}
    for name in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=name, dtype=str, keep_default_na=False)
        df.columns = [c.strip() for c in df.columns]
        sheets[name.strip().lower().replace(" ", "_")] = df

    sources = {}
    src_df = sheets.get("scientific_source", pd.DataFrame())
    for _, row in src_df.iterrows():
        key = _str_or_none(row.get("sourceID"))
        if not key:
            continue
        sources[key] = {
            "source_id": key,
            "source_type": _str_or_none(row.get("source_type")) or "other",
            "title": _str_or_none(row.get("title")),
            "authors": _str_or_none(row.get("authors")),
            "year": _safe_int(row.get("pub_year")),
            "doi": _clean_doi(_str_or_none(row.get("doi"))),
        }

    taxon_sources: dict[str, list[dict]] = {}
    for sheet in ("scientific_taxon_link", "scientific_use", "scientific_ecology"):
        df = sheets.get(sheet, pd.DataFrame())
        for _, row in df.iterrows():
            taxon = _str_or_none(row.get("taxonID"))
            src_key = _str_or_none(row.get("sourceID"))
            if not taxon or src_key not in sources:
                continue
            src = sources[src_key]
            if any(s["source_id"] == src["source_id"] for s in taxon_sources.setdefault(taxon, [])):
                continue
            taxon_sources[taxon].append(src)
    return taxon_sources


def _clean_doi(raw):
    if not raw:
        return None
    doi = raw.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi.org/"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
    return doi or None


def load_morphology(path):
    """Capa_morfologica.xlsx (hoja 'sp') -> {especie: [(measurement_type, valor), ...]}."""
    if not path or not Path(path).is_file():
        return {}
    xl = pd.ExcelFile(path)
    sheet = "sp" if "sp" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    result: dict[str, list[tuple[str, str]]] = {}
    for _, row in df.iterrows():
        species = _str_or_none(row.get("species"))
        if not species:
            continue
        facts = []
        for col, mtype in MORPHOLOGY_COLUMN_MAP.items():
            if col in df.columns:
                val = _str_or_none(row.get(col))
                if val:
                    facts.append((mtype, val))
        if facts:
            result[" ".join(species.split()).lower()] = facts
    return result


# ---------------------------------------------------------------------------
# Importación a la BD (requiere el repo del aplicativo)
# ---------------------------------------------------------------------------

_BASIS_MAP = {"HUMAN_OBSERVATION": "HumanObservation", "PRESERVED_SPECIMEN": "PreservedSpecimen",
              "MATERIAL_SAMPLE": "MaterialSample", "MACHINE_OBSERVATION": "MachineObservation",
              "LIVING_SPECIMEN": "LivingSpecimen", "FOSSIL_SPECIMEN": "FossilSpecimen",
              "OCCURRENCE": "Occurrence"}
_STATUS_MAP = {"PRESENT": "present", "ABSENT": "absent"}

# Columnas de Capa_morfologica.xlsx -> measurement_type del enum morphology_type_enum
MORPHOLOGY_COLUMN_MAP = {
    "tipo de himenio": "tipo_himenio",
    "tipo de láminas": "tipo_laminas",
    "forma de poros": "forma_poros",
    "sombrero (preguntar si se va a medir)": "diametro_sombrero",
    "forma del sombrero": "forma_sombrero",
    "superficie del sombrero": "superficie_sombrero",
    "borde del sombrero": "borde_sombrero",
    "color del sombrero": "color_sombrero",
    "forma del pie": "forma_pie",
    "color del pie": "color_pie",
    "posicion del pie respecto al sombrero": "posicion_pie",
    "ornamentacion del pie": "ornamentacion_pie",
    "superificie del pie": "superficie_pie",
    "anillo": "presencia_anillo",
    "tipo de anillo": "tipo_anillo",
    "volva": "presencia_volva",
    "cambio de color al corte": "cambio_color_corte",
    "habito de crecimiento": "habito_crecimiento",
}


def _import_backend(backend_src):
    sys.path.insert(0, str(backend_src))
    from database.Base import SessionLocal, initialize_database
    from models.TaxonRef import TaxonRef
    from models.Location import Location
    from models.Event import Event
    from models.Occurrence import Occurrence
    from models.Multimedia import Multimedia
    from models.MorphologyFact import MorphologyFact
    from models.ApplicationState import ApplicationState
    from models.CurationDecision import CurationDecision
    from models.UserWeb import UserWeb
    return (SessionLocal, initialize_database, TaxonRef, Location, Event,
            Occurrence, Multimedia, MorphologyFact, ApplicationState,
            CurationDecision, UserWeb)


def _owner_id(session, UserWeb, email):
    if not email:
        return None
    user = session.query(UserWeb).filter(UserWeb.email == email.strip().lower()).first()
    if user is None:
        raise SystemExit(f"No existe un usuario con correo {email!r}. Crea el admin primero: "
                         "Backend/manage.py create-admin --email <correo> --first-name <nombre>")
    return user.user_web_id


# =============================================================================
# Normalización de valores en español -> valores de los enums
# =============================================================================

def _norm(raw, mapping, default=None):
    s = _str_or_none(raw)
    if s is None:
        return default
    key = re.sub(r"[\s\-]+", "_", s.strip().lower()).rstrip("_.,;:")
    return mapping.get(key, default)


_SOURCE_TYPE = {"article": "article", "book": "book", "book_chapter": "book_chapter",
                "thesis": "thesis", "report": "report", "dataset": "dataset",
                "preprint": "preprint", "conference_paper": "conference_paper",
                "field_guide": "field_guide", "other": "other"}
_REGION = {"global": "global", "latam": "latam", "colombia": "colombia", "andes": "andes",
           "orinoco": "orinoco", "amazonia": "amazonia", "other": "other"}
_QUALITY = {"alta": "high", "alto": "high", "media": "medium", "medio": "medium",
            "baja": "low", "bajo": "low", "high": "high", "medium": "medium", "low": "low"}
_MENTION = {"taxonomy": "taxonomy", "taxonomia": "taxonomy", "taxonomía": "taxonomy",
            "ecology": "ecology", "ecologia": "ecology", "ecología": "ecology",
            "use": "use", "uso": "use", "usos": "use", "chemistry": "chemistry",
            "quimica": "chemistry", "química": "chemistry", "distribution": "distribution",
            "distribucion": "distribution", "distribución": "distribution",
            "morphology": "morphology", "morfologia": "morphology", "morfología": "morphology",
            "phylogeny": "phylogeny", "filogenia": "phylogeny", "biocontrol": "biocontrol"}
_SCI_USE = {"edible": "edible", "comestible": "edible", "medicinal": "medicinal",
            "antimicrobial": "antimicrobial", "antioxidant": "antioxidant",
            "enzyme": "enzyme", "bioremediation": "bioremediation", "agriculture": "agriculture",
            "biocontrol": "biocontrol", "dye": "dye", "tinte": "dye", "ritual": "ritual",
            "mythological": "mythological", "other": "other", "otro": "other"}
_EVIDENCE_TYPE = {"in_vitro": "in_vitro", "in_vivo": "in_vivo", "clinical": "clinical",
                  "observational": "observational", "review": "review", "meta_analysis": "meta_analysis"}
_ETHNO_USE = {"edible": "edible", "comestible": "edible", "medicinal": "medicinal",
              "hallucinogenic": "hallucinogenic", "alucinógeno": "hallucinogenic",
              "alucinogeno": "hallucinogenic", "ritual": "ritual", "dye": "dye",
              "tinte": "dye", "soil_improvement": "soil_improvement",
              "biological_control": "biological_control", "animal_feed": "animal_feed",
              "other": "other", "otro": "other"}
_IMPORTANCE = {"alta": "high", "media": "medium", "baja": "low",
               "high": "high", "medium": "medium", "low": "low"}
_LEARNING = {"familia": "family", "family": "family", "comunidad": "community",
             "community": "community", "personal_experience": "personal_experience",
             "experiencia_personal": "personal_experience", "books": "books",
             "libros": "books", "bibliografia": "books", "bibliografía": "books",
             "workshops": "workshops", "talleres": "workshops", "internet": "internet",
             "other": "other", "otro": "other"}
_CULTURAL = {"si": "yes", "sí": "yes", "yes": "yes", "no": "no", "partial": "partial",
             "parcial": "partial"}
_OCCUPATION = {"farmer": "farmer", "agricultor": "farmer", "fisher": "fisher",
               "pescador": "fisher", "indigenous_knowledge_holder": "indigenous_knowledge_holder",
               "rancher": "rancher", "ganadero": "rancher", "forester": "forester",
               "student": "student", "estudiante": "student", "teacher": "teacher",
               "profesor": "teacher", "other": "other", "otro": "other"}


def _bool_es(raw):
    s = _str_or_none(raw)
    if s is None:
        return None
    k = s.strip().lower()
    if k in ("si", "sí", "yes", "true", "1"):
        return True
    if k in ("no", "false", "0", "no reportado"):
        return False
    return None


def _has_table(engine, schema, name):
    from sqlalchemy import inspect
    return inspect(engine).has_table(name, schema=schema)


def _resolve_taxon_id(session, taxon_lookup, name):
    key = " ".join(name.split()).lower()
    taxon = taxon_lookup.get(key)
    return taxon.taxon_id if taxon else None


# =============================================================================
# Capa 3 — Bibliografía (tablas normalizadas) y Capa 2 — Etnomicológica
# =============================================================================

def import_bibliographic_tables(session, path, taxon_lookup):
    """Inserta Capa_bibliografica.xlsx en bibliographic.*. Devuelve conteos o None."""
    if not path or not Path(path).is_file():
        return None
    if not _has_table(session.bind, "bibliographic", "scientific_source"):
        return None
    from sqlalchemy import text

    xl = pd.ExcelFile(path)
    sheets = {}
    for name in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=name, dtype=str, keep_default_na=False)
        df.columns = [c.strip() for c in df.columns]
        sheets[name.strip().lower().replace(" ", "_")] = df

    counts = {"source": 0, "link": 0, "use": 0, "ecology": 0}
    source_ids: dict[str, uuid.UUID] = {}

    for _, row in sheets.get("scientific_source", pd.DataFrame()).iterrows():
        sid = _str_or_none(row.get("sourceID"))
        title = _str_or_none(row.get("title"))
        if not sid or not title:
            continue
        doi = _clean_doi(_str_or_none(row.get("doi")))
        existing = None
        if doi:
            existing = session.execute(text(
                "SELECT source_id FROM bibliographic.scientific_source WHERE doi = :doi"),
                {"doi": doi}).first()
        if existing is None:
            existing = session.execute(text(
                "SELECT source_id FROM bibliographic.scientific_source WHERE title = :t"),
                {"t": title}).first()
        if existing is not None:
            source_ids[sid] = existing[0]
            continue
        uid = uuid.uuid4()
        source_ids[sid] = uid
        stype = _norm(row.get("source_type"), _SOURCE_TYPE, "other")
        region = _norm(row.get("region_scope"), _REGION, "colombia")
        quality = _norm(row.get("quality_level"), _QUALITY, None)
        session.execute(text("""
            INSERT INTO bibliographic.scientific_source
              (source_id, source_type, citation_apa, pub_year, title, authors,
               journal_or_publisher, doi, url, region_scope, quality_level, notes)
            VALUES (:source_id, :source_type, :citation_apa, :pub_year, :title, :authors,
                    :journal, :doi, :url, :region_scope, :quality_level, :notes)
        """), {"source_id": uid, "source_type": stype,
               "citation_apa": _str_or_none(row.get("citation_apa")),
               "pub_year": _safe_int(row.get("pub_year")), "title": title,
               "authors": _str_or_none(row.get("authors")),
               "journal": _str_or_none(row.get("journal_or_publisher")),
               "doi": doi, "url": _str_or_none(row.get("url")),
               "region_scope": region, "quality_level": quality,
               "notes": _str_or_none(row.get("notes"))})
        counts["source"] += 1
    session.flush()

    def _link(row, taxon_col="taxonID"):
        taxon_id = _resolve_taxon_id(session, taxon_lookup, _str_or_none(row.get(taxon_col)) or "")
        src = _str_or_none(row.get("sourceID"))
        return taxon_id, source_ids.get(src)

    for _, row in sheets.get("scientific_taxon_link", pd.DataFrame()).iterrows():
        taxon_id, src_id = _link(row)
        if not taxon_id or not src_id:
            continue
        mention = _norm(row.get("mention_type"), _MENTION, None)
        if mention is None:
            continue
        session.execute(text("""
            INSERT INTO bibliographic.scientific_taxon_link
              (taxon_id, source_id, mention_type, evidence_strength, location_in_source, notes)
            VALUES (:taxon_id, :source_id, :mention, :strength, :loc, :notes)
            ON CONFLICT (taxon_id, source_id, mention_type) DO NOTHING
        """), {"taxon_id": taxon_id, "source_id": src_id, "mention": mention,
               "strength": _norm(row.get("evidence_strength"),
                                 {"strong": "strong", "moderate": "moderate",
                                  "weak": "weak", "anecdotal": "anecdotal"}, None),
               "loc": _str_or_none(row.get("location_in_source")),
               "notes": _str_or_none(row.get("notes"))})
        counts["link"] += 1

    for _, row in sheets.get("scientific_use", pd.DataFrame()).iterrows():
        taxon_id, src_id = _link(row)
        if not taxon_id or not src_id:
            continue
        use_cat = _norm(row.get("use_category"), _SCI_USE, "other")
        session.execute(text("""
            INSERT INTO bibliographic.scientific_use
              (taxon_id, source_id, use_category, evidence_type, claimed_effect,
               method_summary, key_result, safety_notes)
            VALUES (:taxon_id, :source_id, :use_category, :evidence_type, :claimed_effect,
                    :method_summary, :key_result, :safety_notes)
        """), {"taxon_id": taxon_id, "source_id": src_id, "use_category": use_cat,
               "evidence_type": _norm(row.get("evidence_type"), _EVIDENCE_TYPE, None),
               "claimed_effect": _str_or_none(row.get("claimed_effect")),
               "method_summary": _str_or_none(row.get("method_summary")),
               "key_result": _str_or_none(row.get("key_result")),
               "safety_notes": _str_or_none(row.get("safety_notes"))})
        counts["use"] += 1

    for _, row in sheets.get("scientific_ecology", pd.DataFrame()).iterrows():
        taxon_id, src_id = _link(row)
        if not taxon_id or not src_id:
            continue
        session.execute(text("""
            INSERT INTO bibliographic.scientific_ecology
              (taxon_id, source_id, habitat_reported, substrate_reported,
               seasonality, region_reported, notes)
            VALUES (:taxon_id, :source_id, :habitat, :substrate, :seasonality, :region, :notes)
        """), {"taxon_id": taxon_id, "source_id": src_id,
               "habitat": _str_or_none(row.get("habitat_reported")),
               "substrate": _str_or_none(row.get("substrate_reported")),
               "seasonality": _str_or_none(row.get("seasonality")),
               "region": _str_or_none(row.get("region_reported")),
               "notes": _str_or_none(row.get("notes"))})
        counts["ecology"] += 1

    session.flush()
    return counts


def import_ethno_tables(session, path, taxon_lookup):
    """Inserta Capa_etnomicologica.xlsx en socioecological.*. Devuelve conteos o None."""
    if not path or not Path(path).is_file():
        return None
    if not _has_table(session.bind, "socioecological", "ethno_source"):
        return None
    from sqlalchemy import text

    xl = pd.ExcelFile(path)
    sheets = {}
    for name in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=name, dtype=str, keep_default_na=False)
        df.columns = [c.strip() for c in df.columns]
        sheets[name.strip().lower().replace(" ", "_")] = df

    counts = {"source": 0, "knowledge": 0, "use": 0}
    source_ids: dict[str, uuid.UUID] = {}
    know_ids: dict[str, uuid.UUID] = {}
    taxon_know: dict[str, uuid.UUID] = {}

    for _, row in sheets.get("ethno_source", pd.DataFrame()).iterrows():
        sid = _str_or_none(row.get("ethnoSourceID"))
        if not sid:
            continue
        uid = uuid.uuid4()
        source_ids[sid] = uid
        session.execute(text("""
            INSERT INTO socioecological.ethno_source
              (ethno_source_id, interview_date, interviewer, consent_given, consent_type,
               anonymity_level, municipality, village, occupation, age_range, gender, remarks)
            VALUES (:id, :interview_date, :interviewer, :consent_given, :consent_type,
                    :anonymity, :municipality, :village, :occupation, :age_range, :gender, :remarks)
        """), {"id": uid,
               "interview_date": _parse_datetime(_str_or_none(row.get("interviewDate"))),
               "interviewer": _str_or_none(row.get("interviewer")) or "No reportado",
               "consent_given": _bool_es(row.get("consentGiven")) or False,
               "consent_type": _norm(row.get("consentType"), {"verbal": "verbal", "written": "written"}, None),
               "anonymity": _norm(row.get("anonymityLevel"),
                                  {"anonymous": "anonymous", "pseudonym": "pseudonym",
                                   "identified": "identified"}, "anonymous"),
               "municipality": _str_or_none(row.get("municipality")),
               "village": _str_or_none(row.get("village")),
               "occupation": _norm(row.get("occupation"), _OCCUPATION, None),
               "age_range": _norm(row.get("ageRange"),
                                  {"12-17": "12-17", "18-25": "18-25", "26-40": "26-40",
                                   "41-60": "41-60", "60+": "60+"}, None),
               "gender": _norm(row.get("gender"),
                               {"male": "male", "female": "female", "non_binary": "non_binary",
                                "prefer_not_to_say": "prefer_not_to_say"}, None),
               "remarks": _str_or_none(row.get("remarks"))})
        counts["source"] += 1
    session.flush()

    for _, row in sheets.get("ethno_taxon_knowledge", pd.DataFrame()).iterrows():
        kid = _str_or_none(row.get("ethnoKnowID"))
        src_id = source_ids.get(_str_or_none(row.get("ethnoSourceID")))
        taxon_id = _resolve_taxon_id(session, taxon_lookup, _str_or_none(row.get("taxonID")) or "")
        if not kid or not src_id:
            continue
        uid = uuid.uuid4()
        know_ids[kid] = uid
        if taxon_id:
            taxon_know.setdefault(str(taxon_id), uid)
        session.execute(text("""
            INSERT INTO socioecological.ethno_taxon_knowledge
              (ethno_know_id, ethno_source_id, taxon_id, knows_fungi, local_name,
               learning_source, recognition_cues, found_in_places, seasonality, months,
               safety_practices, myths_stories, cultural_identity, recommendations)
            VALUES (:id, :source_id, :taxon_id, :knows_fungi, :local_name, :learning_source,
                    :recognition_cues, :found_in_places, :seasonality, :months,
                    :safety_practices, :myths_stories, :cultural_identity, :recommendations)
            ON CONFLICT (ethno_source_id, taxon_id) DO NOTHING
        """), {"id": uid, "source_id": src_id, "taxon_id": taxon_id,
               "knows_fungi": _bool_es(row.get("knowsFungi")),
               "local_name": _str_or_none(row.get("localName")),
               "learning_source": _norm(row.get("learningSource"), _LEARNING, None),
               "recognition_cues": _str_or_none(row.get("recognitionCues")),
               "found_in_places": _str_or_none(row.get("foundInPlaces")),
               "seasonality": _str_or_none(row.get("seasonality")),
               "months": _str_or_none(row.get("months")),
               "safety_practices": _str_or_none(row.get("safetyPractices")),
               "myths_stories": _str_or_none(row.get("mythsStories")),
               "cultural_identity": _norm(row.get("culturalIdentity"), _CULTURAL, None),
               "recommendations": _str_or_none(row.get("recommendations"))})
        counts["knowledge"] += 1
    session.flush()

    for _, row in sheets.get("ethno_use", pd.DataFrame()).iterrows():
        kid = _str_or_none(row.get("ethnoKnowID"))
        know_id = know_ids.get(kid) if kid else None
        if know_id is None:
            taxon_id = _resolve_taxon_id(session, taxon_lookup, _str_or_none(row.get("taxonID")) or "")
            know_id = taxon_know.get(str(taxon_id)) if taxon_id else None
        if know_id is None:
            continue
        use_cat = _norm(row.get("useCategory"), _ETHNO_USE, "other")
        session.execute(text("""
            INSERT INTO socioecological.ethno_use
              (ethno_know_id, uses_fungi, use_category, preparation_method,
               ailment, dosage, contraindications, importance)
            VALUES (:know_id, :uses_fungi, :use_category, :preparation_method,
                    :ailment, :dosage, :contraindications, :importance)
        """), {"know_id": know_id, "uses_fungi": _bool_es(row.get("usesFungi")),
               "use_category": use_cat,
               "preparation_method": _str_or_none(row.get("preparationMethod")),
               "ailment": _str_or_none(row.get("ailment")),
               "dosage": _str_or_none(row.get("dosage")),
               "contraindications": _str_or_none(row.get("contraindications")),
               "importance": _norm(row.get("importance"), _IMPORTANCE, None)})
        counts["use"] += 1

    session.flush()
    return counts


def run_import(args):
    backend_src = Path(args.backend_src)
    (SessionLocal, initialize_database, TaxonRef, Location, Event,
     Occurrence, Multimedia, MorphologyFact, ApplicationState,
     CurationDecision, UserWeb) = _import_backend(backend_src)

    initialize_database()
    session = SessionLocal()
    owner = _owner_id(session, UserWeb, args.owner_email)
    if owner is None:
        print("[aviso] No se indicó --owner-email. Los registros importados quedarán sin "
              "responsable (el admin deberá asignarlo para poder editarlos).")

    counts = {"taxones": 0, "occurrences": 0, "multimedia": 0, "fuentes": 0, "morfologia": 0}

    # ── 1. Taxones (unión de maestra + curada) ─────────────────────────────
    # La maestra usa su propia hoja ('sp'); los --taxon-ref usan --taxon-sheet.
    sources = [(p, args.taxon_master_sheet) for p in (args.taxon_master or [])] + \
              [(p, args.taxon_sheet) for p in (args.taxon_ref or [])]

    existing_names = {n.lower(): t for (n, t) in
                      session.query(TaxonRef.scientific_name, TaxonRef).all()}
    taxon_lookup = {}
    for t in load_taxones(sources):
        key = t["scientific_name"].lower()
        if key in existing_names:
            taxon_lookup[key] = existing_names[key]
            continue
        row = TaxonRef(taxon_id=uuid.uuid4(), **t)
        session.add(row)
        session.flush()
        taxon_lookup[key] = row
        session.add(ApplicationState(entity_type="taxon_ref", entity_id=row.taxon_id,
                                     owner_id=owner, created_by_id=owner, payload={}))
        session.add(CurationDecision(decision_id=uuid.uuid4(), entity_type="taxon_ref",
                                     entity_id=row.taxon_id, decided_by=owner,
                                     new_status="verified"))
        counts["taxones"] += 1
    session.commit()
    print(f"Taxones importados: {counts['taxones']} (total en BD: {len(taxon_lookup)})")

    # ── 2. Morfología (Capa 4) ─────────────────────────────────────────────
    morph = load_morphology(args.morphology)
    for name, facts in morph.items():
        taxon = taxon_lookup.get(name)
        if taxon is None:
            continue
        for mtype, value in facts:
            session.add(MorphologyFact(morphology_id=uuid.uuid4(),
                                       taxon_id=taxon.taxon_id, occurrence_id=None,
                                       measurement_type=mtype, measurement_value=value))
            counts["morfologia"] += 1
    session.commit()
    print(f"Rasgos morfológicos importados: {counts['morfologia']} "
          f"({len(morph)} especies con datos)")

    # ── 3. Ocurrencias + multimedia ────────────────────────────────────────
    existing_ids = {eid for (eid,) in session.query(Occurrence.external_occurrence_id).all() if eid}
    location_cache: dict[tuple, object] = {}
    event_cache: dict[tuple, object] = {}

    ocurrencias, media_index = load_occurrences(args.occurrence, args.multimedia)
    for idx, o in enumerate(ocurrencias):
        if o["gbif_id"] in existing_ids:
            continue

        loc_key = (o["locality"], o["municipality"], o["state_province"])
        loc = location_cache.get(loc_key)
        if loc is None:
            loc = session.query(Location).filter(
                Location.locality == o["locality"],
                Location.municipality == o["municipality"],
                Location.state_province == o["state_province"]).first()
            if loc is None:
                loc = Location(location_id=uuid.uuid4(), country="Colombia",
                               country_code="CO", state_province=o["state_province"],
                               municipality=o["municipality"], locality=o["locality"],
                               decimal_latitude=o["decimal_latitude"],
                               decimal_longitude=o["decimal_longitude"],
                               coordinate_uncertainty_m=o["coordinate_uncertainty_m"],
                               elevation_m=o["elevation_m"], geodetic_datum="WGS84")
                session.add(loc)
                session.flush()
            location_cache[loc_key] = loc

        ev_key = (loc.location_id, o["event_date_dt"], o["recorded_by"])
        ev = event_cache.get(ev_key)
        if ev is None:
            ev = session.query(Event).filter(
                Event.location_id == loc.location_id,
                Event.event_date == o["event_date_dt"],
                Event.recorded_by == o["recorded_by"]).first()
            if ev is None:
                ev = Event(event_id=uuid.uuid4(), location_id=loc.location_id,
                           event_type="Observation", event_date=o["event_date_dt"],
                           recorded_by=o["recorded_by"])
                session.add(ev)
                session.flush()
            event_cache[ev_key] = ev

        taxon = taxon_lookup.get(o["binomial"].lower())
        occ = Occurrence(
            occurrence_id=uuid.uuid4(), event_id=ev.event_id,
            taxon_id=taxon.taxon_id if taxon else None,
            external_occurrence_id=o["gbif_id"],
            basis_of_record=_BASIS_MAP.get(o["basis_of_record_raw"], "HumanObservation"),
            recorded_by=o["recorded_by"],
            event_date=o["event_datetime"],
            occurrence_status=_STATUS_MAP.get(o["occurrence_status_raw"], "present"),
            individual_count=o["individual_count"],
            occurrence_remarks=o["occurrence_remarks"],
            verbatim_scientific_name=o["verbatim_scientific_name"],
            identification_qualifier="none",
            identified_by=o["identified_by"],
        )
        session.add(occ)
        session.flush()
        session.add(ApplicationState(entity_type="occurrence", entity_id=occ.occurrence_id,
                                     owner_id=owner, created_by_id=owner, payload={}))
        session.add(CurationDecision(decision_id=uuid.uuid4(), entity_type="occurrence",
                                     entity_id=occ.occurrence_id, decided_by=owner,
                                     new_status="verified"))
        counts["occurrences"] += 1
        existing_ids.add(o["gbif_id"])

        for i, m in enumerate(media_index.get(o["gbif_id"], []), start=1):
            if not m["source_url"]:
                continue
            file_name = f"voucher_{i:03d}.jpg"
            media = Multimedia(
                media_id=uuid.uuid4(), occurrence_id=occ.occurrence_id,
                photo_type="voucher", file_name=file_name,
                file_path=f"imported/{o['gbif_id']}/{file_name}",
                source_url=m["source_url"], sha256_hash=None,
                media_type="StillImage", mime_format=m["mime_format"] or "image/jpeg",
                photographer=m["creator"], capture_date=m["created"],
                license=m["license"] or "http://creativecommons.org/licenses/by-nc/4.0/",
                rights_holder=m["rights_holder"],
            )
            session.add(media)
            counts["multimedia"] += 1

        if (idx + 1) % 1000 == 0:
            session.commit()
            print(f"  progreso: {idx + 1}/{len(ocurrencias)} ocurrencias...")
    session.commit()
    print(f"Ocurrencias importadas: {counts['occurrences']}")
    print(f"Fotografías importadas: {counts['multimedia']}")

    # ── 4. Bibliografía (Capa 3) ───────────────────────────────────────────
    biblio_counts = import_bibliographic_tables(session, args.biblio, taxon_lookup)
    if biblio_counts is not None:
        print(f"Bibliografía importada en tablas normalizadas: "
              f"{biblio_counts['source']} fuentes, {biblio_counts['link']} vínculos, "
              f"{biblio_counts['use']} usos, {biblio_counts['ecology']} ecología")
    else:
        biblio = load_biblio(args.biblio)
        matched = 0
        for taxon_name, sources in biblio.items():
            taxon = taxon_lookup.get(taxon_name.strip().lower())
            if taxon is None:
                continue
            matched += 1
            state = session.get(ApplicationState, ("taxon_ref", taxon.taxon_id))
            if state is None:
                state = ApplicationState(entity_type="taxon_ref", entity_id=taxon.taxon_id,
                                         owner_id=owner, created_by_id=owner, payload={})
                session.add(state)
            payload = dict(state.payload or {})
            existing_sources = payload.setdefault("sources", [])
            known = {s.get("source_id") for s in existing_sources}
            for s in sources:
                if s["source_id"] in known:
                    continue
                existing_sources.append(s)
                known.add(s["source_id"])
                counts["fuentes"] += 1
            state.payload = payload
        print(f"[aviso] Tablas bibliographic.* no existen (aplica restore_capas.sql). "
              f"Se aplanó en application_state: {matched}/{len(biblio)} taxones, "
              f"{counts['fuentes']} fuentes")
    session.commit()

    # ── 5. Etnomicología (Capa 2) ──────────────────────────────────────────
    ethno_counts = import_ethno_tables(session, args.ethno, taxon_lookup)
    if ethno_counts is not None:
        print(f"Etnomicología importada en tablas normalizadas: "
              f"{ethno_counts['source']} fuentes, {ethno_counts['knowledge']} conocimientos, "
              f"{ethno_counts['use']} usos")
    elif args.ethno and Path(args.ethno).is_file():
        print("[aviso] Tablas socioecological.* no existen (aplica restore_capas.sql). "
              "La capa etnomicológica no se importó.")
    session.commit()

    session.close()
    print("\nImportación completada.")


def main():
    parser = argparse.ArgumentParser(description="Importa los datos reales de Corte 1 al aplicativo Macromicetos.")
    parser.add_argument("--backend-src", default="Backend/src",
                        help="Ruta a Backend/src del repo del aplicativo (por defecto 'Backend/src').")
    parser.add_argument("--taxon-ref", dest="taxon_ref", action="append", default=[],
                        help="Lista curada de especies (puede repetirse).")
    parser.add_argument("--taxon-sheet", dest="taxon_sheet", default=None,
                        help="Hoja de los archivos --taxon-ref (por defecto la primera).")
    parser.add_argument("--taxon-master", dest="taxon_master", action="append", default=[],
                        help="Lista maestra GBIF (puede repetirse).")
    parser.add_argument("--taxon-master-sheet", dest="taxon_master_sheet", default="sp",
                        help="Hoja de los archivos --taxon-master (por defecto 'sp').")
    parser.add_argument("--occurrence", help="occurrence.txt de GBIF")
    parser.add_argument("--multimedia", help="multimedia.txt de GBIF")
    parser.add_argument("--biblio", help="Capa bibliográfica .xlsx (opcional)")
    parser.add_argument("--morphology", help="Capa_morfologica.xlsx (opcional)")
    parser.add_argument("--ethno", help="Capa_etnomicologica.xlsx (opcional)")
    parser.add_argument("--owner-email", help="Correo del administrador dueño de los registros (opcional).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo lee y valida los archivos; no toca la base de datos.")
    args = parser.parse_args()

    if args.dry_run:
        taxon_sources = [(p, args.taxon_master_sheet) for p in args.taxon_master] + \
                        [(p, args.taxon_sheet) for p in args.taxon_ref]
        taxones = load_taxones(taxon_sources) if taxon_sources else []
        ocurrencias, media_index = load_occurrences(args.occurrence, args.multimedia) \
            if args.occurrence and args.multimedia else ([], {})
        biblio = load_biblio(args.biblio)
        morph = load_morphology(args.morphology)
        ethno_rows = {}
        if args.ethno and Path(args.ethno).is_file():
            xl = pd.ExcelFile(args.ethno)
            ethno_rows = {s: len(pd.read_excel(args.ethno, sheet_name=s)) for s in xl.sheet_names}
        n_fotos = sum(len(v) for v in media_index.values())
        n_morph = sum(len(v) for v in morph.values())
        print("=== Simulación (dry-run) ===")
        print(f"Taxones (unión de listas): {len(taxones)}")
        print(f"Ocurrencias leídas: {len(ocurrencias)}")
        print(f"Fotografías referenciadas: {n_fotos}")
        print(f"Taxones con fuentes bibliográficas: {len(biblio)}")
        print(f"Especies con morfología: {len(morph)} (rasgos: {n_morph})")
        print(f"Capa etnomicológica: {ethno_rows}")
        if taxones:
            print("Ejemplo taxón:", taxones[0]["scientific_name"], "|", taxones[0]["phylum"])
        if ocurrencias:
            print("Ejemplo ocurrencia:", ocurrencias[0]["gbif_id"],
                  "|", ocurrencias[0]["binomial"], "|", ocurrencias[0]["state_province"])
        return

    if not (args.taxon_master or args.taxon_ref):
        parser.error("Se requiere --taxon-master y/o --taxon-ref.")
    if not args.occurrence or not args.multimedia:
        parser.error("Se requieren --occurrence y --multimedia para la importación real.")
    run_import(args)


if __name__ == "__main__":
    main()
