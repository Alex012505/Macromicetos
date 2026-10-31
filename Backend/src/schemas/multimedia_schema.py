import uuid
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field

from schemas.party_schema import PhotoCredit


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


class PhotoData(BaseModel):
    """Metadata sent by the client for each uploaded photo.

    The server computes ``file_path``, hash and dimensions, so this contract is
    intentionally different from ``MultimediaInput``.
    """

    model_config = ConfigDict(extra="forbid")

    media_id: uuid.UUID
    photo_type: str
    file_name: str = Field(min_length=1, max_length=255)
    mime_format: str | None = None
    media_type: str = "StillImage"
    photographer: str | None = None
    license: str | None = None
    rights_holder: str | None = None
    credits: list[PhotoCredit] = Field(default_factory=list, max_length=50)


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

class PhotoArchiveItem(BaseModel):
    media_id: uuid.UUID
    occurrence_id: uuid.UUID
    photo_type: str
    file_name: str
    file_path: str
    scientific_name: str | None = None
    common_name_es: str | None = None
    state_province: str | None = None
    locality: str | None = None
    event_date: dt.date | None = None
    sha256_hash: str | None = None    