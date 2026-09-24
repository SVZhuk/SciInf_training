# Lab Sample Registry API: REST demo

Minimal, production-style FastAPI service for the Module 02 REST API session.
See [ARCHITECTURE.md](ARCHITECTURE.md) for how it works.

## Run  (Python 3.10+, [uv](https://docs.astral.sh/uv/))

```bash
uv sync                               # creates .venv, installs app + ruff + mypy + pytest
uv run uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
uv run python client.py               # in a 2nd terminal
uv run pytest                         # no server needed
uv run python scripts/check.py        # tests + lint + types, compact output
uv tool install httpie                # CLI testing, see docs/httpie.md
```

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /samples?organism=&limit=&offset= | 200 | 422 |
| POST | /samples | 201 + Location | 409, 422 |
| GET | /samples/{id} | 200 + `_links` (Richardson L3) | 404 |
| PATCH | /samples/{id} | 200 | 404, 422 |
| DELETE | /samples/{id} | 204 | 404 |

## Layout & patterns

```
app/
  main.py           # Application Factory (create_app)
  schemas.py        # DTOs: Pydantic contract, validation, computed fields
  repository.py     # Repository pattern (Protocol + in-memory impl)
  dependencies.py   # Dependency Injection via Depends
  routers/samples.py# thin controllers, one router per resource
tests/              # pytest + TestClient + dependency_overrides
client.py           # httpx consumer
```

## Exercises

1. Add `GET /samples/{id}/reverse-complement`.
2. Replace `InMemorySampleRepository` with SQLAlchemy 2.0 + Postgres (routers must not change).
3. Add an `X-API-Key` header dependency; return 401 when missing.
