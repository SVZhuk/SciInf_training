"""/samples resource: one router per resource, thin controllers."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.dependencies import RepoDep, SampleDep
from app.repository import DuplicateNameError
from app.schemas import (
    Link,
    Organism,
    Page,
    SampleCreate,
    SampleRead,
    SampleResource,
    SampleUpdate,
)

router = APIRouter(prefix="/samples", tags=["samples"])


@router.get("", response_model=Page)
async def list_samples(
    repo: RepoDep,
    organism: Organism | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page:
    items, total = await repo.list(organism=organism, limit=limit, offset=offset)
    return Page(
        items=[SampleRead.model_validate(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SampleRead, status_code=status.HTTP_201_CREATED)
async def create_sample(
    payload: SampleCreate, repo: RepoDep, response: Response, request: Request
) -> SampleRead:
    try:
        sample = await repo.add(payload)
    except DuplicateNameError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Sample name already exists") from None
    response.headers["Location"] = str(request.url_for("get_sample", sample_id=sample.id))
    return SampleRead.model_validate(sample)


@router.get("/{sample_id}", response_model=SampleResource)
async def get_sample(sample: SampleDep, request: Request) -> SampleResource:
    """Richardson Level 3: the response tells the client what it can do next."""
    url = str(request.url_for("get_sample", sample_id=sample.id))
    links = {
        "self": Link(href=url),
        "update": Link(href=url, method="PATCH"),
        "delete": Link(href=url, method="DELETE"),
        "collection": Link(href=str(request.url_for("list_samples"))),
    }
    return SampleResource.model_validate(sample).model_copy(update={"links": links})


@router.patch("/{sample_id}", response_model=SampleRead)
async def update_sample(payload: SampleUpdate, sample: SampleDep, repo: RepoDep) -> SampleRead:
    return SampleRead.model_validate(await repo.update(sample, payload))


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(sample: SampleDep, repo: RepoDep) -> None:
    await repo.delete(sample)
