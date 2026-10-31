"""Carga de datos de demostración para Macromicetos.

Idempotente: las cuentas se deduplican por correo, las fichas por nombre
científico y los hallazgos por external_occurrence_id (DEMO-01 … DEMO-12).
Puedes ejecutarlo varias veces sin duplicar datos. NO usar en producción.

Ejecutar después de setup_postgres.py, desde la raíz del repositorio:

    .\\Backend\\.venv\\Scripts\\python.exe Backend/seed_demo.py
"""
import datetime as dt
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sqlalchemy import func, select

from database.Base import SessionLocal, initialize_database
from models.UserWeb import UserWeb
from models.TaxonRef import TaxonRef
from models.Location import Location
from models.Event import Event
from models.Occurrence import Occurrence
from models.MorphologyFact import MorphologyFact
from models.MeasurementOrFact import MeasurementOrFact
from models.CurationDecision import CurationDecision
from models.ApplicationState import ApplicationState
from Security import hash_password

DEMO_PASSWORD = "Demo2026!"

USERS = [
    ("camila@example.org", "Camila", "Torres", "admin"),
    ("laura@example.org", "Laura", "Martínez", "analyst"),
    ("diego@example.org", "Diego", "Ramírez", "analyst"),
    ("andres@example.org", "Andrés", "Rojas", "curator"),
    ("maria@example.org", "María", "Suárez", "viewer"),
]

# nombre, nombre_común, filo, clase, orden, familia, género, epiteto_específico, id_externo, notas
TAXA = [
    ("Pleurotus ostreatus", "Orellana", "Basidiomycota", "Agaricomycetes", "Agaricales",
     "Pleurotaceae", "Pleurotus", "ostreatus", "demo:001",
     "Lignícola en abanico; sombrero liso en tonos grises o pardo grisáceo."),
    ("Trametes versicolor", "Cola de pavo", "Basidiomycota", "Agaricomycetes", "Polyporales",
     "Polyporaceae", "Trametes", "versicolor", "demo:002",
     "Pileo zonado de colores variables; poros blancos en superficie inferior."),
    ("Pycnoporus sanguineus", "Hongo rojo de la madera", "Basidiomycota", "Agaricomycetes", "Polyporales",
     "Polyporaceae", "Pycnoporus", "sanguineus", "demo:003",
     "Poros de color rojo naranja intenso, superficialmente con matices lacre."),
    ("Schizophyllum commune", "Hongo de láminas divididas", "Basidiomycota", "Agaricomycetes", "Agaricales",
     "Schizophyllaceae", "Schizophyllum", "commune", "demo:004",
     "Láminas profundamente hendidas; sombrero peludo de bordes lobulados."),
    ("Auricularia auricula-judae", "Oreja de palo", "Basidiomycota", "Agaricomycetes", "Auriculariales",
     "Auriculariaceae", "Auricularia", "auricula-judae", "demo:005",
     "Basidioma gelatinoso con forma de oreja y superficie velluda."),
    ("Lentinus crinitus", "Hongo de sombrero velloso", "Basidiomycota", "Agaricomycetes", "Polyporales",
     "Polyporaceae", "Lentinus", "crinitus", "demo:006",
     "Sombrero acanalado velloso; láminas nervadas de bordes aserrados."),
    ("Ganoderma lucidum", "Ganoderma", "Basidiomycota", "Agaricomycetes", "Polyporales",
     "Ganodermataceae", "Ganoderma", "lucidum", "demo:007",
     "Cuerpo fructífero lacado marrón rojizo, con pie lateral en la madera."),
    ("Coprinellus disseminatus", "Coprinelo", "Basidiomycota", "Agaricomycetes", "Agaricales",
     "Psathyrellaceae", "Coprinellus", "disseminatus", "demo:008",
     "Fructificación muy numerosa en troncos; sombreros pequeños grisáceos."),
    ("Cookeina speciosa", "Copa roja del bosque", "Ascomycota", "Pezizomycetes", "Pezizales",
     "Sarcoscyphaceae", "Cookeina", "speciosa", "demo:009",
     "Sácuas en copa rojo anaranjado sobre madera en descomposición."),
]

