"""Afirmaciones de uso extraídas de la literatura (bibliographic.scientific_use)."""
import uuid

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

SCI_USE_CATEGORY_ENUM = SQLEnum(
    'edible', 'medicinal', 'antimicrobial', 'antioxidant', 'enzyme',
    'bioremediation', 'agriculture', 'biocontrol', 'dye', 'ritual',
    'mythological', 'other',
    name="sci_use_category_enum", schema="bibliographic", create_type=False,
)
EVIDENCE_TYPE_ENUM = SQLEnum(
    'in_vitro', 'in_vivo', 'clinical', 'observational', 'review', 'meta_analysis',
    name="evidence_type_enum", schema="bibliographic", create_type=False,
)


class ScientificUse(Base):
    """Una fila por afirmación de uso estructurada de la literatura."""
    __tablename__ = "scientific_use"
    __table_args__ = {"schema": "bibliographic"}

    sci_use_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    taxon_id: Mapped[uuid.UUID] = mapped_column(
        PK(), ForeignKey("shared.taxon_ref.taxon_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("bibliographic.scientific_source.source_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    use_category: Mapped[str] = mapped_column(SCI_USE_CATEGORY_ENUM, nullable=False)
    evidence_type: Mapped[str | None] = mapped_column(EVIDENCE_TYPE_ENUM)
    claimed_effect: Mapped[str | None] = mapped_column(Text)
    method_summary: Mapped[str | None] = mapped_column(Text)
    key_result: Mapped[str | None] = mapped_column(Text)
    safety_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
