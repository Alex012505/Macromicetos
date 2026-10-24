import uuid
import datetime as dt
from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.Location import Location
from models.UserWeb import PK

EVENT_TYPE_ENUM = SQLEnum(
    'Observation', 'Survey', 'Expedition', 'SiteVisit', 'SamplingEvent',
    name="event_type_enum", create_type=False,
)
SAMPLING_PROTOCOL_ENUM = SQLEnum(
    'OpportunisticSearch', 'LinearTransect', 'FixedPlot', 'QuadratSampling',
    'TargetedCollection', 'PhotographicRecord', 'MixedProtocol',
    name="sampling_protocol_enum", create_type=False,
)
SAMPLING_EFFORT_ENUM = SQLEnum(
    '1 observer-hour', '2 observer-hours', '4 observer-hours',
    'half-day survey', 'full-day survey',
    '100 m transect', '500 m transect', '1 plot', '2 plots',
    name="sampling_effort_enum", create_type=False,
)


class Event(Base):
    """Una salida de campo (ecological.event). uq_event_site_date en la BD."""
    __tablename__ = "event"
    __table_args__ = {"schema": "ecological"}

    event_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(
        PK(), ForeignKey(Location.location_id, onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str | None] = mapped_column(EVENT_TYPE_ENUM)
    field_number: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    event_time: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[str | None] = mapped_column(Text)
    sampling_protocol: Mapped[str | None] = mapped_column(SAMPLING_PROTOCOL_ENUM)
    sampling_effort: Mapped[str | None] = mapped_column(SAMPLING_EFFORT_ENUM)
    event_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())