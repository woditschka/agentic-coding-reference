"""Plan a review pass: the risk ladder over the change set, the slice history, and the prior round.

A pure policy over the grading context; the two git reads a fix cycle needs are injected.
"""

import posixpath
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, NamedTuple, TypeAlias

from .config import REVIEWERS, Layout, Raw, ReviewConfig
from .features import ReviewKind, review_kind

Pass: TypeAlias = Literal["first", "fix"]
Risk: TypeAlias = Literal["low", "high", "gray"]
Scope: TypeAlias = Literal["full-diff", "fix-delta"]
Records: TypeAlias = Sequence[tuple[int, Raw]]
DeltaReader = Callable[[object, object], "Raw | None"]
TreeFilesReader = Callable[[object, object], "list[str] | None"]

SECURITY_REVIEWER = "security-reviewer"
NOISY_RETRIES = 2
SURFACE_KINDS = frozenset({"docs", "test", "config"})
# The harness's own runtime tree is trust surface whatever its file
# extension: agent instructions render as prompts, schemas and layout config
# drive the gates. A fix-round escape into it takes the cold full read.
RUNTIME_PREFIXES = (".claude/", ".github/", ".opencode/", "schemas/", "scripts/")
# An open finding's quality-bar clause implicates one reviewer's dimension, so
# a fix cycle re-runs that reviewer even when its own verdict was approved.
BAR_CLAUSE_REVIEWER = {
    "secure-by-design": SECURITY_REVIEWER,
    "operationally-honest": "code-quality-reviewer",
    "correct": "test-reviewer",
    "tested-as-spec": "test-reviewer",
    "fit-for-purpose": "code-quality-reviewer",
    "legible-cold": "code-quality-reviewer",
    "consistent-with-codebase": "code-quality-reviewer",
    "spec-grounded": "doc-reviewer",
    "human-maintainable": "doc-reviewer",
}
SECURITY_TRIGGERS = frozenset(
    {"unknown-surface", "sensitive", "binary", "security-surface", "prior-critical"}
)


