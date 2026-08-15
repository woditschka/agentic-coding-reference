"""grading.contracts — the deterministic design-doc sync check.

The most common critical review finding on record is mechanical: a slice
lands with its requirement id absent from `docs/system-design.md`, so the
Contracts table names no implementer for it and the doc-reviewer buys a fix
round to say so. This check moves that class to gate time: the slice's
req_id must appear in `docs/prd.md` (the requirement is recorded) and in
`docs/system-design.md` (the design doc names it — normally a Contracts
table row's Implements column).

Presence is the deterministic floor; whether the *right* rows carry the id
stays reviewer judgment. A project without the design brief passes
vacuously, matching the gate's absent-log convention.

Pure functions over file contents; the CLI wiring lives in grading.py.
Stdlib only, Python 3.11+.
"""

import re
from pathlib import Path

REQ_ID = re.compile(r"^REQ-[A-Z]+-[0-9]{3}$")

PRD = "docs/prd.md"
DESIGN = "docs/system-design.md"


def check_contracts_sync(req_id: str, root: Path) -> list[str]:
    """Failures for the slice's design-doc sync; empty means the gate passes.

    Vacuous pass when the design brief is absent — an un-doctored or
    greenfield tree has nothing to sync against."""
    if not REQ_ID.fullmatch(req_id):
        return [f"{req_id!r} is not a req_id (expected REQ-<AREA>-<NNN>)"]
    design = root / DESIGN
    if not design.is_file():
        return []
    present = re.compile(rf"\b{re.escape(req_id)}\b")
    failures: list[str] = []
    prd = root / PRD
    if prd.is_file() and not present.search(prd.read_text(encoding="utf-8")):
        failures.append(
            f"{req_id} appears nowhere in {PRD} — the slice implements a "
            "requirement the PRD does not record"
        )
    if not present.search(design.read_text(encoding="utf-8")):
        failures.append(
            f"{req_id} appears nowhere in {DESIGN} — add it to the Contracts "
            "table row(s) of the implementing type(s)"
        )
    return failures
