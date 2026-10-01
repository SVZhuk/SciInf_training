"""Data access layer (Repository pattern).

Routers depend on the `SampleRepository` Protocol, not on a concrete class.
`InMemorySampleRepository` is a fast, DB-free implementation; `SqlAlchemySampleRepository`
is the Postgres-backed one. Both satisfy the same Protocol so routers never change.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SampleModel
from app.schemas import Organism, SampleCreate, SampleUpdate


class Sample(Protocol):
    """Structural shape a repository hands back: an in-memory row or an ORM row."""

    id: UUID
    name: str
    organism: Organism
    sequence: str
    created_at: datetime


@dataclass(slots=True)
class InMemorySample:
    name: str
    organism: Organism
    sequence: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DuplicateNameError(Exception):
    pass


class SampleRepository(Protocol):
    async def list(
        self, *, organism: Organism | None, limit: int, offset: int
    ) -> tuple[list[Sample], int]: ...
    async def get(self, sample_id: UUID) -> Sample | None: ...
    async def add(self, data: SampleCreate) -> Sample: ...
    async def update(self, sample: Sample, data: SampleUpdate) -> Sample: ...
    async def delete(self, sample: Sample) -> None: ...


class InMemorySampleRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, InMemorySample] = {}

    async def list(
        self, *, organism: Organism | None, limit: int, offset: int
    ) -> tuple[list[Sample], int]:
        rows = [s for s in self._items.values() if organism is None or s.organism == organism]
        rows.sort(key=lambda s: s.created_at)
        return list(rows[offset : offset + limit]), len(rows)

    async def get(self, sample_id: UUID) -> Sample | None:
        return self._items.get(sample_id)

    async def add(self, data: SampleCreate) -> Sample:
        if any(s.name == data.name for s in self._items.values()):
            raise DuplicateNameError(data.name)
        sample = InMemorySample(**data.model_dump())
        self._items[sample.id] = sample
        return sample

    async def update(self, sample: Sample, data: SampleUpdate) -> Sample:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(sample, key, value)
        return sample

    async def delete(self, sample: Sample) -> None:
        self._items.pop(sample.id, None)


class SqlAlchemySampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, organism: Organism | None, limit: int, offset: int
    ) -> tuple[list[Sample], int]:
        stmt = select(SampleModel)
        if organism is not None:
            stmt = stmt.where(SampleModel.organism == organism)

        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery()))

        rows_stmt = stmt.order_by(SampleModel.created_at).limit(limit).offset(offset)
        result = await self._session.execute(rows_stmt)
        return list(result.scalars().all()), total or 0  # pyright: ignore[reportReturnType]

    async def get(self, sample_id: UUID) -> Sample | None:
        return await self._session.get(SampleModel, sample_id)  # pyright: ignore[reportReturnType]

    async def add(self, data: SampleCreate) -> Sample:
        model = SampleModel(**data.model_dump())
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateNameError(data.name) from exc
        return model  # pyright: ignore[reportReturnType]

    async def update(self, sample: Sample, data: SampleUpdate) -> Sample:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(sample, key, value)
        return sample

    async def delete(self, sample: Sample) -> None:
        await self._session.delete(sample)
        await self._session.flush()
