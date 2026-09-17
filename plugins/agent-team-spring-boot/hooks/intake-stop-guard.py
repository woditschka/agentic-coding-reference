#!/usr/bin/env python3
"""Block a session end while route decides the intake-ready dispatch, and allow otherwise.

A Stop backstop that fails open: a recorded intake obligates the product
expert's dispatch, so the session may not end in prose instead. Every
malfunction allows, and the retry after a block allows, so a session is never
trapped on an infrastructure error.
"""

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ALLOW_EXIT = 0
BLOCK_EXIT = 2

BLOCK_MESSAGE = (
    "route decides dispatch: product-requirements-expert (intake-ready). "
    "The session may not end in prose on a recorded intake — dispatch the "
    "product expert. A scope conflict exits as the expert's recorded "
    "consultation-request, never an unrecorded decline."
)

ROUTE_TIMEOUT_SECONDS = 30

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def route_decision(
    project_dir: str, runner: Runner = subprocess.run
) -> dict[str, object] | None:
    """Return the parsed route decision, or None on any malfunction."""
    project = Path(project_dir)
    log = project / ".scratch" / "handoff.jsonl"
    script = project / "scripts" / "handoff.py"
    if not (log.is_file() and script.is_file()):
        return None
    try:
        proc = runner(
            [sys.executable, str(script), "route"],
            capture_output=True,
            text=True,
            timeout=ROUTE_TIMEOUT_SECONDS,
            cwd=project_dir,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        decision = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return decision if isinstance(decision, dict) else None


def decide(payload_text: str, project_dir: str, runner: Runner = subprocess.run) -> int:
    """Return the exit code for one Stop payload: block only the intake-ready dispatch, once."""
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return ALLOW_EXIT
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return ALLOW_EXIT
    if not project_dir:
        return ALLOW_EXIT
    decision = route_decision(project_dir, runner)
    if decision is None:
        return ALLOW_EXIT
    if (
        decision.get("decision") == "dispatch"
        and decision.get("rule") == "intake-ready"
    ):
        return BLOCK_EXIT
    return ALLOW_EXIT


def main() -> int:
    """Decide for the payload on stdin and print the reason when blocking."""
    code = decide(sys.stdin.read(), os.environ.get("CLAUDE_PROJECT_DIR", ""))
    if code == BLOCK_EXIT:
        print(BLOCK_MESSAGE, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
