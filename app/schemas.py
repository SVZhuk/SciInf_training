"""Pydantic models = the API contract (DTO pattern).

Separate models for input (Create/Update) and output (Read) so clients
can never set server-owned fields such as `id` or `created_at`.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

DNA_ALPHABET: frozenset[str] = frozenset("ACGTN")


class Organism(str, Enum):
    HUMAN = "homo_sapiens"
    MOUSE = "mus_musculus"
    ECOLI = "escherichia_coli"


class SampleBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100, examples=["BRCA1-exon11"])]
    organism: Organism
    sequence: Annotated[str, Field(min_length=1, max_length=10_000, examples=["ATGCGTAC"])]

    @field_validator("sequence", mode="before")
    @classmethod
    def validate_dna(cls, value: str) -> str:
        seq = value.strip().upper()
        if not seq:
            raise ValueError("sequence must not be empty")
        invalid = set(seq) - DNA_ALPHABET
        if invalid:
            raise ValueError(f"invalid nucleotides: {sorted(invalid)}")
        return seq


class SampleCreate(SampleBase):
    """Request body for POST /api/v1/samples."""


class SampleUpdate(BaseModel):
    """Request body for PATCH /api/v1/samples/{id}; every field optional."""

    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    organism: Organism | None = None


class SampleRead(SampleBase):
    """Response body: includes server-generated and derived fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def length(self) -> int:
        return len(self.sequence)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gc_content(self) -> float:
        if not self.sequence:
            return 0.0
        gc = sum(self.sequence.count(base) for base in "GC")
        return round(gc / len(self.sequence), 4)


class Link(BaseModel):
    href: str
    method: str = "GET"


class SampleResource(SampleRead):
    """Level 3 (HATEOAS) representation: data + links to next actions."""

    links: dict[str, Link] = Field(default_factory=dict, serialization_alias="_links")


class Page(BaseModel):
    """Generic pagination envelope."""

    items: list[SampleRead]
    total: int
    limit: int
    offset: int
