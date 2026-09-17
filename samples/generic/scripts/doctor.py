#!/usr/bin/env python3
"""Validate a project's briefs and runtime wiring against the doctor expectations manifest.

The blocking layer of the harness-project API: existence, required sections,
data slots, naming conventions, and channel invariants. Judgment checks live in
the audit-docs skill.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple, TypeAlias, TypeGuard

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("doctor requires Python 3.11+ (tomllib)\n")
    sys.exit(2)

# The layout checks reuse the engine's own validators, so the doctor and the
# engine cannot disagree on what is accepted. The package is absent when a
# maintainer script loads this module by path, and those checks skip there.
try:
    from grading.config import (
        REVIEWERS,
        load_stack_defaults,
        merged_table,
        shadowed_keys,
        validate_module_rules,
        validate_review,
    )

    GRADING_AVAILABLE = True
except ImportError:
    GRADING_AVAILABLE = False

if TYPE_CHECKING:
    from grading.config import ReviewConfig

Status: TypeAlias = Literal["PASS", "FAIL", "SKIP", "WARN"]
Table: TypeAlias = Mapping[str, object]
# The parse boundary: what tomllib returns for the harness-owned manifest.
Raw: TypeAlias = dict[str, Any]

PASS: Final[Status] = "PASS"
FAIL: Final[Status] = "FAIL"
SKIP: Final[Status] = "SKIP"
# Advisory: rendered and emitted like the others, never counted toward the exit code.
WARN: Final[Status] = "WARN"

DEFAULT_MANIFEST = Path(__file__).resolve().parent / "doctor-expectations.toml"
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_BULLET_RE = re.compile(r"^\s*[-*+]\s")
_HOOK_MATCHER_RE = re.compile(r"\.claude/hooks/([\w.-]+)")
# Any REQ-shaped token, so a near-miss id fails here rather than at the first
# ledger append the record schemas reject.
_REQ_TOKEN_RE = re.compile(r"\bREQ-[A-Z]+-[0-9]+\b")
# A field or parameter table mirrors a source schema and rots with the code.
_FIELD_TABLE_HEADER = re.compile(
    r"\s*\|\s*(fields?|parameters?|params?|arguments?|args?)\s*\|",
    re.IGNORECASE,
)
# Shape only: the value is machine-written from VERSION-DATE, so calendar
# validity is not checked here.
STAMP_LINE = re.compile(r"^<!--\s*harness:")
STAMP_WELL_FORMED = re.compile(r"^<!--\s*harness:\s*(\d{4}-\d{2}-\d{2})\b.*-->\s*$")

# Harness-managed chapters of the project-owned CLAUDE.md, matched by exact
# heading; materialize refreshes each in place from the managed-chapter source.
REQUIRED_CHAPTERS = (
    "## Agent Usage (Mandatory)",
    "## Memory",
    "## Writing Standards",
    "## Scratch Directory",
    "## Documentation Updates",
)

# The runtime the marketplace plugin supplies; a second copy in the project
# tree loads every skill and agent twice.
MARKETPLACE_PLUGIN_PATHS = (
    ".claude/skills",
    ".claude/agents",
    ".claude/hooks",
    ".github/agents",
    ".opencode/agents",
)

# The marketplace name before the agent-team rename; a settings key still on
# it silently stops matching updates.
LEGACY_MARKETPLACE = "agentic-harness"

# Harness runtime content: never tracked by git on the manifest and
# marketplace channels. The consumer .gitignore block is rendered from this list.
RUNTIME_PATHS = [
    ".claude/skills",
    ".claude/agents",
    ".claude/hooks",
    ".claude/templates",
    ".github/agents",
    ".opencode/agents",
    "schemas/scratch",
    "scripts/gate.sh",
    "scripts/layout-defaults.toml",
    "scripts/handoff.py",
    "scripts/handoff/__init__.py",
    "scripts/handoff/schema.py",
    "scripts/handoff/records.py",
    "scripts/handoff/ledger.py",
    "scripts/handoff/text.py",
    "scripts/handoff/timestamps.py",
    "scripts/handoff/cost.py",
    "scripts/handoff/findings.py",
    "scripts/handoff/tiers.py",
    "scripts/handoff/roster.py",
    "scripts/handoff/ladder.py",
    "scripts/handoff/scope_lock.py",
    "scripts/handoff/repository.py",
    "scripts/handoff/non_goals.py",
    "scripts/handoff/autofix.py",
    "scripts/handoff/gates.py",
    "scripts/handoff/board.py",
    "scripts/handoff/routing.py",
    "scripts/handoff/view.py",
    "scripts/accounting.py",
    "scripts/backlog.py",
    "scripts/changeset.py",
    "scripts/changeset/__init__.py",
    "scripts/changeset/config.py",
    "scripts/changeset/git_facts.py",
    "scripts/changeset/emit.py",
    "scripts/grading.py",
    "scripts/grading/__init__.py",
    "scripts/grading/config.py",
    "scripts/grading/features.py",
    "scripts/grading/handoff_facts.py",
    "scripts/grading/contracts.py",
    "scripts/grading/coverage.py",
    "scripts/grading/conventions.py",
    "scripts/grading/planner.py",
    "scripts/doctor.py",
    "scripts/doctor-expectations.toml",
    "scripts/tests/__init__.py",
    "scripts/tests/support.py",
    "scripts/tests/test_handoff.py",
    "scripts/tests/test_doctor.py",
    "scripts/tests/test_accounting.py",
    "scripts/tests/test_backlog.py",
    "scripts/tests/test_grading.py",
    "scripts/tests/test_changeset.py",
    "scripts/tests/changeset/__init__.py",
    "scripts/tests/changeset/test_config.py",
    "scripts/tests/changeset/test_git_facts.py",
    "scripts/tests/changeset/test_emit.py",
    "scripts/tests/grading/__init__.py",
    "scripts/tests/grading/test_config.py",
    "scripts/tests/grading/test_config_layout.py",
    "scripts/tests/grading/test_features.py",
    "scripts/tests/grading/test_features_layout.py",
    "scripts/tests/grading/test_handoff_facts.py",
    "scripts/tests/grading/test_contracts.py",
    "scripts/tests/grading/test_coverage.py",
    "scripts/tests/grading/test_conventions.py",
    "scripts/tests/grading/test_planner.py",
    "scripts/tests/handoff/__init__.py",
    "scripts/tests/handoff/test_schema.py",
    "scripts/tests/handoff/test_records.py",
    "scripts/tests/handoff/test_ledger.py",
    "scripts/tests/handoff/test_text.py",
    "scripts/tests/handoff/test_timestamps.py",
    "scripts/tests/handoff/test_cost.py",
    "scripts/tests/handoff/test_board.py",
    "scripts/tests/handoff/test_findings.py",
    "scripts/tests/handoff/test_tiers.py",
    "scripts/tests/handoff/test_roster.py",
    "scripts/tests/handoff/test_ladder.py",
    "scripts/tests/handoff/test_scope_lock.py",
    "scripts/tests/handoff/test_repository.py",
    "scripts/tests/handoff/test_non_goals.py",
    "scripts/tests/handoff/test_autofix.py",
    "scripts/tests/handoff/test_gates.py",
    "scripts/tests/handoff/test_routing.py",
    "scripts/tests/handoff/test_view.py",
]

# Every roster reviewer states the dispatch-event contract; without
# dispatch-start it never appends its start record, and truncation detection
# is blind to it.
_REQUIRED_REVIEWER_TOKENS = ("dispatch-start", "review-workflow")

# The working-memory artifact a reviewer body must never instruct reading. The
# bare slug matches with or without the .md suffix. design-block is not
# forbidden: every reviewer reads the ledger that holds it.
_FORBIDDEN_REVIEWER_REFS = ("implementation-plan",)


class Result(NamedTuple):
    """One check row: its status, the check name or checked path, and the detail."""

    status: Status
    check: str
    detail: str


def passed(check: str, detail: str) -> Result:
    """Build a passing row."""
    return Result(PASS, check, detail)


def failed(check: str, detail: str) -> Result:
    """Build a failing row."""
    return Result(FAIL, check, detail)


def skipped(check: str, detail: str) -> Result:
    """Build a skipped row."""
    return Result(SKIP, check, detail)


def warned(check: str, detail: str) -> Result:
    """Build an advisory row."""
    return Result(WARN, check, detail)


class Slot(NamedTuple):
    """A data slot: a section whose body must match a pattern."""

    section: str
    must_match: re.Pattern[str]


class Budget(NamedTuple):
    """A word ceiling and the layout key that may raise it."""

    max_words: int
    override_key: str | None


@dataclass(frozen=True, slots=True)
class FileSpec:
    """One roster entry: a brief, or the decision-log directory when `directory` is set."""

    path: str
    template: str
    directory: bool
    entry_pattern: re.Pattern[str] | None
    required_sections: tuple[str, ...]
    slots: tuple[Slot, ...]
    budget: Budget | None


class AgentSurface(NamedTuple):
    """Where one tool keeps an agent body: the path around the agent's name."""

    prefix: str
    suffix: str

    @property
    def directory(self) -> str:
        """Return the agent directory, relative to the project root."""
        return self.prefix.rstrip("/")

    def body_path(self, name: str) -> str:
        """Return the body path for one agent name."""
        return f"{self.prefix}{name}{self.suffix}"

    def agent_name(self, filename: str) -> str | None:
        """Return the agent name a body file carries, or None when the file is not a body."""
        if not filename.endswith(self.suffix):
            return None
        return filename[: -len(self.suffix)] if self.suffix else filename


