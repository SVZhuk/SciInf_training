"""Data access layer (Repository pattern).

Routers depend on the `SampleRepository` Protocol, not on a concrete class.
Swap `InMemorySampleRepository` for a SQLAlchemy + Postgres implementation
later without touching a single endpoint.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from app.schemas import Organism, SampleCreate, SampleUpdate


@dataclass(slots=True)
class Sample:
    """Domain/persistence object (would be a SQLAlchemy model in production)."""

    name: str
    organism: Organism
    sequence: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DuplicateNameError(Exception):
    pass


class SampleRepository(Protocol):
    def list(
        self, *, organism: Organism | None, limit: int, offset: int
    ) -> tuple[list[Sample], int]: ...
    def get(self, sample_id: UUID) -> Sample | None: ...
    def add(self, data: SampleCreate) -> Sample: ...
    def update(self, sample: Sample, data: SampleUpdate) -> Sample: ...
    def delete(self, sample: Sample) -> None: ...


class InMemorySampleRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Sample] = {}

    def list(
        self, *, organism: Organism | None, limit: int, offset: int
    ) -> tuple[list[Sample], int]:
        rows = [s for s in self._items.values() if organism is None or s.organism == organism]
        rows.sort(key=lambda s: s.created_at)
        return rows[offset : offset + limit], len(rows)

    def get(self, sample_id: UUID) -> Sample | None:
        return self._items.get(sample_id)

    def add(self, data: SampleCreate) -> Sample:
        if any(s.name == data.name for s in self._items.values()):
            raise DuplicateNameError(data.name)
        sample = Sample(**data.model_dump())
        self._items[sample.id] = sample
        return sample

    def update(self, sample: Sample, data: SampleUpdate) -> Sample:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(sample, key, value)
        return sample

    def delete(self, sample: Sample) -> None:
        self._items.pop(sample.id, None)
