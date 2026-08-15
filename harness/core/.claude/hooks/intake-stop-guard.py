#!/usr/bin/env python3
"""Stop hook — a session may not end while route decides `intake-ready`.

A recorded `intake-decision` obligates a product-expert dispatch; the only
refusal exit is the expert's recorded `consultation-request`. The failure
this guards: root reads the docs itself, judges the request to conflict
with recorded non-goals, and ends the session with a prose decline —
leaving the ledger saying "work pending" while the operator heard "no".
Ledger-visible states one step later are already caught deterministically
(an abandoned dispatch escalates through the truncation rules); the
session end itself is observable only here.

Blocking is narrow: exit 2 only when `handoff.py route` decides
`dispatch` with rule `intake-ready` — the exact measured failure state —
and only once (`stop_hook_active` allows the retry through, so a blocked
model that still stops is not trapped). Every other path exits 0,
including every malfunction: missing log, missing script, route failing
or emitting non-JSON. A Stop hook that failed closed would trap sessions
on infrastructure errors, so unlike the deny-by-default PreToolUse
guards, this backstop fails OPEN; the doctrine prose and the audit review
remain the outer layers.

Stdlib only. Tested by test_intake_stop_guard.py alongside this file.
"""

import json
import os
import subprocess
import sys

BLOCK_MESSAGE = (
    "route decides dispatch: product-requirements-expert (intake-ready). "
    "The session may not end in prose on a recorded intake — dispatch the "
    "product expert. A scope conflict exits as the expert's recorded "
    "consultation-request, never an unrecorded decline."
)

ROUTE_TIMEOUT_SECONDS = 30


def route_decision(project_dir, runner=subprocess.run):
    """The parsed route decision, or None on any malfunction (fails open)."""
    log = os.path.join(project_dir, ".scratch", "handoff.jsonl")
    script = os.path.join(project_dir, "scripts", "handoff.py")
    if not (os.path.isfile(log) and os.path.isfile(script)):
        return None
    try:
        proc = runner(
            [sys.executable, script, "route"],
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


def decide(payload_text, project_dir, runner=subprocess.run):
    """0 to allow the stop, 2 to block — the only two exits."""
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0
    if not project_dir:
        return 0
    decision = route_decision(project_dir, runner)
    if decision is None:
        return 0
    if (
        decision.get("decision") == "dispatch"
        and decision.get("rule") == "intake-ready"
    ):
        return 2
    return 0


def main():
    code = decide(sys.stdin.read(), os.environ.get("CLAUDE_PROJECT_DIR", ""))
    if code == 2:
        print(BLOCK_MESSAGE, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
