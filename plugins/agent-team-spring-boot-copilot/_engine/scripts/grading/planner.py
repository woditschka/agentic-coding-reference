"""grading.planner — the pure risk-ladder for review planning.

Every decision here is a pure function of its inputs: the feature row, the
slice history, the plan context folded from already-loaded log records, the
roster, and the [review] config. The planner calls no gateway — the two
git-backed reads a fix cycle needs (the fix delta, a capped basis's reviewed
surface) are injected by the entry as callables, so the ladder runs no I/O of
its own and every test drives it with plain fakes. (It imports `review_kind`
from `features` for pure classification; the git edges are the injected ones.)

Fail-closed throughout: any null diff feature, unclassifiable surface, noisy
history, or unknowable reviewed surface yields a high plan with the full
roster.

Stdlib only.
"""

from collections.abc import Callable
from typing import Any

from .config import REVIEWERS
from .features import review_kind

# The git-backed reads the entry injects (features.delta_features and
# features.tree_files in production; plain fakes in the planner's tests).
DeltaReader = Callable[[Any, Any, dict[str, Any]], "dict[str, Any] | None"]
TreeFilesReader = Callable[[Any, Any], "list[str] | None"]

# An open finding's quality-bar clause implicates one reviewer's dimension, so a
# fix cycle re-runs that reviewer even when its own verdict was approved — the
# cross-dimension safety net (review-workflow reference.md § Quality-Bar Clause Mapping).
# Deliberately engine-owned and closed to the floor: the bar_clause enum is
# closed in the review-feedback schema, and a declared extra re-enters fix
# rounds through its own dissent, so a clause→extra mapping has no referent.
_BAR_CLAUSE_REVIEWER = {
    "secure-by-design": "security-reviewer",
    "operationally-honest": "security-reviewer",
    "correct": "test-reviewer",
    "tested-as-spec": "test-reviewer",
    "fit-for-purpose": "code-quality-reviewer",
    "legible-cold": "code-quality-reviewer",
    "consistent-with-codebase": "code-quality-reviewer",
    "spec-grounded": "doc-reviewer",
    "human-maintainable": "doc-reviewer",
}


def _loc_path(location: Any) -> str | None:
    """The file path an open finding's `location` names (path before ':line')."""
    if not isinstance(location, str):
        return None
    return location.split(":", 1)[0]


