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

## Local database access

The dev Postgres instance (`db`) is for manual poking around: running ad hoc queries, checking
what a request actually wrote, inspecting the schema. It's separate from `test_db`, which tests
own exclusively and which is never meant to be queried by hand.

```bash
docker compose up -d db                         # make sure it's running
docker compose exec db psql -U app -d lab_samples   # opens a psql shell inside the container
```

Inside `psql`: `\dt` lists tables, `\d samples` describes the `samples` table, `select * from
samples;` shows what's there. `\q` exits.

To connect with a host-side client instead (DBeaver, TablePlus, VS Code extensions, a native
`psql`), use the connection details from `.env`'s `DATABASE_URL`: host `localhost`, port `5434`
(see `docker-compose.yml`'s `db` port mapping), user/password `app`, database `lab_samples`.

## Housekeeping

```bash
docker compose down                   # stop db + test_db, keep dev data (named volume)
docker compose down -v                # also delete the dev volume: next `up` starts from empty
docker compose logs -f db             # tail the dev Postgres container's logs
uv run alembic downgrade -1           # revert the last migration (dev db)
uv run alembic upgrade head           # re-apply migrations (dev db)
rm -rf .ruff_cache .mypy_cache .pytest_cache  # clear tool caches if they ever get confused
```

`test_db` has no named volume, so it always starts empty; there's nothing to reset there besides
restarting the container.

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /samples?organism=&limit=&offset= | 200 | 422 |
| POST | /samples | 201 + Location | 409, 422 |
| GET | /samples/{id} | 200 + `_links` (Richardson L3) | 404, 422 |
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
