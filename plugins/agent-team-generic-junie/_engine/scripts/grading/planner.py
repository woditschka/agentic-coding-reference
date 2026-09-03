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

import posixpath
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
# The harness's own runtime tree is trust surface whatever its file
# extension: agent instructions render as prompts, schemas and layout config
# drive the gates. review_kind classifies those files as docs or config, so
# without this list a fix-round escape into them would take the surface
# widening instead of the cold full read (ADR 2026-08-07).
_RUNTIME_PREFIXES = (
    ".claude/",
    ".github/",
    ".opencode/",
    ".junie/",
    "schemas/",
    "scripts/",
)

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


def _placeable_path(location: Any) -> str | None:
    """A finding location the surface rules may trust, or None. The location
    is agent-written: only a path that is already in normalized relative form
    (no `..`, no leading `/` or `./`, no whitespace, no backslash) can place
    a critical on a surface. Anything else reads as unplaceable, which the
    caller treats as the cold read — a `docs/../src/main.txt` or a
    `./.claude/x.md` must never widen trust."""
    if not isinstance(location, str) or any(ch.isspace() for ch in location):
        return None
    path = _loc_path(location)
    if path is None or "\\" in path:
        return None
    if path != posixpath.normpath(path) or path.startswith(("/", "..")):
        return None
    return path


def _loc_path(location: Any) -> str | None:
    """The file path an open finding's `location` names (path before ':line')."""
    if not isinstance(location, str):
        return None
    return location.split(":", 1)[0]


