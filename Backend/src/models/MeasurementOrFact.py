import uuid
import datetime as dt
from sqlalchemy import DateTime, ForeignKey, Numeric, Text,func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from models.UserWeb import PK
from database.Base import Base
from models.Event import Event

MEASUREMENT_TYPE_ENUM = SQLEnum(
    'temperature', 'relativeHumidity', 'atmosphericPressure', 'altitude',
    'dewPoint', 'heatIndex', 'windSpeed', 'windChill',
    name="measurement_type_enum", create_type=False,
)


class MeasurementOrFact(Base):
    """Lectura de microclima por evento (ecological.measurement_or_fact)."""
    __tablename__ = "measurement_or_fact"
    __table_args__ = {"schema": "ecological"}

    measurement_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(PK(), ForeignKey(Event.event_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    measurement_type: Mapped[str] = mapped_column(MEASUREMENT_TYPE_ENUM, nullable=False)
    measurement_value: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    measurement_unit: Mapped[str] = mapped_column(Text, nullable=False)
    measurement_determined_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    measurement_method: Mapped[str | None] = mapped_column(Text, default="Kestrel 3500")
    measurement_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Sin updated_at a propósito: las lecturas no se modifican (diseño del SQL).