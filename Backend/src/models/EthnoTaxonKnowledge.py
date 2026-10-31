"""Puente entrevista-taxón (socioecological.ethno_taxon_knowledge)."""
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

LEARNING_SOURCE_ENUM = SQLEnum(
    'family', 'community', 'personal_experience', 'books',
    'workshops', 'internet', 'other',
    name="learning_source_enum", schema="socioecological", create_type=False,
)
CULTURAL_IDENTITY_ENUM = SQLEnum(
    'yes', 'no', 'partial',
    name="cultural_identity_enum", schema="socioecological", create_type=False,
)


class EthnoTaxonKnowledge(Base):
    """Conocimiento local sobre un taxón en una entrevista.

    UNIQUE (ethno_source_id, taxon_id): una entrevista no puede repetirse para
    el mismo taxón; los usos van en ethno_use. `taxon_id` admite NULL para
    registrar saberes que aún no se han identificado taxonómicamente.
    """
    __tablename__ = "ethno_taxon_knowledge"
    __table_args__ = {"schema": "socioecological"}

    ethno_know_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    ethno_source_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey(
            "socioecological.ethno_source.ethno_source_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    taxon_id: Mapped[uuid.UUID | None] = mapped_column(
        PK(),
        ForeignKey("shared.taxon_ref.taxon_id", onupdate="CASCADE", ondelete="SET NULL"),
    )
    knows_fungi: Mapped[bool | None] = mapped_column(Boolean)
    local_name: Mapped[str | None] = mapped_column(Text)
    learning_source: Mapped[str | None] = mapped_column(LEARNING_SOURCE_ENUM)
    recognition_cues: Mapped[str | None] = mapped_column(Text)
    found_in_places: Mapped[str | None] = mapped_column(Text)
    seasonality: Mapped[str | None] = mapped_column(Text)
    months: Mapped[str | None] = mapped_column(Text)
    safety_practices: Mapped[str | None] = mapped_column(Text)
    myths_stories: Mapped[str | None] = mapped_column(Text)
    cultural_identity: Mapped[str | None] = mapped_column(CULTURAL_IDENTITY_ENUM)
    recommendations: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
