"""Map the added comments, raw constructions, and literal-bearing lines of a change.

A leaf over the unified diff and the compiled [conventions] record: the map
lists what the implementer's walk and the reviewers' checklists judge, and
carries no verdict.
"""

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_LICENSE = re.compile(
    r"copyright \(c\)|copyright \d|licensed under|licen[cs]e, version|"
    r"without warranties|apache\.org|\"as is\"",
    re.IGNORECASE,
)
_STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])+\'')
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
_DECLARATIVE = re.compile(r"^\s*(?:@|import\b|package\b|using\b|from\b[^=]*\bimport\b)")
_TAB = 9
_CONTROL = {c: None for c in range(32) if c != _TAB} | {127: None}
_PATH_WIDTH = 200
_LINE_WIDTH = 100
_ELLIPSIS = "…"

Marker = str
Numbered = tuple[int, str]
DiffLine = tuple[str, Marker, int, str]


@dataclass(frozen=True, slots=True)
class Conventions:
    """The validated [conventions] table, compiled once per map."""

    comment_markers: tuple[str, ...]
    construction: re.Pattern[str] | None
    construction_ignore: tuple[re.Pattern[str], ...]
    constant_declaration: re.Pattern[str] | None


@dataclass(frozen=True, slots=True)
class Block:
    """One run of consecutive added comment lines, shown by its first line."""

    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class FileRows:
    """The rows one changed code file lists."""

    path: str
    kind: str
    comments: tuple[Block, ...]
    constructions: tuple[Numbered, ...]
    literals: tuple[Numbered, ...]

    @property
    def empty(self) -> bool:
        """Return whether the file lists nothing."""
        return not (self.comments or self.constructions or self.literals)


@dataclass(frozen=True, slots=True)
class ConventionsMap:
    """The map over one change: the files with rows, the count without, and the read notes."""

    files: tuple[FileRows, ...]
    quiet_files: int
    notes: tuple[str, ...] = field(default_factory=tuple)


class _Cursor:
    """The parser's place in a unified diff: the open path and the next new-file line number."""

    def __init__(self) -> None:
        self.path: str | None = None
        self.lineno = 0
        self._minus_path: str | None = None
        self._after_minus = False

    def is_header(self, raw: str) -> bool:
        """Return whether the line is a file header: a "--- " outside any file, or its "+++ " partner."""
        if raw.startswith("--- "):
            return self.path is None
        return raw.startswith("+++ ") and self._after_minus

    def header(self, raw: str) -> DiffLine | None:
        """Consume a file-header line and return the open event a new path raises.

        A deleted file opens under its old path with no event, since its
        removed lines still count.
        """
        if raw.startswith("--- "):
            self._after_minus = True
            minus = raw[4:].strip()
            self._minus_path = (
                None if minus == "/dev/null" else minus.removeprefix("a/")
            )
            return None
        self._after_minus = False
        target = raw[4:].strip()
        if target == "/dev/null":
            self.path = self._minus_path
            return None
        self.path = target.removeprefix("b/")
        return self.path, "h", 0, ""

    def content(self, raw: str) -> DiffLine | None:
        """Consume a hunk line and return its added or removed event, if any."""
        self._after_minus = False
        if (hunk := _HUNK.match(raw)) is not None:
            self.lineno = int(hunk.group(1))
            return None
        if self.path is None or raw.startswith("\\"):
            return None
        if raw.startswith("+"):
            event = (self.path, "+", self.lineno, raw[1:])
            self.lineno += 1
            return event
        if raw.startswith("-"):
            return self.path, "-", self.lineno, raw[1:]
        self.lineno += 1
        return None


def _diff_lines(diff: str) -> Iterator[DiffLine]:
    """Yield (path, marker, new-file line number, text) for every added and removed line, plus one open event per file."""
    cursor = _Cursor()
    for raw in diff.splitlines():
        if raw.startswith("diff "):
            cursor = _Cursor()
            continue
        event = cursor.header(raw) if cursor.is_header(raw) else cursor.content(raw)
        if event is not None:
            yield event


def added_lines(diff: str) -> dict[str, list[Numbered]]:
    """Return the added lines per path; a file with no added line maps to an empty list, a deleted file to nothing."""
    out: dict[str, list[Numbered]] = {}
    for path, marker, lineno, text in _diff_lines(diff):
        if marker == "h":
            out.setdefault(path, [])
        elif marker == "+":
            out.setdefault(path, []).append((lineno, text))
    return out


def changed_lines(diff: str) -> dict[str, list[str]]:
    """Return the added and removed line texts per path; a deleted file's lines count under its old path."""
    out: dict[str, list[str]] = {}
    for path, marker, _lineno, text in _diff_lines(diff):
        if marker == "h":
            out.setdefault(path, [])
        else:
            out.setdefault(path, []).append(text)
    return out


def _is_comment(text: str, markers: tuple[str, ...]) -> bool:
    stripped = text.lstrip()
    return bool(stripped) and any(stripped.startswith(m) for m in markers)


