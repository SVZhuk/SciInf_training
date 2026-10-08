# Lab Sample Registry API
FastAPI + Pydantic v2 teaching demo; async SQLAlchemy 2.0 + Postgres storage, Alembic migrations.
Python 3.10+: no `datetime.UTC`, `enum.StrEnum`, `typing.Self`.

## Layers (never cross)
`schemas.py` DTOs → `routers/` thin async HTTP → `dependencies.py` DI → `repository.py` sole storage access.
Routers never import storage code; repositories never import FastAPI. `models.py` holds SQLAlchemy
table metadata only (no Session usage), same role for storage that `schemas.py` plays for HTTP.
Postgres for dev/test runs via `docker-compose.yml` (`db` + `test_db`); tests roll back a SAVEPOINT
per test (see `tests/conftest.py`), never committing real rows.

## Rules
- Full type hints, `X | None`, Pydantic v2 API only. No `print`, no broad `except`.
- Reuse existing patterns; ask before adding abstractions, dependencies or changing API shapes.
- Frontend JS (`app/frontend/static/js/app.js`) stays a thin REST client against `/api/v1/samples`;
  no business logic or validation duplicated client-side beyond basic HTML attributes
  (`required`/`maxlength`) - `schemas.py` is the single source of validation truth.
- Never weaken or delete a test to make it pass.
- No double-backtick notation in comments or code. Minimal comments.
- No em dash (U+2014) or en dash (U+2013) in code, comments, docstrings or docs; `/check` fails on them.
- Dependency management: `uv` (`pyproject.toml` + `uv.lock`). Always invoke python/pytest/ruff/mypy via `uv run`; never bare `pip` or `python -m venv`.
- Formatting/lint autofix and a `pyright` type-check (`app/` only, standard mode) run via hook after every edit; don't restate style rules or reformat manually.
- Done = `/check` passes (`mypy --strict` gates it; `pyright` is edit-time only, not part of `/check`). Many failures → `test-fixer` agent. Be brief; show diffs, not whole files.
