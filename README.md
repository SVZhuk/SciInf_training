# Lab Sample Registry API: REST demo

Minimal, production-style FastAPI service for the Module 02 REST API session.
See [ARCHITECTURE.md](ARCHITECTURE.md) for how it works.

## Run  (Python 3.10+, [uv](https://docs.astral.sh/uv/), Docker for Postgres)

```bash
cp .env.example .env                  # DATABASE_URL / TEST_DATABASE_URL
docker compose up -d db               # dev Postgres (test_db starts itself for pytest)
uv sync                               # creates .venv, installs app + ruff + mypy + pytest
uv run alembic upgrade head           # create the schema
uv run uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
uv run python client.py               # in a 2nd terminal
uv run pytest                         # auto-starts test_db, rolled back per test
uv run python scripts/check.py        # tests + lint + types, compact output
uv tool install httpie                # CLI testing, see docs/httpie.md
```

### Windows

The commands above are bash (WSL, Git Bash, macOS/Linux). Two ways to run on Windows:

- **WSL (recommended)**: open a WSL terminal in the project directory and run the commands above
  unchanged. Docker Desktop must have WSL2 integration enabled for `docker compose` to reach it.
- **Native PowerShell**: same commands, except copy the env file with
  `Copy-Item .env.example .env` instead of `cp`. `uv`, `docker compose`, `uv run ...` work the
  same in PowerShell as in bash.

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
| GET | /api/v1/samples?organism=&limit=&offset= | 200 | 422 |
| POST | /api/v1/samples | 201 + Location | 409, 422 |
| GET | /api/v1/samples/{id} | 200 + `_links` (Richardson L3) | 404, 422 |
| PATCH | /api/v1/samples/{id} | 200 | 404, 422 |
| DELETE | /api/v1/samples/{id} | 204 | 404 |
| GET | / | 200, HTML page: samples table + Add/Edit/Delete sidebar | - |
| GET | /health | 200 | - |

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
  api/router.py     # /api/v1 aggregator: mounts resource routers under the version prefix
  frontend/         # HTML frontend: router + templates + static, separate from the JSON API
                     # so it can be swapped for a SPA later without touching anything above.
                     # static/js/app.js adds/edits/deletes samples by calling the same /api/v1
                     # endpoints from the browser, then re-renders the table.
alembic/            # schema migrations (async env.py, autogenerate from Base.metadata)
tests/              # pytest-asyncio + httpx AsyncClient + dependency_overrides
docker-compose.yml  # dev (db) + test (test_db) Postgres instances
client.py           # httpx consumer
```

## Exercises

1. Add `GET /api/v1/samples/{id}/reverse-complement`.
2. Add an `X-API-Key` header dependency; return 401 when missing.
