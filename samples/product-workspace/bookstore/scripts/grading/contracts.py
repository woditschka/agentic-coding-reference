"""Check the slice's requirement id is recorded in the PRD and named in the design doc.

A leaf over two files: presence is the deterministic floor, and a tree
without the design brief passes vacuously.
"""

import re
from pathlib import Path

REQ_ID = re.compile(r"^REQ-[A-Z]+-[0-9]{3}$")

PRD = "docs/prd.md"
DESIGN = "docs/system-design.md"


def check_contracts_sync(req_id: str, root: Path) -> list[str]:
    """Return the failures of the slice's design-doc sync; empty when it passes."""
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
