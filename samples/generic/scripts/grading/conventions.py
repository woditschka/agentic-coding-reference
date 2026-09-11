"""grading.conventions — the change set's write-time conventions map.

The blind judge's recurring deductions are conventions the testing brief
already states: a comment restating the code, a raw construction in a
test whose arguments say nothing, a bare literal. Each is a write-time
decision, and the recorded lesson is that a listed line gets acted on where
a prose clause does not. So this map lists, per changed code file, every
added comment block, every raw construction in a test file, and every
literal-bearing added test line, for the implementer's Test-Conventions
Walk and the reviewers' checklists to work from.

Whether a comment explains WHY, a construction is the type's entry point,
or a literal is the value under test is judgment, so this is a map, never
a gate: no exit code carries a verdict. Every input is agent-written (the
diff, the layout table), so the map reads defensively and renders only
printable text; any read problem lands in the notes.

Pure functions over the unified diff; the CLI wiring lives in grading.py.
Stdlib only, Python 3.11+.
"""

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_LICENSE = re.compile(
    r"copyright \(c\)|copyright \d|licensed under|licen[cs]e, version|"
    r"without warranties|apache\.org|\"as is\"",
    re.I,
)
_STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])+\'')
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
_DECLARATIVE = re.compile(r"^\s*(?:@|import\b|package\b|using\b|from\b[^=]*\bimport\b)")
_CONTROL = {c: None for c in range(32) if c not in (9,)} | {127: None}


@dataclass(frozen=True)
class Conventions:
    """The validated [conventions] table, compiled once per map."""

    comment_markers: tuple[str, ...]
    construction: re.Pattern[str] | None
    construction_ignore: tuple[re.Pattern[str], ...]
    constant_declaration: re.Pattern[str] | None

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "Conventions":
        construction = cfg.get("construction")
        constant = cfg.get("constant_declaration")
        return cls(
            comment_markers=tuple(cfg.get("comment_markers", ())),
            construction=re.compile(construction) if construction else None,
            construction_ignore=tuple(
                re.compile(p) for p in cfg.get("construction_ignore", ())
            ),
            constant_declaration=re.compile(constant) if constant else None,
        )


@dataclass(frozen=True)
class Block:
    start: int
    end: int
    text: str  # the block's first line


@dataclass(frozen=True)
class FileRows:
    path: str
    kind: str
    comments: tuple[Block, ...]
    constructions: tuple[tuple[int, str], ...]
    literals: tuple[tuple[int, str], ...]

    @property
    def empty(self) -> bool:
        return not (self.comments or self.constructions or self.literals)


@dataclass(frozen=True)
class ConventionsMap:
    files: tuple[FileRows, ...]
    quiet_files: int
    notes: tuple[str, ...] = field(default_factory=tuple)


def _clean(text: str) -> str:
    return text.translate(_CONTROL)


def _diff_lines(diff: str) -> Iterator[tuple[str, str, int, str]]:
    """(path, marker, new-file line number, text) for every added ("+") and
    removed ("-") line in a unified diff, hunk-aware, plus one ("h") event
    when a file header opens a path, so a file with no added line is still
    known. Deleted files and binary
    patches contribute nothing; a context line advances the counter, a
    removed line does not. A "+++ " line is a file header only directly
    after its "--- " partner, outside any hunk; inside a hunk an added line
    whose text begins "++ " renders the same way and is content, never a
    header. "diff " opens a new file and closes the previous one's hunks."""
    path: str | None = None
    minus_path: str | None = None
    lineno = 0
    after_minus = False
    for raw in diff.splitlines():
        if raw.startswith("diff "):
            path = None
            after_minus = False
            continue
        if raw.startswith("--- ") and path is None:
            after_minus = True
            minus = raw[4:].strip()
            minus_path = None if minus == "/dev/null" else minus.removeprefix("a/")
            continue
        if raw.startswith("+++ ") and after_minus:
            after_minus = False
            target = raw[4:].strip()
            if target == "/dev/null":
                # A deleted file: no header event, since it has no added
                # lines, but its removed lines still yield under the old
                # path — a deleted guard is a weakened one.
                path = minus_path
            else:
                path = target.removeprefix("b/")
                yield path, "h", 0, ""
            continue
        after_minus = False
        m = _HUNK.match(raw)
        if m:
            lineno = int(m.group(1))
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            yield path, "+", lineno, raw[1:]
            lineno += 1
        elif raw.startswith("-"):
            yield path, "-", lineno, raw[1:]
        elif raw.startswith("\\"):
            continue
        else:
            lineno += 1


def added_lines(diff: str) -> dict[str, list[tuple[int, str]]]:
    """(new-file line number, text) per path for every added line in a
    unified diff; a file with a header and no added line maps to [], and a
    deleted file contributes nothing."""
    out: dict[str, list[tuple[int, str]]] = {}
    for path, marker, lineno, text in _diff_lines(diff):
        if marker == "h":
            out.setdefault(path, [])
        elif marker == "+":
            out.setdefault(path, []).append((lineno, text))
    return out