@dataclass(frozen=True, slots=True)
class ReviewerSpec:
    """The reviewer floor, the name shape, and each tool's agent surface."""

    floor: tuple[str, ...]
    name_pattern: re.Pattern[str]
    surfaces: Mapping[str, AgentSurface]


@dataclass(frozen=True, slots=True)
class Manifest:
    """The expectations manifest, parsed once."""

    spec_version: str
    project_data_path: str
    required_keys: tuple[str, ...]
    channel_values: tuple[str, ...]
    reviewers: ReviewerSpec | None
    req_id_pattern: re.Pattern[str]
    design_doc: str
    prd: str
    handbook_denylist: tuple[str, ...]
    files: tuple[FileSpec, ...]


class LayoutFault(NamedTuple):
    """Why the project's layout could not be read."""

    kind: Literal["missing", "unparseable"]
    detail: str


@dataclass(frozen=True, slots=True)
class Project:
    """The project under check, with its layout read once and its declarations resolved."""

    root: Path
    layout_file: Path
    layout: Table
    layout_fault: LayoutFault | None
    channel: str | None
    extensions: tuple[str, ...]


def read_manifest(path: Path) -> Manifest:
    """Parse the expectations manifest into its record."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    project_data = raw["project_data"]
    cross_doc = raw["cross_doc"]
    reviewers = raw.get("reviewers")
    return Manifest(
        spec_version=raw["spec_version"],
        project_data_path=project_data["path"],
        required_keys=tuple(project_data["required_keys"]),
        channel_values=tuple(project_data["channel_values"]),
        reviewers=None if reviewers is None else _reviewer_spec(reviewers),
        req_id_pattern=re.compile(cross_doc["req_id_pattern"]),
        design_doc=cross_doc["source"],
        prd=cross_doc["defined_in"],
        handbook_denylist=tuple(raw["handbook"]["denylist"]),
        files=tuple(_file_spec(entry) for entry in raw["file"]),
    )


def _reviewer_spec(raw: Raw) -> ReviewerSpec:
    tool_dirs = raw["tool_dirs"]
    if not isinstance(tool_dirs, dict):
        raise TypeError("[reviewers] tool_dirs must be a table")
    surfaces = {
        tool: AgentSurface(*template.split("{name}"))
        for tool, template in tool_dirs.items()
    }
    return ReviewerSpec(
        floor=tuple(raw["floor"]),
        name_pattern=re.compile(raw["name_pattern"]),
        surfaces=surfaces,
    )


def _file_spec(entry: Raw) -> FileSpec:
    entry_pattern = entry.get("entry_pattern")
    if entry.get("directory") and entry_pattern is None:
        raise TypeError(
            f"[[file]] {entry['path']} is a directory entry without an entry_pattern"
        )
    max_words = entry.get("max_words")
    if max_words is not None and not isinstance(max_words, int):
        raise TypeError(f"[[file]] max_words must be an integer, got {max_words!r}")
    override_key = entry.get("budget_override_key")
    return FileSpec(
        path=entry["path"],
        template=entry["template"],
        directory=bool(entry.get("directory")),
        entry_pattern=None if entry_pattern is None else re.compile(entry_pattern),
        required_sections=tuple(entry.get("required_sections", ())),
        slots=tuple(
            Slot(slot["section"], re.compile(slot["must_match"]))
            for slot in entry.get("slots", ())
        ),
        budget=None if max_words is None else Budget(max_words, override_key),
    )


def read_project(manifest: Manifest, root: Path) -> Project:
    """Read the project's layout once and resolve the declarations later checks key on."""
    layout_file = root / manifest.project_data_path
    layout, fault = _read_layout(layout_file)
    return Project(
        root=root,
        layout_file=layout_file,
        layout=layout,
        layout_fault=fault,
        channel=declared_channel(manifest, layout),
        extensions=declared_extensions(layout),
    )


