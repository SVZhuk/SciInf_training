# Test conventions
- pytest + `TestClient`; fresh repo per test via `app.dependency_overrides[get_repository]` (see `client` fixture).
- Name `test_<action>_<condition>_<expected>`; `@pytest.mark.parametrize` for input variants.
- Assert status code and body shape; one behaviour per test. No sleeps, network or shared state.
- Every endpoint: happy path + each documented error code.
- Debug cheaply: `uv run python scripts/check.py` → Grep `.claude/logs/check.log` → single test `--tb=long -vv` → `--lf` after fixes. Never paste whole logs.
- E2E later: Robot Framework + RequestsLibrary in `e2e/` against a running server.
