import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field


class EventInput(BaseModel):
    location_id: uuid.UUID
    event_type: str = "Observation"
    field_number: str | None = None
    event_date: dt.date
    event_time: str | None = None          # formato libre: "08:30" o "08:30/17:00"
    recorded_by: str | None = None
    sampling_protocol: str | None = None
    sampling_effort: str | None = None
    event_remarks: str | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    location_id: uuid.UUID
    event_type: str | None = None
    field_number: str | None = None
    event_date: dt.date
    event_time: str | None = None
    recorded_by: str | None = None
    sampling_protocol: str | None = None
    sampling_effort: str | None = None
    event_remarks: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime