---
name: add-endpoint
description: Add or change a REST endpoint (schemas, repository method, route, tests) per project conventions.
---
1. `app/schemas.py`: separate `XCreate` / `XUpdate` (all fields optional) / `XRead`; validation in `field_validator`.
2. `app/repository.py`: extend the `SampleRepository` Protocol first, then implementations; raise domain exceptions.
3. `app/routers/`: `RepoDep` / `SampleDep`, explicit `status_code` + `response_model`.
   201 + `Location` create · 200 read/update · 204 delete · 404 missing · 409 conflict · 422 validation.
   Translate domain exceptions to `HTTPException` here only (`raise ... from None`).
4. Tests in `tests/` (see `tests/CLAUDE.md`): happy path + every error code.
5. Update the README endpoint table, then run `/check`.
