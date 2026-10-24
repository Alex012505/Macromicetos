import uuid
from sqlalchemy import DateTime, Numeric, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

HABITAT_ENUM = SQLEnum(
    'GalleryForest', 'FloodplainForest', 'Forest', 'Savanna', 'SecondaryForest',
    'Pasture', 'PalmGrove', 'RiparianVegetation', 'DisturbedArea', 'UrbanGreenArea',
    'CropEdge', 'Morichal', 'PermanentWetland', 'SeasonalWetland', 'Estero',
    'Laguna', 'ForestPlantation', 'Other',
    name="habitat_enum", create_type=False,
)


class Location(Base):
    """Sitio de campo nombrado (ecological.location). geog lo llena un trigger."""
    __tablename__ = "location"
    __table_args__ = {"schema": "ecological"}

    location_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    country: Mapped[str] = mapped_column(Text, nullable=False, default="Colombia")
    country_code: Mapped[str] = mapped_column(Text(2), nullable=False, default="CO")
    state_province: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text)
    locality: Mapped[str | None] = mapped_column(Text)
    decimal_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    decimal_longitude: Mapped[float | None] = mapped_column(Numeric(10, 6))
    coordinate_uncertainty_m: Mapped[float | None] = mapped_column(Numeric(10, 2))
    elevation_m: Mapped[float | None] = mapped_column(Numeric(7, 2))
    geodetic_datum: Mapped[str] = mapped_column(Text, nullable=False, default="WGS84")
    habitat: Mapped[str | None] = mapped_column(HABITAT_ENUM)
    location_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())