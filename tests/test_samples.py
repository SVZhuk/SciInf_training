"""API tests: pytest + httpx AsyncClient (no running server needed).

Each test gets a fresh Postgres transaction via `sample_repository` (see conftest.py),
overridden into `app.dependency_overrides[get_repository]` -> full isolation, nothing committed.
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_repository
from app.main import create_app
from app.repository import SqlAlchemySampleRepository


@pytest.fixture
async def client(sample_repository: SqlAlchemySampleRepository) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: sample_repository
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def payload() -> dict[str, Any]:
    return {"name": "BRCA1-exon11", "organism": "homo_sapiens", "sequence": "atgcgc"}


async def test_create_returns_201_and_location(
    client: AsyncClient, payload: dict[str, Any]
) -> None:
    r = await client.post("/api/v1/samples", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert r.headers["Location"].endswith(f"/api/v1/samples/{body['id']}")
    assert body["sequence"] == "ATGCGC"  # normalized by validator
    assert body["gc_content"] == pytest.approx(0.6667)


@pytest.mark.parametrize(
    ("field", "value"),
    [("sequence", "ATGXZ"), ("organism", "alien"), ("name", "")],
)
async def test_invalid_payload_returns_422(
    client: AsyncClient, payload: dict[str, Any], field: str, value: str
) -> None:
    r = await client.post("/api/v1/samples", json={**payload, field: value})
    assert r.status_code == 422


async def test_duplicate_name_returns_409(client: AsyncClient, payload: dict[str, Any]) -> None:
    await client.post("/api/v1/samples", json=payload)
    assert (await client.post("/api/v1/samples", json=payload)).status_code == 409


async def test_full_crud_lifecycle(client: AsyncClient, payload: dict[str, Any]) -> None:
    sample_id = (await client.post("/api/v1/samples", json=payload)).json()["id"]

    assert (await client.get(f"/api/v1/samples/{sample_id}")).status_code == 200

    r = await client.patch(f"/api/v1/samples/{sample_id}", json={"name": "renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"

    assert (await client.delete(f"/api/v1/samples/{sample_id}")).status_code == 204
    assert (await client.get(f"/api/v1/samples/{sample_id}")).status_code == 404


async def test_list_filter_and_pagination(client: AsyncClient) -> None:
    for i, org in enumerate(["homo_sapiens", "mus_musculus", "homo_sapiens"]):
        await client.post(
            "/api/v1/samples", json={"name": f"s{i}", "organism": org, "sequence": "ACGT"}
        )

    r = await client.get("/api/v1/samples", params={"organism": "homo_sapiens", "limit": 1})
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 2
    assert len(body["items"]) == 1


async def test_unknown_id_returns_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/samples/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_get_returns_hypermedia_links(client: AsyncClient, payload: dict[str, Any]) -> None:
    sample_id = (await client.post("/api/v1/samples", json=payload)).json()["id"]
    links = (await client.get(f"/api/v1/samples/{sample_id}")).json()["_links"]

    assert links["self"]["href"].endswith(f"/api/v1/samples/{sample_id}")
    assert links["delete"]["method"] == "DELETE"
    # a client follows the link instead of building the URL itself
    r = await client.request(links["delete"]["method"], links["delete"]["href"])
    assert r.status_code == 204