MORPHOLOGY_BY_TAXON = {
    "Pleurotus ostreatus": [
        ("tipo_himenio", "láminas decurrentes", None),
        ("diametro_sombrero", "6–14", "cm"),
        ("color_sombrero", "gris pardo a blanquecino", None),
        ("habito_crecimiento", "cespitoso sobre madera", None),
    ],
    "Trametes versicolor": [
        ("tipo_himenio", "tubos con poros blancos", None),
        ("diametro_sombrero", "2–8", "cm"),
        ("color_sombrero", "zonado multicolor", None),
        ("habito_crecimiento", "imbricado en grupos", None),
    ],
    "Pycnoporus sanguineus": [
        ("tipo_himenio", "poros rojo naranja", None),
        ("diametro_sombrero", "4–15", "cm"),
        ("color_sombrero", "rojo lacre a naranja", None),
        ("habito_crecimiento", "sésil o con pie rudimentario", None),
    ],
    "Schizophyllum commune": [
        ("tipo_laminas", "láminas hendidas en grieta", None),
        ("diametro_sombrero", "1–4", "cm"),
        ("color_sombrero", "blanco grisáceo", None),
        ("habito_crecimiento", "en racimos sobre madera", None),
    ],
    "Auricularia auricula-judae": [
        ("tipo_himenio", "superficie rugosa gelatinosa", None),
        ("color_sombrero", "marrón púrpura", None),
        ("habito_crecimiento", "solitario o agrupado en ramas", None),
    ],
    "Lentinus crinitus": [
        ("tipo_laminas", "láminas nervadas de bordes aserrados", None),
        ("diametro_sombrero", "3–10", "cm"),
        ("color_sombrero", "blanquecino pardo", None),
        ("habito_crecimiento", "cespitoso en tocos", None),
    ],
    "Ganoderma lucidum": [
        ("forma_poros", "poro circular de color crema", None),
        ("diametro_sombrero", "10–25", "cm"),
        ("color_sombrero", "marrón rojizo lacado", None),
        ("habito_crecimiento", "en zonas basales del tronco", None),
    ],
    "Coprinellus disseminatus": [
        ("tipo_laminas", "láminas de bordes que se oscurecen", None),
        ("diametro_sombrero", "0.5–1.5", "cm"),
        ("color_sombrero", "blanco pardo", None),
        ("habito_crecimiento", "en grandes agrupaciones numerosas", None),
    ],
    "Cookeina speciosa": [
        ("tipo_himenio", "superficie interna lisa rojo anaranjada", None),
        ("diametro_sombrero", "2–5", "cm"),
        ("forma_sombrero", "copa o vaso", None),
        ("habito_crecimiento", "agrupado sobre madera muerta", None),
    ],
}

# provincia, municipio, localidad, lat, lng, elevación, hábitat, incertidumbre_m, notas
LOCATIONS = [
    ("Meta", "Villavicencio", "Bosque de galería del río Ocoa", 4.151347, -73.635670, 467,
     "GalleryForest", 20, "Riberas arboladas con abundante madera muerta."),
    ("Casanare", "Yopal", "Sendero de muestreo La Guavira", 5.337860, -72.395860, 272,
     "SecondaryForest", 30, "Ecotono de bosque secundario y potrero ganadero."),
    ("Arauca", "Tame", "Ribera del río Tame", 6.460140, -71.732850, 320,
     "RiparianVegetation", 25, "Vegetación de ribera con hojarasca abundante."),
    ("Vichada", "Puerto Carreño", "Bosque secundario La Pedrera", 6.189540, -67.486010, 112,
     "Forest", 40, "Bosque de terraza alta con material leñoso variado."),
    ("Meta", "Puerto López", "Morichal bajo La Reforma", 4.088810, -72.955260, 178,
     "Morichal", 35, "Palma de moriche con suelos parcialmente encharcados."),
]

# índice de localidad, tipo de evento, protocolo, esfuerzo, n.º de campo, persona
EVENTS = [
    (0, "SiteVisit", "OpportunisticSearch", "half-day survey", "MT-2026-041", "Laura Martínez"),
    (1, "Survey", "FixedPlot", "full-day survey", "YP-2026-012", "Diego Ramírez"),
    (2, "Observation", "OpportunisticSearch", "2 observer-hours", "TA-2026-007", "Laura Martínez"),
    (3, "Survey", "LinearTransect", "500 m transect", "PC-2026-021", "Diego Ramírez"),
    (4, "SiteVisit", "TargetedCollection", "half-day survey", "PL-2026-009", "Laura Martínez"),
]

