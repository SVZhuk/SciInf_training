---
name: check
description: Run tests, lint and type checks; use before declaring any task done.
allowed-tools: Bash(uv run python scripts/check.py:*), Bash(uv run pytest:*), Bash(docker compose up -d test_db:*), Grep, Read
---

Run `uv run python scripts/check.py`: prints ≤40 lines (first failure only), full output in `.claude/logs/check.log`.

- Pass → reply "check: pass" only.
- `pytest` failing with `ConnectionRefusedError`/`OSError` to Postgres means `test_db` isn't running, not a code bug: run `docker compose up -d test_db` and retry before drilling into any test.
- Fail → drill down only as far as needed:
  1. Excerpt usually suffices. Else `Grep` the log for the test name / error; never Read the whole log.
  2. Still unclear → `uv run pytest <file>::<test> --tb=long -vv` for that one test.
  3. After a fix → `uv run python scripts/check.py --lf` (last-failed first), then the plain command.
- 3+ failing tests or unclear root cause → delegate to the `test-fixer` agent.
- Fix the root cause, never the test's intent. Report only what failed and what changed.
