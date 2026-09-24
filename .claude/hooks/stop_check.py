"""Stop hook: refuse to finish while scripts/check.py fails.

Honours stop_hook_active so a still-failing check cannot trap the agent in a loop.
Reads the hook payload on stdin; exit 2 sends stderr back to the agent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "check.py"


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("stop_hook_active"):
        return 0
    proc = subprocess.run(
        [sys.executable, str(CHECK)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode == 0:
        return 0
    sys.stderr.write(proc.stdout + proc.stderr)
    sys.stderr.write("\nDone means /check passes. Fix the root cause, never the test's intent.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