def changed_lines(diff: str) -> dict[str, list[str]]:
    """Added and removed line texts per path — the security-surface probe's
    input: a removed match is a weakened guard and hits like an added one,
    and a deleted file's lines count under its old path."""
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


def comment_blocks(
    lines: list[tuple[int, str]], markers: tuple[str, ...]
) -> list[Block]:
    """Consecutive added comment lines as one block each, license headers
    dropped: a block any line of which reads as a license notice is the
    file header, not a comment the change wrote."""
    blocks: list[Block] = []
    run: list[tuple[int, str]] = []

    def flush() -> None:
        if run and not any(_LICENSE.search(t) for _, t in run):
            blocks.append(Block(run[0][0], run[-1][0], run[0][1].strip()))
        run.clear()

    for no, text in lines:
        if _is_comment(text, markers) and (not run or no == run[-1][0] + 1):
            run.append((no, text))
        else:
            flush()
            if _is_comment(text, markers):
                run.append((no, text))
    flush()
    return blocks


def constructions(
    lines: list[tuple[int, str]], cv: Conventions
) -> list[tuple[int, str]]:
    """Added lines carrying the stack's construction syntax, minus the
    declared framework types; none when the project declares no pattern."""
    if cv.construction is None:
        return []
    out: list[tuple[int, str]] = []
    for no, text in lines:
        if _is_comment(text, cv.comment_markers):
            continue
        hits = [m for m in cv.construction.finditer(text)]
        if not hits:
            continue
        if all(
            any(ig.search(m.group(0)) for ig in cv.construction_ignore) for m in hits
        ):
            continue
        out.append((no, text.strip()))
    return out


def literal_lines(
    lines: list[tuple[int, str]], cv: Conventions
) -> list[tuple[int, str]]:
    """Added lines carrying a string or number literal outside a constant
    declaration, a comment, an annotation, or an import."""
    out: list[tuple[int, str]] = []
    for no, text in lines:
        if _is_comment(text, cv.comment_markers) or _DECLARATIVE.match(text):
            continue
        if cv.constant_declaration is not None and cv.constant_declaration.search(text):
            continue
        code = _STRING.sub('""', text)
        if _STRING.search(text) or _NUMBER.search(code):
            out.append((no, text.strip()))
    return out


def conventions_map(
    diff: str, kind_of: Callable[[str], str], cfg: dict[str, Any]
) -> ConventionsMap:
    """The map over a unified diff: comments for every code file, constructions
    and literals for test files. kind_of classifies a path as the layout does
    ("prod", "test", or anything else, which is not code and lists nothing)."""
    cv = Conventions.from_config(cfg)
    notes: list[str] = []
    files: list[FileRows] = []
    quiet = 0
    for path, lines in added_lines(diff).items():
        kind = kind_of(path)
        if kind not in ("prod", "test"):
            continue
        rows = FileRows(
            path=path,
            kind=kind,
            comments=tuple(comment_blocks(lines, cv.comment_markers)),
            constructions=tuple(constructions(lines, cv) if kind == "test" else ()),
            literals=tuple(literal_lines(lines, cv) if kind == "test" else ()),
        )
        if rows.empty:
            quiet += 1
        else:
            files.append(rows)
    if cv.construction is None:
        notes.append(
            "no [conventions] construction pattern in layout.toml — raw "
            "constructions are not listed"
        )
    return ConventionsMap(files=tuple(files), quiet_files=quiet, notes=tuple(notes))


def _cut(text: str, width: int = 100) -> str:
    text = _clean(text)
    return text if len(text) <= width else text[: width - 1] + "…"


def render(cm: ConventionsMap, base_label: str) -> str:
    lines = [
        f"conventions-map: {len(cm.files)} code file(s) with rows, "
        f"{cm.quiet_files} without (base {_clean(base_label)})"
    ]
    for note in cm.notes:
        lines.append(f"  note: {_clean(note)}")
    for f in cm.files:
        lines.append(f"  {_cut(f.path, 200)} ({f.kind})")
        if f.comments:
            lines.append(
                f"    comments ({len(f.comments)}) — each explains WHY; one a better "
                "name would make redundant is a rename:"
            )
            for b in f.comments:
                span = f"{b.start}" if b.start == b.end else f"{b.start}-{b.end}"
                lines.append(f"      {span}: {_cut(b.text)}")
        if f.constructions:
            lines.append(
                f"    constructions ({len(f.constructions)}) — each through the type's "
                "entry point with named arguments, or a named default:"
            )
            for no, text in f.constructions:
                lines.append(f"      {no}: {_cut(text)}")
        if f.literals:
            lines.append(
                f"    literal-bearing lines ({len(f.literals)}) — each literal named "
                "by role or declared irrelevant:"
            )
            for no, text in f.literals:
                lines.append(f"      {no}: {_cut(text)}")
    return "\n".join(lines)
