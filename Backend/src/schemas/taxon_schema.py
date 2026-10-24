import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

TAXON_RANKS = [
    'kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species',
    'subspecies', 'variety', 'form',
]


class TaxonRefInput(BaseModel):
    scientific_name: str = Field(min_length=2)
    taxon_rank: str = Field()  # validado por el Enum de la BD
    kingdom: str = "Fungi"
    phylum: str | None = None
    class_name: str | None = Field(None, alias="class")
    order_name: str | None = Field(None, alias="order")
    family: str | None = None
    genus: str | None = None
    specific_epithet: str | None = None
    external_taxon_id: str | None = None
    common_name_es: str | None = None
    taxon_remarks: str | None = None

    @field_validator("taxon_rank")
    @classmethod
    def valid_rank(cls, value):
        if value not in TAXON_RANKS:
            raise ValueError("Rango taxonómico inválido.")
        return value


class TaxonRefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    taxon_id: uuid.UUID
    scientific_name: str
    taxon_rank: str
    kingdom: str
    phylum: str | None = None
    class_name: str | None = Field(None, alias="class")
    order_name: str | None = Field(None, alias="order")
    family: str | None = None
    genus: str | None = None
    specific_epithet: str | None = None
    external_taxon_id: str | None = None
    common_name_es: str | None = None
    taxon_remarks: str | None = None
    created_at: datetime
    updated_at: datetime
