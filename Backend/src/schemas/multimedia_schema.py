import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field


class MultimediaInput(BaseModel):
    occurrence_id: uuid.UUID
    photo_type: str                                     # requerido en la BD
    file_name: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    source_url: str | None = None
    sha256_hash: str | None = Field(None, pattern=r"^[0-9a-fA-F]{64}$")
    media_type: str = "StillImage"
    mime_format: str = "image/jpeg"
    captured_with: str | None = None
    photographer: str | None = None
    capture_date: dt.datetime | None = None
    width_px: int | None = Field(None, gt=0)
    height_px: int | None = Field(None, gt=0)
    license: str | None = None                          # default del modelo: CC BY-NC 4.0
    rights_holder: str | None = None


class MultimediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    media_id: uuid.UUID
    occurrence_id: uuid.UUID
    photo_type: str
    file_name: str
    file_path: str
    source_url: str | None = None
    sha256_hash: str | None = None
    media_type: str
    mime_format: str
    captured_with: str | None = None
    photographer: str | None = None
    capture_date: dt.datetime | None = None
    width_px: int | None = None
    height_px: int | None = None
    blur_score: float | None = None
    qc_passed: bool | None = None
    license: str | None = None
    rights_holder: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime