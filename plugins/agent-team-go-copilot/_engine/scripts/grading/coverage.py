"""grading.coverage — the slice's test-coverage map.

The test reviewer's dominant first-pass finding classes on record are a PRD
edge case with no dedicated test and a "Done when" bullet with no test —
19 of 35 fix-routable findings in the v0.3.3 to v0.3.8 rows by the
description keywords "edge case" and "Done when"/"acceptance", each buying
a fix round. Whether a test *covers* a bullet is judgment, so this is a
map, never a gate: it lays the requirement's Done-when bullets, the
declared test names beside the tests that define them, and the capability
group's numbered edge cases, so the implementer's Test-Conventions Walk
works from data and the test reviewer cites the same map.

Presence is string-checked for declared test names: a name exists when a
test file defines it. Edge cases are listed, never matched — a citation
comment in a test is narration the testing brief bans, and the judge
scored it as such — so each listed case is a walk item the implementer
resolves with a test or a note naming why. Every input is agent-written (the PRD, the test
tree, the handoff log), so the map reads defensively and renders only
printable text; any read problem lands in the notes, never in an exit code.

Pure functions over text; the CLI wiring lives in grading.py.
Stdlib only, Python 3.11+.
"""

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

PRD = "docs/prd.md"
_SKIP_DIRS = {".git", ".scratch", "build", "target", "node_modules", "bin", "out"}
_MAX_FILE_BYTES = 2_000_000
_EDGE_LABEL = re.compile(r"^\s*[*_]*edge cases?[*_]*:?[*_]*\s*$", re.IGNORECASE)
_NUMBERED = re.compile(r"^\s*(\d{1,6})\.\s+(.*)$")
_HEADING = re.compile(r"^(#{2,3})\s+(.*)$")
_CONTROL = {c: None for c in range(32) if c not in (9,)} | {127: None}


@dataclass(frozen=True)
class CoverageMap:
    req_id: str
    done_when: tuple[str, ...]
    declared: tuple[tuple[str, tuple[str, ...]], ...] | None  # None: no prd-entry
    group: str | None
    edge_cases: tuple[tuple[int, str], ...]
    notes: tuple[str, ...] = field(default_factory=tuple)


def _clean(text: str) -> str:
    """Printable text for the terminal: control characters dropped, tabs kept."""
    return text.translate(_CONTROL)


def _sections(prd: str) -> list[tuple[str, str]]:
    """(heading, body) per `##`/`###` section in order; the preamble before
    the first heading carries an empty heading and never hosts a group."""
    out: list[tuple[str, str]] = []
    heading = ""
    body: list[str] = []
    for line in prd.splitlines():
        m = _HEADING.match(line)
        if m:
            if heading or body:
                out.append((heading, "\n".join(body)))
            heading, body = m.group(2).strip(), []
        else:
            body.append(line)
    if heading or body:
        out.append((heading, "\n".join(body)))
    return out


def done_when_bullets(prd: str, req_id: str) -> list[str]:
    """List bullets opening with the requirement's id — the acceptance
    contract. The shipped form is a dash, the id in backticks and brackets, then the clause; bold, bare,
    and bracket-only wrappings are accepted too."""
    tag = re.compile(
        r"^\s*[-*]\s+[`*]*\[?" + re.escape(req_id) + r"\]?[`*]*\s*[:—-]?\s*(.*)$"
    )
    return [m.group(1).strip() for line in prd.splitlines() if (m := tag.match(line))]


