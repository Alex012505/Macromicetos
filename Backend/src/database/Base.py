from sqlalchemy import create_engine, event
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from settings import DATABASE_URL

# Esquemas donde viven las tablas y los enums del proyecto. La base heredada
# (Macromycets) los declara con nombre propio en shared/ecological/curaduria,
# mientras que los modelos los referencian sin calificar. Exponerlos en el
# search_path permite que PostgreSQL resuelva ambos casos.
SCHEMAS = ("public", "shared", "ecological", "curaduria", "socioecological", "bibliographic")

options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    options["connect_args"] = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql"):
    options["connect_args"] = {"options": "-csearch_path=" + ",".join(SCHEMAS)}
engine = create_engine(DATABASE_URL, **options)
if engine.dialect.name == "sqlite":
    # Preserve the PostgreSQL model schemas while using one local development DB.
    engine = engine.execution_options(schema_translate_map={
        "shared": None,
        "ecological": None,
        "curaduria": None,
        "socioecological": None,
        "bibliographic": None,
    })

    @event.listens_for(engine, "connect")
    def sqlite_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)



class Base(DeclarativeBase):
    pass
    """Base declarativa de todos los modelos."""


def get_db():
    """Entrega una sesión por petición y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database():
    import models  # noqa: F401: registers the mapped tables
    from models.ApplicationState import ApplicationState  # noqa: F401
    from models.Occurrence import Occurrence  # noqa: F401
    from models.Multimedia import Multimedia  # noqa: F401
    from models.MorphologyFact import MorphologyFact  # noqa: F401
    from models.MeasurementOrFact import MeasurementOrFact  # noqa: F401
    from models.CurationDecision import CurationDecision  # noqa: F401
    from sqlalchemy import Enum
    from sqlalchemy.dialects.postgresql import ENUM

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            # CREATE SCHEMA exige CREATE sobre la base aunque el esquema ya
            # exista, así que solo se crea el que falte de verdad.
            existing = set(sa_inspect(connection).get_schema_names())
            for schema in SCHEMAS:
                if schema not in existing:
                    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            enums = {(column.type.name, column.type.schema): column.type
                     for table in Base.metadata.tables.values() for column in table.columns
                     if isinstance(column.type, Enum)}
            for enum in enums.values():
                # to_regtype busca en el search_path: encuentra los enums de
                # Macromycets (shared/ecological/curaduria) y los de public.
                if connection.execute(text("SELECT to_regtype(:name)"), {"name": enum.name}).scalar():
                    continue
                ENUM(*enum.enums, name=enum.name, schema=enum.schema).create(connection, checkfirst=True)
        Base.metadata.create_all(connection)