def _read_layout(path: Path) -> tuple[Table, LayoutFault | None]:
    if not path.is_file():
        return {}, LayoutFault("missing", "")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), None
    except tomllib.TOMLDecodeError as exc:
        return {}, LayoutFault("unparseable", str(exc))


def declared_channel(manifest: Manifest, layout: Table) -> str | None:
    """Return the declared channel when it is one the manifest allows."""
    channel = lookup(layout, "harness.channel")
    if isinstance(channel, str) and channel in manifest.channel_values:
        return channel
    return None


def declared_extensions(layout: Table) -> tuple[str, ...]:
    """Return the declared extension paths when the declaration is well-formed."""
    extensions = lookup(layout, "harness.extensions")
    return tuple(extensions) if _is_string_list(extensions) else ()


def _is_string_list(value: object) -> TypeGuard[list[str]]:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def lookup(table: Table, dotted: str) -> object:
    """Return the value at a dotted key path, or None when any step is absent."""
    node: object = table
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def parse_sections(text: str) -> dict[str, str]:
    """Map each `## ` heading to its body text."""
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines)
            current = line[3:].strip()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines)
    return sections


def unfenced_lines(lines: Sequence[str]) -> Iterator[tuple[int, str]]:
    """Yield each line outside a fenced code block with its index; a fence line is never yielded."""
    in_fence = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            yield index, line


def count_words(text: str) -> int:
    """Count words as `wc -w` does, after stripping HTML comments."""
    stripped = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    return len(stripped.split())


def check_project_data(manifest: Manifest, project: Project) -> list[Result]:
    """Check the layout's [harness] declarations against the manifest."""
    rel = manifest.project_data_path
    fault = project.layout_fault
    if fault is not None:
        if fault.kind == "missing":
            return [failed("project-data", f"{rel} missing")]
        return [failed("project-data", f"{rel} unparseable: {fault.detail}")]
    layout = project.layout
    results = [_required_key_result(rel, layout, key) for key in manifest.required_keys]
    declarations = (
        _channel_result(manifest, layout),
        _spec_version_result(manifest, layout),
        _extensions_result(layout),
        _auto_grade_result(layout),
    )
    results.extend(result for result in declarations if result is not None)
    return results


def _required_key_result(rel: str, layout: Table, dotted: str) -> Result:
    value = lookup(layout, dotted)
    if value is None:
        return failed("project-data", f"{rel}: key {dotted} missing")
    return passed("project-data", f"{dotted} = {value}")


def _channel_result(manifest: Manifest, layout: Table) -> Result | None:
    channel = lookup(layout, "harness.channel")
    if channel is None or declared_channel(manifest, layout) is not None:
        return None
    return failed(
        "project-data",
        f"channel must be one of {list(manifest.channel_values)}, got {channel!r}",
    )


def _spec_version_result(manifest: Manifest, layout: Table) -> Result | None:
    declared = lookup(layout, "harness.spec_version")
    if declared is None or declared == manifest.spec_version:
        return None
    return failed(
        "project-data",
        f"spec_version {declared} does not match manifest {manifest.spec_version}",
    )


def _extensions_result(layout: Table) -> Result | None:
    extensions = lookup(layout, "harness.extensions")
    if extensions is None or _is_string_list(extensions):
        return None
    return failed(
        "project-data", "harness.extensions must be a list of runtime-relative paths"
    )


def _auto_grade_result(layout: Table) -> Result | None:
    # The router fails open on a non-boolean, so a quoted "false" would keep
    # grading on; this is where the typo is fixable.
    auto_grade = lookup(layout, "harness.auto_grade")
    if auto_grade is None or isinstance(auto_grade, bool):
        return None
    return failed(
        "project-data", f"harness.auto_grade must be a boolean, got {auto_grade!r}"
    )


def check_file_entry(spec: FileSpec, root: Path) -> list[Result]:
    """Check one roster entry: presence, required sections, and filled slots."""
    if spec.directory:
        return check_directory_entry(spec, root)
    rel = spec.path
    path = root / rel
    if not path.is_file():
        return [failed(rel, f"missing — materialize {spec.template}")]
    sections = parse_sections(path.read_text(encoding="utf-8"))
    results = [passed(rel, "exists")]
    results.extend(
        _section_result(rel, sections, name) for name in spec.required_sections
    )
    results.extend(
        result
        for slot in spec.slots
        if (result := _slot_result(rel, sections, slot)) is not None
    )
    return results


def _section_result(rel: str, sections: Mapping[str, str], name: str) -> Result:
    if name in sections:
        return passed(rel, f"section '{name}' present")
    return failed(rel, f"required section '## {name}' missing")


def _slot_result(rel: str, sections: Mapping[str, str], slot: Slot) -> Result | None:
    body = sections.get(slot.section)
    if body is None:
        return None
    if slot.must_match.search(body):
        return passed(rel, f"slot in '{slot.section}' filled")
    return failed(
        rel,
        f"section '{slot.section}' lacks required data "
        f"(pattern {slot.must_match.pattern})",
    )


def check_directory_entry(spec: FileSpec, root: Path) -> list[Result]:
    """Check a directory entry: present, with a README and conforming entry names."""
    rel = spec.path
    path = root / rel
    if not path.is_dir():
        return [failed(rel, f"missing — materialize {spec.template}")]
    results = [passed(rel, "exists")]
    if (path / "README.md").is_file():
        results.append(passed(rel, "README.md present"))
    else:
        results.append(failed(rel, f"README.md missing — materialize {spec.template}"))
    entries = (
        child
        for child in sorted(path.iterdir())
        if child.name != "README.md" and child.name.endswith(".md")
    )
    results.extend(_entry_name_result(rel, spec, child.name) for child in entries)
    return results


def _entry_name_result(rel: str, spec: FileSpec, name: str) -> Result:
    if spec.entry_pattern is not None and spec.entry_pattern.match(name):
        return passed(rel, f"{name} conforms")
    return failed(rel, f"{name} violates entry naming YYYY-MM-DD-kebab.md")


