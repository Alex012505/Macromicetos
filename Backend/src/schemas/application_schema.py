"""Validated aggregate contracts used by the frontend's complete forms."""
import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.event_schema import EventInput
from schemas.occurrence_schema import OccurrenceInput
from schemas.taxon_schema import TaxonRefInput


class LocationData(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    location_id: uuid.UUID
    country: str = Field("CO", pattern="^[A-Za-z]{2}$")
    state_province: str | None = None
    municipality: str | None = None
    locality: str = Field(min_length=1)
    decimal_latitude: float | None = Field(None, ge=-90, le=90)
    decimal_longitude: float | None = Field(None, ge=-180, le=180)
    coordinate_uncertainty_m: float | None = Field(None, ge=0)
    elevation_m: float | None = None
    habitat: str | None = None
    location_remarks: str | None = None

    @model_validator(mode="after")
    def paired_coordinates(self):
        if (self.decimal_latitude is None) != (self.decimal_longitude is None):
            raise ValueError("Ingresa latitud y longitud juntas.")
        return self


class EventData(EventInput):
    model_config = ConfigDict(extra="forbid")
    event_id: uuid.UUID


class OccurrenceData(OccurrenceInput):
    model_config = ConfigDict(extra="forbid")
    occurrence_id: uuid.UUID


class MorphologyData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    taxon_id: uuid.UUID | None = None
    occurrence_id: uuid.UUID | None = None
    measurement_type: str
    measurement_value: str = Field(min_length=1, max_length=2000)
    measurement_unit: str | None = None
    measurement_determined_date: dt.date | None = None
    measurement_remarks: str | None = None


class PhotoData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_id: uuid.UUID
    photo_type: str
    file_name: str = Field(min_length=1, max_length=255)
    mime_format: str | None = None
    media_type: str = "StillImage"
    photographer: str | None = None
    license: str | None = None
    rights_holder: str | None = None
    credits: list[dict] = Field(default_factory=list, max_length=50)


class RecordBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner_id: uuid.UUID | None = None
    location: LocationData
    event: EventData
    occurrence: OccurrenceData
    morphology: list[MorphologyData] = Field(default_factory=list, max_length=18)
    measurements: list[dict] = Field(default_factory=list, max_length=100)
    participants: list[dict] = Field(default_factory=list, max_length=100)
    multimedia: list[PhotoData] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def linked_ids(self):
        if self.event.location_id != self.location.location_id or self.occurrence.event_id != self.event.event_id:
            raise ValueError("Los identificadores de ubicación, evento y hallazgo no coinciden.")
        return self


class TaxonData(TaxonRefInput):
    model_config = ConfigDict(extra="forbid")
    taxon_id: uuid.UUID

class TaxonBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    taxon: TaxonData
    morphology: list[MorphologyData] = Field(default_factory=list, max_length=18)
    sources: list[dict] = Field(default_factory=list, max_length=100)
    knowledge: list[dict] = Field(default_factory=list, max_length=100)
    participants: list[dict] = Field(default_factory=list, max_length=100)


class MediaBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    occurrence_id: uuid.UUID
    multimedia: list[PhotoData] = Field(min_length=1, max_length=10)


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["viewer", "analyst", "curator", "admin"]


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["verified", "rejected"]
    review_note: str = Field("", max_length=2000)

    @model_validator(mode="after")
    def rejection_reason(self):
        if self.status == "rejected" and len(self.review_note.strip()) < 10:
            raise ValueError("Explica los ajustes necesarios con al menos 10 caracteres.")
        return self