def edge_cases_for(prd: str, req_id: str) -> tuple[str | None, list[tuple[int, str]]]:
    """(group heading, numbered edge cases) of the capability group carrying
    the requirement: the first headed section naming the id, the anchor
    form preferred. The list opens only at a bare "Edge cases:" label line
    and closes at the first line that is neither numbered nor blank."""
    anchor = re.compile(r'id="' + re.escape(req_id.lower()) + r'"')
    mention = re.compile(r"\b" + re.escape(req_id) + r"\b")
    sections = [(h, b) for h, b in _sections(prd) if h]
    hit = next(((h, b) for h, b in sections if anchor.search(b)), None) or next(
        ((h, b) for h, b in sections if mention.search(b)), None
    )
    if hit is None:
        return None, []
    heading, body = hit
    cases: list[tuple[int, str]] = []
    in_list = False
    for line in body.splitlines():
        if _EDGE_LABEL.match(line):
            in_list = True
            continue
        if not in_list:
            continue
        m = _NUMBERED.match(line)
        if m:
            cases.append((int(m.group(1)), m.group(2).strip()))
        elif line.strip():
            break
    return heading, cases


def test_files(root: Path, globs: list[str]) -> list[Path]:
    """Files under root matching any test glob (fnmatch over the relative
    path, the layout's convention), skipping VCS and build trees by their
    relative parts and never following a symlink."""
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part in _SKIP_DIRS for part in rel.parts) or path.is_symlink():
            continue
        if not path.is_file():
            continue
        if any(fnmatch(rel.as_posix(), g) for g in globs):
            found.append(path)
    return found


def _read(path: Path, notes: list[str], label: str) -> str:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            notes.append(f"{label} skipped: larger than {_MAX_FILE_BYTES} bytes")
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        notes.append(f"{label} unreadable: {exc.__class__.__name__}")
        return ""


def coverage_map(
    req_id: str, root: Path, test_globs: list[str], declared: list[str] | None
) -> CoverageMap:
    notes: list[str] = []
    prd_path = root / PRD
    prd = _read(prd_path, notes, PRD) if prd_path.is_file() else ""
    if not prd_path.is_file():
        notes.append(f"{PRD} is absent — no bullets or edge cases to map")
    if declared is None:
        notes.append(f"no prd-entry on record for {req_id} — no declared tests")
    files = test_files(root, test_globs)
    texts = {
        p.relative_to(root).as_posix(): _read(p, notes, p.relative_to(root).as_posix())
        for p in files
    }
    if not files:
        notes.append("no test files match the layout's test globs")
    decl: list[tuple[str, tuple[str, ...]]] = []
    for name in declared or []:
        pat = re.compile(r"(?<![\w.])" + re.escape(name) + r"[ \t]*\(")
        decl.append((name, tuple(f for f, t in texts.items() if pat.search(t))))
    group, cases = edge_cases_for(prd, req_id)
    return CoverageMap(
        req_id=req_id,
        done_when=tuple(done_when_bullets(prd, req_id)),
        declared=None if declared is None else tuple(decl),
        group=group,
        edge_cases=tuple(cases),
        notes=tuple(notes),
    )


def _cut(text: str, width: int = 90) -> str:
    text = _clean(text)
    return text if len(text) <= width else text[: width - 1] + "…"


def render(cm: CoverageMap) -> str:
    lines = [f"coverage-map: {_clean(cm.req_id)}"]
    for note in cm.notes:
        lines.append(f"  note: {_clean(note)}")
    lines.append(
        f"  Done-when bullets ({len(cm.done_when)}) — each needs a test whose name states it:"
    )
    for i, text in enumerate(cm.done_when, 1):
        lines.append(f"    {i}. {_cut(text, 120)}")
    if cm.declared is None:
        lines.append("  Declared tests: none on record")
    else:
        present = sum(1 for _, fs in cm.declared if fs)
        lines.append(f"  Declared tests: {present} of {len(cm.declared)} present")
        for name, fs in cm.declared:
            tail = f"  ({', '.join(_clean(f) for f in fs)})" if fs else ""
            lines.append(f"    {'✔' if fs else '✗'} {_clean(name)}{tail}")
    where = f" of {_clean(cm.group)}" if cm.group else ""
    lines.append(
        f"  Edge cases{where} ({len(cm.edge_cases)}) — each needs a test or a walk note:"
    )
    for n, text in cm.edge_cases:
        lines.append(f"    {n}. {_cut(text)}")
    return "\n".join(lines)
