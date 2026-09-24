"""PostToolUse hook: reject em/en dashes in the file that was just edited.

Same rule as dash_check() in scripts/check.py, but on one file so it fires at write time.
Reads the hook payload on stdin; exit 2 sends stderr back to the agent.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DASHES = re.compile("[\u2013\u2014]")
SUFFIXES = {".py", ".md", ".toml", ".json", ".txt", ".robot", ".cfg", ".ini"}
NOTE = "Found em/en dash(es); reword with a colon, comma, period or parentheses."


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    raw = str(payload.get("tool_input", {}).get("file_path", ""))
    path = Path(raw)
    if not raw or path.suffix not in SUFFIXES or not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits = [
        f"{path.name}:{no}: {line.strip()[:100]}"
        for no, line in enumerate(text.splitlines(), 1)
        if DASHES.search(line)
    ]
    if not hits:
        return 0
    sys.stderr.write("\n".join([*hits, NOTE]) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
