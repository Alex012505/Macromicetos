import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MorphologyInput(BaseModel):
    taxon_id: uuid.UUID | None = None
    occurrence_id: uuid.UUID | None = None
    measurement_type: str
    measurement_value: str = Field(min_length=1)
    measurement_unit: str | None = None
    measurement_determined_date: dt.date | None = None
    measurement_remarks: str | None = None

    @model_validator(mode="after")
    def requiere_anclaje(self):
        if self.taxon_id is None and self.occurrence_id is None:
            raise ValueError("El rasgo debe anclarse a un taxón o a una ocurrencia (CHECK chk_morphology_link)")
        return self


class MorphologyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    morphology_id: uuid.UUID
    taxon_id: uuid.UUID | None = None
    occurrence_id: uuid.UUID | None = None
    measurement_type: str
    measurement_value: str
    measurement_unit: str | None = None
    measurement_determined_date: dt.date | None = None
    measurement_remarks: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime