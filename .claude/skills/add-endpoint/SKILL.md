---
name: add-endpoint
description: Add or change a REST endpoint (schemas, repository method, route, tests) per project conventions.
---
1. `app/schemas.py`: separate `XCreate` / `XUpdate` (all fields optional) / `XRead`; validation in `field_validator`.
2. `app/repository.py`: extend the `SampleRepository` Protocol first (methods are `async def`), then both implementations (`InMemorySampleRepository`, `SqlAlchemySampleRepository`); raise domain exceptions.
3. If the change adds or changes a persisted field: update `app/models.py`'s `SampleModel` too, then `uv run alembic revision --autogenerate -m "..."` and check the generated migration before committing it.
4. `app/routers/`: `async def` handlers awaiting `RepoDep` / `SampleDep` calls, explicit `status_code` + `response_model`.
   201 + `Location` create · 200 read/update · 204 delete · 404 missing · 409 conflict · 422 validation.
   Translate domain exceptions to `HTTPException` here only (`raise ... from None`).
5. Tests in `tests/` (see `tests/CLAUDE.md`): happy path + every error code.
6. Update the README endpoint table, then run `/check`.
