"""SQLAlchemy 2.0 declarative models (table shape only, no storage logic).

Mirrors `schemas.py` being separate from `routers/`: this module defines
column metadata, never opens a Session or runs a query. `repository.py`
remains the sole module that talks to a live Session.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.schemas import Organism

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    pass


Base.metadata.naming_convention = NAMING_CONVENTION


class SampleModel(Base):
    __tablename__ = "samples"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    organism: Mapped[Organism] = mapped_column(
        Enum(
            Organism,
            native_enum=False,
            length=50,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    sequence: Mapped[str] = mapped_column(String(10_000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
