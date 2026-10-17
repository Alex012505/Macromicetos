import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict


class MeasurementInput(BaseModel):
    event_id: uuid.UUID
    measurement_type: str
    measurement_value: float
    measurement_unit: str                       # "°C", "%", "hPa", "m", "m/s"
    measurement_determined_date: dt.datetime | None = None
    measurement_method: str = "Kestrel 3500"
    measurement_remarks: str | None = None


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    measurement_id: uuid.UUID
    event_id: uuid.UUID
    measurement_type: str
    measurement_value: float
    measurement_unit: str
    measurement_determined_date: dt.datetime | None = None
    measurement_method: str | None = None
    measurement_remarks: str | None = None
    created_at: dt.datetime