def check_cross_doc(manifest: Manifest, root: Path) -> list[Result]:
    """Check that every requirement id the design doc cites is defined in the PRD, and well-formed."""
    source = root / manifest.design_doc
    target = root / manifest.prd
    if not source.is_file() or not target.is_file():
        return [skipped("cross-doc", "source or target missing (reported above)")]
    pattern = manifest.req_id_pattern
    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8")
    cited = set(pattern.findall(source_text))
    defined = set(pattern.findall(target_text))
    results: list[Result] = []
    malformed = sorted(
        {
            token
            for text in (source_text, target_text)
            for token in _REQ_TOKEN_RE.findall(text)
            if not pattern.fullmatch(token)
        }
    )
    if malformed:
        results.append(
            failed(
                "cross-doc",
                "malformed REQ-ID token(s) — the record schemas require "
                "REQ-<LETTERS>-<3 digits>: " + ", ".join(malformed),
            )
        )
    unknown = sorted(cited - defined)
    if unknown:
        results.append(
            failed(
                "cross-doc",
                f"cited in {manifest.design_doc} but not defined in {manifest.prd}: "
                + ", ".join(unknown),
            )
        )
    if not results:
        results.append(
            passed("cross-doc", f"{len(cited)} REQ-ID citation(s), all defined")
        )
    return results


def check_handbook_refs(manifest: Manifest, root: Path) -> list[Result]:
    """Fail each roster file that references a harness-owned handbook document."""
    names = manifest.handbook_denylist
    results = [
        failed(
            "handbook-refs",
            f"{file.relative_to(root)} references harness-owned doc(s): "
            + ", ".join(hits),
        )
        for file in _roster_files(manifest, root)
        if (
            hits := sorted(
                {name for name in names if name in file.read_text(encoding="utf-8")}
            )
        )
    ]
    if not results:
        return [passed("handbook-refs", "no roster file references handbook documents")]
    return results


def _roster_files(manifest: Manifest, root: Path) -> Iterator[Path]:
    for spec in manifest.files:
        path = root / spec.path
        if spec.directory:
            yield from sorted(path.glob("*.md")) if path.is_dir() else ()
        elif path.is_file():
            yield path


def check_handbook_docs_absent(manifest: Manifest, root: Path) -> list[Result]:
    """Fail when docs/ carries a harness-owned handbook document of its own."""
    docs = root / "docs"
    stale = sorted(
        name for name in manifest.handbook_denylist if (docs / name).is_file()
    )
    if stale:
        return [
            failed(
                "handbook-docs",
                "docs/ holds harness-owned handbook doc(s) — remove them; the "
                "harness or its reference repo carries the canonical copy: "
                f"{', '.join(stale)}",
            )
        ]
    return [passed("handbook-docs", "no harness-owned handbook docs in docs/")]


def check_channel_invariants(project: Project) -> list[Result]:
    """Check the channel's runtime invariants: nothing beside the plugin, nothing tracked out-of-band."""
    channel = project.channel
    if channel is None:
        return [skipped("channel", "channel undeclared (reported above)")]
    if channel == "copy":
        return [passed("channel", "copy channel: harness runtime committed by design")]
    extensions = [path.rstrip("/") for path in project.extensions]
    if channel == "marketplace":
        present = _runtime_on_disk(project.root, extensions)
        if present:
            return [
                failed(
                    "channel",
                    f"marketplace channel but {len(present)} runtime file(s) on "
                    f"disk beside the plugin: {', '.join(present[:5])} — these load twice; "
                    "delete the leftovers or declare them as extensions",
                )
            ]
    tracked = _tracked_runtime(project.root)
    if tracked is None:
        return [skipped("channel", "git unavailable; untracked invariant not verified")]
    tracked = [path for path in tracked if not _under_extension(path, extensions)]
    if tracked:
        return [
            failed(
                "channel",
                f"{channel} channel but {len(tracked)} harness runtime file(s) "
                f"tracked: {', '.join(tracked[:5])}",
            )
        ]
    detail = f"{channel} channel: no harness runtime files tracked"
    if extensions:
        detail += f"; {len(extensions)} declared extension(s) kept tracked"
    return [passed("channel", detail)]


def _under_extension(path: str, extensions: Sequence[str]) -> bool:
    return any(path == ext or path.startswith(ext + "/") for ext in extensions)


def _runtime_on_disk(root: Path, extensions: Sequence[str]) -> list[str]:
    # Presence on disk, not git status: an untracked copy loads twice as well.
    return [
        rel
        for base in MARKETPLACE_PLUGIN_PATHS
        for rel in _files_under(root, base)
        if not _under_extension(rel, extensions)
    ]


def _files_under(root: Path, base: str) -> Iterator[str]:
    if not (root / base).exists():
        return
    for path in sorted((root / base).rglob("*")):
        if path.is_file():
            yield path.relative_to(root).as_posix()


