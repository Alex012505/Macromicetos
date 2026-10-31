"""Vínculo muchos-a-muchos entre taxones y fuentes (bibliographic.scientific_taxon_link)."""
import uuid

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

MENTION_TYPE_ENUM = SQLEnum(
    'taxonomy', 'ecology', 'use', 'chemistry', 'distribution',
    'morphology', 'phylogeny', 'biocontrol',
    name="mention_type_enum", schema="bibliographic", create_type=False,
)
EVIDENCE_STRENGTH_ENUM = SQLEnum(
    'strong', 'moderate', 'weak', 'anecdotal',
    name="evidence_strength_enum", schema="bibliographic", create_type=False,
)


class ScientificTaxonLink(Base):
    """Una mención de un taxón en una fuente.

    UNIQUE (taxon_id, source_id, mention_type): la misma fuente puede mencionar
    el mismo taxón por ecología y por uso, pero no dos veces por el mismo motivo.
    """
    __tablename__ = "scientific_taxon_link"
    __table_args__ = {"schema": "bibliographic"}

    taxon_source_link_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    taxon_id: Mapped[uuid.UUID] = mapped_column(
        PK(), ForeignKey("shared.taxon_ref.taxon_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("bibliographic.scientific_source.source_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    mention_type: Mapped[str] = mapped_column(MENTION_TYPE_ENUM, nullable=False)
    evidence_strength: Mapped[str | None] = mapped_column(EVIDENCE_STRENGTH_ENUM)
    location_in_source: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
