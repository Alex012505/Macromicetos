import uuid
import datetime as dt
from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK
from models.TaxonRef import TaxonRef
from models.Occurrence import Occurrence

MORPHOLOGY_TYPE_ENUM = SQLEnum(
    'tipo_himenio', 'tipo_laminas', 'forma_poros', 'diametro_sombrero',
    'forma_sombrero', 'superficie_sombrero', 'borde_sombrero', 'color_sombrero',
    'forma_pie', 'color_pie', 'posicion_pie', 'ornamentacion_pie',
    'superficie_pie', 'presencia_anillo', 'tipo_anillo', 'presencia_volva',
    'cambio_color_corte', 'habito_crecimiento',
    name="morphology_type_enum", create_type=False,
)


class MorphologyFact(Base):
    """Característica morfológica EAV (ecological.morphology_fact)."""
    __tablename__ = "morphology_fact"
    __table_args__ = {"schema": "ecological"}

    morphology_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    taxon_id: Mapped[uuid.UUID | None] = mapped_column(
        PK(), ForeignKey(TaxonRef.taxon_id, onupdate="CASCADE", ondelete="CASCADE")
    )
    occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        PK(), ForeignKey(Occurrence.occurrence_id, onupdate="CASCADE", ondelete="CASCADE")
    )
    measurement_type: Mapped[str] = mapped_column(MORPHOLOGY_TYPE_ENUM, nullable=False)
    measurement_value: Mapped[str] = mapped_column(Text, nullable=False)
    measurement_unit: Mapped[str | None] = mapped_column(Text)
    measurement_determined_date: Mapped[dt.date | None] = mapped_column(Date)
    measurement_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())