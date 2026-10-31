"""Referencias bibliográficas (bibliographic.scientific_source)."""
import uuid

from sqlalchemy import DateTime, SmallInteger, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

SOURCE_TYPE_ENUM = SQLEnum(
    'article', 'book', 'book_chapter', 'thesis', 'report',
    'dataset', 'preprint', 'conference_paper', 'field_guide', 'website', 'other',
    name="source_type_enum", schema="bibliographic", create_type=False,
)
REGION_SCOPE_ENUM = SQLEnum(
    'global', 'latam', 'colombia', 'andes', 'orinoco', 'amazonia', 'other',
    name="region_scope_enum", schema="bibliographic", create_type=False,
)
QUALITY_LEVEL_ENUM = SQLEnum(
    'high', 'medium', 'low',
    name="quality_level_enum", schema="bibliographic", create_type=False,
)


class ScientificSource(Base):
    """Una fila por referencia bibliográfica.

    `pub_year` corresponde al campo `year` del formulario y de los Excel; el
    contrato de la API lo expone como `year` mediante un alias.
    """
    __tablename__ = "scientific_source"
    __table_args__ = {"schema": "bibliographic"}

    source_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(SOURCE_TYPE_ENUM, nullable=False)
    citation_apa: Mapped[str | None] = mapped_column(Text)
    pub_year: Mapped[int | None] = mapped_column(SmallInteger)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[str | None] = mapped_column(Text)
    journal_or_publisher: Mapped[str | None] = mapped_column(Text)
    doi: Mapped[str | None] = mapped_column(Text, unique=True)
    url: Mapped[str | None] = mapped_column(Text)
    region_scope: Mapped[str | None] = mapped_column(REGION_SCOPE_ENUM)
    quality_level: Mapped[str | None] = mapped_column(QUALITY_LEVEL_ENUM)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