# (external_id, índice de taxón, índice de evento, sustrato)
OCCURRENCES = [
    ("DEMO-01", 0, 0, "DeadWood"),
    ("DEMO-02", 3, 0, "LiveTreeTrunks"),
    ("DEMO-03", 5, 1, "StumpAttachedToTheGround"),
    ("DEMO-04", 7, 1, "VeryDecomposedFallenWood"),
    ("DEMO-05", 4, 2, "Branches"),
    ("DEMO-06", 8, 2, "HalfBuriedWood"),
    ("DEMO-07", 6, 3, "FallenLogs"),
    ("DEMO-08", 1, 3, "DeadWoodFromWoodyPlants"),
    ("DEMO-09", 2, 4, "DeadWood"),
    ("DEMO-10", 5, 4, "BurnedLog"),
]

# Decisión final de curaduría por hallazgo; None = queda en revisión (pendiente)
FINAL_STATUS = {
    "DEMO-01": "verified", "DEMO-02": None, "DEMO-03": "needs_adjustment",
    "DEMO-04": "verified", "DEMO-05": "verified", "DEMO-06": None,
    "DEMO-07": "verified", "DEMO-08": "verified", "DEMO-09": "verified",
    "DEMO-10": None,
}
DECISION_COMMENTS = {
    "DEMO-03": "Adjunte una fotografía de la superficie porosa para confirmar la identificación.",
    "DEMO-01": "Registro verificado; morfología y localidad consistentes.",
    "DEMO-04": "Registro verificado; morfología y localidad consistentes.",
    "DEMO-05": "Registro verificado; morfología y localidad consistentes.",
    "DEMO-07": "Registro verificado; se recomienda respaldo fotográfico adicional.",
    "DEMO-08": "Registro verificado; morfología y localidad consistentes.",
    "DEMO-09": "Registro verificado; morfología y localidad consistentes.",
}

OCCURRENCE_REMARKS = {
    "DEMO-02": "Se recolectó una parte del basidioma para depositar en muestra.",
    "DEMO-07": "Cuerpo fructífero de gran tamaño; quedó sin extraer en sitio.",
    "DEMO-10": "Cuerp fructífero potencialmente patógeno en trenza quemada. Revisión pendiente.",
    "DEMO-06": "Sácuas copa y de color muy visible; se registró también el sustrato asociado.",
}


def ensure_users():
    ids = {}
    with SessionLocal() as db:
        for email, first, last, role in USERS:
            user = db.scalar(select(UserWeb).where(func.lower(UserWeb.email) == email))
            if not user:
                user = UserWeb(email=email, first_name=first, last_name=last,
                               role=role, password_hash=hash_password(DEMO_PASSWORD))
                db.add(user)
                db.flush()
            ids.setdefault(role, []).append(user.user_web_id)
        db.commit()
    return ids


