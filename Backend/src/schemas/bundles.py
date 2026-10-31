"""Aggregate request contracts for the complete taxon, record and media forms."""
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.bibliographic_schema import SourceData
from schemas.event_schema import EventData
from schemas.location_schema import LocationData
from schemas.measurement_schema import MeasurementData
from schemas.morphology_schema import MorphologyData
from schemas.multimedia_schema import PhotoData
from schemas.occurrence_schema import OccurrenceData
from schemas.party_schema import ParticipantData
from schemas.socioecological_schema import EthnoSurveyData
from schemas.taxon_schema import TaxonData


class RecordBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: uuid.UUID | None = None
    location: LocationData
    event: EventData
    occurrence: OccurrenceData
    morphology: list[MorphologyData] = Field(default_factory=list, max_length=18)
    measurements: list[MeasurementData] = Field(default_factory=list, max_length=100)
    participants: list[ParticipantData] = Field(default_factory=list, max_length=100)
    multimedia: list[PhotoData] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def linked_ids(self):
        if self.event.location_id != self.location.location_id or self.occurrence.event_id != self.event.event_id:
            raise ValueError("Los identificadores de ubicación, evento y hallazgo no coinciden.")
        return self


class TaxonBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taxon: TaxonData
    morphology: list[MorphologyData] = Field(default_factory=list, max_length=18)
    sources: list[SourceData] = Field(default_factory=list, max_length=100)
    knowledge: list[EthnoSurveyData] = Field(default_factory=list, max_length=100)
    participants: list[ParticipantData] = Field(default_factory=list, max_length=100)


class MediaBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurrence_id: uuid.UUID
    multimedia: list[PhotoData] = Field(min_length=1, max_length=10)
