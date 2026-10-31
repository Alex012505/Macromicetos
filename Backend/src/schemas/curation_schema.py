import uuid
import datetime as dt
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Espejo EXACTO del ENUM curaduria.curable_entity_enum de la BD.
# Cuando agregues una capa nueva, toca aquí Y en el SQL.
EntityType = Literal[
    "taxon_ref", "location", "event", "occurrence",
    "multimedia", "measurement_or_fact", "morphology_fact", "user_web",
]

CURATION_STATUSES = Literal[
    "draft", "submitted", "in_review",
    "verified", "needs_adjustment", "rejected",
]

# Decisión simplificada que expone el formulario de curaduría del aplicativo.
CurationStatus = Literal["verified", "rejected"]

# Estados que ve la cola de curaduría del aplicativo. Agrupan los estados
# técnicos de curation_status_enum sin exponerlos al frontend.
QueueStatus = Literal["pending", "verified", "rejected"]


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CurationStatus
    review_note: str = Field("", max_length=2000)

    @model_validator(mode="after")
    def rejection_reason(self):
        if self.status == "rejected" and len(self.review_note.strip()) < 10:
            raise ValueError("Explica los ajustes necesarios con al menos 10 caracteres.")
        return self


class CurationDecisionInput(BaseModel):
    entity_type: EntityType
    entity_id: uuid.UUID
    new_status: CURATION_STATUSES
    comment: str | None = Field(None, max_length=2000)


class CurationDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    decided_by: uuid.UUID | None = None
    previous_status: str | None = None
    new_status: str
    comment: str | None = None
    created_at: dt.datetime


class CurrentStatusItem(BaseModel):
    """Estado vigente de una entidad (última decisión)."""
    entity_type: str
    entity_id: uuid.UUID
    current_status: str
    decided_by: uuid.UUID | None = None
    comment: str | None = None
    last_decision_at: dt.datetime


class AuditLogItem(BaseModel):
    """Lectura del log técnico (tabla audit_log, la llena el trigger)."""
    model_config = ConfigDict(from_attributes=True)

    log_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    column_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    changed_by: str | None = None
    changed_at: dt.datetime