import uuid
import datetime as dt
from sqlalchemy import Boolean, CHAR, DateTime, ForeignKey, Numeric, SmallInteger, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from models.UserWeb import PK
from database.Base import Base
from models.Occurrence import Occurrence

PHOTO_TYPE_ENUM = SQLEnum(
    'voucher', 'cap', 'hymenophore', 'side', 'stipe',
    'habitat', 'spore_print', 'detail', 'scale_reference',
    name="photo_type_enum", create_type=False,
)
CAPTURE_DEVICE_ENUM = SQLEnum(
    'phone', 'camera', 'stereomicroscope', 'scanner',
    name="capture_device_enum", create_type=False,
)


class Multimedia(Base):
    """Metadatos de una fotografía de campo (ecological.multimedia)."""
    __tablename__ = "multimedia"
    __table_args__ = {"schema": "ecological"}

    media_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    occurrence_id: Mapped[uuid.UUID] = mapped_column(
        PK(), ForeignKey(Occurrence.occurrence_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False
    )
    photo_type: Mapped[str] = mapped_column(PHOTO_TYPE_ENUM, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    sha256_hash: Mapped[str | None] = mapped_column(CHAR(64), unique=True)
    media_type: Mapped[str] = mapped_column(Text, nullable=False, default="StillImage")
    mime_format: Mapped[str] = mapped_column(Text, nullable=False, default="image/jpeg")
    captured_with: Mapped[str | None] = mapped_column(CAPTURE_DEVICE_ENUM)
    photographer: Mapped[str | None] = mapped_column(Text)
    capture_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    width_px: Mapped[int | None] = mapped_column(SmallInteger)
    height_px: Mapped[int | None] = mapped_column(SmallInteger)
    blur_score: Mapped[float | None] = mapped_column(Numeric(10, 4))     # lo llena image_qc
    qc_passed: Mapped[bool | None] = mapped_column(Boolean)              # lo llena image_qc
    license: Mapped[str | None] = mapped_column(
        Text, default="http://creativecommons.org/licenses/by-nc/4.0/"
    )
    rights_holder: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())