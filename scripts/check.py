"""Run tests, lint and type checks with token-lean output.

Steps: dashes (no em/en dash in project text files) -> pytest -> ruff -> mypy.
Prints a short summary (max ~40 lines); the full output goes to .claude/logs/check.log.
Stops at the first failing step.

Usage: uv run python scripts/check.py [extra pytest args, e.g. --lf or tests/test_samples.py]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / ".claude" / "logs" / "check.log"
MAX_LINES = 40
FRAME = re.compile(r"^(\S.*?):\d+: in ")
SUMMARY = re.compile(r"\d+ (failed|passed|errors?)\b")
DASHES = re.compile("[\u2013\u2014]")
DASH_GLOBS = ("*.py", "*.md", "*.toml", "*.json", "*.txt", "*.robot", "*.cfg", "*.ini")
SKIP_DIRS = {".git", ".venv", ".ruff_cache", ".mypy_cache", ".pytest_cache", "__pycache__", "logs"}


def dash_check() -> tuple[int, str]:
    """House rule: no em dash (U+2014) or en dash (U+2013) in code, comments or docs."""
    hits: list[str] = []
    for pattern in DASH_GLOBS:
        for path in sorted(ROOT.rglob(pattern)):
            rel = path.relative_to(ROOT)
            if SKIP_DIRS & set(rel.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for no, line in enumerate(text.splitlines(), 1):
                if DASHES.search(line):
                    hits.append(f"{rel.as_posix()}:{no}: {line.strip()[:100]}")
    if not hits:
        return 0, "no em/en dashes"
    note = f"Found {len(hits)} em/en dash(es); reword with a colon, comma, period or parentheses."
    return 1, "\n".join([*hits, note])


def steps(pytest_args: list[str]) -> list[tuple[str, list[str]]]:
    py = sys.executable
    return [
        ("pytest", [py, "-m", "pytest", "-x", "--tb=short", "-rfE", *pytest_args]),
        ("ruff", [py, "-m", "ruff", "check", "--output-format", "concise", "."]),
        ("mypy", [py, "-m", "mypy", "app"]),
    ]


def last_line(output: str) -> str:
    lines = [line.strip("= ") for line in output.splitlines() if line.strip()]
    return next(
        (line for line in reversed(lines) if SUMMARY.search(line)), lines[-1] if lines else ""
    )


def is_project(path: str) -> bool:
    return (
        "site-packages" not in path and not Path(path).is_absolute() and not path.startswith("..")
    )


def drop_library_frames(lines: list[str]) -> list[str]:
    """Remove traceback frames (header + indented source) outside the project."""
    kept: list[str] = []
    hidden = 0
    skipping = False
    for line in lines:
        match = FRAME.match(line)
        if match:
            skipping = not is_project(match.group(1))
            hidden += skipping
        elif skipping and not line.startswith(" "):
            skipping = False
        if not skipping:
            kept.append(line)
    if hidden:
        kept.append(f"({hidden} library frames hidden)")
    return kept


def excerpt(name: str, output: str) -> list[str]:
    """First failure only for pytest; head of the report for other tools."""
    lines = output.splitlines()
    if name == "pytest":
        start = next((i for i, line in enumerate(lines) if line.startswith("____")), None)
        if start is not None:
            end = next(
                (j for j in range(start + 1, len(lines)) if lines[j].startswith(("____", "===="))),
                len(lines),
            )
            summary = [line for line in lines if line.startswith(("FAILED", "ERROR"))]
            lines = [*drop_library_frames(lines[start:end]), *summary]
    if len(lines) > MAX_LINES:
        hidden = len(lines) - MAX_LINES
        lines = [*lines[:MAX_LINES], f"... (+{hidden} lines, see {LOG.relative_to(ROOT)})"]
    return lines


def main() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    report: list[str] = []
    with LOG.open("w", encoding="utf-8") as log:
        code, output = dash_check()
        log.write(f"===== dashes\n{output}\n")
        if code != 0:
            print("\n".join(["dashes: FAIL", *excerpt("dashes", output)]))
            return 1
        report.append("dashes: ok")
        for name, cmd in steps(sys.argv[1:]):
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
            output = proc.stdout + proc.stderr
            log.write(f"===== {name}: {' '.join(cmd[1:])}\n{output}\n")
            if proc.returncode != 0:
                report.append(f"{name}: FAIL ({last_line(output)})")
                report.extend(excerpt(name, output))
                report.append(f"full log: {LOG.relative_to(ROOT).as_posix()}")
                print("\n".join(report))
                return 1
            status = f"ok ({last_line(output)})" if name == "pytest" else "ok"
            report.append(f"{name}: {status}")
    print("check: pass · " + " · ".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
