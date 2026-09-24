# Lab Sample Registry API
FastAPI + Pydantic v2 teaching demo; in-memory repo now, SQLAlchemy 2.0 + Postgres next.
Python 3.10+: no `datetime.UTC`, `enum.StrEnum`, `typing.Self`.

## Layers (never cross)
`schemas.py` DTOs → `routers/` thin HTTP → `dependencies.py` DI → `repository.py` sole storage access.
Routers never import storage code; repositories never import FastAPI.

## Rules
- Full type hints, `X | None`, Pydantic v2 API only. No `print`, no broad `except`.
- Reuse existing patterns; ask before adding abstractions, dependencies or changing API shapes.
- Never weaken or delete a test to make it pass.
- No double-backtick notation in comments or code. Minimal comments.
- No em dash (U+2014) or en dash (U+2013) in code, comments, docstrings or docs; `/check` fails on them.
- Dependency management: `uv` (`pyproject.toml` + `uv.lock`). Always invoke python/pytest/ruff/mypy via `uv run`; never bare `pip` or `python -m venv`.
- Formatting/lint autofix runs via hook; don't restate style rules or reformat manually.
- Done = `/check` passes. Many failures → `test-fixer` agent. Be brief; show diffs, not whole files.
