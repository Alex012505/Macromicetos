import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocationInput(BaseModel):
    state_province: str | None = None
    municipality: str | None = None
    locality: str | None = None
    decimal_latitude: float | None = Field(None, ge=-90, le=90)
    decimal_longitude: float | None = Field(None, ge=-180, le=180)
    coordinate_uncertainty_m: float | None = Field(None, ge=0)
    elevation_m: float | None = Field(None, gt=-500)
    habitat: str | None = None
    location_remarks: str | None = None


class LocationData(LocationInput):
    """Location payload used inside the complete record form."""

    model_config = ConfigDict(extra="forbid")

    location_id: uuid.UUID
    country: str = Field("CO", pattern="^[A-Za-z]{2}$")

    @model_validator(mode="after")
    def paired_coordinates(self):
        if (self.decimal_latitude is None) != (self.decimal_longitude is None):
            raise ValueError("Ingresa latitud y longitud juntas.")
        return self


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: uuid.UUID
    country: str
    country_code: str
    state_province: str | None = None
    municipality: str | None = None
    locality: str | None = None
    decimal_latitude: float | None = None
    decimal_longitude: float | None = None
    coordinate_uncertainty_m: float | None = None
    elevation_m: float | None = None
    geodetic_datum: str
    habitat: str | None = None
    location_remarks: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime