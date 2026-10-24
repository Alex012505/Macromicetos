import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field



class LocationInput(BaseModel):
    state_province: str | None = None
    municipality: str | None = None
    locality: str | None = None
    decimal_latitude: float | None = Field(None, ge=-90, le=90)
    decimal_longitude: float | None = Field(None, ge=-180, le=180)
    coordinate_uncertainty_m: float | None = Field(None, gt=0)
    elevation_m: float | None = Field(None, gt=-500)
    habitat: str | None = None
    location_remarks: str | None = None


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