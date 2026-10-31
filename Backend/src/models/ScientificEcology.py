"""Observaciones ecológicas extraídas de la literatura (bibliographic.scientific_ecology)."""
import uuid

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK


class ScientificEcology(Base):
    """Una fila por descripción ecológica reportada por una fuente para un taxón.

    Hábitat y sustrato son texto libre a propósito: cada artículo usa su propio
    vocabulario y forzarlo al enum de la Orinoquía introduciría errores.
    """
    __tablename__ = "scientific_ecology"
    __table_args__ = {"schema": "bibliographic"}

    sci_eco_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    taxon_id: Mapped[uuid.UUID] = mapped_column(
        PK(), ForeignKey("shared.taxon_ref.taxon_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("bibliographic.scientific_source.source_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    habitat_reported: Mapped[str | None] = mapped_column(Text)
    substrate_reported: Mapped[str | None] = mapped_column(Text)
    seasonality: Mapped[str | None] = mapped_column(Text)
    region_reported: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