@dataclass(frozen=True, slots=True)
class OpenFinding:
    """One finding a dissenting review left open, as the fix plan reads it."""

    reviewer: object
    location: object
    tag: object
    bar_clause: object
    severity: object

    @property
    def critical(self) -> bool:
        """Return whether the finding blocks the merge; a blocked finding without a severity fails closed."""
        return self.severity == "critical" or (
            self.tag == "blocked" and not self.severity
        )

    @property
    def path(self) -> str | None:
        """Return the file the location names, before its line, or None for a non-string."""
        if not isinstance(self.location, str):
            return None
        return self.location.split(":", 1)[0]

    @property
    def implicated_reviewer(self) -> str | None:
        """Return the reviewer whose dimension the finding's quality-bar clause names."""
        if not isinstance(self.bar_clause, str):
            return None
        return BAR_CLAUSE_REVIEWER.get(self.bar_clause)

    def as_dict(self) -> Raw:
        """Return the finding as the plan record carries it."""
        return {
            "reviewer": self.reviewer,
            "location": self.location,
            "tag": self.tag,
            "bar_clause": self.bar_clause,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class PlanContext:
    """What the pass about to be planned inherits from the log."""

    pass_: Pass
    prev_tree_sha: object = None
    reviewed_files: tuple[object, ...] | None = ()
    dissenters: tuple[object, ...] = ()
    open_findings: tuple[OpenFinding, ...] = ()

    @property
    def fix_with_dissent(self) -> bool:
        """Return whether the pass is a fix cycle with dissenters to re-run."""
        return self.pass_ == "fix" and bool(self.dissenters)

    @property
    def critical_prior(self) -> bool:
        """Return whether an open finding of the prior round is critical."""
        return any(f.critical for f in self.open_findings)


@dataclass(frozen=True, slots=True)
class Plan:
    """The ladder's answer: the risk, the reviewers, the read scope, and why."""

    risk: Risk
    roster: tuple[str, ...] | None
    scope: Scope
    rationale: str
    triggers: tuple[str, ...]
    open_findings: tuple[OpenFinding, ...] | None = None


@dataclass(frozen=True, slots=True)
class PlanInputs:
    """The facts the ladder judges: the feature row, the history, the context, the layout, the trees."""

    features: Raw
    history: Raw
    context: PlanContext
    layout: Layout
    review: ReviewConfig
    tree_sha: str | None
    base_sha: str | None = None

    @property
    def roster(self) -> tuple[str, ...]:
        """Return the reviewers the layout declares: the floor plus its extras."""
        return self.layout.roster

    def review_kind_of(self, path: str) -> ReviewKind:
        """Classify a path by the review surface it presents."""
        return review_kind(path, self.layout, self.review)


@dataclass(frozen=True, slots=True)
class Delta:
    """The fix delta between the prior plan's tree and the current one."""

    paths: tuple[str, ...]
    kinds: tuple[str, ...]
    sensitive: bool
    binary: bool
    lines: int


class GitReaders(NamedTuple):
    """The two git-backed reads a fix cycle needs, injected by the entry."""

    delta_of: DeltaReader
    tree_files_of: TreeFilesReader


class _CriticalRead(NamedTuple):
    """How the open criticals shape the fix read: cold, the surfaces they sit on, their raisers."""

    cold: bool
    kinds: set[ReviewKind]
    raisers: list[object]


class _DeltaRead(NamedTuple):
    """What the fix delta adds: its triggers, whether it escaped the reviewed surface, the escape's kinds."""

    triggers: list[str]
    escaped: bool
    escape_kinds: set[ReviewKind]


class _FixReads(NamedTuple):
    """The three reads a fix round widens from: the delta, the criticals, the escape."""

    delta: Delta | None
    critical: _CriticalRead
    escape: _DeltaRead


# --- the ladder ---------------------------------------------------------------


def derive_plan(inputs: PlanInputs, readers: GitReaders) -> Plan:
    """Apply the risk ladder and return the plan; every unknown fails closed to high."""
    if inputs.review.mode == "always-full":
        return Plan(
            "high",
            tuple(inputs.roster),
            "full-diff",
            "review.mode = always-full; full battery",
            ("mode-always-full",),
        )
    files = inputs.features.get("files")
    if files is None or inputs.tree_sha is None:
        return Plan(
            "high",
            tuple(inputs.roster),
            "full-diff",
            "diff features unavailable; full battery (fail-closed)",
            ("null-features",),
        )
    if inputs.context.fix_with_dissent:
        return fix_plan(inputs, readers)
    kinds = [inputs.review_kind_of(f["path"]) for f in files]
    triggers = slice_triggers(inputs, kinds)
    if triggers:
        return _high_plan(inputs, kinds, triggers)
    if "prod" not in kinds:
        return _surface_plan(inputs, kinds)
    return Plan(
        "gray",
        None,
        "full-diff",
        "small clean production change; planner judges the roster",
        (),
    )


def slice_triggers(inputs: PlanInputs, kinds: Sequence[str]) -> list[str]:
    """Name the slice-level risks of a pass judged over the accumulated features."""
    features, history, context = inputs.features, inputs.history, inputs.context
    triggers: list[str] = []
    if any(k == "unknown" for k in kinds):
        triggers.append("unknown-surface")
    if features.get("sensitive_paths"):
        triggers.append("sensitive")
    if features.get("binary_files"):
        triggers.append("binary")
    if (features.get("module_count") or 0) > 1:
        triggers.append("multi-module")
    size = (features.get("prod_lines") or 0) + (features.get("test_lines") or 0)
    if size > inputs.review.size_threshold:
        triggers.append("oversize")
    if (history.get("build_retries") or 0) >= NOISY_RETRIES:
        triggers.append("build-retries")
    if (history.get("design_revisions") or 0) >= 1:
        triggers.append("design-revision")
    if context.critical_prior:
        triggers.append("prior-critical")
    if features.get("security_surface_paths"):
        triggers.append("security-surface")
    return triggers


def _high_plan(inputs: PlanInputs, kinds: Sequence[str], triggers: list[str]) -> Plan:
    """Return the full battery, or defer an oversize carried by test lines alone to the planner."""
    features = inputs.features
    prod_lines = features.get("prod_lines")
    if (
        triggers == ["oversize"]
        and prod_lines is not None
        and prod_lines <= inputs.review.size_threshold
    ):
        return Plan(
            "gray",
            None,
            "full-diff",
            "oversize on test lines alone; planner judges the roster",
            tuple(triggers),
        )
    roster = list(inputs.roster)
    rationale = f"risk triggers present ({', '.join(triggers)}); full battery"
    if SECURITY_REVIEWER in roster and not security_relevant(
        triggers, features, kinds, inputs.review
    ):
        roster = [r for r in roster if r != SECURITY_REVIEWER]
        rationale += "; no security surface, security reviewer not dispatched"
    return Plan("high", tuple(roster), "full-diff", rationale, tuple(triggers))


def _surface_plan(inputs: PlanInputs, kinds: Sequence[str]) -> Plan:
    """Scope a non-production change to its surface's reviewers, or fail closed when none maps."""
    picked = surface_roster(kinds, inputs.roster, inputs.review)
    if not picked:
        return Plan(
            "high",
            tuple(inputs.roster),
            "full-diff",
            "changed surface maps to no reviewer; full battery",
            ("no-surface-match",),
        )
    surfaces = ", ".join(sorted(set(kinds)))
    return Plan(
        "low",
        tuple(picked),
        "full-diff",
        f"non-production surface ({surfaces}); reviewers matched to changed surface",
        (),
    )


# --- the fix cycle ------------------------------------------------------------


def fix_plan(inputs: PlanInputs, readers: GitReaders) -> Plan:
    """Re-review a fix: dissenters and implicated reviewers read the delta, or the full roster reads cold."""
    context, roster = inputs.context, list(inputs.roster)
    raw_delta = readers.delta_of(context.prev_tree_sha, inputs.tree_sha)
    delta = None if raw_delta is None else _lift_delta(raw_delta)
    reviewed = context.reviewed_files
    if reviewed is None:
        recomputed = readers.tree_files_of(inputs.base_sha, context.prev_tree_sha)
        reviewed = None if recomputed is None else tuple(recomputed)
    critical = _critical_read(inputs, delta)
    read = _delta_read(inputs, delta, reviewed)
    dissenters = [r for r in roster if r in context.dissenters]
    widened = _widening(inputs, dissenters, _FixReads(delta, critical, read))
    triggers = (["prior-critical"] if critical.cold else []) + read.triggers
    reviewers = [r for r in roster if r in set(dissenters) | set(widened)]
    if triggers:
        return Plan(
            "high",
            tuple(roster),
            "full-diff" if read.escaped else "fix-delta",
            f"fix-cycle risk ({', '.join(triggers)}); full roster",
            tuple(triggers),
            context.open_findings,
        )
    if not reviewers:
        return Plan(
            "high",
            tuple(roster),
            "fix-delta",
            "no roster member among dissenters; full roster (fail-closed)",
            ("no-dissenter-in-roster",),
            context.open_findings,
        )
    return Plan(
        "low",
        tuple(reviewers),
        "fix-delta",
        _low_fix_rationale(widened, critical, read),
        (),
        context.open_findings,
    )


def _widening(inputs: PlanInputs, dissenters: list[str], reads: _FixReads) -> list[str]:
    """Name the approved reviewers a fix round re-runs, in the order the rules add them."""
    roster, context, features = list(inputs.roster), inputs.context, inputs.features
    delta, critical, read = reads
    widened: list[str] = []

    def widen(reviewers: Sequence[object]) -> None:
        for reviewer in reviewers:
            if (
                isinstance(reviewer, str)
                and reviewer in roster
                and reviewer not in dissenters
                and reviewer not in widened
            ):
                widened.append(reviewer)

    widen([f.implicated_reviewer for f in context.open_findings])
    if features.get("sensitive_paths"):
        # A fix in a non-sensitive file can still break behavior the
        # sensitive surface depends on.
        widen([SECURITY_REVIEWER])
    surface = features.get("security_surface_paths") or []
    if delta is not None and any(p in surface for p in delta.paths):
        # Only the security reviewer reads a removed check as a weakened one.
        widen([SECURITY_REVIEWER])
    if critical.kinds and not critical.cold:
        widen(
            critical.raisers
            + surface_roster(sorted(critical.kinds), roster, inputs.review)
        )
    if read.escape_kinds and not read.escaped:
        widen(surface_roster(sorted(read.escape_kinds), roster, inputs.review))
    return widened


def _critical_read(inputs: PlanInputs, delta: Delta | None) -> _CriticalRead:
    """Decide whether the open criticals force the cold full read, or stay scoped to their surface."""
    cold = False
    kinds: set[ReviewKind] = set()
    raisers: list[object] = []
    for finding in inputs.context.open_findings:
        if not finding.critical:
            continue
        if finding.reviewer not in raisers:
            raisers.append(finding.reviewer)
        path = placeable_path(finding.location)
        security_owned = (
            finding.reviewer == SECURITY_REVIEWER
            or finding.implicated_reviewer == SECURITY_REVIEWER
        )
        if security_owned or path is None:
            cold = True
            continue
        kind = inputs.review_kind_of(path)
        if kind in SURFACE_KINDS and not path.startswith(RUNTIME_PREFIXES):
            kinds.add(kind)
        else:
            cold = True
    if kinds and delta is not None and "prod" in delta.kinds:
        cold = True
    return _CriticalRead(cold, kinds, raisers)


def _delta_read(
    inputs: PlanInputs, delta: Delta | None, reviewed: tuple[object, ...] | None
) -> _DeltaRead:
    """Judge the fix delta: its own risks, and whether it escaped the reviewed surface."""
    if delta is None:
        return _DeltaRead(["delta-unavailable"], True, set())
    triggers: list[str] = []
    if delta.sensitive:
        triggers.append("delta-sensitive")
    if delta.binary:
        triggers.append("delta-binary")
    if any(k == "unknown" for k in delta.kinds):
        triggers.append("delta-unknown-surface")
    if delta.lines > inputs.review.size_threshold:
        triggers.append("delta-oversize")
    if reviewed is None:
        # The reviewed surface is unknowable, so containment cannot be judged.
        triggers.append("reviewed-surface-unavailable")
        return _DeltaRead(triggers, True, set())
    allowed = set(reviewed) | {
        f.path for f in inputs.context.open_findings if f.location
    }
    outside = [p for p in delta.paths if p not in allowed]
    if not outside:
        return _DeltaRead(triggers, False, set())
    # An escape confined to docs, test, or config surface widens the pass with
    # that surface's reviewers; one reaching prod, an unclassifiable file, or
    # the harness runtime keeps the cold full read.
    escape_kinds = {inputs.review_kind_of(p) for p in outside}
    if not escape_kinds <= SURFACE_KINDS or any(
        p.startswith(RUNTIME_PREFIXES) for p in outside
    ):
        triggers.append("delta-escaped-surface")
        return _DeltaRead(triggers, True, escape_kinds)
    return _DeltaRead(triggers, False, escape_kinds)


def _low_fix_rationale(
    widened: list[str], critical: _CriticalRead, read: _DeltaRead
) -> str:
    """Word the low plan: what the delta touched and who reads it."""
    note = f" (widened for {', '.join(widened)})" if widened else ""
    if critical.kinds:
        note += f" (prior critical on {', '.join(sorted(critical.kinds))} surface)"
    containment = (
        f"fix delta adds unreviewed {', '.join(sorted(read.escape_kinds))} surface"
        if read.escape_kinds
        else "fix contained to reviewed surface"
    )
    return f"{containment}; dissenters re-review the delta{note}"


def _lift_delta(raw: Raw) -> Delta:
    return Delta(
        tuple(raw["paths"]),
        tuple(raw["kinds"]),
        bool(raw["sensitive"]),
        bool(raw["binary"]),
        raw.get("lines") or 0,
    )


# --- the roster and the paths ---------------------------------------------------


def surface_roster(
    kinds: Sequence[str], roster: Sequence[str], review: ReviewConfig
) -> list[str]:
    """Return the reviewers whose dimension has surface among the kinds, plus every unmapped extra."""
    surface_map = review.surface_reviewers
    mapped = {r for names in surface_map.values() for r in names}
    wanted: set[object] = set()
    for kind in kinds:
        wanted.update(surface_map.get(kind, ()))
    picked = [r for r in roster if r in wanted]
    picked += [r for r in roster if r not in REVIEWERS and r not in mapped]
    return picked


def security_relevant(
    triggers: Sequence[str], features: Raw, kinds: Sequence[str], review: ReviewConfig
) -> bool:
    """Return whether a high plan sized over slice features keeps the security reviewer."""
    if set(triggers) & SECURITY_TRIGGERS:
        return True
    if "config" in kinds:
        return True
    if not review.security_surface:
        return True
    return features.get("security_surface_paths") is None


def placeable_path(location: object) -> str | None:
    """Return a finding location the surface rules may trust, or None for any other shape."""
    if not isinstance(location, str) or any(ch.isspace() for ch in location):
        return None
    path = location.split(":", 1)[0]
    if "\\" in path or path != posixpath.normpath(path):
        return None
    if path.startswith(("/", "..")):
        return None
    return path


# --- the plan context --------------------------------------------------------


def plan_context(records: Records) -> PlanContext:
    """Fold what the coming pass inherits: first or fix, the reviewed surface, the dissent, the open findings."""
    start = cycle_start(records)
    build_pass_line = current_build_pass_line(records)
    previous = _latest_plan_between(records, start, build_pass_line)
    if previous is None:
        return PlanContext("first")
    latest = _latest_feedback(records, start, build_pass_line)
    dissenters, oldest_dissent = _dissent(latest, build_pass_line)
    basis_plan = (
        _latest_plan_between(records, start, oldest_dissent) if dissenters else previous
    )
    basis = (basis_plan or {}).get("basis") or {}
    return PlanContext(
        "fix",
        basis.get("tree_sha"),
        _reviewed_files(basis),
        tuple(dissenters),
        tuple(_open_findings(latest)),
    )


def cycle_start(records: Records) -> int:
    """Return the line of the latest design-block that validly supersedes an earlier one, or 0."""
    by_no = dict(records)
    start = 0
    for no, raw in records:
        if raw.get("type") != "design-block":
            continue
        pointer = raw.get("supersedes_record_at")
        if not isinstance(pointer, int) or isinstance(pointer, bool) or pointer >= no:
            continue
        target = by_no.get(pointer)
        if isinstance(target, dict) and target.get("type") == "design-block":
            start = no
    return start


def current_build_pass_line(records: Records) -> int:
    """Return the latest build-pass line; with none, the line after the slice's last record."""
    build_pass = _latest_of(records, "build-pass")
    if build_pass is not None:
        return build_pass[0]
    return records[-1][0] + 1 if records else 1


def _latest_of(records: Records, record_type: str) -> tuple[int, Raw] | None:
    found: tuple[int, Raw] | None = None
    for no, raw in records:
        if raw.get("type") == record_type:
            found = (no, raw)
    return found


def _latest_plan_between(records: Records, after: int, before: int) -> Raw | None:
    plan: Raw | None = None
    for no, raw in records:
        if raw.get("type") == "review-plan" and after < no < before:
            plan = raw
    return plan


def _latest_feedback(
    records: Records, after: int, before: int
) -> dict[object, tuple[int, Raw]]:
    """Return the latest review-feedback per author in the window, keyed by author."""
    latest: dict[object, tuple[int, Raw]] = {}
    for no, raw in records:
        if after < no < before and raw.get("type") == "review-feedback":
            latest[raw.get("author")] = (no, raw)
    return latest


def _dissent(
    latest: dict[object, tuple[int, Raw]], build_pass_line: int
) -> tuple[list[object], int]:
    """Return the dissenting authors and the line of the oldest dissent."""
    dissenters: list[object] = []
    oldest = build_pass_line
    for author, (no, raw) in latest.items():
        if raw.get("verdict") != "approved":
            dissenters.append(author)
            oldest = min(oldest, no)
    return dissenters, oldest


def _open_findings(latest: dict[object, tuple[int, Raw]]) -> list[OpenFinding]:
    return [
        OpenFinding(
            author,
            finding.get("location"),
            finding.get("tag"),
            finding.get("bar_clause"),
            finding.get("severity"),
        )
        for author, (_no, raw) in latest.items()
        for finding in raw.get("findings", []) or []
        if isinstance(finding, dict)
    ]


def _reviewed_files(basis: Raw) -> tuple[object, ...] | None:
    """Return the basis's reviewed paths; None marks a capped basis whose surface git recomputes."""
    files = basis.get("files")
    if files is None:
        return None
    return tuple(f.get("path") for f in files if isinstance(f, dict))
