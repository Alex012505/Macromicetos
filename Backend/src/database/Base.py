from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from settings import DATABASE_URL

options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **options)
if engine.dialect.name == "sqlite":
    # Preserve the PostgreSQL model schemas while using one local development DB.
    engine = engine.execution_options(schema_translate_map={"shared": None, "ecological": None, "curaduria": None})

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
    from sqlalchemy import Enum, text
    from sqlalchemy.dialects.postgresql import ENUM

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            for schema in ("shared", "ecological", "curaduria"):
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            enums = {(column.type.name, column.type.schema): column.type
                     for table in Base.metadata.tables.values() for column in table.columns
                     if isinstance(column.type, Enum)}
            for enum in enums.values():
                ENUM(*enum.enums, name=enum.name, schema=enum.schema).create(connection, checkfirst=True)
        Base.metadata.create_all(connection)
