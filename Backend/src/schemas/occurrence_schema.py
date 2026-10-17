import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field


class OccurrenceInput(BaseModel):
    event_id: uuid.UUID
    taxon_id: uuid.UUID | None = None
    external_occurrence_id: str | None = None
    basis_of_record: str = "HumanObservation"
    recorded_by: str | None = None
    event_date: dt.datetime | None = None
    occurrence_status: str = "present"
    individual_count: int | None = Field(None, ge=0)
    occurrence_remarks: str | None = None
    verbatim_scientific_name: str | None = None
    identification_qualifier: str = "none"
    identified_by: str | None = None
    date_identified: dt.date | None = None
    substrate: str | None = None
    associated_organisms: str | None = None
    associated_references: str | None = None


class OccurrenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    occurrence_id: uuid.UUID
    event_id: uuid.UUID
    taxon_id: uuid.UUID | None = None
    external_occurrence_id: str | None = None
    basis_of_record: str
    recorded_by: str | None = None
    event_date: dt.datetime | None = None
    occurrence_status: str
    individual_count: int | None = None
    occurrence_remarks: str | None = None
    verbatim_scientific_name: str | None = None
    identification_qualifier: str | None = None
    identified_by: str | None = None
    date_identified: dt.date | None = None
    substrate: str | None = None
    associated_organisms: str | None = None
    associated_references: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime