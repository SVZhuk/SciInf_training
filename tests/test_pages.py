"""Homepage tests: same client fixture pattern as test_samples.py."""

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


async def test_homepage_renders_empty_state(client: AsyncClient) -> None:
    r = await client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "No samples yet" in r.text


async def test_homepage_renders_with_samples(client: AsyncClient) -> None:
    payloads: list[dict[str, Any]] = [
        {"name": "first-sample", "organism": "homo_sapiens", "sequence": "ACGT"},
        {"name": "second-sample", "organism": "mus_musculus", "sequence": "ACGTACGT"},
    ]
    for payload in payloads:
        await client.post("/api/v1/samples", json=payload)

    r = await client.get("/")
    assert r.status_code == 200
    assert "first-sample" in r.text
    assert "second-sample" in r.text
    # newest first: the second sample's row should appear before the first's
    assert r.text.index("second-sample") < r.text.index("first-sample")


async def test_homepage_renders_sidebar_and_row_ids(client: AsyncClient) -> None:
    payload = {"name": "sidebar-sample", "organism": "homo_sapiens", "sequence": "ACGT"}
    created = await client.post("/api/v1/samples", json=payload)
    sample_id = created.json()["id"]

    r = await client.get("/")
    assert r.status_code == 200
    assert 'id="btn-add"' in r.text
    assert 'id="btn-edit"' in r.text
    assert 'id="btn-delete"' in r.text
    assert f'data-id="{sample_id}"' in r.text
