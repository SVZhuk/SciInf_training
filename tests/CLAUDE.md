# Test conventions
- pytest-asyncio + `httpx.AsyncClient`; fresh Postgres transaction per test via the `sample_repository`
  fixture (`tests/conftest.py`), overridden into `app.dependency_overrides[get_repository]` (see
  `client` fixture in `test_samples.py`). Nothing is ever committed; the fixture rolls back a
  SAVEPOINT after each test, so tests never share state.
- Requires `test_db` running (`docker compose up -d test_db`); `TEST_DATABASE_URL` in `.env`.
- All tests and fixtures are `async def`; `asyncio_mode = "auto"` and a session-scoped event loop
  (`pyproject.toml`) mean no per-test `@pytest.mark.asyncio` boilerplate is needed.
- Name `test_<action>_<condition>_<expected>`; `@pytest.mark.parametrize` for input variants.
- Assert status code and body shape; one behaviour per test. No sleeps, network or shared state.
- Every endpoint: happy path + each documented error code.
- Debug cheaply: `uv run python scripts/check.py` → Grep `.claude/logs/check.log` → single test `--tb=long -vv` → `--lf` after fixes. Never paste whole logs.
- E2E later: Robot Framework + RequestsLibrary in `e2e/` against a running server.
