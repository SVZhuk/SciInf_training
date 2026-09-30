"""Dependency Injection wiring (FastAPI `Depends`)."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.repository import Sample, SampleRepository, SqlAlchemySampleRepository

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_repository(session: SessionDep) -> SampleRepository:
    return SqlAlchemySampleRepository(session)


RepoDep = Annotated[SampleRepository, Depends(get_repository)]


async def get_sample_or_404(sample_id: UUID, repo: RepoDep) -> Sample:
    sample = await repo.get(sample_id)
    if sample is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sample not found")
    return sample


SampleDep = Annotated[Sample, Depends(get_sample_or_404)]
