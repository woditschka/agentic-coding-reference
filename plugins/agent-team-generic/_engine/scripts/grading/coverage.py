"""Map the slice's Done-when bullets, declared tests, and edge cases beside the tests that define them.

A leaf over the PRD and the test tree: presence is string-checked, edge cases
are listed and never matched, and every read problem lands in the notes.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

PRD = "docs/prd.md"
_SKIP_DIRS = {".git", ".scratch", "build", "target", "node_modules", "bin", "out"}
_MAX_FILE_BYTES = 2_000_000
_EDGE_LABEL = re.compile(r"^\s*[*_]*edge cases?[*_]*:?[*_]*\s*$", re.IGNORECASE)
_NUMBERED = re.compile(r"^\s*(\d{1,6})\.\s+(.*)$")
_HEADING = re.compile(r"^(#{2,3})\s+(.*)$")
_TAB = 9
_CONTROL = {c: None for c in range(32) if c != _TAB} | {127: None}
_BULLET_WIDTH = 120
_CASE_WIDTH = 90
_ELLIPSIS = "…"

Declared = tuple[str, tuple[str, ...]]
EdgeCase = tuple[int, str]


@dataclass(frozen=True, slots=True)
class CoverageMap:
    """The map for one slice; declared is None when no prd-entry names tests."""

    req_id: str
    done_when: tuple[str, ...]
    declared: tuple[Declared, ...] | None
    group: str | None
    edge_cases: tuple[EdgeCase, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)


def _sections(prd: str) -> list[tuple[str, str]]:
    """Return (heading, body) per `##` or `###` section; the preamble carries an empty heading."""
    out: list[tuple[str, str]] = []
    heading = ""
    body: list[str] = []
    for line in prd.splitlines():
        found = _HEADING.match(line)
        if found:
            if heading or body:
                out.append((heading, "\n".join(body)))
            heading, body = found.group(2).strip(), []
        else:
            body.append(line)
    if heading or body:
        out.append((heading, "\n".join(body)))
    return out


def done_when_bullets(prd: str, req_id: str) -> list[str]:
    """Return the bullets opening with the requirement's id, in backticks, brackets, bold, or bare."""
    tag = re.compile(
        r"^\s*[-*]\s+[`*]*\[?" + re.escape(req_id) + r"\]?[`*]*\s*[:—-]?\s*(.*)$"
    )
    return [
        found.group(1).strip()
        for line in prd.splitlines()
        if (found := tag.match(line))
    ]


def edge_cases_for(prd: str, req_id: str) -> tuple[str | None, list[EdgeCase]]:
    """Return the heading and numbered edge cases of the first section naming the id, the anchor form preferred."""
    anchor = re.compile(r'id="' + re.escape(req_id.lower()) + r'"')
    mention = re.compile(r"\b" + re.escape(req_id) + r"\b")
    sections = [(heading, body) for heading, body in _sections(prd) if heading]
    hit = next(((h, b) for h, b in sections if anchor.search(b)), None) or next(
        ((h, b) for h, b in sections if mention.search(b)), None
    )
    if hit is None:
        return None, []
    heading, body = hit
    return heading, _numbered_cases(body)


def _numbered_cases(body: str) -> list[EdgeCase]:
    """Return the numbered list under the edge-case label, closed by the first other non-blank line."""
    cases: list[EdgeCase] = []
    in_list = False
    for line in body.splitlines():
        if _EDGE_LABEL.match(line):
            in_list = True
            continue
        if not in_list:
            continue
        found = _NUMBERED.match(line)
        if found:
            cases.append((int(found.group(1)), found.group(2).strip()))
        elif line.strip():
            break
    return cases


def test_files(root: Path, globs: Sequence[str]) -> list[Path]:
    """Return the files under the root matching a test glob, VCS and build trees skipped, symlinks never followed."""
    return [
        path for path in sorted(root.rglob("*")) if _is_test_file(path, root, globs)
    ]


def _is_test_file(path: Path, root: Path, globs: Sequence[str]) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    if any(part in _SKIP_DIRS for part in rel.parts) or path.is_symlink():
        return False
    return path.is_file() and any(fnmatch(rel.as_posix(), g) for g in globs)


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
    req_id: str, root: Path, test_globs: Sequence[str], declared: Sequence[str] | None
) -> CoverageMap:
    """Return the slice's map over the PRD and the test tree under the root."""
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
    group, cases = edge_cases_for(prd, req_id)
    return CoverageMap(
        req_id=req_id,
        done_when=tuple(done_when_bullets(prd, req_id)),
        declared=None if declared is None else _defined_in(declared, texts),
        group=group,
        edge_cases=tuple(cases),
        notes=tuple(notes),
    )


def _defined_in(declared: Sequence[str], texts: dict[str, str]) -> tuple[Declared, ...]:
    """Pair every declared test name with the files defining it."""
    return tuple(
        (name, tuple(path for path, text in texts.items() if _defines(name, text)))
        for name in declared
    )


def _defines(name: str, text: str) -> bool:
    return re.search(r"(?<![\w.])" + re.escape(name) + r"[ \t]*\(", text) is not None


def _cut(text: str, width: int = _CASE_WIDTH) -> str:
    text = text.translate(_CONTROL)
    return text if len(text) <= width else text[: width - 1] + _ELLIPSIS


def render(coverage: CoverageMap) -> str:
    """Render the map for the terminal, control characters dropped."""
    lines = [f"coverage-map: {_cut(coverage.req_id, len(coverage.req_id) + 1)}"]
    lines.extend(f"  note: {_cut(note, len(note) + 1)}" for note in coverage.notes)
    lines.append(
        f"  Done-when bullets ({len(coverage.done_when)}) — each needs a test whose name states it:"
    )
    lines.extend(
        f"    {i}. {_cut(text, _BULLET_WIDTH)}"
        for i, text in enumerate(coverage.done_when, 1)
    )
    lines.extend(_render_declared(coverage.declared))
    where = (
        f" of {_cut(coverage.group, len(coverage.group) + 1)}" if coverage.group else ""
    )
    lines.append(
        f"  Edge cases{where} ({len(coverage.edge_cases)}) — each needs a test or a walk note:"
    )
    lines.extend(f"    {n}. {_cut(text)}" for n, text in coverage.edge_cases)
    return "\n".join(lines)


def _render_declared(declared: tuple[Declared, ...] | None) -> list[str]:
    if declared is None:
        return ["  Declared tests: none on record"]
    present = sum(1 for _, files in declared if files)
    lines = [f"  Declared tests: {present} of {len(declared)} present"]
    for name, files in declared:
        tail = f"  ({', '.join(_clean(f) for f in files)})" if files else ""
        lines.append(f"    {'✔' if files else '✗'} {_clean(name)}{tail}")
    return lines


def _clean(text: str) -> str:
    return text.translate(_CONTROL)
