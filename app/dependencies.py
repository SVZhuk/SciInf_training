"""Dependency Injection wiring (FastAPI `Depends`)."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.repository import InMemorySampleRepository, Sample, SampleRepository


@lru_cache  # one shared instance per process (Singleton)
def get_repository() -> SampleRepository:
    return InMemorySampleRepository()


RepoDep = Annotated[SampleRepository, Depends(get_repository)]


def get_sample_or_404(sample_id: UUID, repo: RepoDep) -> Sample:
    sample = repo.get(sample_id)
    if sample is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sample not found")
    return sample


SampleDep = Annotated[Sample, Depends(get_sample_or_404)]
