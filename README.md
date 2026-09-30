# Lab Sample Registry API: REST demo

Minimal, production-style FastAPI service for the Module 02 REST API session.
See [ARCHITECTURE.md](ARCHITECTURE.md) for how it works.

## Run  (Python 3.10+, [uv](https://docs.astral.sh/uv/), Docker for Postgres)

```bash
cp .env.example .env                  # DATABASE_URL / TEST_DATABASE_URL
docker compose up -d db test_db       # dev + test Postgres
uv sync                               # creates .venv, installs app + ruff + mypy + pytest
uv run alembic upgrade head           # create the schema
uv run uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
uv run python client.py               # in a 2nd terminal
uv run pytest                         # runs against test_db (Postgres), rolled back per test
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
  main.py           # Application Factory (create_app), wires the db lifespan
  config.py         # Settings (pydantic-settings), env-driven DATABASE_URL
  db.py             # async engine/session lifecycle (lifespan + per-request session)
  models.py         # SQLAlchemy 2.0 declarative models (table shape only)
  schemas.py        # DTOs: Pydantic contract, validation, computed fields
  repository.py     # Repository pattern (Protocol + in-memory + SQLAlchemy impls)
  dependencies.py   # Dependency Injection via Depends
  routers/samples.py# thin async controllers, one router per resource
alembic/            # schema migrations (async env.py, autogenerate from Base.metadata)
tests/              # pytest-asyncio + httpx AsyncClient + dependency_overrides
docker-compose.yml  # dev (db) + test (test_db) Postgres instances
client.py           # httpx consumer
```

## Exercises

1. Add `GET /samples/{id}/reverse-complement`.
2. Add an `X-API-Key` header dependency; return 401 when missing.