def plan_context(records: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
    """What the pass about to be planned inherits from the log: whether a prior
    plan exists (first vs fix pass), the reviewed surface and tree it covered,
    and the dissenters and open findings of the round being responded to.

    The current build-pass is the anchor: the engine runs right after the
    implementer appends it. A review-plan before that build-pass means an
    earlier round already reviewed this slice, so this is a fix pass. The prior
    review round is the review-feedback between the previous build-pass and the
    current one."""

    def latest(
        rtype: str, before: int | None = None
    ) -> tuple[int, dict[str, Any]] | None:
        match: tuple[int, dict[str, Any]] | None = None
        for no, rec in records:
            if rec.get("type") == rtype and (before is None or no < before):
                match = (no, rec)
        return match

    # A fix pass is one with a prior review-plan *since the latest design-block*
    # (the schema's definition of first vs fix). Bounding by the design-block is
    # load-bearing: a re-triage (superseding design-block + fresh build-pass)
    # starts a new cycle, so the previous cycle's plan must not be read as this
    # pass's prior — that would diff a stale pre-re-triage tree and pull
    # dissenters from the wrong round. Mirrors read_handoff's last_db scoping.
    last_db = 0
    for no, rec in records:
        if rec.get("type") == "design-block":
            last_db = no

    cur_bp = latest("build-pass")
    # The no-build-pass sentinel must live in the same domain as the record
    # numbers — global file line numbers, not this slice's record count. With
    # earlier slices in the log, len(records) + 1 lands below the slice's own
    # lines and silently reads a fix pass as a first pass.
    cur_bp_line = cur_bp[0] if cur_bp else (records[-1][0] + 1 if records else 1)
    prev_plan: dict[str, Any] | None = None
    for no, rec in records:
        if rec.get("type") == "review-plan" and last_db < no < cur_bp_line:
            prev_plan = rec
    if prev_plan is None:
        return {
            "pass": "first",
            "prev_tree_sha": None,
            "reviewed_files": [],
            "dissenters": [],
            "open_findings": [],
            "critical_prior": False,
        }

    prev_bp = latest("build-pass", before=cur_bp_line)
    prev_bp_line = prev_bp[0] if prev_bp else 0
    # The prior review round is the feedback between the previous build-pass and
    # the current one — never reaching across the design-block into an old cycle.
    window_start = max(prev_bp_line, last_db)
    # Latest record per author: a reviewer re-appends after a Gate 4 bounce,
    # and the superseded record must not keep widening the round (the same
    # latest-per-reviewer rule route applies).
    latest_fb: dict[Any, dict[str, Any]] = {}
    for no, rec in records:
        if (
            not (window_start < no < cur_bp_line)
            or rec.get("type") != "review-feedback"
        ):
            continue
        latest_fb[rec.get("author")] = rec
    dissenters: list[Any] = []
    open_findings: list[dict[str, Any]] = []
    critical = False
    for who, rec in latest_fb.items():
        if rec.get("verdict") != "approved" and who not in dissenters:
            dissenters.append(who)
        for finding in rec.get("findings", []) or []:
            if not isinstance(finding, dict):
                continue
            # A blocked finding that omits severity reads as critical:
            # Gate 4 bounces such records, but this engine also runs over
            # logs Gate 4 never validated — fail closed, never narrow.
            if finding.get("severity") == "critical" or (
                finding.get("tag") == "blocked" and not finding.get("severity")
            ):
                critical = True
            open_findings.append(
                {
                    "reviewer": who,
                    "location": finding.get("location"),
                    "tag": finding.get("tag"),
                    "bar_clause": finding.get("bar_clause"),
                    "severity": finding.get("severity"),
                }
            )
    basis = prev_plan.get("basis") or {}
    # files: null means the basis was capped (features._BASIS_FILE_CAP), not
    # that nothing was reviewed — None tells the fix plan to recompute the
    # reviewed surface from git rather than treat every path as escaped.
    bfiles = basis.get("files")
    reviewed = (
        None
        if bfiles is None
        else [f.get("path") for f in bfiles if isinstance(f, dict)]
    )
    return {
        "pass": "fix",
        "prev_tree_sha": basis.get("tree_sha"),
        "reviewed_files": reviewed,
        "dissenters": dissenters,
        "open_findings": open_findings,
        "critical_prior": critical,
    }


def surface_roster(
    kinds: list[str], roster: list[str], cfg: dict[str, Any]
) -> list[str]:
    """Reviewers whose dimension has surface among the changed review kinds,
    in roster order. The kind→reviewer map is `[review] surface_reviewers`
    (defaults in config.SURFACE_REVIEWERS). An extra named anywhere in the
    declared map is surface-scoped like the floor; an unmapped extra always
    joins — its dimension is project-specific with no surface map, so
    including it fails closed rather than silently skipping a declared gate."""
    surface_map = cfg["surface_reviewers"]
    mapped = {r for names in surface_map.values() for r in names}
    want: set[Any] = set()
    for kind in kinds:
        want.update(surface_map.get(kind, ()))
    picked = [r for r in roster if r in want]
    picked += [r for r in roster if r not in REVIEWERS and r not in mapped]
    return picked


def _plan_result(
    risk: str,
    roster: list[str] | None,
    scope: str,
    rationale: str,
    triggers: list[str] | None = None,
    open_findings: Any = None,
) -> dict[str, Any]:
    return {
        "risk": risk,
        "roster": roster,
        "scope": scope,
        "rationale": rationale,
        "triggers": triggers,
        "open_findings": open_findings,
    }


def _derive_fix_plan(
    features: dict[str, Any],
    ctx: dict[str, Any],
    roster: list[str],
    cfg: dict[str, Any],
    tree_sha: Any,
    base_sha: Any,
    delta_of: DeltaReader,
    tree_files_of: TreeFilesReader,
) -> dict[str, Any]:
    """A re-review cycle: dissenters plus bar-clause-implicated reviewers read
    the fix delta; a slice that touched sensitive paths keeps the security
    reviewer aboard every round. The full roster returns only when the delta is
    itself risky — sensitive, binary, unclassifiable, over the size threshold,
    or following a critical finding — and reads cold (full-diff) when the fix
    escaped the reviewed surface or that surface cannot be established.
    Slice-level triggers (oversize, multi-module, sensitive, binary,
    unknown-surface, noisy history) stay out of fix rounds: the first pass's
    full battery already paid the cold full read they demand, and carrying
    them here re-ran it on every round of any large slice (ADR 2026-07-14,
    refining ADR 2026-07-09). A prior plan whose basis
    was capped (files: null) has its reviewed surface recomputed from git
    (base..prev_tree) rather than assumed empty — otherwise every large-slice
    fix would false-fire delta-escaped-surface."""
    delta = delta_of(ctx["prev_tree_sha"], tree_sha, cfg)
    dissenters = [r for r in roster if r in ctx["dissenters"]]
    widened: list[str] = []
    for finding in ctx["open_findings"]:
        who = _BAR_CLAUSE_REVIEWER.get(finding.get("bar_clause"))
        if who and who in roster and who not in dissenters and who not in widened:
            widened.append(who)
    if features.get("sensitive_paths"):
        # Slice-sensitive retention: a fix in a non-sensitive file can still
        # break behavior the sensitive surface depends on, so the security
        # reviewer never leaves a sensitive slice's fix rounds.
        who = "security-reviewer"
        if who in roster and who not in dissenters and who not in widened:
            widened.append(who)
    reviewers = [r for r in roster if r in set(dissenters) | set(widened)]

    reviewed = ctx["reviewed_files"]
    if reviewed is None:
        reviewed = tree_files_of(base_sha, ctx["prev_tree_sha"])

    triggers = ["prior-critical"] if ctx["critical_prior"] else []
    escaped = False
    if delta is None:
        triggers.append("delta-unavailable")
        escaped = True
    else:
        if delta["sensitive"]:
            triggers.append("delta-sensitive")
        if delta["binary"]:
            triggers.append("delta-binary")
        if any(k == "unknown" for k in delta["kinds"]):
            triggers.append("delta-unknown-surface")
        if (delta.get("lines") or 0) > cfg["size_threshold"]:
            triggers.append("delta-oversize")
        if reviewed is None:
            # Capped basis and the recompute failed — the reviewed surface is
            # unknowable, so containment cannot be judged. Fail closed, cold.
            triggers.append("reviewed-surface-unavailable")
            escaped = True
        else:
            allowed = set(reviewed) | {
                _loc_path(f["location"])
                for f in ctx["open_findings"]
                if f.get("location")
            }
            if any(p not in allowed for p in delta["paths"]):
                escaped = True
                triggers.append("delta-escaped-surface")

    if triggers:
        # An escaped or unknowable surface (or an uncomputable delta) needs a
        # cold full read; a risky-but-contained delta gets the full roster
        # over the delta only.
        scope = "full-diff" if escaped else "fix-delta"
        return _plan_result(
            "high",
            list(roster),
            scope,
            f"fix-cycle risk ({', '.join(triggers)}); full roster",
            triggers=triggers,
            open_findings=ctx["open_findings"],
        )
    if not reviewers:
        # Dissenters exist in the log but none maps into the roster (e.g. a
        # record from a since-removed extra reviewer). An empty-roster low
        # plan would read as "nobody reviews" — fail closed instead, like the
        # first-pass no-surface-match branch.
        return _plan_result(
            "high",
            list(roster),
            "fix-delta",
            "no roster member among dissenters; full roster (fail-closed)",
            triggers=["no-dissenter-in-roster"],
            open_findings=ctx["open_findings"],
        )
    note = f" (widened for {', '.join(widened)})" if widened else ""
    return _plan_result(
        "low",
        reviewers,
        "fix-delta",
        f"fix contained to reviewed surface; dissenters re-review the delta{note}",
        triggers=triggers,
        open_findings=ctx["open_findings"],
    )


def derive_plan(
    features: dict[str, Any],
    history: dict[str, Any],
    ctx: dict[str, Any],
    roster: list[str],
    cfg: dict[str, Any],
    tree_sha: Any,
    delta_of: DeltaReader,
    tree_files_of: TreeFilesReader,
    base_sha: Any = None,
) -> dict[str, Any]:
    """Apply the risk ladder to the change set and slice history, returning the
    plan fragment (risk, roster, scope, rationale, triggers). Fail-closed: any
    null diff feature, unclassifiable surface, or noisy history yields high with
    the full roster."""
    files = features.get("files")
    if files is None or tree_sha is None:
        return _plan_result(
            "high",
            list(roster),
            "full-diff",
            "diff features unavailable; full battery (fail-closed)",
            triggers=["null-features"],
        )

    # A fix cycle with real dissenters routes through the delta logic, which
    # sizes risk over the fix delta alone — the slice-level triggers below
    # never reach it. A fix pass with no dissenters left (e.g. an autofix-only
    # round) falls through and is judged over the accumulated slice features:
    # fail-closed, so an oversize slice's autofix round still runs the full
    # battery.
    if ctx["pass"] == "fix" and ctx["dissenters"]:
        return _derive_fix_plan(
            features, ctx, roster, cfg, tree_sha, base_sha, delta_of, tree_files_of
        )

    kinds = [review_kind(f["path"], cfg) for f in files]
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
    if size > cfg["size_threshold"]:
        triggers.append("oversize")
    if (history.get("build_retries") or 0) >= 2:
        triggers.append("build-retries")
    if (history.get("design_revisions") or 0) >= 1:
        triggers.append("design-revision")
    if ctx["critical_prior"]:
        triggers.append("prior-critical")

    if triggers:
        return _plan_result(
            "high",
            list(roster),
            "full-diff",
            f"risk triggers present ({', '.join(triggers)}); full battery",
            triggers=triggers,
        )
    if "prod" not in kinds:
        picked = surface_roster(kinds, roster, cfg)
        if not picked:
            # A non-prod change that maps to no reviewer (no known surface, no
            # extras) has nothing to scope down to — fail closed to the full
            # battery rather than emit a low plan with an empty roster the
            # grader would misread as "nobody reviewed".
            return _plan_result(
                "high",
                list(roster),
                "full-diff",
                "changed surface maps to no reviewer; full battery",
                triggers=["no-surface-match"],
            )
        surfaces = ", ".join(sorted(set(kinds)))
        return _plan_result(
            "low",
            picked,
            "full-diff",
            f"non-production surface ({surfaces}); reviewers matched to changed surface",
            triggers=[],
        )
    return _plan_result(
        "gray",
        None,
        "full-diff",
        "small clean production change; planner judges the roster",
        triggers=[],
    )