def plan_context(records: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
    """What the pass about to be planned inherits from the log: whether a prior
    plan exists (first vs fix pass), the reviewed surface and tree the dissent
    covered, and the cycle's outstanding dissent and open findings.

    The current build-pass is the anchor: the engine runs right after the
    implementer appends it. A review-plan before that build-pass means an
    earlier round already reviewed this slice, so this is a fix pass."""

    def latest(rtype: str) -> tuple[int, dict[str, Any]] | None:
        match: tuple[int, dict[str, Any]] | None = None
        for no, rec in records:
            if rec.get("type") == rtype:
                match = (no, rec)
        return match

    # A fix pass is one with a prior review-plan *in the current review cycle*
    # (the schema's definition of first vs fix). The cycle starts at the latest
    # *superseding* design-block: a re-triage voids the prior cycle's review
    # history, and its design-revision trigger re-runs the full battery. An
    # initial design-block landing mid-slice (a fix-round design record) is not
    # a reset — the review history carries forward, so approvals and dissent
    # survive it (ADR 2026-08-07). The pointer is re-checked in Gate-2 shape
    # before the reset is honored: the router gates a design-block only when it
    # is the latest substantive record, so a mid-turn append can carry a bogus
    # pointer, and a reset on an unvalidated field would let one forged record
    # void outstanding dissent. bool is excluded — True passes isinstance(int).
    by_no = dict(records)
    last_db = 0
    for no, rec in records:
        if rec.get("type") != "design-block":
            continue
        sup = rec.get("supersedes_record_at")
        if not isinstance(sup, int) or isinstance(sup, bool) or sup >= no:
            continue
        target = by_no.get(sup)
        if isinstance(target, dict) and target.get("type") == "design-block":
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

    # Dissent is cycle-wide: the latest review-feedback per reviewer since the
    # cycle start, not the last inter-build-pass window. A round interrupted
    # before its reviews ran (a mid-slice prd-entry or design-block landing
    # between build-passes) must not orphan unresolved dissent — the same
    # latest-verdict-per-reviewer rule route's completion invariant enforces.
    # Latest record per author also covers the Gate 4 bounce: a reviewer
    # re-appends, and the superseded record must not keep widening the round.
    latest_fb: dict[Any, tuple[int, dict[str, Any]]] = {}
    for no, rec in records:
        if not (last_db < no < cur_bp_line) or rec.get("type") != "review-feedback":
            continue
        latest_fb[rec.get("author")] = (no, rec)
    dissenters: list[Any] = []
    oldest_dissent = cur_bp_line
    open_findings: list[dict[str, Any]] = []
    critical = False
    for who, (no, rec) in latest_fb.items():
        if rec.get("verdict") != "approved" and who not in dissenters:
            dissenters.append(who)
            oldest_dissent = min(oldest_dissent, no)
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
    # The basis is the plan governing the round the oldest outstanding dissent
    # spoke in — the latest plan before that feedback line. A dissenter's
    # fix-delta read then always covers everything since it last reviewed,
    # even when an interrupted round left a newer plan whose reviews never
    # ran. With no dissent the latest plan stands (the ladder ignores the
    # basis on that path); a dissent no plan precedes leaves the basis null,
    # which the fix plan fails closed on (delta-unavailable).
    basis_plan: dict[str, Any] | None = None
    for no, rec in records:
        if rec.get("type") == "review-plan" and last_db < no < oldest_dissent:
            basis_plan = rec
    if not dissenters:
        basis_plan = prev_plan
    basis = (basis_plan or {}).get("basis") or {}
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
    escaped the reviewed surface into prod or unclassifiable files, or that
    surface cannot be established. An escape confined to docs/test/config
    surface widens the pass with that surface's reviewers instead
    (ADR 2026-08-07).
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

    reviewed = ctx["reviewed_files"]
    if reviewed is None:
        reviewed = tree_files_of(base_sha, ctx["prev_tree_sha"])

    # prior-critical, scoped to the critical's surface (ADR 2026-07-14,
    # amended 2026-09-03). The cold full read stays for a critical on
    # production code or the harness runtime, one the security reviewer
    # raised or whose clause maps to it, one whose location cannot be placed,
    # and — whatever the critical's surface — a fix delta that touches
    # production code, since the placement owner must re-read moved code. A
    # critical confined to docs, test, or config surface keeps its raiser
    # plus that surface's reviewers, as a delta escape into that surface
    # does. The 98-run v0.3.x replay: 19 prior-critical fix passes, every
    # critical on docs or tests, and the added reviewers returned zero
    # findings; 12 of the 19 become low plans under this rule.
    crit_cold = False
    crit_kinds: set[str] = set()
    crit_raisers: list[Any] = []
    for f in ctx["open_findings"]:
        is_crit = f.get("severity") == "critical" or (
            f.get("tag") == "blocked" and not f.get("severity")
        )
        if not is_crit:
            continue
        raiser = f.get("reviewer")
        if raiser not in crit_raisers:
            crit_raisers.append(raiser)
        path = _placeable_path(f.get("location"))
        security_owned = (
            raiser == "security-reviewer"
            or _BAR_CLAUSE_REVIEWER.get(f.get("bar_clause")) == "security-reviewer"
        )
        if security_owned or path is None:
            crit_cold = True
            continue
        kind = review_kind(path, cfg)
        if kind in ("docs", "test", "config") and not path.startswith(
            _RUNTIME_PREFIXES
        ):
            crit_kinds.add(kind)
        else:
            crit_cold = True
    if ctx["critical_prior"] and not crit_kinds and not crit_cold:
        # The context says critical but no open finding carries it (a log
        # Gate 4 never validated): fail closed to the cold read.
        crit_cold = True
    if crit_kinds and delta is not None and "prod" in delta["kinds"]:
        crit_cold = True
    triggers = ["prior-critical"] if crit_cold else []
    if crit_kinds and not crit_cold:
        for r in crit_raisers + surface_roster(sorted(crit_kinds), roster, cfg):
            if r in roster and r not in dissenters and r not in widened:
                widened.append(r)
    escaped = False
    escape_kinds: set[str] = set()
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
            outside = [p for p in delta["paths"] if p not in allowed]
            if outside:
                # An escape confined to docs/test/config surface widens the
                # pass with that surface's reviewers instead of re-running
                # the full battery cold: the escaped files sit in the fix
                # delta those reviewers read (a fix round routinely adds a
                # PRD bullet or a design-doc note). An escape reaching prod
                # or unclassifiable files — or the harness runtime, whose
                # docs/config-shaped files are trust surface — keeps the
                # fail-closed full read (ADR 2026-08-07).
                escape_kinds = {review_kind(p, cfg) for p in outside}
                if not escape_kinds <= {"docs", "test", "config"} or any(
                    p.startswith(_RUNTIME_PREFIXES) for p in outside
                ):
                    escaped = True
                    triggers.append("delta-escaped-surface")
    if escape_kinds and not escaped:
        for r in surface_roster(sorted(escape_kinds), roster, cfg):
            if r not in dissenters and r not in widened:
                widened.append(r)
    reviewers = [r for r in roster if r in set(dissenters) | set(widened)]

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
    if crit_kinds:
        note += f" (prior critical on {', '.join(sorted(crit_kinds))} surface)"
    containment = (
        f"fix delta adds unreviewed {', '.join(sorted(escape_kinds))} surface"
        if escape_kinds
        else "fix contained to reviewed surface"
    )
    return _plan_result(
        "low",
        reviewers,
        "fix-delta",
        f"{containment}; dissenters re-review the delta{note}",
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
    # round) falls through and is judged over the accumulated slice features,
    # test-only-oversize deferral included: the same slice rules apply on
    # every pass that reads slice features.
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
        # An oversize whose excess sits entirely in test lines is the
        # planner's gray zone, not a forced full battery: added tests raise
        # no security surface, and the planner reads the diff — it may
        # still answer high. Any second trigger keeps the full battery, and
        # so does a null prod_lines — a downgrade never rides an unknown.
        prod_lines = features.get("prod_lines")
        if (
            triggers == ["oversize"]
            and prod_lines is not None
            and prod_lines <= cfg["size_threshold"]
        ):
            return _plan_result(
                "gray",
                None,
                "full-diff",
                "oversize on test lines alone; planner judges the roster",
                triggers=triggers,
            )
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
