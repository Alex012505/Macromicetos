import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class MeasurementData(BaseModel):
    """Free measurement used inside the complete record form.

    The value stays a string because the form accepts expressions such as
    "5–8" or "24 °C"; it is not restricted to the legacy microclimate enum.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID | None = None
    occurrence_id: uuid.UUID | None = None
    measurement_type: str = Field(min_length=1, max_length=200)
    measurement_value: str = Field(min_length=1, max_length=2000)
    measurement_unit: str | None = None
    measurement_determined_date: dt.datetime | None = None
    measurement_method: str | None = None
    measurement_remarks: str | None = None

    @model_validator(mode="after")
    def one_scope(self):
        if (self.event_id is None) == (self.occurrence_id is None):
            raise ValueError("Cada medida debe pertenecer al evento o al hallazgo, pero no a ambos.")
        return self