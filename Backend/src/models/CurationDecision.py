import uuid
import datetime as dt
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK, UserWeb

# Espejo exacto del ENUM curaduria.curable_entity_enum (create_type=False:
# el tipo ya existe en PostgreSQL, SQLAlchemy no lo recrea — igual que los demás)
CURABLE_ENTITY_ENUM = SQLEnum(
    "taxon_ref", "location", "event", "occurrence",
    "multimedia", "measurement_or_fact", "morphology_fact", "user_web",
    name="curable_entity_enum", create_type=False,
)

CURATION_STATUS_ENUM = SQLEnum(
    "draft", "submitted", "in_review",
    "verified", "needs_adjustment", "rejected",
    name="curation_status_enum", create_type=False,
)


class CurationDecision(Base):
    """Decisión de curaduría polimórfica (curaduria.curation_decision).

    entity_id NO lleva ForeignKey a propósito: apunta a una tabla distinta
    según entity_type. La integridad la maneja la API (validación de
    existencia) y el trigger purge_on_delete en la BD.
    """
    __tablename__ = "curation_decision"
    __table_args__ = {"schema": "curaduria"}

    decision_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(CURABLE_ENTITY_ENUM, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(PK(), nullable=False, index=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        PK(), ForeignKey(UserWeb.user_web_id, onupdate="CASCADE", ondelete="SET NULL")
    )
    previous_status: Mapped[str | None] = mapped_column(CURATION_STATUS_ENUM)
    new_status: Mapped[str] = mapped_column(CURATION_STATUS_ENUM, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())