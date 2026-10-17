import uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, SmallInteger,
    String, Text, func,
)

from database.Base import Base
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

PK = lambda: PGUUID(as_uuid=True)  # noqa: E731

USER_ROLE_ENUM = SQLEnum(
    'admin', 'curator', 'analyst', 'viewer', 
    name="user_role_enum", 
    create_type=False
)

class UserWeb(Base):
    """Solo autenticación. """
    __tablename__ = "user_web"

    user_web_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)#
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(USER_ROLE_ENUM, default="viewer", nullable=False)


