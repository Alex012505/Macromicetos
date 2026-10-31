"""Usos reportados en entrevistas (socioecological.ethno_use)."""
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

ETHNO_USE_CATEGORY_ENUM = SQLEnum(
    'edible', 'medicinal', 'ritual', 'dye', 'soil_improvement',
    'biological_control', 'animal_feed', 'other',
    name="ethno_use_category_enum", schema="socioecological", create_type=False,
)
IMPORTANCE_ENUM = SQLEnum(
    'high', 'medium', 'low',
    name="importance_enum", schema="socioecological", create_type=False,
)


class EthnoUse(Base):
    """Un uso reportado para un conocimiento entrevista-taxón.

    Un taxón puede ser comestible, medicinal y ritual a la vez: cada uso es una
    fila. `taxon_id` es una FK redundante a shared.taxon_ref para consultar por
    especie sin pasar por ethno_taxon_knowledge; se mantiene sincronizada en la
    capa de servicio.
    """
    __tablename__ = "ethno_use"
    __table_args__ = {"schema": "socioecological"}

    ethno_use_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    ethno_know_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey(
            "socioecological.ethno_taxon_knowledge.ethno_know_id",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    taxon_id: Mapped[uuid.UUID | None] = mapped_column(
        PK(),
        ForeignKey("shared.taxon_ref.taxon_id", onupdate="CASCADE", ondelete="SET NULL"),
    )
    uses_fungi: Mapped[bool | None] = mapped_column(Boolean)
    use_category: Mapped[str] = mapped_column(ETHNO_USE_CATEGORY_ENUM, nullable=False)
    preparation_method: Mapped[str | None] = mapped_column(Text)
    ailment: Mapped[str | None] = mapped_column(Text)
    dosage: Mapped[str | None] = mapped_column(Text)
    contraindications: Mapped[str | None] = mapped_column(Text)
    importance: Mapped[str | None] = mapped_column(IMPORTANCE_ENUM)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
