"""Contratos de personas e instituciones (shared.party)."""
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Mismas expresiones que los CHECK de shared.party: validar aquí convierte un
# error de base de datos (500) en un 422 explicable al usuario.
ORCID_PATTERN = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

PartyScope = Literal["taxon", "occurrence", "event"]


class PartyData(BaseModel):
    """Persona o institución tal como la envía el formulario.

    ``display_name`` lo genera PostgreSQL en ``shared.party``; se acepta para no
    romper el contrato actual y la capa de servicio lo ignora al escribir.
    """
    model_config = ConfigDict(extra="forbid")

    party_id: uuid.UUID | None = None
    given_name: str | None = Field(None, max_length=120)
    family_name: str | None = Field(None, max_length=120)
    display_name: str | None = Field(None, max_length=250)
    orcid: str | None = Field(None, max_length=19, pattern=ORCID_PATTERN)
    affiliation: str | None = Field(None, max_length=250)
    contact_email: str | None = Field(None, max_length=254, pattern=EMAIL_PATTERN)

    @field_validator("orcid", "contact_email", mode="before")
    @classmethod
    def strip_identifiers(cls, value):
        # Un espacio pegado al copiar el ORCID o el correo rompería el CHECK.
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("*", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class ParticipantData(BaseModel):
    """Vínculo entre una persona y un registro.

    ``party_role`` es metadato del formulario: shared.taxon_party no guarda rol,
    pero event_party, occurrence_party y media_party sí lo conservan.
    """
    model_config = ConfigDict(extra="forbid")

    party: PartyData
    party_role: str | None = Field(None, max_length=40)
    scope: PartyScope | None = None
    is_primary: bool | None = False

    @field_validator("party_role", "scope", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class PhotoCredit(BaseModel):
    """Persona acreditada en una fotografía (shared.media_party).

    El formulario envía ``credit_role``; ``is_primary`` marca el crédito
    principal de la imagen.
    """
    model_config = ConfigDict(extra="forbid")

    party: PartyData
    credit_role: str | None = Field(None, max_length=40)
    is_primary: bool = False

    @field_validator("credit_role", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value