def _tracked_runtime(root: Path) -> list[str] | None:
    try:
        listing = subprocess.run(
            ["git", "ls-files", "--", *RUNTIME_PATHS],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [line for line in listing.splitlines() if line.strip()]


def check_reviewer_roster(manifest: Manifest, project: Project) -> list[Result]:
    """Check the reviewer roster: the floor's bodies, each declared extra, and undeclared bodies."""
    spec = manifest.reviewers
    if spec is None:
        return [skipped("reviewer-roster", "manifest declares no [reviewers] floor")]
    fault = project.layout_fault
    if fault is not None:
        rel = manifest.project_data_path
        return [skipped("reviewer-roster", f"{rel} {fault.kind} (reported above)")]
    extras_value = lookup(project.layout, "harness.extra_reviewers")
    names: object = [] if extras_value is None else extras_value
    if not _is_string_list(names):
        return [
            failed(
                "reviewer-roster",
                "harness.extra_reviewers must be a list of reviewer names",
            )
        ]
    extras, results = _declared_extras(spec, names)
    tools, tool_results = _declared_tools(spec, lookup(project.layout, "harness.tools"))
    results.extend(tool_results)
    if not tools:
        # With no surface the body loops run zero times, and a declared,
        # bodyless extra would pass silently.
        results.append(
            failed(
                "reviewer-roster",
                "harness.tools names no known tool surface — reviewer "
                "bodies cannot be checked on any channel; fix the "
                "[harness] tools list",
            )
        )
        return results
    floor_results = _floor_body_results(spec, project, tools)
    if floor_results is None:
        results.append(
            skipped(
                "reviewer-roster",
                "no agent directories present — runtime not materialized in tree",
            )
        )
        return results
    results.extend(floor_results)
    results.extend(_extra_body_results(spec, project, extras, tools))
    results.extend(_undeclared_body_results(spec, project.root, {*spec.floor, *extras}))
    return results


def _declared_extras(
    spec: ReviewerSpec, names: Sequence[str]
) -> tuple[list[str], list[Result]]:
    results = [
        failed(
            "reviewer-roster",
            f"extra reviewer {name!r} must match the *-reviewer naming convention",
        )
        for name in names
        if not spec.name_pattern.match(name)
    ]
    shaped = [name for name in names if spec.name_pattern.match(name)]
    results.extend(
        failed(
            "reviewer-roster",
            f"{name!r} is a floor reviewer and must not be listed in extra_reviewers",
        )
        for name in shaped
        if name in spec.floor
    )
    return [name for name in shaped if name not in spec.floor], results


def _declared_tools(
    spec: ReviewerSpec, value: object
) -> tuple[list[str], list[Result]]:
    # An absent or malformed list means every known surface; an unknown name
    # is a typo, and filtering it silently would let materialize skip that
    # tool while this check passes.
    tools = value if _is_string_list(value) else list(spec.surfaces)
    results = [
        failed(
            "reviewer-roster",
            f"harness.tools names unknown surface {tool!r} — known: {sorted(spec.surfaces)}",
        )
        for tool in tools
        if tool not in spec.surfaces
    ]
    return [tool for tool in tools if tool in spec.surfaces], results


def _floor_body_results(
    spec: ReviewerSpec, project: Project, tools: Sequence[str]
) -> list[Result] | None:
    if project.channel == "marketplace":
        return [
            skipped(
                "reviewer-floor",
                f"marketplace channel: {len(spec.floor)} floor reviewer "
                "bodies ship in the plugin, not the tree",
            )
        ]
    directories = {project.root / spec.surfaces[tool].directory for tool in tools}
    if not any(directory.is_dir() for directory in directories):
        return None
    return [
        _floor_body_result(project.root, spec.surfaces[tool].body_path(name))
        for name in spec.floor
        for tool in tools
    ]


def _floor_body_result(root: Path, expected: str) -> Result:
    if (root / expected).is_file():
        return passed("reviewer-floor", f"{expected} present")
    return failed(
        "reviewer-floor",
        f"floor reviewer body missing: {expected} — the four-reviewer floor is mandatory",
    )


def _extra_body_results(
    spec: ReviewerSpec, project: Project, extras: Sequence[str], tools: Sequence[str]
) -> list[Result]:
    return [
        _extra_body_result(project, spec.surfaces[tool].body_path(name))
        for name in extras
        for tool in tools
    ]


def _extra_body_result(project: Project, expected: str) -> Result:
    if not (project.root / expected).is_file():
        hint = (
            " — extras never ship in a plugin; commit the body project-side"
            if project.channel == "marketplace"
            else ""
        )
        return failed(
            "reviewer-roster", f"extra reviewer body missing: {expected}{hint}"
        )
    if expected not in project.extensions:
        return failed(
            "reviewer-roster",
            f"extra reviewer {expected} not in [harness] "
            "extensions — list it there to declare it "
            "project-owned; on manifest the gitignore "
            "re-include and untracked check also key on "
            "the entry",
        )
    return _extra_body_contract(project.root, expected)


def _extra_body_contract(root: Path, expected: str) -> Result:
    try:
        text = (root / expected).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return failed("reviewer-roster", f"cannot read {expected}: {exc}")
    missing = [token for token in _REQUIRED_REVIEWER_TOKENS if token not in text]
    if missing:
        return failed(
            "reviewer-roster",
            f"extra reviewer {expected} lacks {', '.join(missing)} — "
            "every roster reviewer carries the dispatch-start First Tool "
            "Call stanza and the review-workflow output protocol; without "
            "dispatch-start, truncation detection is blind to this reviewer",
        )
    return passed(
        "reviewer-roster",
        f"{expected} present, kept, and carries the dispatch-event contract",
    )


def _undeclared_body_results(
    spec: ReviewerSpec, root: Path, roster: set[str]
) -> list[Result]:
    # Every known surface is scanned, declared or not: a body in an undeclared
    # surface is exactly the forgotten wiring.
    discovered = {name for name, _path in reviewer_bodies(root, spec.surfaces)}
    return [
        failed(
            "reviewer-roster",
            f"{name!r} agent body present but not in [harness] "
            "extra_reviewers — it will not gate; declare it or remove it",
        )
        for name in sorted(discovered - roster)
    ]


def reviewer_bodies(
    root: Path, surfaces: Mapping[str, AgentSurface]
) -> Iterator[tuple[str, Path]]:
    """Yield every reviewer body in the tree across all known surfaces, with its agent name."""
    for surface in surfaces.values():
        directory = root / surface.directory
        if not directory.is_dir():
            continue
        for child in sorted(directory.iterdir()):
            name = surface.agent_name(child.name) if child.is_file() else None
            if name is not None and name.endswith("-reviewer"):
                yield name, child


def check_reviewer_fresh_eyes(manifest: Manifest, root: Path) -> list[Result]:
    """Fail each reviewer body that instructs reading the implementer's plan."""
    # An in-tree body is project-owned on every channel: on marketplace the
    # floor ships in the plugin, so only extras appear in the tree.
    spec = manifest.reviewers
    if spec is None:
        return [
            skipped("reviewer-fresh-eyes", "manifest declares no [reviewers] floor")
        ]
    results = [
        _fresh_eyes_result(root, body)
        for _name, body in reviewer_bodies(root, spec.surfaces)
    ]
    if not results:
        return [
            skipped(
                "reviewer-fresh-eyes",
                "no reviewer bodies in the tree — runtime not materialized, "
                "or a marketplace project with no extras",
            )
        ]
    return results


def _fresh_eyes_result(root: Path, body: Path) -> Result:
    rel = body.relative_to(root).as_posix()
    text = body.read_text(encoding="utf-8")
    hits = [token for token in _FORBIDDEN_REVIEWER_REFS if token in text]
    if hits:
        return failed(
            "reviewer-fresh-eyes",
            f"{rel!r} references working memory ({', '.join(hits)}) "
            "— a reviewer reads the change set, not the "
            "implementer's plan (fresh-eyes invariant)",
        )
    return passed("reviewer-fresh-eyes", f"{rel!r} reads no working memory")


def check_hook_registration(root: Path, channel: str | None) -> list[Result]:
    """Check that hook scripts and settings matchers agree in both directions."""
    hooks_dir = root / ".claude" / "hooks"
    scripts = _hook_scripts(hooks_dir)
    registrations = _settings_text(root)
    if scripts and not registrations:
        return [
            failed(
                "hook-registration",
                f"{len(scripts)} hook script(s) in .claude/hooks/ but no "
                ".claude/settings.json to register them",
            )
        ]
    results = [_registration_result(name, registrations) for name in scripts]
    results.extend(_matcher_results(registrations, scripts, channel))
    if results:
        return results
    if not hooks_dir.is_dir():
        return [skipped("hook-registration", "no .claude/hooks/ in tree")]
    return [skipped("hook-registration", "no hook scripts in .claude/hooks/")]


def _hook_scripts(hooks_dir: Path) -> list[str]:
    # Hooks are Python; .sh is still recognized for a legacy tree. A test_
    # sibling is a suite, not a hook.
    if not hooks_dir.is_dir():
        return []
    return sorted(
        path.name
        for pattern in ("*.py", "*.sh")
        for path in hooks_dir.glob(pattern)
        if path.is_file() and not path.name.startswith("test_")
    )


def _settings_text(root: Path) -> str:
    text = ""
    for name in ("settings.json", "settings.local.json"):
        path = root / ".claude" / name
        if not path.is_file():
            continue
        try:
            text += path.read_text(encoding="utf-8") + "\n"
        except OSError:
            continue
    return text


def _registration_result(name: str, registrations: str) -> Result:
    # A path segment, not a substring, so allow.py is not masked by handoff-allow.py.
    if "/" + name in registrations:
        return passed("hook-registration", f"{name} registered")
    return failed(
        "hook-registration",
        f"{name} present in .claude/hooks/ but not registered in "
        ".claude/settings.json — the hook never runs; add its "
        "PreToolUse matcher (or remove the script)",
    )


def _matcher_results(
    registrations: str, scripts: Sequence[str], channel: str | None
) -> list[Result]:
    results: list[Result] = []
    for name in sorted(set(_HOOK_MATCHER_RE.findall(registrations))):
        if channel == "marketplace":
            results.append(
                failed(
                    "hook-registration",
                    f"settings registers .claude/hooks/{name} but hooks ship "
                    "in the plugin on the marketplace channel — leftover from "
                    "a channel switch; remove the matcher",
                )
            )
        elif name not in scripts:
            results.append(
                failed(
                    "hook-registration",
                    f"settings registers .claude/hooks/{name} but the script "
                    "is absent — the matcher invokes a nonexistent command on "
                    "every matched tool call; remove it or restore the script",
                )
            )
    return results


class Headings(NamedTuple):
    """The live `## ` headings of a CLAUDE.md: every position, and each title's first position and count."""

    positions: frozenset[int]
    first_at: Mapping[str, int]
    occurrences: Mapping[str, int]


def check_required_chapters(root: Path) -> list[Result]:
    """Check that CLAUDE.md carries each harness-managed chapter once, filled."""
    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        return [failed("required-chapter", "no CLAUDE.md in project root")]
    try:
        lines = claude_md.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [failed("required-chapter", f"cannot read CLAUDE.md: {exc}")]
    headings = _live_headings(lines)
    return [_chapter_result(title, headings, lines) for title in REQUIRED_CHAPTERS]


def _live_headings(lines: Sequence[str]) -> Headings:
    first_at: dict[str, int] = {}
    occurrences: dict[str, int] = {}
    positions: set[int] = set()
    for index, line in unfenced_lines(lines):
        if line.startswith("## "):
            positions.add(index)
            first_at.setdefault(line, index)
            occurrences[line] = occurrences.get(line, 0) + 1
    return Headings(frozenset(positions), first_at, occurrences)


def _chapter_result(title: str, headings: Headings, lines: Sequence[str]) -> Result:
    start = headings.first_at.get(title)
    if start is None:
        return failed(
            "required-chapter", f"CLAUDE.md has no '{title}' chapter — run /materialize"
        )
    if headings.occurrences[title] > 1:
        return failed(
            "required-chapter",
            f"CLAUDE.md has {headings.occurrences[title]} '{title}' chapters — keep one (run /materialize)",
        )
    end = min(
        (index for index in headings.positions if index > start), default=len(lines)
    )
    if not any(line.strip() for line in lines[start + 1 : end]):
        return failed(
            "required-chapter", f"'{title}' chapter is empty — run /materialize"
        )
    return passed("required-chapter", f"'{title}' present and filled")


def check_harness_stamp(root: Path) -> list[Result]:
    """Check that CLAUDE.md carries one well-formed harness date stamp."""
    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        return [failed("harness-stamp", "no CLAUDE.md in project root")]
    try:
        # read_text would translate CRLF away and hide the case below.
        raw = claude_md.read_bytes()
        stamps = _stamp_lines(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return [failed("harness-stamp", f"cannot read CLAUDE.md: {exc}")]
    if not stamps:
        return [_absent_stamp_result(raw)]
    if len(stamps) > 1:
        return [
            failed(
                "harness-stamp",
                f"CLAUDE.md has {len(stamps)} harness stamps — keep one (run /materialize)",
            )
        ]
    match = STAMP_WELL_FORMED.match(stamps[0].strip())
    if not match:
        return [
            failed(
                "harness-stamp",
                "CLAUDE.md harness stamp is malformed — expected "
                "'<!-- harness: <YYYY-MM-DD> -->' (run /materialize)",
            )
        ]
    return [passed("harness-stamp", f"harness stamp present: {match.group(1)}")]


def _stamp_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if STAMP_LINE.match(line.lstrip())]


def _absent_stamp_result(raw: bytes) -> Result:
    # The chapter refresh refuses a CRLF file, so a stamp-less CRLF CLAUDE.md
    # needs the line-ending fix, not another materialize.
    if b"\r\n" in raw:
        return failed(
            "harness-stamp",
            "CLAUDE.md has CRLF line endings — normalize to LF, then run /materialize",
        )
    return failed(
        "harness-stamp",
        "CLAUDE.md has no '<!-- harness: <YYYY-MM-DD> -->' stamp — run /materialize",
    )


def check_layout_module_rules(project: Project) -> list[Result]:
    """Fail when the layout's [[module]] rules would not survive engine load."""
    if not project.layout:
        return [skipped("layout-modules", "no parseable scripts/layout.toml")]
    if not GRADING_AVAILABLE:
        return [skipped("layout-modules", "grading package not importable")]
    try:
        validate_module_rules(project.layout.get("module", []))
    except ValueError as exc:
        return [failed("layout-modules", str(exc))]
    return [passed("layout-modules", "[[module]] rules validate")]


def check_layout_review(project: Project) -> list[Result]:
    """Fail when the layout's merged [review] table would not survive engine load."""
    layout = project.layout
    if not layout:
        return [skipped("layout-review", "no parseable scripts/layout.toml")]
    if not GRADING_AVAILABLE:
        return [skipped("layout-review", "grading package not importable")]
    try:
        defaults = load_stack_defaults(project.layout_file.parent)
    except (ValueError, tomllib.TOMLDecodeError):
        # layout-defaults owns that failure; one FAIL, not two.
        return [
            skipped(
                "layout-review", "stack defaults failed to load; see layout-defaults"
            )
        ]
    try:
        merged = merged_table("review", layout, defaults)
        review = validate_review(merged, _review_roster(layout))
    except ValueError as exc:
        return [failed("layout-review", str(exc))]
    probe = _probe_source(review, layout)
    return [passed("layout-review", f"[review] table validates; probe: {probe}")]


def _review_roster(layout: Table) -> list[str]:
    harness_table = layout.get("harness")
    extras = (
        harness_table.get("extra_reviewers")
        if isinstance(harness_table, dict)
        else None
    )
    declared = extras if isinstance(extras, list) else []
    return [
        *REVIEWERS,
        *(name for name in declared if isinstance(name, str) and name not in REVIEWERS),
    ]


def _probe_source(review: "ReviewConfig", layout: Table) -> str:
    # The engine's merged view, which the project file alone does not show.
    probe = review.security_surface
    table = layout.get("review")
    if not probe:
        return "empty; the security reviewer runs on every high and gray plan"
    if isinstance(table, dict) and "security_surface" in table:
        return f"project override, {len(probe)} patterns"
    return f"stack default, {len(probe)} patterns"


def check_layout_defaults(project: Project) -> list[Result]:
    """Fail when the stack defaults would not load; warn when the layout restates one."""
    if not project.layout:
        return [skipped("layout-defaults", "no parseable scripts/layout.toml")]
    if not GRADING_AVAILABLE:
        return [skipped("layout-defaults", "grading package not importable")]
    scripts_dir = project.layout_file.parent
    if not (scripts_dir / "layout-defaults.toml").is_file():
        return [
            skipped(
                "layout-defaults", "no scripts/layout-defaults.toml (older install)"
            )
        ]
    try:
        defaults = load_stack_defaults(scripts_dir)
    except (ValueError, tomllib.TOMLDecodeError) as exc:
        return [failed("layout-defaults", str(exc))]
    shadowed = shadowed_keys(project.layout, defaults)
    if shadowed:
        return [
            warned(
                "layout-defaults",
                f"layout.toml restates the stack default for {', '.join(shadowed)}; "
                "delete the key to follow upgrades",
            )
        ]
    return [passed("layout-defaults", "stack defaults load; no key shadowed")]


def check_backlog_connector(root: Path) -> list[Result]:
    """Warn when the project-owned backlog connector is absent."""
    if (root / "scripts" / "backlog.sh").is_file():
        return [passed("backlog-connector", "scripts/backlog.sh present")]
    return [
        warned(
            "backlog-connector",
            "scripts/backlog.sh missing — /next ranks from git alone until "
            "/init scaffolds the connector skeleton",
        )
    ]


def check_layout_gate(project: Project) -> list[Result]:
    """Fail when a present [gate] table has the wrong shape."""
    if not project.layout:
        return [skipped("layout-gate", "no parseable scripts/layout.toml")]
    gate = project.layout.get("gate")
    if gate is None:
        return [skipped("layout-gate", "no [gate] table (optional)")]
    if not isinstance(gate, dict):
        return [failed("layout-gate", f"[gate] must be a table (got {gate!r})")]
    problems: list[str] = []
    command = gate.get("command")
    if not (isinstance(command, str) and command.strip()):
        problems.append(f"[gate] command must be a non-empty string (got {command!r})")
    verbs = gate.get("verbs")
    if not (
        isinstance(verbs, list)
        and verbs
        and all(isinstance(verb, str) and verb for verb in verbs)
    ):
        problems.append(
            f"[gate] verbs must be a non-empty list of strings (got {verbs!r})"
        )
    if problems:
        return [failed("layout-gate", problem) for problem in problems]
    return [passed("layout-gate", "[gate] command and verbs validate")]


def check_doc_budgets(manifest: Manifest, project: Project) -> list[Result]:
    """Fail each budgeted doc that exceeds its word ceiling."""
    return [
        _budget_result(spec, spec.budget, project)
        for spec in manifest.files
        if spec.budget is not None and (project.root / spec.path).is_file()
    ]


def _budget_result(spec: FileSpec, budget: Budget, project: Project) -> Result:
    ceiling, source = _budget_ceiling(budget, project.layout)
    words = count_words((project.root / spec.path).read_text(encoding="utf-8"))
    if words <= ceiling:
        return passed("doc-budget", f"{spec.path} {words}/{ceiling} words ({source})")
    remedy = "compact source-owned detail and superseded entries (doc-sync skill § Compaction)"
    if budget.override_key is not None:
        remedy += (
            f", or raise {budget.override_key} in layout.toml [harness] deliberately"
        )
    return failed(
        "doc-budget",
        f"{spec.path} is {words} words, over the {ceiling}-word ceiling "
        f"({source}) — {remedy}",
    )


def _budget_ceiling(budget: Budget, layout: Table) -> tuple[int, str]:
    key = budget.override_key
    override = None if key is None else lookup(layout, key)
    if isinstance(override, int) and not isinstance(override, bool) and override > 0:
        return override, f"override {key}={override}"
    return budget.max_words, "default"


def check_field_tables(manifest: Manifest, root: Path) -> list[Result]:
    """Fail when the design doc carries a field or parameter table outside a code fence."""
    rel = manifest.design_doc
    path = root / rel
    if not path.is_file():
        return [skipped("field-tables", f"{rel} missing (reported above)")]
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = [
        index + 1
        for index, line in unfenced_lines(lines)
        if _FIELD_TABLE_HEADER.match(line)
    ]
    if hits:
        shown = ", ".join(str(number) for number in hits[:5])
        return [
            failed(
                "field-tables",
                f"{rel} has {len(hits)} field/parameter table(s) (line(s) {shown}) — "
                "source is authoritative for field lists; replace each with a one-line "
                "purpose summary plus a source pointer (document-writing § Prohibited "
                "Patterns)",
            )
        ]
    return [passed("field-tables", f"{rel}: no field/parameter tables")]


def check_req_acceptance(manifest: Manifest, root: Path) -> list[Result]:
    """Fail each PRD requirement id that never appears in a list item."""
    rel = manifest.prd
    path = root / rel
    if not path.is_file():
        return [skipped("req-acceptance", f"{rel} missing (reported above)")]
    in_bullet: set[str] = set()
    anywhere: set[str] = set()
    for _index, line in unfenced_lines(path.read_text(encoding="utf-8").splitlines()):
        ids = manifest.req_id_pattern.findall(line)
        anywhere.update(ids)
        if _BULLET_RE.match(line):
            in_bullet.update(ids)
    orphans = sorted(anywhere - in_bullet)
    if orphans:
        return [
            failed(
                "req-acceptance",
                f"{rel}: {len(orphans)} requirement(s) mentioned only in prose, with no "
                f'"Done when" acceptance bullet: {", ".join(orphans[:5])} — give each a '
                "tagged list item stating its bounded, testable contract",
            )
        ]
    return [
        passed(
            "req-acceptance",
            f"{rel}: all {len(anywhere)} requirement(s) carry an acceptance bullet",
        )
    ]


def check_legacy_plugin_keys(root: Path) -> list[Result]:
    """Warn when a settings file still registers the plugin under the retired marketplace name."""
    findings = [
        finding
        for name in ("settings.json", "settings.local.json")
        for finding in _legacy_keys(root / ".claude" / name)
    ]
    if not findings:
        return [passed("legacy-keys", "no pre-v0.2.0 registration keys")]
    return [
        warned(
            "legacy-keys",
            f"pre-v0.2.0 key(s): {'; '.join(findings)} — migrate once: remove "
            f"the {LEGACY_MARKETPLACE} marketplace, add agent-team, reinstall "
            "the plugin, re-run marketplace-setup (adoption guide § Upgrading)",
        )
    ]


def _legacy_keys(settings: Path) -> list[str]:
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    findings: list[str] = []
    enabled = data.get("enabledPlugins")
    if isinstance(enabled, dict):
        findings.extend(
            f"{settings.name}: {key}"
            for key in enabled
            if isinstance(key, str) and key.endswith("@" + LEGACY_MARKETPLACE)
        )
    markets = data.get("extraKnownMarketplaces")
    if isinstance(markets, dict) and LEGACY_MARKETPLACE in markets:
        findings.append(f"{settings.name}: extraKnownMarketplaces.{LEGACY_MARKETPLACE}")
    return findings


def check_version_skew(root: Path, version_date_file: Path) -> list[Result]:
    """Warn when the CLAUDE.md stamp and the plugin's VERSION-DATE disagree."""
    try:
        plugin_date = _plugin_date(version_date_file)
        stamp_date = _stamp_date(root)
    except ValueError as exc:
        return [skipped("version-skew", str(exc))]
    if stamp_date == plugin_date:
        return [
            passed("version-skew", f"project engines and plugin agree: {plugin_date}")
        ]
    return [
        warned(
            "version-skew",
            f"project engines stamped {stamp_date}, plugin is {plugin_date} — "
            + _skew_hint(stamp_date, plugin_date),
        )
    ]


def _plugin_date(version_date_file: Path) -> str:
    try:
        first_line = version_date_file.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read {version_date_file}: {exc}") from exc
    plugin_date = first_line.strip()
    if not _ISO_DATE_RE.fullmatch(plugin_date):
        raise ValueError(f"{version_date_file} carries no YYYY-MM-DD first line")
    return plugin_date


def _stamp_date(root: Path) -> str:
    try:
        stamps = _stamp_lines((root / "CLAUDE.md").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(
            "no readable CLAUDE.md stamp to compare (harness-stamp reports it)"
        ) from exc
    match = STAMP_WELL_FORMED.match(stamps[0].strip()) if len(stamps) == 1 else None
    if match is None:
        raise ValueError(
            "no well-formed CLAUDE.md stamp to compare (harness-stamp reports it)"
        )
    return match.group(1)


def _skew_hint(stamp_date: str, plugin_date: str) -> str:
    # ISO dates order lexically, so the hint names the stale side.
    if stamp_date < plugin_date:
        return (
            "the plugin updated without a setup re-run; re-run the "
            "marketplace-setup skill so the engine sliver and managed "
            "chapters match the plugin surfaces"
        )
    return (
        "the project engines are newer than the plugin — update the "
        "plugin from the marketplace, then re-run the "
        "marketplace-setup skill"
    )


def run(
    project_root: Path,
    manifest_path: Path,
    plugin_version_date: Path | None = None,
) -> list[Result]:
    """Run every check over a project and return the rows in report order."""
    manifest = read_manifest(manifest_path)
    project = read_project(manifest, project_root)
    root = project.root
    results = check_project_data(manifest, project)
    for spec in manifest.files:
        results.extend(check_file_entry(spec, root))
    results.extend(check_layout_module_rules(project))
    results.extend(check_layout_review(project))
    results.extend(check_layout_defaults(project))
    results.extend(check_layout_gate(project))
    results.extend(check_backlog_connector(root))
    results.extend(check_doc_budgets(manifest, project))
    results.extend(check_field_tables(manifest, root))
    results.extend(check_req_acceptance(manifest, root))
    results.extend(check_cross_doc(manifest, root))
    results.extend(check_handbook_refs(manifest, root))
    results.extend(check_handbook_docs_absent(manifest, root))
    results.extend(check_channel_invariants(project))
    results.extend(check_reviewer_roster(manifest, project))
    results.extend(check_reviewer_fresh_eyes(manifest, root))
    results.extend(check_hook_registration(root, project.channel))
    results.extend(check_legacy_plugin_keys(root))
    results.extend(check_required_chapters(root))
    results.extend(check_harness_stamp(root))
    results.extend(_version_skew_results(project, plugin_version_date))
    return results


def _version_skew_results(project: Project, explicit: Path | None) -> list[Result]:
    version_date_file = explicit or _plugin_version_date_from_environment()
    if version_date_file is not None:
        return check_version_skew(project.root, version_date_file)
    if project.channel == "marketplace":
        return [
            skipped(
                "version-skew",
                "not checked: pass --plugin-version-date (the plugin doctor "
                "skill does) to compare engine and plugin dates",
            )
        ]
    return []


def _plugin_version_date_from_environment() -> Path | None:
    # A plugin skill that forgot the flag still has the plugin root in its
    # environment; a marketplace run then reports a visible row.
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root:
        return None
    candidate = Path(plugin_root) / "VERSION-DATE"
    return candidate if candidate.is_file() else None


def render_report(results: Sequence[Result], *, as_json: bool) -> str:
    """Render the rows for the terminal, or as JSON."""
    if as_json:
        return json.dumps([result._asdict() for result in results], indent=2)
    # A detail may quote a key from a project-tree file; strip control bytes
    # before the terminal render.
    lines = "".join(
        f"{result.status:4} {result.check}: {_CONTROL_RE.sub('', result.detail)}\n"
        for result in results
    )
    failures = sum(1 for result in results if result.status == FAIL)
    return f"{lines}\n{failures} failure(s), {len(results)} check(s)"


def main(argv: list[str] | None = None) -> int:
    """Run the doctor from the command line and return its exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--project-root", type=Path, default=Path())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--plugin-version-date",
        type=Path,
        default=None,
        help="marketplace channel: the plugin's VERSION-DATE "
        "file; compared to the CLAUDE.md stamp, advisory "
        "WARN on mismatch",
    )
    args = parser.parse_args(argv)
    try:
        results = run(
            args.project_root.resolve(), args.manifest, args.plugin_version_date
        )
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError, re.error) as exc:
        sys.stderr.write(f"doctor: {exc}\n")
        return 2
    print(render_report(results, as_json=args.json))
    return 1 if any(result.status == FAIL for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
