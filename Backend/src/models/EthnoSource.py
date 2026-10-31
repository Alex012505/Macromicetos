"""Sesiones de entrevista (socioecological.ethno_source)."""
import uuid

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK

CONSENT_TYPE_ENUM = SQLEnum(
    'verbal', 'written',
    name="consent_type_enum", schema="socioecological", create_type=False,
)
ANONYMITY_LEVEL_ENUM = SQLEnum(
    'anonymous', 'pseudonym', 'identified',
    name="anonymity_level_enum", schema="socioecological", create_type=False,
)
OCCUPATION_ENUM = SQLEnum(
    'farmer', 'fisher', 'indigenous_knowledge_holder', 'rancher',
    'forester', 'student', 'teacher', 'other',
    name="occupation_enum", schema="socioecological", create_type=False,
)
AGE_RANGE_ENUM = SQLEnum(
    '12-17', '18-25', '26-40', '41-60', '60+',
    name="age_range_enum", schema="socioecological", create_type=False,
)
GENDER_ENUM = SQLEnum(
    'male', 'female', 'non_binary', 'prefer_not_to_say',
    name="gender_enum", schema="socioecological", create_type=False,
)


class EthnoSource(Base):
    """Una fila por sesión de entrevista.

    No identifica a la persona entrevistada: solo guarda al entrevistador del
    equipo y el nivel de anonimato. `state_province` se añadió respecto al
    diseño original porque el formulario web lo envía.
    """
    __tablename__ = "ethno_source"
    __table_args__ = {"schema": "socioecological"}

    ethno_source_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    interview_date: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    interviewer: Mapped[str] = mapped_column(Text, nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_type: Mapped[str | None] = mapped_column(CONSENT_TYPE_ENUM)
    anonymity_level: Mapped[str] = mapped_column(
        ANONYMITY_LEVEL_ENUM, nullable=False, default="anonymous", server_default="anonymous"
    )
    state_province: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text)
    village: Mapped[str | None] = mapped_column(Text)
    occupation: Mapped[str | None] = mapped_column(OCCUPATION_ENUM)
    age_range: Mapped[str | None] = mapped_column(AGE_RANGE_ENUM)
    gender: Mapped[str | None] = mapped_column(GENDER_ENUM)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
