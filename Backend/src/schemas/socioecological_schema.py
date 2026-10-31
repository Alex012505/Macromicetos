"""Contratos de la capa socioecológica (socioecological.*).

Los tipos Literal reproducen los enums de PostgreSQL. Los campos que el
formulario deja en blanco llegan como cadena vacía y se normalizan a NULL.
"""
import datetime as dt
import uuid
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

ConsentType = Literal['verbal', 'written']
AnonymityLevel = Literal['anonymous', 'pseudonym', 'identified']
Occupation = Literal[
    'farmer', 'fisher', 'indigenous_knowledge_holder', 'rancher',
    'forester', 'student', 'teacher', 'other',
]
AgeRange = Literal['12-17', '18-25', '26-40', '41-60', '60+']
Gender = Literal['male', 'female', 'non_binary', 'prefer_not_to_say']
LearningSource = Literal[
    'family', 'community', 'personal_experience', 'books',
    'workshops', 'internet', 'other',
]
EthnoUseCategory = Literal[
    'edible', 'medicinal', 'ritual', 'dye', 'soil_improvement',
    'biological_control', 'animal_feed', 'other',
]
Importance = Literal['high', 'medium', 'low']
CulturalIdentity = Literal['yes', 'no', 'partial']


class EthnoSourceData(BaseModel):
    """Una sesión de entrevista (socioecological.ethno_source).

    No identifica a la persona entrevistada: solo al entrevistador del equipo.
    """
    model_config = ConfigDict(extra="forbid")

    ethno_source_id: uuid.UUID | None = None
    interview_date: dt.datetime | None = None
    interviewer: str | None = Field(None, max_length=250)
    consent_given: bool | None = False
    consent_type: ConsentType | None = None
    anonymity_level: AnonymityLevel | None = None
    state_province: str | None = Field(None, max_length=120)
    municipality: str | None = Field(None, max_length=120)
    village: str | None = Field(None, max_length=120)
    occupation: Occupation | None = None
    age_range: AgeRange | None = None
    gender: Gender | None = None
    remarks: str | None = Field(None, max_length=4000)

    @field_validator("*", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class EthnoKnowledgeData(BaseModel):
    """Conocimiento local sobre el taxón (socioecological.ethno_taxon_knowledge)."""
    model_config = ConfigDict(extra="forbid")

    knowledge_id: uuid.UUID | None = Field(
        None, validation_alias=AliasChoices("knowledge_id", "ethno_know_id")
    )
    ethno_source_id: uuid.UUID | None = None
    taxon_id: uuid.UUID | None = None
    knows_fungi: bool | None = None
    local_name: str | None = Field(None, max_length=250)
    learning_source: LearningSource | None = None
    recognition_cues: str | None = Field(None, max_length=4000)
    found_in_places: str | None = Field(None, max_length=1000)
    seasonality: str | None = Field(None, max_length=250)
    months: str | None = Field(None, max_length=120)
    safety_practices: str | None = Field(None, max_length=4000)
    myths_stories: str | None = Field(None, max_length=8000)
    cultural_identity: CulturalIdentity | None = None
    recommendations: str | None = Field(None, max_length=4000)

    @field_validator("*", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class EthnoUseData(BaseModel):
    """Un uso reportado (socioecological.ethno_use).

    ``recommendations`` no existe en ethno_use: el servicio la guarda en
    ethno_taxon_knowledge.recommendations. ``taxon_id`` es una FK redundante
    que el servicio copia desde el conocimiento.
    """
    model_config = ConfigDict(extra="forbid")

    use_id: uuid.UUID | None = Field(
        None, validation_alias=AliasChoices("use_id", "ethno_use_id", "id")
    )
    knowledge_id: uuid.UUID | None = Field(
        None, validation_alias=AliasChoices("knowledge_id", "ethno_know_id")
    )
    taxon_id: uuid.UUID | None = None
    uses_fungi: bool | None = None
    use_category: EthnoUseCategory | None = None
    preparation_method: str | None = Field(None, max_length=4000)
    ailment: str | None = Field(None, max_length=500)
    dosage: str | None = Field(None, max_length=500)
    contraindications: str | None = Field(None, max_length=4000)
    importance: Importance | None = None
    recommendations: str | None = Field(None, max_length=4000)

    @field_validator("*", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class EthnoSurveyData(BaseModel):
    """Una entrevista completa: fuente, conocimiento del taxón y usos."""
    model_config = ConfigDict(extra="forbid")

    source: EthnoSourceData
    knowledge: EthnoKnowledgeData
    uses: list[EthnoUseData] = Field(default_factory=list, max_length=20)
