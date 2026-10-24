import uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

# Alineado con shared.taxon_rank_enum del script SQL (create_type=False:
# el tipo ya existe en PostgreSQL, SQLAlchemy no lo recrea)
TAXON_RANK_ENUM = SQLEnum(
    'kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species',
    'subspecies', 'variety', 'form',
    name="taxon_rank_enum",
    create_type=False,
)


class TaxonRef(Base):
    """Diccionario autoritativo de taxones (shared.taxon_ref)."""
    __tablename__ = "taxon_ref"
    __table_args__ = {"schema": "shared"}

    taxon_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    scientific_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    taxon_rank: Mapped[str] = mapped_column(TAXON_RANK_ENUM, nullable=False)
    kingdom: Mapped[str] = mapped_column(Text, nullable=False, default="Fungi")
    phylum: Mapped[str | None] = mapped_column(Text)
    class_name: Mapped[str | None] = mapped_column(Text, name="class")
    order_name: Mapped[str | None] = mapped_column(Text, name="order")
    family: Mapped[str | None] = mapped_column(Text)
    genus: Mapped[str | None] = mapped_column(Text)
    specific_epithet: Mapped[str | None] = mapped_column(Text)
    external_taxon_id: Mapped[str | None] = mapped_column(Text)   # ej: "gbif:5556482"
    common_name_es: Mapped[str | None] = mapped_column(Text)
    taxon_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())