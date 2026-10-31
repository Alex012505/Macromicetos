"""Contratos de la capa bibliográfica (bibliographic.*).

Los tipos Literal reproducen los enums de PostgreSQL. Si un valor no está en la
lista, la API responde 422 antes de tocar la base.
"""
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceType = Literal[
    'article', 'book', 'book_chapter', 'thesis', 'report',
    'dataset', 'preprint', 'conference_paper', 'field_guide', 'website', 'other',
]
RegionScope = Literal['global', 'latam', 'colombia', 'andes', 'orinoco', 'amazonia', 'other']
QualityLevel = Literal['high', 'medium', 'low']
MentionType = Literal[
    'taxonomy', 'ecology', 'use', 'chemistry', 'distribution',
    'morphology', 'phylogeny', 'biocontrol',
]
EvidenceStrength = Literal['strong', 'moderate', 'weak', 'anecdotal']
SciUseCategory = Literal[
    'edible', 'medicinal', 'antimicrobial', 'antioxidant', 'enzyme',
    'bioremediation', 'agriculture', 'biocontrol', 'dye', 'ritual',
    'mythological', 'other',
]
EvidenceType = Literal['in_vitro', 'in_vivo', 'clinical', 'observational', 'review', 'meta_analysis']


class SourceData(BaseModel):
    """Una referencia bibliográfica del formulario.

    ``year`` es el nombre del formulario y de la API; en la tabla se llama
    ``pub_year``. La traducción ocurre en la capa de servicio.
    """
    model_config = ConfigDict(extra="forbid")

    source_id: uuid.UUID | None = None
    source_type: SourceType | None = None
    title: str | None = Field(None, max_length=2000)
    authors: str | None = Field(None, max_length=1000)
    year: int | None = Field(None, ge=1753, le=2100)
    doi: str | None = Field(None, max_length=300)
    citation_apa: str | None = Field(None, max_length=4000)
    journal_or_publisher: str | None = Field(None, max_length=500)
    url: str | None = Field(None, max_length=1000)
    region_scope: RegionScope | None = None
    quality_level: QualityLevel | None = None
    notes: str | None = Field(None, max_length=4000)

    @field_validator("*", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class ScientificTaxonLinkData(BaseModel):
    """Mención de un taxón en una fuente (futuro endpoint de vínculos)."""
    model_config = ConfigDict(extra="forbid")

    taxon_source_link_id: uuid.UUID | None = None
    taxon_id: uuid.UUID
    source_id: uuid.UUID
    mention_type: MentionType
    evidence_strength: EvidenceStrength | None = None
    location_in_source: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=4000)


class ScientificUseData(BaseModel):
    """Afirmación de uso extraída de la literatura (futuro endpoint de usos)."""
    model_config = ConfigDict(extra="forbid")

    sci_use_id: uuid.UUID | None = None
    taxon_id: uuid.UUID
    source_id: uuid.UUID
    use_category: SciUseCategory
    evidence_type: EvidenceType | None = None
    claimed_effect: str | None = Field(None, max_length=4000)
    method_summary: str | None = Field(None, max_length=4000)
    key_result: str | None = Field(None, max_length=4000)
    safety_notes: str | None = Field(None, max_length=4000)