def main():
    initialize_database()
    role_ids = ensure_users()
    analysts = role_ids.get("analyst", [])
    curator_id = (role_ids.get("curator") or [None])[0]
    if not analysts:
        raise SystemExit("No hay cuenta analyst; ejecuta de nuevo tras crear usuarios.")

    added = {"taxa": 0, "locations": 0, "events": 0, "occurrences": 0,
             "morphology": 0, "measurements": 0, "decisions": 0}
    with SessionLocal() as db:
        # ------------------------------------------------------------------ fichas
        taxon_ids = []
        for name, common, phylum, klass, order, family, genus, epithet, external, remarks in TAXA:
            taxon = db.scalar(select(TaxonRef).where(func.lower(TaxonRef.scientific_name) == name.lower()))
            is_new = taxon is None
            if is_new:
                taxon = TaxonRef(scientific_name=name, taxon_rank="species", kingdom="Fungi",
                                 phylum=phylum, class_name=klass, order_name=order, family=family,
                                 genus=genus, specific_epithet=epithet, external_taxon_id=external,
                                 common_name_es=common, taxon_remarks=remarks)
                db.add(taxon)
                db.flush()
                owner = analysts[0]
                db.add(ApplicationState(entity_type="taxon_ref", entity_id=taxon.taxon_id,
                                        owner_id=owner, created_by_id=owner, payload={}))
                added["taxa"] += 1
                for type_, value, unit in MORPHOLOGY_BY_TAXON[name]:
                    db.add(MorphologyFact(taxon_id=taxon.taxon_id, measurement_type=type_,
                                          measurement_value=value, measurement_unit=unit,
                                          measurement_remarks="Dato ilustrativo de la carga demo."))
                added["morphology"] += len(MORPHOLOGY_BY_TAXON[name])
            taxon_ids.append(taxon.taxon_id)
        db.commit()

        # ------------------------------------------------- hallazgos y su entorno
        seeded = {row for row in db.scalars(select(Occurrence.external_occurrence_id))
                  if row and row.startswith("DEMO-")}
        day = 1                                               # día de octubre de 2026
        for external, taxon_index, event_index, substrate in OCCURRENCES:
            if external in seeded:
                continue
            loc_index, event_type, protocol, effort, field_number, person = EVENTS[event_index]
            province, municipality, locality, lat, lng, elevation, habitat, uncertainty, loc_remarks = LOCATIONS[loc_index]
            location = db.scalar(select(Location).where(Location.municipality == municipality,
                                                        Location.locality == locality))
            if not location:
                location = Location(country="Colombia", country_code="CO", state_province=province,
                                    municipality=municipality, locality=locality,
                                    decimal_latitude=lat, decimal_longitude=lng,
                                    coordinate_uncertainty_m=uncertainty, elevation_m=elevation,
                                    geodetic_datum="WGS84", habitat=habitat, location_remarks=loc_remarks)
                db.add(location)
                db.flush()
                added["locations"] += 1
            event = Event(location_id=location.location_id, event_type=event_type,
                          field_number=field_number, event_date=dt.date(2026, 10, day),
                          event_time="08:30", recorded_by=person, sampling_protocol=protocol,
                          sampling_effort=effort, event_remarks="Salida demostrativa (datos ficticios).")
            db.add(event)
            db.flush()
            added["events"] += 1
            for type_, unit, value in (("temperature", "°C", 24.0 + day * 0.1),
                                       ("relativeHumidity", "%", float(70 + day)),
                                       ("altitude", "m", float(elevation))):
                db.add(MeasurementOrFact(event_id=event.event_id, measurement_type=type_,
                                         measurement_value=value, measurement_unit=unit,
                                         measurement_determined_date=dt.datetime(2026, 10, day, 9, 0,
                                                                                 tzinfo=dt.timezone.utc),
                                         measurement_method="Estación portátil (demostración)"))
                added["measurements"] += 1
            owner = analysts[event_index % len(analysts)]
            occurrence = Occurrence(external_occurrence_id=external,
                                    event_id=event.event_id, taxon_id=taxon_ids[taxon_index],
                                    basis_of_record="HumanObservation", recorded_by=person,
                                    identified_by=person,
                                    event_date=dt.datetime(2026, 10, day, 10, 0, tzinfo=dt.timezone.utc),
                                    date_identified=dt.date(2026, 10, day), substrate=substrate,
                                    occurrence_remarks=OCCURRENCE_REMARKS.get(external))
            db.add(occurrence)
            db.flush()
            db.add(ApplicationState(entity_type="occurrence", entity_id=occurrence.occurrence_id,
                                    owner_id=owner, created_by_id=owner, payload={}))
            status = FINAL_STATUS.get(external)
            if status and curator_id:
                db.add(CurationDecision(entity_type="occurrence", entity_id=occurrence.occurrence_id,
                                        decided_by=curator_id, previous_status="submitted",
                                        new_status=status, comment=DECISION_COMMENTS.get(external, ""),
                                        created_at=dt.datetime(2026, 10, min(23, day + 10),
                                                               15, 0, tzinfo=dt.timezone.utc)))
                added["decisions"] += 1
            added["occurrences"] += 1
            day += 2
        db.commit()

    print("Cuenta:                 camila@example.org (admin)")
    print("Contraseña demo común:  Demo2026!")
    print("cuentas analyst:        laura@example.org · diego@example.org")
    print("curador:                andres@example.org · visitante: maria@example.org")
    print("Carga:", added)


if __name__ == "__main__":
    main()