def comment_blocks(lines: list[Numbered], markers: tuple[str, ...]) -> list[Block]:
    """Return the consecutive added comment lines as blocks, a license header dropped."""
    blocks: list[Block] = []
    run: list[Numbered] = []

    def flush() -> None:
        if run and not any(_LICENSE.search(text) for _, text in run):
            blocks.append(Block(run[0][0], run[-1][0], run[0][1].strip()))
        run.clear()

    for lineno, text in lines:
        if _is_comment(text, markers) and (not run or lineno == run[-1][0] + 1):
            run.append((lineno, text))
        else:
            flush()
            if _is_comment(text, markers):
                run.append((lineno, text))
    flush()
    return blocks


def constructions(lines: list[Numbered], conventions: Conventions) -> list[Numbered]:
    """Return the added lines carrying a construction outside the ignored framework types."""
    if conventions.construction is None:
        return []
    return [
        (lineno, text.strip())
        for lineno, text in lines
        if not _is_comment(text, conventions.comment_markers)
        and _constructs(text, conventions)
    ]


def _constructs(text: str, conventions: Conventions) -> bool:
    assert conventions.construction is not None
    hits = list(conventions.construction.finditer(text))
    return bool(hits) and not all(
        any(ignore.search(hit.group(0)) for ignore in conventions.construction_ignore)
        for hit in hits
    )


def literal_lines(lines: list[Numbered], conventions: Conventions) -> list[Numbered]:
    """Return the added lines carrying a literal outside a constant declaration, comment, annotation, or import."""
    return [
        (lineno, text.strip())
        for lineno, text in lines
        if _bears_literal(text, conventions)
    ]


def _bears_literal(text: str, conventions: Conventions) -> bool:
    if _is_comment(text, conventions.comment_markers) or _DECLARATIVE.match(text):
        return False
    declaration = conventions.constant_declaration
    if declaration is not None and declaration.search(text):
        return False
    code = _STRING.sub('""', text)
    return bool(_STRING.search(text) or _NUMBER.search(code))


def conventions_map(
    diff: str, kind_of: Callable[[str], str], conventions: Conventions
) -> ConventionsMap:
    """Return the map over a unified diff: comments for every code file, constructions and literals for test files."""
    files: list[FileRows] = []
    quiet = 0
    for path, lines in added_lines(diff).items():
        kind = kind_of(path)
        if kind not in ("prod", "test"):
            continue
        is_test = kind == "test"
        rows = FileRows(
            path=path,
            kind=kind,
            comments=tuple(comment_blocks(lines, conventions.comment_markers)),
            constructions=tuple(constructions(lines, conventions) if is_test else ()),
            literals=tuple(literal_lines(lines, conventions) if is_test else ()),
        )
        if rows.empty:
            quiet += 1
        else:
            files.append(rows)
    notes: tuple[str, ...] = ()
    if conventions.construction is None:
        notes = (
            "no [conventions] construction pattern in layout.toml — raw "
            "constructions are not listed",
        )
    return ConventionsMap(files=tuple(files), quiet_files=quiet, notes=notes)


def _cut(text: str, width: int = _LINE_WIDTH) -> str:
    text = text.translate(_CONTROL)
    return text if len(text) <= width else text[: width - 1] + _ELLIPSIS


def render(conventions: ConventionsMap, base_label: str) -> str:
    """Render the map for the terminal, control characters dropped."""
    lines = [
        f"conventions-map: {len(conventions.files)} code file(s) with rows, "
        f"{conventions.quiet_files} without (base {base_label.translate(_CONTROL)})"
    ]
    lines.extend(f"  note: {note.translate(_CONTROL)}" for note in conventions.notes)
    for rows in conventions.files:
        lines.append(f"  {_cut(rows.path, _PATH_WIDTH)} ({rows.kind})")
        lines.extend(_render_rows(rows))
    return "\n".join(lines)


def _render_rows(rows: FileRows) -> list[str]:
    lines: list[str] = []
    if rows.comments:
        lines.append(
            f"    comments ({len(rows.comments)}) — each explains WHY; one a better "
            "name would make redundant is a rename:"
        )
        lines.extend(
            f"      {_span(block)}: {_cut(block.text)}" for block in rows.comments
        )
    if rows.constructions:
        lines.append(
            f"    constructions ({len(rows.constructions)}) — each through the type's "
            "entry point with named arguments, or a named default:"
        )
        lines.extend(
            f"      {lineno}: {_cut(text)}" for lineno, text in rows.constructions
        )
    if rows.literals:
        lines.append(
            f"    literal-bearing lines ({len(rows.literals)}) — each literal named "
            "by role or declared irrelevant:"
        )
        lines.extend(f"      {lineno}: {_cut(text)}" for lineno, text in rows.literals)
    return lines


def _span(block: Block) -> str:
    return (
        f"{block.start}" if block.start == block.end else f"{block.start}-{block.end}"
    )
