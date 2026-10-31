"""Personas e instituciones y su vínculo con taxones, hallazgos y fotos."""
import uuid

from sqlalchemy import Boolean, Computed, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.UserWeb import PK


class Party(Base):
    """Persona o institución (shared.party).

    display_name es una columna generada por PostgreSQL: nunca se inserta ni
    se actualiza desde Python.
    """
    __tablename__ = "party"
    __table_args__ = {"schema": "shared"}

    party_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    given_name: Mapped[str] = mapped_column(Text, nullable=False)
    family_name: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(
        Text,
        Computed("given_name || ' ' || COALESCE(family_name, '')", persisted=True),
        nullable=False,
    )
    orcid: Mapped[str | None] = mapped_column(Text, unique=True)
    affiliation: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaxonParty(Base):
    """Responsables de un taxón (shared.taxon_party)."""
    __tablename__ = "taxon_party"
    __table_args__ = {"schema": "shared"}

    taxon_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("shared.taxon_ref.taxon_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("shared.party.party_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventParty(Base):
    """Personas que participaron en una salida de campo (shared.event_party)."""
    __tablename__ = "event_party"
    __table_args__ = {"schema": "shared"}

    event_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("ecological.event.event_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("shared.party.party_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )
    party_role: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OccurrenceParty(Base):
    """Personas vinculadas a un hallazgo (shared.occurrence_party)."""
    __tablename__ = "occurrence_party"
    __table_args__ = {"schema": "shared"}

    occurrence_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("ecological.occurrence.occurrence_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("shared.party.party_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )
    party_role: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MediaParty(Base):
    """Créditos de una fotografía (shared.media_party)."""
    __tablename__ = "media_party"
    __table_args__ = {"schema": "shared"}

    media_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("ecological.multimedia.media_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        PK(),
        ForeignKey("shared.party.party_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    )
    party_role: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
