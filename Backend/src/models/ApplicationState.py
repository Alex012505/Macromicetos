"""Ownership and extended form collections absent from the original core schema.

This additive companion table leaves existing scientific tables intact. Core
taxa, locations, events, occurrences, morphology and media retain their models.
"""
import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK, UserWeb


class ApplicationState(Base):
    __tablename__ = "application_state"

    entity_type: Mapped[str] = mapped_column(String(24), primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(PK(), ForeignKey(UserWeb.user_web_id))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(PK(), ForeignKey(UserWeb.user_web_id))
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
