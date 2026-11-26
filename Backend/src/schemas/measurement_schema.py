"""Contratos de ecological.measurement_or_fact (microclima de una salida de campo).

La tabla es el requisito: no tiene occurrence_id, el tipo es el enum cerrado
public.measurement_type_enum, el valor es numérico y la unidad es obligatoria.
"""
import uuid
import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Espejo del enum public.measurement_type_enum de PostgreSQL.
MeasurementType = Literal[
    "temperature", "relativeHumidity", "atmosphericPressure", "altitude",
    "dewPoint", "heatIndex", "windSpeed", "windChill",
]


class MeasurementInput(BaseModel):
    event_id: uuid.UUID
    measurement_type: MeasurementType
    measurement_value: Decimal = Field(max_digits=10, decimal_places=4)
    measurement_unit: str = Field(min_length=1, max_length=50)   # "°C", "%", "hPa", "m", "m/s"
    measurement_determined_date: dt.datetime | None = None
    measurement_method: str = "Kestrel 3500"
    measurement_remarks: str | None = None

    @field_validator("measurement_unit")
    @classmethod
    def unit_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Indica la unidad de la medida.")
        return value


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    measurement_id: uuid.UUID
    event_id: uuid.UUID
    measurement_type: str
    measurement_value: float
    measurement_unit: str
    measurement_determined_date: dt.datetime | None = None
    measurement_method: str | None = None
    measurement_remarks: str | None = None
    created_at: dt.datetime


class MeasurementData(BaseModel):
    """Medida ambiental de la salida de campo dentro del formulario completo.

    Se adapta a ecological.measurement_or_fact: el evento es obligatorio, el
    tipo pertenece al enum de microclima, el valor es numérico y la unidad no
    puede quedar vacía.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID
    measurement_type: MeasurementType
    measurement_value: Decimal = Field(max_digits=10, decimal_places=4)
    measurement_unit: str = Field(min_length=1, max_length=50)
    measurement_method: str | None = Field(default=None, max_length=200)
    measurement_remarks: str | None = Field(default=None, max_length=2000)

    @field_validator("measurement_unit")
    @classmethod
    def unit_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Indica la unidad de la medida.")
        return value

    @field_validator("measurement_method", "measurement_remarks", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value
