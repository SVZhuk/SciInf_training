"""PreToolUse hook: keep Bash commands on uv.

Blocks pip, venv creation and bare python/pytest/ruff/mypy/uvicorn calls, including ones hidden
behind &&, ||, ; or a pipe. Reads the hook payload on stdin; exit 2 sends stderr back to the agent.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

SPLIT = re.compile(r"&&|\|\||;|\|")
ASSIGNMENT = re.compile(r"^\w+=")
BLOCKED = {
    "pip": "uv add (deps) or uv sync",
    "pip3": "uv add (deps) or uv sync",
    "virtualenv": "uv sync (creates .venv from uv.lock)",
    "python": "uv run python",
    "python3": "uv run python",
    "py": "uv run python",
    "pytest": "uv run pytest",
    "ruff": "uv run ruff",
    "mypy": "uv run mypy",
    "uvicorn": "uv run uvicorn",
}


def first_token(segment: str) -> str:
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return ""
    tokens = [token for token in tokens if not ASSIGNMENT.match(token)]
    return tokens[0].rsplit("/", 1)[-1] if tokens else ""


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    command = str(payload.get("tool_input", {}).get("command", ""))
    for segment in SPLIT.split(command):
        token = first_token(segment)
        if token in BLOCKED:
            sys.stderr.write(
                f"Blocked: '{token}' must go through uv. Use: {BLOCKED[token]}.\n"
                "This project manages dependencies with uv (pyproject.toml + uv.lock).\n"
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
