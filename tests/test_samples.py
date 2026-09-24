"""API tests: pytest + FastAPI TestClient (no running server needed).

Each test gets a fresh repository via `dependency_overrides` -> full isolation.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_repository
from app.main import create_app
from app.repository import InMemorySampleRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    repo = InMemorySampleRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    with TestClient(app) as c:
        yield c


@pytest.fixture
def payload() -> dict[str, Any]:
    return {"name": "BRCA1-exon11", "organism": "homo_sapiens", "sequence": "atgcgc"}


def test_create_returns_201_and_location(client: TestClient, payload: dict[str, Any]) -> None:
    r = client.post("/samples", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert r.headers["Location"] == f"/samples/{body['id']}"
    assert body["sequence"] == "ATGCGC"  # normalized by validator
    assert body["gc_content"] == pytest.approx(0.6667)


@pytest.mark.parametrize(
    ("field", "value"),
    [("sequence", "ATGXZ"), ("organism", "alien"), ("name", "")],
)
def test_invalid_payload_returns_422(
    client: TestClient, payload: dict[str, Any], field: str, value: str
) -> None:
    r = client.post("/samples", json={**payload, field: value})
    assert r.status_code == 422


def test_duplicate_name_returns_409(client: TestClient, payload: dict[str, Any]) -> None:
    client.post("/samples", json=payload)
    assert client.post("/samples", json=payload).status_code == 409


def test_full_crud_lifecycle(client: TestClient, payload: dict[str, Any]) -> None:
    sample_id = client.post("/samples", json=payload).json()["id"]

    assert client.get(f"/samples/{sample_id}").status_code == 200

    r = client.patch(f"/samples/{sample_id}", json={"name": "renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"

    assert client.delete(f"/samples/{sample_id}").status_code == 204
    assert client.get(f"/samples/{sample_id}").status_code == 404


def test_list_filter_and_pagination(client: TestClient) -> None:
    for i, org in enumerate(["homo_sapiens", "mus_musculus", "homo_sapiens"]):
        client.post("/samples", json={"name": f"s{i}", "organism": org, "sequence": "ACGT"})

    r = client.get("/samples", params={"organism": "homo_sapiens", "limit": 1})
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_unknown_id_returns_404(client: TestClient) -> None:
    r = client.get("/samples/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_get_returns_hypermedia_links(client: TestClient, payload: dict[str, Any]) -> None:
    sample_id = client.post("/samples", json=payload).json()["id"]
    links = client.get(f"/samples/{sample_id}").json()["_links"]

    assert links["self"]["href"].endswith(f"/samples/{sample_id}")
    assert links["delete"]["method"] == "DELETE"
    # a client follows the link instead of building the URL itself
    assert client.request(links["delete"]["method"], links["delete"]["href"]).status_code == 204
