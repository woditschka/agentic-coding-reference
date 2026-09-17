#!/usr/bin/env python3
"""Regenerate the derived views from the run folders and the operator notes.

The folders are the ground truth; every view is derived and deterministic,
and --check renders without writing and fails on drift from any committed
view. Every rendered string is scrubbed to stay inert in a terminal.
"""

import datetime
import functools
import itertools
import json
import math
import re
import statistics
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

EVALS = Path(__file__).resolve().parent
RUNS_DIR = EVALS / "results" / "runs"
TASKS_DIR = EVALS / "tasks"
JUDGE_DIR = EVALS / "judge"
TREND = EVALS / "results" / "TREND.md"
TREND_DEV = EVALS / "results" / "TREND-dev.md"
TREND_DATA = EVALS / "results" / "trend-data.json"
NOTES = EVALS / "results" / "notes.toml"

DEV_NOTE = (
    "Local pre-release comparison: the dev rows beside the tagged series."
    " Never committed — `dev-*` run folders and this file are gitignored,"
    " and the battery fails if one is ever tracked. `TREND.md` carries the"
    " tagged series only."
)

INTRO = (
    "The bench measures harness versions, not models: each row installs one"
    " version in a fresh SUT clone, runs the pipeline on every task prompt, and"
    " grades the result. The grade is machine-verified — a held-out oracle plus"
    " the project's full test suite; a refusal task grades by its recorded diff"
    " and the suite. Method, quality bar, and measurement tiers:"
    " [README](../README.md)."
)

# The escalation rule's confirmation depth: the default single rep plus the
# two re-runs the rule adds. A pair whose cells both reach this depth is
# settled, however the reps landed.
ESCALATION_CONFIRMED_REPS = 3

# One table per task, versions newest first, each concern its own column.
TREND_INTRO = (
    "One table per task, its description under the heading and its frozen"
    " prompt under `../tasks/`. Each row is one measured cell — a version"
    " and its reps, newest version first — so the trend reads straight"
    " down; a version without a row is unmeasured. Spend and wall are"
    " delivery figures: the change grader's share nets out proportionally,"
    " and only when the ledger's `grader-verdict` record backs it — a run"
    " without both stays whole-run. Reps links each rep's run page; the"
    " per-rep figures behind a row — each rep's bar verdict, spend, and"
    " delivery wall — sit in the Recorded runs table at the page foot."
)

_TREND_BULLETS = (
    "- Bar reads `cleared/reps`: how many reps cleared the machine-verified"
    " bar — complete, held-out oracle all-pass, suite green. A refusal"
    " task's section states its own inverted bar.",
    "- Outcome, in a refusal section only, names each rep's fate in Reps"
    " order: `refused` is the inverted bar's pass, `refused*` one without"
    " the advisory consultation record, `implemented` means the diff"
    " touched `src/`; otherwise the terminal status.",
    "- Ckpt fills only when a rep missed a checkpoint: each rep's"
    " checkpoints hit over its ladder, in Reps order (README § Checkpoints)"
    " — context only, never part of the bar. Each figure links the rep's"
    " ladder on its run page.",
    "- Cost/pass is the row's whole agent spend over its clearing reps — a"
    " rep below the bar is charged in, contributing nothing. Without a"
    " clearing rep there is no unit cost (`—`).",
    "- Waste is the below-bar reps' spend: the share of the row's spend"
    " that bought no pass.",
    "- Wall is the median delivery wall of the clearing reps — the grader's"
    " serial hop excluded. Without a clearing rep it medians the wasted"
    " reps.",
    "- Δ is the cost-per-pass move against the row below, the previous"
    " measured version. `(model)` marks a move across a change of the"
    " requested root pin — it carries the model condition as well as the"
    " version's, and the note rule never lists the pair; the Sweep spend"
    " Models column names each row's models. A `!` marks a settled"
    " same-pin move past 30% with no explaining note (Settled moves without"
    " a note, below).",
    "- Burn is the median spend per delivery minute over the clearing reps"
    " ($/min): cost of a clearing rep ≈ wall × burn, so a flat burn means"  # noqa: RUF001
    " the cost moved with the pipeline's length, not its price.",
    "- `>=` marks a lower bound: a rep's spend went unrecorded.",
)

# The `~` bullet renders only on a page that can carry an Escalation check
# for it to point at; it joins the trend bullets last.
_PROVISIONAL_BULLET = (
    "- `~` prefixes a provisional figure: the row is an arm of a tripped"
    " escalation pair (Escalation check, below) still under"
    f" {ESCALATION_CONFIRMED_REPS} reps. An arm sheds the mark at that depth;"
    " a thin row whose deltas stay quiet never carries it."
)

_SWEEP_BULLETS = (
    "- Models lists every model the pipeline actually used; the requested pin"
    " binds only the root agent. The pin renders beside a version only when"
    " the record holds that version under more than one pin.",
    "- Tasks counts the row's measured tasks over the page's task count. The"
    " spend columns price one sweep for budgeting — every task run once,"
    " failures included: each task cell contributes its mean spend per rep,"
    " and the row sums those means. They price runs, not passes; judgment"
    " lives in the per-task tables. A task unmeasured in a row adds nothing,"
    " so a row under the full count prices a partial sweep.",
    "- Grading spend reports the netted share (accounted basis), so Agent"
    " spend plus Grading spend approximates the whole-sweep figure; the run"
    " pages break each run out.",
    "- Judge spend is the optional Tier C measurement cost: each cell's mean"
    " over its judged reps only, summed across tasks like the other columns."
    " `—` means the judge did not run.",
)

# The refusal task kind, graded by the recorded diff rather than a held-out
# oracle. The constant lives here because run_eval imports this module.
KIND_REFUSAL = "refusal"

# The result.json schema stamp the runner writes and this reader expects.
RESULT_SCHEMA = 1


@dataclass(frozen=True, slots=True)
class LadderFacts:
    """The recorded facts a checkpoint ladder is derived from."""

    kind: str
    status: str
    files_changed: int | None
    src_files_changed: int | None
    suite_green: bool | None
    oracle_tests: dict[str, str]
    consultations: int


def checkpoint_ladder(facts: LadderFacts) -> list[tuple[str, bool]]:
    """Derive the task kind's graded checkpoint ladder, a missing fact reading as not hit."""
    # The refusal ladder's consultation step reads the agent-authored ledger
    # and never enters the bar.
    if facts.kind == KIND_REFUSAL:
        return [
            ("agent complete", facts.status == "complete"),
            ("no src change", facts.src_files_changed == 0),
            ("suite green", facts.suite_green is True),
            ("consultation recorded", facts.consultations > 0),
        ]
    steps = [
        ("agent complete", facts.status == "complete"),
        ("change produced", bool(facts.files_changed)),
        ("suite green", facts.suite_green is True),
    ]
    steps += [
        (name, outcome == "passed")
        for name, outcome in sorted(facts.oracle_tests.items())
    ]
    return steps


# The judge facet roster in render order; the runner and the rubric contract
# test import it from here.
JUDGE_FACETS = ("design_fit", "test_quality", "maintainability", "doc_fit")


@dataclass(frozen=True)
class DefectProbe:
    """A named defect a task declares: a pattern over the added lines of its diff, optionally guarded."""

    # The probe is deterministic context over every run on record, never
    # part of the bar.

    id: str
    description: str
    added: re.Pattern[str]
    guard: re.Pattern[str] | None
    # Path prefix the probe reads; "" reads every changed file. A probe over
    # production code names its root so a doc that quotes the pattern never
    # counts.
    files: str = ""


def _probe_from_entry(manifest: Path, entry: object) -> DefectProbe:
    """Parse one `[[defect]]` table, refusing any malformed field by name."""
    if not isinstance(entry, dict):
        raise TypeError(f"{manifest}: [[defect]] entries must be tables")
    probe_id = entry.get("id")
    added = entry.get("added")
    guard = entry.get("guard")
    files = entry.get("files", "")
    if not isinstance(files, str):
        raise TypeError(
            f"{manifest}: [[defect]] {probe_id}: files must be a path prefix"
        )
    if not isinstance(probe_id, str) or not probe_id:
        raise ValueError(f"{manifest}: [[defect]] id must be a non-empty string")
    if not isinstance(added, str) or not added:
        raise ValueError(f"{manifest}: [[defect]] {probe_id}: added must be a regex")
    if guard is not None and not isinstance(guard, str):
        raise TypeError(f"{manifest}: [[defect]] {probe_id}: guard must be a regex")
    try:
        return DefectProbe(
            id=probe_id,
            description=str(entry.get("description", "")),
            added=re.compile(added),
            guard=re.compile(guard) if guard else None,
            files=files,
        )
    except re.error as error:
        raise ValueError(
            f"{manifest}: [[defect]] {probe_id}: invalid regex: {error}"
        ) from None


def load_defect_probes(
    tasks_dir: Path | None = None,
) -> dict[str, tuple[DefectProbe, ...]]:
    """Load each task's declared probes from its task.toml, failing loud on a malformed one."""
    # A missing directory is not memoized: one created later must be read.
    resolved = (tasks_dir or TASKS_DIR).resolve()
    if not resolved.is_dir():
        return {}
    return _read_defect_probes(resolved)


@functools.cache
def _read_defect_probes(tasks_dir: Path) -> dict[str, tuple[DefectProbe, ...]]:
    """Read every task's probes beneath one resolved tasks directory."""
    # A silently dropped probe would read as a clean history.
    probes: dict[str, tuple[DefectProbe, ...]] = {}
    for manifest in sorted(tasks_dir.glob("*/task.toml")):
        raw = tomllib.loads(manifest.read_text(encoding="utf-8"))
        declared = raw.get("defect") or []
        if not isinstance(declared, list):
            raise TypeError(f"{manifest}: [[defect]] must be an array of tables")
        loaded = tuple(_probe_from_entry(manifest, entry) for entry in declared)
        if loaded:
            probes[manifest.parent.name] = loaded
    return probes


def _added_lines_by_file(patch: str) -> dict[str, list[str]]:
    """Return the added lines per changed file, keyed by the `+++ b/` header path."""
    # A `+++ ` line is a header only directly after its `--- ` partner,
    # outside any hunk; inside a hunk an added line beginning `++ ` is content.
    files: dict[str, list[str]] = {}
    current: str | None = None
    after_minus = False
    for line in patch.splitlines():
        if line.startswith("diff "):
            current = None
            after_minus = False
            continue
        if line.startswith("--- ") and current is None:
            after_minus = True
            continue
        if line.startswith("+++ ") and after_minus:
            after_minus = False
            target = line[4:].strip()
            current = None if target == "/dev/null" else target.removeprefix("b/")
            if current is not None:
                files.setdefault(current, [])
            continue
        after_minus = False
        if line.startswith("+") and current is not None:
            files[current].append(line[1:])
    return files


def _under(path: str, prefix: str) -> bool:
    """Tell whether path sits under the directory prefix names, an empty prefix matching every path."""
    if not prefix:
        return True
    root = prefix.rstrip("/")
    return path == root or path.startswith(root + "/")


def defect_hits(patch: str, probes: tuple[DefectProbe, ...]) -> dict[str, bool]:
    """Judge each probe against the recorded diff: an added match with no guard added in the same file."""
    # Only added lines count, so a defect the diff removes or leaves
    # untouched is not the change's; the guard is file-scoped.
    by_file = _added_lines_by_file(patch)
    hits: dict[str, bool] = {}
    for probe in probes:
        hit = False
        for path, lines in by_file.items():
            if not _under(path, probe.files):
                continue
            present = any(probe.added.search(line) for line in lines)
            guarded = probe.guard is not None and any(
                probe.guard.search(line) for line in lines
            )
            if present and not guarded:
                hit = True
                break
        hits[probe.id] = hit
    return hits


# Control bytes, escape sequences, table syntax, code-span backticks, and
# direction-control, zero-width, or line/paragraph-separator characters have
# no place in a cell — a backtick in agent-influenced content could close
# the span the renderer wraps it in, a bidi override reorders rendered text,
# and U+2028/29 visually split a line mid-string in terminals and on GitHub.
_CELL_UNSAFE = re.compile(
    r"[\x00-\x1f\x7f-\x9f|`\u200b-\u200f\u2028-\u202e\u2066-\u2069\ufeff]+"
)

# A GitHub owner/name slug and a URL-safe branch name. A run-folder field
# failing the shape renders as plain text, never inside a link target.
_REPO_SLUG = re.compile(r"^[\w.-]+/[\w.-]+\Z")
_BRANCH_SAFE = re.compile(r"^[\w./-]+\Z")
# A `.` or `..` path segment inside a URL normalizes to a different target;
# a repo or branch carrying one renders as plain text, never as a link.
_DOT_SEGMENT = re.compile(r"(?:^|/)\.+(?:/|\Z)")
# A relative link target assembled from on-disk names. Every segment starts
# with a word character — no traversal, no hidden dirs, no scheme, no
# separators beyond `/` — or the name renders as plain text.
_LINK_SAFE = re.compile(r"^\w[\w.-]*(?:/\w[\w.-]*)*\Z")


def finite(value: object) -> float | None:
    """Return a usable number from an agent-influenceable record, or None."""
    # A JSON `true` is not a dollar, and json.loads accepts bare NaN and
    # Infinity, which must not poison arithmetic or abort the corpus render.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def scrub(text: str) -> str:
    """Neutralize agent-influenceable bytes before they land in markdown or a terminal."""
    return _CELL_UNSAFE.sub(" ", text).strip()


@dataclass(frozen=True)
class Run:
    """One measured run, loaded from its folder's records."""

    folder: str  # run-folder path relative to results/, "" when unknown
    rep: int
    epoch: str
    sut_repo: str
    sut_branch: str
    version: str
    model_requested: str
    task: str
    task_kind: str
    task_title: str
    started: str
    status: str
    oracle_ok: bool | None
    oracle_tests: dict[str, str]
    suite_green: bool | None
    suite_green_base: bool | None
    files_changed: int | None
    src_files_changed: int | None
    consultations: int
    models: tuple[str, ...]
    cost: float | None
    accounted_cost: float | None
    judge_cost: float | None
    wall: float | None
    judge_median: dict[str, float] | None
    judge_rubric: str | None
    judge_model: str | None
    # The change grader's accounted share, 0.0 when no grader transcript
    # was recorded — the netting below then subtracts nothing.
    grading_spend: float = 0.0
    grading_seconds: float = 0.0
    # The ledger's grader verdict (Tier B, the system under test's
    # self-assessment) — concordance context only, never a claim.
    grader_verdict: str | None = None
    # The run's condition, from the manifest: the executing tool version and
    # the operator-injected settings-env prep lines. The page spans
    # conditions rather than partitioning by them, and calls a span out.
    cc_version: str = ""
    env_prep: tuple[str, ...] = ()
    # Whether prep applied the era contract: the
    # arm ran its version's own era files and entry. A follow-up sweep of
    # such a cell must carry the flag, or its reps land under a different
    # condition than the pair it re-runs.
    era_contract: bool = False
    # The task fingerprint from the manifest. A clarifying prompt edit keeps
    # the task id, so one task's runs may span
    # fingerprints; the task section calls a span out, never silently mixes.
    fingerprint: str = ""
    # The runner-recorded post-session routing decision; None on runs
    # recorded before the field existed.
    route_decision: str | None = None
    # The session completed while the pipeline still owed work — a stall,
    # not a capability failure. Derived at load time (`run_stalled`).
    stalled: bool = False
    # Named-defect probe results over the recorded change.patch (probe id →
    # hit); None when the task declares no probe or the run kept no patch.
    known_defects: dict[str, bool] | None = None

    @property
    def agent_spend(self) -> float:
        """Return the delivery cost with the change grader's share netted out proportionally."""
        # The self-report and the accounting price the run differently, so a
        # cross-basis subtraction would over-net; the fraction is capped at 1.
        # The CLI self-report is preferred; the accounted figure covers crashes.
        total = self.cost if self.cost is not None else (self.accounted_cost or 0.0)
        if self.grading_spend <= 0 or not self.accounted_cost:
            return total
        fraction = min(self.grading_spend / self.accounted_cost, 1.0)
        return total * (1.0 - fraction)

    @property
    def delivery_wall(self) -> float | None:
        """Return the wall minus the grader's serial terminal hop, or None unrecorded."""
        if self.wall is None:
            return None
        return max(self.wall - self.grading_seconds, 0.0)

    @property
    def spend_known(self) -> bool:
        """Tell whether any cost source recorded a spend for the rep."""
        return self.cost is not None or self.accounted_cost is not None

    @property
    def cleared(self) -> bool:
        """Judge the machine-verified bar, fail-closed on any missing fact."""
        # A red pristine baseline gets no waiver: it makes the bar unreachable
        # and the sweep loudly worthless until the SUT base is fixed. A refusal
        # task's bar reads the recorded diff instead of an oracle.
        if self.task_kind == KIND_REFUSAL:
            return (
                self.status == "complete"
                and self.suite_green is True
                and self.src_files_changed == 0
            )
        return (
            self.status == "complete"
            and self.oracle_ok is True
            and self.suite_green is True
        )

    def checkpoints(self) -> tuple[int, int]:
        """Return (hit, total) on the kind's checkpoint ladder."""
        steps = checkpoint_ladder(
            LadderFacts(
                self.task_kind,
                self.status,
                self.files_changed,
                self.src_files_changed,
                self.suite_green,
                self.oracle_tests,
                self.consultations,
            )
        )
        return sum(1 for _name, hit in steps if hit), len(steps)


def _str_or_none(value: object) -> str | None:
    """Return a record's string value, or None for any other type."""
    return value if isinstance(value, str) else None


def _int_or_none(value: object) -> int | None:
    """Return a record's integer value, or None for a bool or any other type."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _bool_or_none(value: object) -> bool | None:
    """Return a record's boolean value, or None for any other type."""
    return value if isinstance(value, bool) else None


def _table(record: dict[str, object], key: str) -> dict[str, object]:
    """Return the object under key, or {} when it is absent or not an object."""
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    """Return a record's list value, or [] when it is not a list."""
    return value if isinstance(value, list) else []


def _judge_median(value: object) -> dict[str, float] | None:
    """Return the recorded facet medians as numbers, or None when any is malformed."""
    if not isinstance(value, dict):
        return None
    medians: dict[str, float] = {}
    for facet, score in value.items():
        number = finite(score)
        if number is None:
            return None
        medians[str(facet)] = number
    return medians or None


def _read_json(path: Path) -> dict[str, object] | None:
    """Parse one JSON object file, or None when it is absent, malformed, or not an object."""
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if isinstance(loaded, dict):
        return loaded
    # A run must never vanish from the trend silently.
    _warn(f"warning: {path.name} is not a JSON object, skipped", path.parent)
    return None


def _folder_grading(folder: Path) -> "tuple[str | None, GradingShare | None]":
    """Return the folder's ledger verdict and the grader share it backs."""
    # A cost row without a backing verdict record does not count as grading.
    verdict = ledger_grader_verdict(folder)
    grading = None
    if verdict:
        grading = grading_figures(_read_json(folder / "agent-costs.json"))
    return verdict, grading


def _known_defects(
    folder: Path, task_id: str, probes_by_task: dict[str, tuple[DefectProbe, ...]]
) -> dict[str, bool] | None:
    """Probe the folder's recorded patch, or None without probes or a patch."""
    patch_path = folder / "change.patch"
    if task_id not in probes_by_task or not patch_path.is_file():
        return None
    return defect_hits(
        patch_path.read_text(encoding="utf-8", errors="replace"),
        probes_by_task[task_id],
    )


def _warn(message: str, folder: Path) -> None:
    """Report one loading note on stderr, naming the run folder."""
    rel = folder.relative_to(RUNS_DIR.parent).as_posix()
    print(f"{message}: {rel}", file=sys.stderr)


def _run_from_folder(
    folder: Path, probes_by_task: dict[str, tuple[DefectProbe, ...]]
) -> Run | None:
    """Load one run folder's records into a Run, or None when they are unreadable."""
    result = _read_json(folder / "result.json")
    manifest = _read_json(folder / "manifest.json")
    if result is None or manifest is None:
        return None
    stamp = result.get("schema")
    if stamp != RESULT_SCHEMA:
        _warn(
            f"warning: result schema {stamp!r} != expected {RESULT_SCHEMA};"
            " fields this reader does not know may go unrendered",
            folder,
        )
    oracle = _table(result, "oracle")
    agent = _table(result, "agent")
    judge = _table(result, "quality_judge")
    diff = _table(result, "diff")
    pipeline = _table(result, "pipeline")
    task = _table(manifest, "task")
    sut = _table(manifest, "sut")
    tests_raw = oracle.get("tests")
    oracle_tests = (
        {str(name): str(outcome) for name, outcome in tests_raw.items()}
        if isinstance(tests_raw, dict)
        else {}
    )
    judge_median = _judge_median(judge.get("median"))
    if judge.get("median") is not None and judge_median is None:
        _warn(
            "warning: malformed judge median, row renders unjudged"
            " while its judge cost still enters Judge spend",
            folder,
        )
    verdict, grading = _folder_grading(folder)
    task_id = str(task.get("id", "unknown"))
    route = _str_or_none(pipeline.get("route_decision"))
    outcome = Outcome(
        kind=str(task.get("kind", "")),
        status=str(result.get("status", "error")),
        oracle_ok=oracle.get("oracle_passed"),
        route=route,
    )
    return Run(
        folder=folder.relative_to(RUNS_DIR.parent).as_posix(),
        rep=_int_or_none(manifest.get("rep")) or 0,
        epoch=str(sut.get("sha", "unknown")),
        sut_repo=str(sut.get("repo", "")),
        sut_branch=str(sut.get("branch", "")),
        version=str(_table(manifest, "version").get("label", folder.parent.name)),
        model_requested=str(manifest.get("model_requested", "(default)")),
        task=task_id,
        task_kind=outcome.kind,
        task_title=str(task.get("title", "")),
        started=str(manifest.get("started", "")),
        status=outcome.status,
        oracle_ok=_bool_or_none(oracle.get("oracle_passed")),
        oracle_tests=oracle_tests,
        suite_green=_bool_or_none(oracle.get("suite_green")),
        suite_green_base=_bool_or_none(oracle.get("suite_green_base")),
        files_changed=_int_or_none(diff.get("files_changed")),
        src_files_changed=_int_or_none(diff.get("src_files_changed")),
        consultations=_int_or_none(pipeline.get("consultation_requests")) or 0,
        models=tuple(sorted(str(m) for m in _list(agent.get("models")))),
        cost=finite(agent.get("total_cost_usd")),
        accounted_cost=finite(_table(agent, "accounted").get("cost")),
        judge_cost=finite(judge.get("cost_usd")),
        wall=finite(result.get("wall_seconds")),
        judge_median=judge_median,
        judge_rubric=_str_or_none(judge.get("rubric")),
        judge_model=_str_or_none(judge.get("model")),
        grading_spend=grading.spend if grading else 0.0,
        grading_seconds=grading.seconds if grading else 0.0,
        grader_verdict=verdict,
        cc_version=_str_or_none(manifest.get("cc_version")) or "",
        env_prep=_env_prep(manifest.get("prep")),
        era_contract=_era_contract(manifest.get("prep")),
        fingerprint=_str_or_none(task.get("fingerprint")) or "",
        route_decision=route,
        known_defects=_known_defects(folder, task_id, probes_by_task),
        stalled=run_stalled(outcome, folder),
    )


def load_runs() -> list[Run]:
    """Load every measured run folder on record."""
    if not RUNS_DIR.is_dir():
        return []
    probes_by_task = load_defect_probes()
    # A folder without result.json renders nowhere; a silent skip would
    # contradict the every-run-persists rule.
    for manifest_path in sorted(RUNS_DIR.glob("*/*/manifest.json")):
        if not (manifest_path.parent / "result.json").is_file():
            _warn("note: run folder without result.json, skipped", manifest_path.parent)
    runs = [
        _run_from_folder(result_path.parent, probes_by_task)
        for result_path in sorted(RUNS_DIR.glob("*/*/result.json"))
    ]
    return [run for run in runs if run is not None]


@dataclass(frozen=True, slots=True)
class Outcome:
    """The recorded outcome facts a stall verdict reads."""

    kind: str
    status: str
    oracle_ok: object
    route: str | None


def run_stalled(outcome: Outcome, folder: Path) -> bool:
    """Tell whether a complete non-refusal run ended with pipeline work still owed."""
    # The runner-recorded route decision is authoritative. Older records
    # read the copied ledger: a non-empty ledger with no implementer terminal
    # record ended before implementation, so a mid-review stall on an old
    # record stays unlabeled rather than guessed.
    if (
        outcome.kind == KIND_REFUSAL
        or outcome.status != "complete"
        or outcome.oracle_ok is True
    ):
        return False
    if outcome.route is not None:
        return outcome.route == "dispatch"
    records = ledger_records(folder)
    if not records:
        return False
    return not any(
        record.get("type") in ("build-pass", "build-failure") for record in records
    )


def _env_prep(prep: object) -> tuple[str, ...]:
    """Return the operator-injected settings-env lines of a manifest's prep array."""
    if not isinstance(prep, list):
        return ()
    return tuple(
        sorted(
            line
            for line in prep
            if isinstance(line, str) and line.startswith("settings.json: env")
        )
    )


def _era_contract(prep: object) -> bool:
    """Tell whether the manifest's prep array records the era contract."""
    return isinstance(prep, list) and any(
        isinstance(line, str) and line.startswith("era contract:") for line in prep
    )


_NOTE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}\Z")
_NOTE_KEYS = frozenset({"date", "text", "task", "version", "model"})


class NotesError(ValueError):
    """A defect in the hand-authored notes file, phrased for the operator."""


@dataclass(frozen=True)
class Note:
    """One dated operator note, optionally scoped to a task, a cell, or a pin."""

    # task places the note under that task's table; version narrows it to a
    # cell; model narrows its explaining power to one pin's rows. Figures
    # never come from notes.

    date: str
    text: str
    task: str | None = None
    version: str | None = None
    model: str | None = None


def _note_date(value: object, where: str) -> str:
    """Return the note's date as YYYY-MM-DD, refusing a datetime or an impossible day."""
    if type(value) is datetime.date:
        return value.isoformat()
    if isinstance(value, str) and _NOTE_DATE.match(value):
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise NotesError(f"{where} needs a real calendar date") from None
        return value
    raise NotesError(f"{where} needs a calendar date (YYYY-MM-DD)")


def load_notes() -> tuple[Note, ...]:
    """Load the operator notes, refusing a malformed entry rather than misplacing prose."""
    if not NOTES.is_file():
        return ()
    try:
        data = tomllib.loads(NOTES.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise NotesError(f"{NOTES.name}: {error}") from error
    entries = data.pop("note", [])
    if data:
        raise NotesError(f"{NOTES.name}: unknown top-level keys {sorted(data)}")
    if not isinstance(entries, list):
        raise NotesError(f"{NOTES.name}: `note` must be an array of tables")
    return tuple(
        _note_from_entry(entry, f"{NOTES.name}: note {index}")
        for index, entry in enumerate(entries, start=1)
    )


def _scope_field(entry: dict[str, object], key: str, where: str) -> str | None:
    """Return one optional string scope of a note, refusing another type."""
    value = entry.get(key)
    if value is not None and not isinstance(value, str):
        raise NotesError(f"{where}: {key} must be a string")
    return value


def _note_from_entry(entry: object, where: str) -> Note:
    """Parse one note table, refusing any malformed field by name."""
    if not isinstance(entry, dict):
        raise NotesError(f"{where} is not a table")
    unknown = sorted(set(entry) - _NOTE_KEYS)
    if unknown:
        raise NotesError(f"{where} has unknown keys {unknown}")
    text = entry.get("text")
    if not isinstance(text, str) or not text.strip():
        raise NotesError(f"{where} needs a non-empty text")
    task = _scope_field(entry, "task", where)
    version = _scope_field(entry, "version", where)
    model = _scope_field(entry, "model", where)
    if version is not None and task is None:
        raise NotesError(f"{where} scopes a version without a task")
    if model is not None and task is None:
        raise NotesError(f"{where} scopes a model without a task")
    return Note(
        date=_note_date(entry.get("date"), where),
        text=text,
        task=task,
        version=version,
        model=model,
    )


def validate_notes(notes: tuple[Note, ...], runs: list[Run]) -> None:
    """Refuse a scoped note that names no recorded task, cell, or pin."""
    tasks = {r.task for r in runs}
    cells = {(r.task, r.version) for r in runs}
    pins = {r.model_requested for r in runs}
    for note in notes:
        if note.task is not None and note.task not in tasks:
            raise NotesError(f"{NOTES.name}: no recorded task {note.task!r}")
        if note.version is not None and (note.task, note.version) not in cells:
            raise NotesError(
                f"{NOTES.name}: no recorded cell {note.task!r} / {note.version!r}"
            )
        if note.model is not None and note.model not in pins:
            raise NotesError(f"{NOTES.name}: no recorded pin {note.model!r}")


def version_key(label: str) -> tuple[int, tuple[int, ...] | str]:
    """Return the sort key placing tagged versions numerically before other labels."""
    if label.startswith("v") and all(part.isdigit() for part in label[1:].split(".")):
        return (0, tuple(int(part) for part in label[1:].split(".")))
    return (1, label)


def bar_cell(cell_runs: list[Run], *, provisional: bool = False) -> str:
    """Render the Bar cell: reps cleared over reps run."""
    n = len(cell_runs)
    cleared = sum(1 for r in cell_runs if r.cleared)
    mark = "~" if provisional else ""
    return f"{mark}{cleared}/{n}"


def _spend_bound(cell_runs: list[Run]) -> str:
    """Return the `>=` lower-bound marker when any rep's spend went unrecorded."""
    return ">=" if any(not r.spend_known for r in cell_runs) else ""


def cost_cell(cell_runs: list[Run], *, provisional: bool = False) -> str:
    """Render the Cost/pass cell, the same figure the escalation trigger compares."""
    unit = _unit_cost(cell_runs)
    if unit is None:
        return "—"
    mark = "~" if provisional else ""
    return f"{mark}{_spend_bound(cell_runs)}${unit:.2f}"


def burn_cell(cell_runs: list[Run]) -> str:
    """Render the median spend per delivery minute over the clearing reps."""
    # A median of per-rep ratios, so one slow rep cannot move the figure
    # through the denominator.
    rates = [
        r.agent_spend / (r.delivery_wall / 60)
        for r in cell_runs
        if r.cleared and r.spend_known and r.delivery_wall
    ]
    return f"${statistics.median(rates):.2f}" if rates else "—"


def delta_cell(
    cell_runs: list[Run],
    prev_runs: list[Run] | None,
    *,
    flagged: bool = False,
    pin_change: bool = False,
) -> str:
    """Render the cost-per-pass move against the previous measured version's cell."""
    if prev_runs is None:
        return ""
    cur, prev = _unit_cost(cell_runs), _unit_cost(prev_runs)
    if cur is None or prev is None or prev == 0:
        return "—"
    move = f"{(cur - prev) / prev * 100:+.0f}%"
    if pin_change:
        return f"{move} (model)"
    return f"{move} !" if flagged else move


def waste_cell(cell_runs: list[Run]) -> str:
    """Render the below-bar reps' spend, blank when every rep cleared."""
    wasted = [r for r in cell_runs if not r.cleared]
    if not wasted:
        return ""
    return f"{_spend_bound(wasted)}${sum(r.agent_spend for r in wasted):.2f}"


def wall_cell(cell_runs: list[Run], *, provisional: bool = False) -> str:
    """Render the median delivery wall of the clearing reps, or of the wasted reps without one."""
    mark = "~" if provisional else ""
    pool = [r for r in cell_runs if r.cleared] or cell_runs
    walls = [r.delivery_wall for r in pool if r.delivery_wall is not None]
    return f"{mark}{statistics.median(walls) / 60:.0f}m" if walls else f"{mark}?m"


def outcome_cell(cell_runs: list[Run]) -> str:
    """Render each rep's fate in Reps order for a refusal section."""

    def fate(r: Run) -> str:
        if r.cleared:
            return "refused" if r.consultations else "refused*"
        if r.status != "complete":
            return scrub(r.status) or "?"
        if r.src_files_changed:
            return "implemented"
        if r.suite_green is False:
            return "suite red"
        return "?"

    return " · ".join(fate(r) for r in cell_runs)


def ckpt_cell(cell_runs: list[Run]) -> str:
    """Render each rep's checkpoints over its ladder, blank when every rep hit them all."""
    # The spread stays visible, never medianed away, so a stopped rep is
    # identifiable from the cell.
    marks = [r.checkpoints() for r in cell_runs]
    if all(hit == total for hit, total in marks):
        return ""
    figures = []
    for r, (hit, total) in zip(cell_runs, marks, strict=True):
        label = f"{hit}/{total}"
        if r.folder and _LINK_SAFE.match(r.folder):
            label = f"[{label}]({r.folder}/README.md#checkpoints)"
        figures.append(label)
    return " · ".join(figures)


# A cost-per-pass move past this share of the earlier cell's figure is not
# believed until re-run.
ESCALATION_COST_MOVE = 0.30


@dataclass(frozen=True)
class Escalation:
    """One cell pair tripping the escalation rule, with its follow-up sweep."""

    pin: str
    task: str
    earlier: str
    later: str
    triggers: tuple[str, ...]
    command: str | None
    bar_flip: bool
    unit_cost_lost: bool
    cost_move: float | None


def _severity(candidate: Escalation) -> tuple[int, int, float]:
    """Return the sort key listing candidates most severe first."""
    # A lost unit cost outranks a bar flip, a flip outranks a cost move, a
    # rise outranks a fall, a larger move a smaller.
    tier = 0 if candidate.unit_cost_lost else 1 if candidate.bar_flip else 2
    move = candidate.cost_move if candidate.cost_move is not None else 0.0
    return (tier, 0 if move > 0 else 1, -abs(move))


def _unit_cost(cell_runs: list[Run]) -> float | None:
    """Return the cell's cost per pass, or None without a clearing rep."""
    cleared = sum(1 for r in cell_runs if r.cleared)
    if not cleared:
        return None
    return sum(r.agent_spend for r in cell_runs) / cleared


def _version_spec(label: str) -> str:
    """Return the --version argument reproducing a recorded label."""
    return "dev" if label.startswith("dev-") else label


# The shape a runnable spec, task id, or pin must hold before it renders as
# executable text in a follow-up command; mirrors the runner's label rule.
_SPEC_SAFE = re.compile(r"^[A-Za-z0-9._-]+\Z")


@dataclass(frozen=True, slots=True)
class CellPair:
    """Two adjacent version cells of one task under one pin."""

    pin: str
    task: str
    earlier: str
    later: str
    cell_a: list[Run]
    cell_b: list[Run]

    @property
    def settled(self) -> bool:
        """Tell whether both arms hold the confirmation depth."""
        return min(len(self.cell_a), len(self.cell_b)) >= ESCALATION_CONFIRMED_REPS

    @property
    def touches_dev(self) -> bool:
        """Tell whether either arm is a dev row."""
        return self.earlier.startswith("dev-") or self.later.startswith("dev-")


def _follow_up_command(pair: CellPair, kind: str, *, era_contract: bool) -> str | None:
    """Render the sweep re-running both arms of a tripped pair, or None when none reproduces it."""
    # Two dev rows collapse to one spec; a label, task id, or pin outside the
    # spec shape never renders as executable text. `(default)` is not a flag
    # value and stays implicit.
    spec_a, spec_b = _version_spec(pair.earlier), _version_spec(pair.later)
    if spec_a == spec_b:
        return None
    model = [] if pair.pin == "(default)" else [pair.pin]
    if not all(_SPEC_SAFE.match(part) for part in [spec_a, spec_b, pair.task, *model]):
        return None
    command = (
        f"python3 evals/run_eval.py --version {spec_a} --version {spec_b}"
        f" --task {pair.task} --reps 2"
    )
    if model:
        command += f" --model {pair.pin}"
    if kind != KIND_REFUSAL:
        command += " --judge"
    if era_contract:
        command += " --era-contract"
    return command


def _adjacent_cells(runs: list[Run]) -> Iterator[CellPair]:
    """Yield each task's adjacent version pairs within one pin."""
    # The one pairing both the escalation queue and the settled-moves check
    # walk, so a pair can never fall between them. A task unmeasured on an
    # intervening row pairs its two nearest measured cells.
    for pin in sorted({run.model_requested for run in runs}):
        pin_runs = [run for run in runs if run.model_requested == pin]
        for task in sorted({run.task for run in pin_runs}):
            task_runs = [run for run in pin_runs if run.task == task]
            versions = sorted({run.version for run in task_runs}, key=version_key)
            for earlier, later in itertools.pairwise(versions):
                yield CellPair(
                    pin,
                    task,
                    earlier,
                    later,
                    [run for run in task_runs if run.version == earlier],
                    [run for run in task_runs if run.version == later],
                )


def _priced_move(
    cell_a: list[Run], cell_b: list[Run]
) -> tuple[float, float, float] | None:
    """Return the pair's over-threshold cost move, or None when it stays under."""
    # A cell whose spend went entirely unrecorded compares as zero and is
    # excluded; the figure measures nothing.
    cost_a, cost_b = _unit_cost(cell_a), _unit_cost(cell_b)
    if cost_a is None or cost_b is None or cost_a <= 0 or cost_b <= 0:
        return None
    move = (cost_b - cost_a) / cost_a
    if abs(move) <= ESCALATION_COST_MOVE:
        return None
    return cost_a, cost_b, move


def escalation_candidates(runs: list[Run]) -> list[Escalation]:
    """List the unsettled pairs tripping the escalation rule, most severe first."""
    candidates = [
        candidate
        for pair in _adjacent_cells(runs)
        if not pair.settled and (candidate := _escalation(pair)) is not None
    ]
    return sorted(candidates, key=_severity)


def _escalation(pair: CellPair) -> Escalation | None:
    """Judge one unsettled pair against the triggers, or None when none trips."""
    cell_a, cell_b = pair.cell_a, pair.cell_b
    triggers: list[str] = []
    cleared_a = sum(1 for run in cell_a if run.cleared)
    cleared_b = sum(1 for run in cell_b if run.cleared)
    flipped = (cleared_a == len(cell_a)) != (cleared_b == len(cell_b))
    if flipped:
        triggers.append(
            f"bar verdict flipped ({cleared_a}/{len(cell_a)}"
            f" → {cleared_b}/{len(cell_b)})"
        )
    cost_move: float | None = None
    priced = _priced_move(cell_a, cell_b)
    if priced is not None:
        cost_a, cost_b, cost_move = priced
        # `>=` mirrors the trend cell, so the trigger never presents a
        # lower bound as a measurement.
        triggers.append(
            f"cost per pass {_spend_bound(cell_a)}${cost_a:.2f}"
            f" → {_spend_bound(cell_b)}${cost_b:.2f} ({cost_move * 100:+.0f}%)"
        )
    lost = _unit_cost(cell_a) is not None and _unit_cost(cell_b) is None
    if lost:
        triggers.append("unit cost lost (no clearing rep)")
    if not triggers:
        return None
    latest = max(cell_a + cell_b, key=lambda run: run.started)
    return Escalation(
        pin=pair.pin,
        task=pair.task,
        earlier=pair.earlier,
        later=pair.later,
        triggers=tuple(triggers),
        command=_follow_up_command(
            pair,
            latest.task_kind,
            era_contract=any(run.era_contract for run in cell_a + cell_b),
        ),
        bar_flip=flipped,
        unit_cost_lost=lost,
        cost_move=cost_move,
    )


def provisional_cells(runs: list[Run]) -> set[tuple[str, str, str]]:
    """Return the cells of tripped, unsettled pairs still under the confirmation depth."""
    depth: dict[tuple[str, str, str], int] = {}
    for r in runs:
        key = (r.model_requested, r.version, r.task)
        depth[key] = depth.get(key, 0) + 1
    thin: set[tuple[str, str, str]] = set()
    for candidate in escalation_candidates(runs):
        for version in (candidate.earlier, candidate.later):
            key = (candidate.pin, version, candidate.task)
            if depth.get(key, 0) < ESCALATION_CONFIRMED_REPS:
                thin.add(key)
    return thin


def _has_comparable_pair(runs: list[Run]) -> bool:
    """Tell whether any (pin, task) cell spans two version rows."""
    by_cell: dict[tuple[str, str], set[str]] = {}
    for r in runs:
        by_cell.setdefault((r.model_requested, r.task), set()).add(r.version)
    return any(len(versions) > 1 for versions in by_cell.values())


ESCALATION_LEGEND = (
    "Derived candidates for the escalation rule, which stays operator-applied"
    " (README § Cost accounting and statistical discipline). A pair of"
    " adjacent version rows sharing pin and task lists while a trigger trips"
    f" and either cell holds fewer than {ESCALATION_CONFIRMED_REPS} reps."
    " Each command re-runs both arms, keeping the added reps adjacent in"
    " time. A `~` row in the trend table is an arm of a listed pair still"
    " under that depth. Pairs list most severe first — a lost unit cost, then"
    " a bar flip, then cost rises, then falls, larger moves first — so the"
    " list reads as a backfill queue."
)


def escalation_section(runs: list[Run]) -> list[str]:
    """Render the trend page's escalation check, omitted without a comparable pair."""
    if not _has_comparable_pair(runs):
        return []
    lines = ["### Escalation check", "", ESCALATION_LEGEND, ""]
    candidates = escalation_candidates(runs)
    if not candidates:
        lines += [
            "No pair trips a trigger, or every tripped pair already holds"
            f" {ESCALATION_CONFIRMED_REPS} reps per arm.",
            "",
        ]
        return lines
    ambiguous = ambiguous_versions(runs)
    for candidate in candidates:
        collides = candidate.earlier in ambiguous or candidate.later in ambiguous
        pin = pin_note(candidate.pin) if collides else ""
        lines.append(
            f"- `{scrub(candidate.task)}` · `{scrub(candidate.earlier)} → {scrub(candidate.later)}`"
            f"{pin}: {', '.join(candidate.triggers)}"
        )
        lines.append(
            f"  `{candidate.command}`"
            if candidate.command
            else "  (no runnable follow-up command for this pair's recorded labels)"
        )
    lines.append("")
    return lines


@dataclass(frozen=True)
class SettledMove:
    """One settled pair whose cost per pass moved past the threshold unexplained."""

    pin: str
    task: str
    earlier: str
    later: str
    cost_a: float
    cost_b: float
    bound_a: str
    bound_b: str
    move: float


def _pair_noted(pair: CellPair, notes: tuple[Note, ...]) -> bool:
    """Tell whether an operator note explains the pair's move."""
    # A note scoped to the task and either version, or task-wide, explains
    # the pair; it must be dated no earlier than the younger cell's first
    # rep, so an old note never mutes a later move, and a model-scoped note
    # explains only its own pin's pairs.
    firsts = [
        min(days)
        for cell in (pair.cell_a, pair.cell_b)
        if (days := [run.started[:10] for run in cell if run.started])
    ]
    born = max(firsts) if firsts else None
    return any(
        note.task == pair.task
        and note.model in (None, pair.pin)
        and note.version in (None, pair.earlier, pair.later)
        and (born is None or note.date >= born)
        for note in notes
    )


def settled_moves_check(
    runs: list[Run], notes: tuple[Note, ...]
) -> tuple[bool, list[SettledMove]]:
    """Return whether any settled pair exists and the settled moves no note explains."""
    # The queue stops listing a pair once both arms reach depth, so without
    # this check a believed-shift-sized move between settled cells never
    # surfaces.
    # A pair touching a dev row never lists and never counts as settled: a
    # pre-release move is resolved by the release decision, not a note.
    settled = [
        pair for pair in _adjacent_cells(runs) if pair.settled and not pair.touches_dev
    ]
    flagged = [
        move
        for pair in settled
        if not _pair_noted(pair, notes) and (move := _settled_move(pair)) is not None
    ]
    flagged.sort(key=lambda move: (0 if move.move > 0 else 1, -abs(move.move)))
    return bool(settled), flagged


def _settled_move(pair: CellPair) -> SettledMove | None:
    """Price one settled pair's move, or None when it stays under the threshold."""
    priced = _priced_move(pair.cell_a, pair.cell_b)
    if priced is None:
        return None
    cost_a, cost_b, move = priced
    return SettledMove(
        pair.pin,
        pair.task,
        pair.earlier,
        pair.later,
        cost_a,
        cost_b,
        _spend_bound(pair.cell_a),
        _spend_bound(pair.cell_b),
        move,
    )


SETTLED_MOVES_LEGEND = (
    "Settled pairs — both arms at the confirmation depth, so the escalation"
    " queue no longer lists them — whose cost per pass moved past"
    f" {ESCALATION_COST_MOVE:.0%} of the earlier cell with no explaining"
    " operator note: one scoped to the task and either of the pair's"
    " versions, or a task-wide condition note; dated no earlier than the"
    " younger cell's first rep (both rows existed when it was written), and"
    " matching the pair's pin when it names a model."
    " The README's rule is the reason this renders: a rise with no named"
    " mechanism is a regression at any percentage. A `>=` figure is a lower"
    " bound — a rep's spend went unrecorded. Dev rows never list: a"
    " pre-release move is resolved by the release decision, not a note."
    " Resolve a row by attributing the move from the committed ledgers and"
    " landing the note; rows list rises before falls, larger moves first."
)


def settled_moves_section(runs: list[Run], notes: tuple[Note, ...]) -> list[str]:
    """Render the settled-moves check, omitted while no settled pair exists."""
    any_settled, flagged = settled_moves_check(runs, notes)
    if not any_settled:
        return []
    lines = ["### Settled moves without a note", "", SETTLED_MOVES_LEGEND, ""]
    if not flagged:
        lines += [
            f"No settled pair moved past {ESCALATION_COST_MOVE:.0%} without"
            " an explaining operator note.",
            "",
        ]
        return lines
    ambiguous = ambiguous_versions(runs)
    for move in flagged:
        collides = move.earlier in ambiguous or move.later in ambiguous
        pin = pin_note(move.pin) if collides else ""
        lines.append(
            f"- `{scrub(move.task)}` · `{scrub(move.earlier)} → {scrub(move.later)}`"
            f"{pin}: cost per pass {move.bound_a}${move.cost_a:.2f}"
            f" → {move.bound_b}${move.cost_b:.2f}"
            f" ({move.move * 100:+.0f}%), no explaining note"
        )
    lines.append("")
    return lines


def escalation_report(runs: list[Run]) -> str:
    """Render the sweep's terminal tail: the escalation candidates as copy-ready commands."""
    if not _has_comparable_pair(runs):
        return ""
    candidates = escalation_candidates(runs)
    if not candidates:
        return "escalation check: no pair trips a trigger"
    ambiguous = ambiguous_versions(runs)
    lines = [
        "Escalation candidates (operator-applied rule, README § Cost"
        " accounting and statistical discipline):"
    ]
    for candidate in candidates:
        collides = candidate.earlier in ambiguous or candidate.later in ambiguous
        pin = pin_note(candidate.pin) if collides else ""
        lines.append(
            f"  {scrub(candidate.task)} ({scrub(candidate.earlier)} → {scrub(candidate.later)}){pin}:"
            f" {', '.join(candidate.triggers)}"
        )
        lines.append(
            f"    {candidate.command}"
            if candidate.command
            else "    (no runnable follow-up command for this pair's recorded labels)"
        )
    return "\n".join(lines)


# The CLI ledger lists `<synthetic>` for locally synthesized turns; it is not
# a model, and the angle brackets vanish as an HTML tag on GitHub.
SYNTHETIC_MODEL = "<synthetic>"


def models_label(models: tuple[str, ...]) -> str:
    """Render a models list, `—` for a record holding only the synthetic entry and `?` for none."""
    real = [m for m in models if m != SYNTHETIC_MODEL]
    if not real:
        return "—" if models else "?"
    return scrub(" · ".join(m.removeprefix("claude-") for m in real))


def rubric_cell(name: str) -> str:
    """Render the rubric as a link into judge/ when a file of exactly that name exists."""
    # Membership is byte-exact against the directory listing: a
    # case-insensitive is_file hit would commit a link that 404s on GitHub.
    on_disk = (
        {p.name for p in JUDGE_DIR.iterdir() if p.is_file()}
        if JUDGE_DIR.is_dir()
        else set()
    )
    if "/" not in name and _LINK_SAFE.match(name) and name in on_disk:
        return f"[{name}](../judge/{name})"
    return scrub(name)


def pin_note(pin: str) -> str:
    """Render the pin note for a row whose pin deviates from the record's norm."""
    if pin == "(default)":
        return " (default pin)"
    return f" (pin {scrub(pin.removeprefix('claude-'))})"


def ambiguous_versions(runs: list[Run]) -> set[str]:
    """Return the versions the record holds under more than one requested pin."""
    pins: dict[str, set[str]] = {}
    for r in runs:
        pins.setdefault(r.version, set()).add(r.model_requested)
    return {v for v, p in pins.items() if len(p) > 1}


def sut_line(runs: list[Run]) -> str:
    """Render where the SUT lives, from the newest manifest on record."""
    latest = max(runs, key=lambda r: r.started)
    repo = scrub(latest.sut_repo)
    branch = scrub(latest.sut_branch)
    if (
        _REPO_SLUG.match(repo)
        and _BRANCH_SAFE.match(branch)
        and not _DOT_SEGMENT.search(f"{repo}/{branch}")
    ):
        line = (
            f"SUT: [`{repo}`](https://github.com/{repo}/tree/{branch}),"
            f" branch `{branch}`"
        )
    else:
        line = f"SUT: `{repo or '?'}`" + (f", branch `{branch}`" if branch else "")
    line += (
        ". A sweep pins the branch head as its base commit;"
        " each run's manifest records the exact SHA."
    )
    bases = len({r.epoch for r in runs})
    if bases > 1:
        line += f" Runs on record span {bases} base commits."
    return line


def _cc_key(value: str) -> tuple[int, ...]:
    """Return the numeric sort key of an executing-tool version's leading token."""
    try:
        return tuple(int(part) for part in value.split(" ", maxsplit=1)[0].split("."))
    except ValueError:
        return ()


def conditions_line(runs: list[Run]) -> str | None:
    """Render the callout for a record spanning tool versions or prep conditions, or None."""
    clauses: list[str] = []
    # Distinct leading tokens, not distinct raw strings: a suffix-only
    # difference is one version. The raw-string tie-break keeps equal-key
    # tokens in one fixed order — set iteration is hash-seed dependent, and
    # a flapping line would fail the derivation gate intermittently.
    cc = sorted(
        {r.cc_version.split(" ")[0] for r in runs if r.cc_version},
        key=lambda token: (_cc_key(token), token),
    )
    if len(cc) > 1:
        clauses.append(
            f"{len(cc)} executing Claude Code versions ({scrub(cc[0])}–{scrub(cc[-1])})"  # noqa: RUF001
        )
    env = {r.env_prep for r in runs}
    if len(env) > 1:
        clauses.append(f"{len(env)} settings-env prep conditions")
    if not clauses:
        return None
    return (
        "Runs on record span "
        + " and ".join(clauses)
        + "; each run's manifest records its own condition."
    )


def _note_text(note: Note) -> str:
    """Render the note as one paragraph, however the TOML author wrapped it."""
    return scrub(" ".join(note.text.split()))


def notes_header_lines(notes: tuple[Note, ...]) -> list[str]:
    """Render the page-level notes block with the unscoped notes as dated bullets."""
    if not notes:
        return []
    lines = [
        "Notes — dated operator commentary recorded in"
        " [`notes.toml`](notes.toml); a scoped note renders under its task."
        " Figures never come from notes; the run folders stay the ground"
        " truth.",
        "",
    ]
    page = sorted((n for n in notes if n.task is None), key=lambda n: n.date)
    if page:
        lines += [f"- {n.date} — {_note_text(n)}" for n in page]
        lines.append("")
    return lines


def task_note_lines(notes: tuple[Note, ...], task: str) -> list[str]:
    """Render the dated bullets under one task's table."""
    scoped = sorted(
        (n for n in notes if n.task == task),
        key=lambda n: (n.date, n.version or ""),
    )
    lines: list[str] = []
    for note in scoped:
        prefix = f"{scrub(note.version)}: " if note.version else ""
        lines.append(f"- {note.date} — {prefix}{_note_text(note)}")
    if lines:
        lines.append("")
    return lines


def unmeasured_note(measured: set[str]) -> str | None:
    """Name the tasks defined on disk but absent from the recorded series, or None."""
    if not TASKS_DIR.is_dir():
        return None
    defined = {path.parent.name for path in TASKS_DIR.glob("*/task.toml")}
    missing = sorted(defined - measured)
    if not missing:
        return None
    names = ", ".join(f"`{scrub(name)}`" for name in missing)
    return f"Defined in `../tasks/` but unmeasured in this series: {names}."


def _row_spend(total: float, bound: str = "") -> str:
    """Render a row spend figure, `$?` when a crafted record overflowed the sum."""
    if not math.isfinite(total):
        return "$?"
    return f"{bound}${total:.2f}"


def _arm_label(version: str, pin: str, ambiguous: set[str]) -> str:
    """Render the row label: the version, with its pin only when the version is ambiguous."""
    return scrub(version) + (pin_note(pin) if version in ambiguous else "")


@dataclass(frozen=True, slots=True)
class _Layout:
    """The row and column order every trend table shares."""

    tasks: list[str]
    arms: list[tuple[str, str]]
    ambiguous: set[str]
    thin: set[tuple[str, str, str]]


def _layout(runs: list[Run]) -> _Layout:
    """Derive the shared table layout: tasks sorted, arms newest first, pin ascending."""
    arms = sorted(
        {(run.version, run.model_requested) for run in runs}, key=lambda a: a[1]
    )
    arms.sort(key=lambda a: version_key(a[0]), reverse=True)
    return _Layout(
        tasks=sorted({run.task for run in runs}),
        arms=arms,
        ambiguous=ambiguous_versions(runs),
        thin=provisional_cells(runs),
    )


def _task_rows(
    runs: list[Run], task: str, arms: list[tuple[str, str]]
) -> list[tuple[str, str, list[Run]]]:
    """Return one task's measured (version, pin, reps) rows in arm order."""
    rows = []
    for version, pin in arms:
        cell_runs = sorted(
            (
                run
                for run in runs
                if run.version == version
                and run.model_requested == pin
                and run.task == task
            ),
            key=lambda run: (run.rep, run.started),
        )
        if cell_runs:
            rows.append((version, pin, cell_runs))
    return rows


def _task_description(runs: list[Run], task: str) -> tuple[str, bool]:
    """Return the task's heading description and whether it is a refusal task."""
    latest = max((run for run in runs if run.task == task), key=lambda run: run.started)
    kind = scrub(latest.task_kind) or "?"
    title = scrub(latest.task_title) or "?"
    description = f"{kind}: {title}"
    refusal = latest.task_kind == KIND_REFUSAL
    if refusal:
        description += (
            " — the expected outcome is a refusal: consult and change"
            " nothing. The bar inverts to complete, suite green, no"
            " `src/` change; whether the run consulted stays an advisory"
            " checkpoint, never part of the bar (README § Refusal tasks)."
        )
    return description, refusal


def _trend_lines(
    runs: list[Run], layout: _Layout, notes: tuple[Note, ...] = ()
) -> list[str]:
    """Render one subsection per task: its heading, then its versions newest first."""
    lines: list[str] = []
    tasks, arms, ambiguous, thin = (
        layout.tasks,
        layout.arms,
        layout.ambiguous,
        layout.thin,
    )
    for task in tasks:
        description, refusal = _task_description(runs, task)
        outcome_head = "Outcome | " if refusal else ""
        unexplained = {
            (move.pin, move.later)
            for move in settled_moves_check(runs, notes)[1]
            if move.task == task
        }
        # A clarifying prompt edit keeps the task id, so one section's runs
        # may span fingerprints. The span is called out like the page-level
        # condition spans, never silently mixed; the dated note records what
        # changed, and each run's manifest records its own fingerprint.
        fingerprints = {r.fingerprint for r in runs if r.task == task and r.fingerprint}
        span_lines = (
            [
                f"Runs on record span {len(fingerprints)} task fingerprints;"
                " a dated note records each prompt change, and each run's"
                " manifest records its own.",
                "",
            ]
            if len(fingerprints) > 1
            else []
        )
        lines += [
            f"#### {scrub(task)}",
            "",
            description,
            "",
            *span_lines,
            f"| Version | Reps | Bar | {outcome_head}Ckpt | Cost/pass | Δ | Burn"
            " | Waste | Wall |",
            "|---" * (10 if refusal else 9) + "|",
        ]
        rows = _task_rows(runs, task, arms)
        for n, (version, pin, cell_runs) in enumerate(rows):
            provisional = (pin, version, task) in thin
            # The previous measured version — the row below. Across a pin
            # change the Δ cell carries the caveat; the `!` rule stays within
            # a pin, as the pairing doctrine holds.
            older = rows[n + 1][2] if n + 1 < len(rows) else None
            pin_change = n + 1 < len(rows) and rows[n + 1][1] != pin
            row = [
                _arm_label(version, pin, ambiguous),
                ", ".join(
                    rep_link(r) + (" (stalled)" if r.stalled else "") for r in cell_runs
                ),
                bar_cell(cell_runs, provisional=provisional),
                *([outcome_cell(cell_runs)] if refusal else []),
                ckpt_cell(cell_runs),
                cost_cell(cell_runs, provisional=provisional),
                delta_cell(
                    cell_runs,
                    older,
                    flagged=(pin, version) in unexplained,
                    pin_change=pin_change,
                ),
                burn_cell(cell_runs),
                waste_cell(cell_runs),
                wall_cell(cell_runs, provisional=provisional),
            ]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines += task_note_lines(notes, task)
    return lines


def _arm_agent_spend(arm_runs: list[Run], tasks: list[str]) -> tuple[str, int]:
    """Return the arm's per-sweep agent spend and the count of tasks it measures."""
    total = 0.0
    bound = ""
    measured = 0
    for task in tasks:
        cell_runs = [r for r in arm_runs if r.task == task]
        if not cell_runs:
            continue
        measured += 1
        if any(not r.spend_known for r in cell_runs):
            bound = ">="
        total += sum(r.agent_spend for r in cell_runs) / len(cell_runs)
    return _row_spend(total, bound), measured


def headline_section(runs: list[Run]) -> list[str]:
    """Render the at-a-glance grid: cost per pass per task down the versions."""
    # The grid carries no sum: a total of per-task figures hides which task
    # moved; the Sweep spend table prices a whole sweep.
    layout = _layout(runs)
    tasks, arms, ambiguous, thin = (
        layout.tasks,
        layout.arms,
        layout.ambiguous,
        layout.thin,
    )
    width = len(tasks) + 1
    lines = [
        "### At a glance",
        "",
        "Cost per pass by task, newest version first — the figure each task"
        " table below carries, read across. `~` is provisional and `>=` a"
        " lower bound as in the tables; an empty cell is an unmeasured task.",
        "",
        "| Version | " + " | ".join(scrub(t) for t in tasks) + " |",
        "|---" * width + "|",
    ]
    for version, pin in arms:
        arm_runs = [
            r for r in runs if r.version == version and r.model_requested == pin
        ]
        cells = []
        for task in tasks:
            cell_runs = [r for r in arm_runs if r.task == task]
            provisional = (pin, version, task) in thin
            cells.append(
                cost_cell(cell_runs, provisional=provisional) if cell_runs else ""
            )
        lines.append(
            "| " + " | ".join([_arm_label(version, pin, ambiguous), *cells]) + " |"
        )
    lines.append("")
    return lines


def _sweep_lines(runs: list[Run], layout: _Layout) -> list[str]:
    """Render the per-version table: resolved models and the sweep spend columns."""
    tasks, arms, ambiguous = layout.tasks, layout.arms, layout.ambiguous
    lines = [
        "| Version | Tasks | Models | Agent spend | Grading spend | Judge spend |",
        "|---" * 6 + "|",
    ]
    for version, pin in arms:
        arm_runs = [
            r for r in runs if r.version == version and r.model_requested == pin
        ]
        resolved = tuple(sorted({m for r in arm_runs for m in r.models}))
        measured = sum(1 for t in tasks if any(r.task == t for r in arm_runs))
        row = [
            _arm_label(version, pin, ambiguous),
            f"{measured}/{len(tasks)}",
            models_label(resolved),
        ]
        # The spend columns are per-sweep figures: each task cell contributes
        # its per-rep mean, so rows with unequal rep depth stay comparable.
        # A rep with unrecorded spend still counts in its cell's denominator,
        # so the row's Agent spend becomes a lower bound (`>=`).
        grading_total = 0.0
        judge_total = 0.0
        judged_any = False
        for task in tasks:
            cell_runs = [r for r in arm_runs if r.task == task]
            if not cell_runs:
                continue
            grading_total += sum(r.grading_spend for r in cell_runs) / len(cell_runs)
            judged_costs = [r.judge_cost for r in cell_runs if r.judge_cost is not None]
            if judged_costs:
                judged_any = True
                judge_total += sum(judged_costs) / len(judged_costs)
        row.append(_arm_agent_spend(arm_runs, tasks)[0])
        row.append(_row_spend(grading_total) if grading_total else "—")
        row.append(_row_spend(judge_total) if judged_any else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines


def table_section(runs: list[Run], notes: tuple[Note, ...] = ()) -> list[str]:
    """Render the trend tables, the sweep spend, the judge medians, and the defect probes."""
    layout = _layout(runs)
    bullets = list(_TREND_BULLETS)
    if _has_comparable_pair(runs):
        bullets.append(_PROVISIONAL_BULLET)
    lines: list[str] = ["### Trend by task", "", *bullets, ""]
    lines += _trend_lines(runs, layout, notes)
    lines += ["### Sweep spend", "", *_SWEEP_BULLETS, ""]
    lines += _sweep_lines(runs, layout)
    lines += _judge_section(runs)
    lines += defect_section(runs)
    return lines


def _judge_section(runs: list[Run]) -> list[str]:
    """Render the advisory judge medians per task and their provenance rows."""
    judged = [run for run in runs if run.judge_median]
    lines: list[str] = []
    if judged:
        lines.append("### Advisory judge medians")
        lines.append("")
        lines.append(
            "Tier C context, never a claim: a blind judge scores each run's"
            " sanitized patch 1–5 per facet, and each score is the median of"  # noqa: RUF001
            " independent samples against the pinned rubric and model. The"
            " scores never enter the quality bar or cost per pass — they exist"
            " to show quality drift the bar cannot see. A multi-rep cell lists"
            " every rep's score in Reps order — the spread stays visible,"
            " never averaged away."
        )
        lines.append("")
        facet_heads = " | ".join(f.replace("_", "-") for f in JUDGE_FACETS)
        judged_rows = sorted(judged, key=lambda r: (r.task, r.started))
        judged_rows.sort(key=lambda r: version_key(r.version), reverse=True)
        # One subsection per judged task, mirroring the trend's per-task
        # split: a task's quality trajectory reads down one short table.
        for task in sorted({r.task for r in judged}):
            lines.append(f"#### {scrub(task)}")
            lines.append("")
            lines.append(f"| Version | Reps | {facet_heads} |")
            lines.append("|---" * (len(JUDGE_FACETS) + 2) + "|")
            cells: dict[str, list[Run]] = {}
            for r in judged_rows:
                if r.task == task:
                    cells.setdefault(scrub(r.version), []).append(r)
            for version, cell_runs in cells.items():
                rep_cell = ", ".join(rep_link(r) for r in cell_runs)
                facet_cells = " | ".join(
                    " · ".join(_facet_score(r, facet) for r in cell_runs)
                    for facet in JUDGE_FACETS
                )
                lines.append(f"| {version} | {rep_cell} | {facet_cells} |")
            lines.append("")
        lines.append(
            "The models behind the judged rows — one row per distinct"
            " provenance: the run's agent models, the pinned judge, the"
            " rubric. A version listed whole shares the row across every"
            " judged rep; a cell judged under two provenances names its"
            " reps, so a rubric or judge change mid-cell stays attributable:"
        )
        lines.append("")
        lines.append("| Judged rows | Agent models | Judge model | Rubric |")
        lines.append("|---" * 4 + "|")
        grouped: dict[tuple[str, str, str], list[Run]] = {}
        for r in judged_rows:
            provenance = (
                models_label(r.models),
                scrub(r.judge_model or "?"),
                rubric_cell(r.judge_rubric or "?"),
            )
            grouped.setdefault(provenance, []).append(r)
        for provenance, members in grouped.items():
            models_cell, judge_model, rubric = provenance
            lines.append(
                f"| {_judged_coverage(members, judged_rows)} | {models_cell}"
                f" | {judge_model} | {rubric} |"
            )
        lines.append("")
    return lines


def defect_section(runs: list[Run]) -> list[str]:
    """Render one named-defect probe table per task that declares a probe."""
    probed = [r for r in runs if r.known_defects is not None]
    if not probed:
        return []
    lines = [
        "### Named-defect probes",
        "",
        "Tier B context, never a claim: each probe is a pattern over the added"
        " lines of the recorded `change.patch`, declared per task in its"
        " `task.toml`, and computed over every run on record. `hit` means the"
        " shipped change carries the named defect; `clear` means it does not."
        " The bar and the cost cells never read it (README § Named-defect"
        " probes).",
        "",
    ]
    # Every rep of a probed task renders, a rep that kept no patch as "—":
    # the cell keeps Reps order and the spread stays visible.
    probed_tasks = {r.task for r in probed}
    rows = sorted(
        (r for r in runs if r.task in probed_tasks), key=lambda r: (r.task, r.started)
    )
    rows.sort(key=lambda r: version_key(r.version), reverse=True)
    for task in sorted(probed_tasks):
        task_rows = [r for r in rows if r.task == task]
        ids = sorted({pid for r in task_rows for pid in (r.known_defects or {})})
        lines.append(f"#### {scrub(task)}")
        lines.append("")
        lines.append("| Version | Reps | " + " | ".join(scrub(i) for i in ids) + " |")
        lines.append("|---" * (len(ids) + 2) + "|")
        cells: dict[str, list[Run]] = {}
        for r in task_rows:
            cells.setdefault(scrub(r.version), []).append(r)
        for version, cell_runs in cells.items():
            rep_cell = ", ".join(rep_link(r) for r in cell_runs)
            probe_cells = " | ".join(
                " · ".join(_defect_cell(r, pid) for r in cell_runs) for pid in ids
            )
            lines.append(f"| {version} | {rep_cell} | {probe_cells} |")
        lines.append("")
    return lines


def _run_defect_lines(manifest: dict[str, object], patch: str | None) -> list[str]:
    """Render the run page's probe table, empty without probes or a patch."""
    task = manifest.get("task")
    task_id = task.get("id") if isinstance(task, dict) else None
    probes = load_defect_probes().get(str(task_id), ()) if task_id else ()
    if not probes or patch is None:
        return []
    hits = defect_hits(patch, probes)
    lines = [
        "",
        "## Named-defect probes",
        "",
        "Tier B context, never part of the bar: a pattern over this run's added"
        " lines, declared in the task's `task.toml` (README § Named-defect probes).",
        "",
        "| probe | result | what it names |",
        "|---|---|---|",
    ]
    for probe in probes:
        verdict = "hit" if hits.get(probe.id) else "clear"
        lines.append(
            f"| `{scrub(probe.id)}` | {verdict} | {scrub(probe.description)} |"
        )
    return lines


def _defect_cell(r: Run, probe_id: str) -> str:
    """Render one rep's result for one probe."""
    hits = r.known_defects or {}
    if probe_id not in hits:
        return "—"
    return "hit" if hits[probe_id] else "clear"


def grader_concordance_section(runs: list[Run]) -> list[str]:
    """Render whether the change grader's verdict tracks the bar or the judge."""
    graded = [r for r in runs if r.grader_verdict]
    if not graded:
        return []
    lines = [
        "### Grader concordance",
        "",
        "Tier B context, never a claim: the change grader's verdict is the"
        " system under test's self-assessment of its own change. The table"
        " asks one question — does a `scrutinize` verdict track the"
        " machine-verified bar or the advisory judge? Judge quality is a"
        " run's mean over its facet medians; the cell holds the median of"
        " those means across the group's judged runs, `—` when the judge"
        " ran on none.",
        "",
        "| Verdict | Runs | Bar cleared | Median judge quality |",
        "|---|---|---|---|",
    ]
    rates: list[tuple[str, float]] = []
    verdicts = {r.grader_verdict for r in graded if r.grader_verdict}
    for verdict in sorted(verdicts, key=lambda v: (GRADE_ORDER.get(v, 2), v)):
        group = [r for r in graded if r.grader_verdict == verdict]
        cleared = sum(1 for r in group if r.cleared)
        quality = [
            statistics.mean(r.judge_median.values()) for r in group if r.judge_median
        ]
        quality_cell = f"{statistics.median(quality):.1f}" if quality else "—"
        lines.append(
            f"| {scrub(verdict)} | {len(group)} | {cleared}/{len(group)}"
            f" | {quality_cell} |"
        )
        rates.append((scrub(verdict), 100 * cleared / len(group)))
    lines.append("")
    if len(rates) > 1:
        spread = max(r for _, r in rates) - min(r for _, r in rates)
        lines.append(
            "Bar clearance by verdict: "
            + ", ".join(f"`{v}` {r:.0f}%" for v, r in rates)
            + f" — a {spread:.0f}-point spread. The verdict tracks the bar"
            " only as far as that spread reaches."
        )
        lines.append("")
    return lines


def _judged_coverage(members: list[Run], judged_rows: list[Run]) -> str:
    """Render a provenance row's coverage at the coarsest attributable grain."""
    ids = {id(r) for r in members}
    items: list[str] = []
    done: set[tuple[str, str | None]] = set()
    for r in members:
        version_runs = [v for v in judged_rows if v.version == r.version]
        if all(id(v) in ids for v in version_runs):
            if (r.version, None) not in done:
                done.add((r.version, None))
                items.append(scrub(r.version))
            continue
        if (r.version, r.task) in done:
            continue
        done.add((r.version, r.task))
        label = f"{scrub(r.version)} {scrub(r.task)}"
        cell_runs = [v for v in version_runs if v.task == r.task]
        if all(id(v) in ids for v in cell_runs):
            items.append(label)
        else:
            in_cell = [m for m in members if id(m) in {id(c) for c in cell_runs}]
            reps = ", ".join(rep_link(m) for m in in_cell)
            items.append(f"{label} ({reps})")
    return ", ".join(items)


def _facet_score(r: Run, facet: str) -> str:
    """Render one rep's facet score, dropping the spurious .0 of an even-sample median."""
    median = r.judge_median or {}
    return f"{median[facet]:g}" if facet in median else "?"


def rep_link(r: Run) -> str:
    """Render the rep label, linked to its run folder when the path holds the link shape."""
    label = scrub(f"r{r.rep}")
    if r.folder and _LINK_SAFE.match(r.folder):
        return f"[{label}]({r.folder}/README.md)"
    return label


def roster_section(runs: list[Run]) -> list[str]:
    """Render the collapsed per-rep table behind every trend cell."""
    plural = "s" if len(runs) != 1 else ""
    lines = [
        "### Recorded runs",
        "",
        "<details>",
        f"<summary>Per-rep detail — {len(runs)} run{plural}, the spread behind"
        " each trend cell</summary>",
        "",
        "Each run folder carries a generated `README.md` presenting the run;"
        " the folder's records are the ground truth. Spend and wall are the"
        " delivery figures the trend cells aggregate. A multi-rep cell lists"
        " every rep's figures in Reps order.",
        "",
        "| Version | Task | Reps | Bar | Spend | Wall |",
        "|---|---|---|---|---|---|",
    ]
    cells = sorted({(r.version, r.task) for r in runs}, key=lambda c: c[1])
    cells.sort(key=lambda c: version_key(c[0]), reverse=True)
    for version, task in cells:
        reps = sorted(
            (r for r in runs if r.version == version and r.task == task),
            key=lambda r: (r.rep, r.started),
        )
        # html_safe, not scrub: these cells sit inside the details
        # block, where a literal `</details>` in a record would close it.
        bars = " · ".join(
            "cleared"
            if r.cleared
            else f"wasted ({'stalled' if r.stalled else html_safe(r.status)})"
            for r in reps
        )
        spends = " · ".join(
            f"${r.agent_spend:.2f}" if r.spend_known else "$?" for r in reps
        )
        walls = " · ".join(
            f"{r.delivery_wall / 60:.0f}m" if r.delivery_wall is not None else "?m"
            for r in reps
        )
        rep_cell = ", ".join(rep_link(r) for r in reps)
        lines.append(
            f"| {html_safe(version)} | {html_safe(task)} | {rep_cell}"
            f" | {bars} | {spends} | {walls} |"
        )
    lines += ["", "</details>", ""]
    return lines


FIGURE_EMBED = (
    '<p align="center">\n'
    '  <img src="../../docs/images/eval-trend.drawio.png" width="720"'
    ' alt="Five aligned panels across every measured harness version:'
    " cost of a clearing rep per task, median delivery wall, burn rate,"
    " share of reps clearing the bar with the known-defect clear rate dashed"
    " beside it, and blind-judge quality as one line"
    ' per rubric facet">\n'
    "</p>\n\n"
    "*The figure is a dated snapshot the `update-diagrams` skill redraws"
    " at story changes; the tables below are the live series.*"
)


def render(
    runs: list[Run],
    note: str | None = None,
    operator_notes: tuple[Note, ...] = (),
    *,
    include_figure: bool = True,
) -> str:
    """Render the trend page for a series of runs."""
    lines = ["# Harness Eval Trend", "", INTRO, ""]
    if note:
        lines += [note, ""]
    if not runs:
        # Page notes still render — only scoped notes need rows, and
        # validation already rejects a scoped note with no recorded cell.
        lines += ["No runs recorded yet.", ""]
        lines += notes_header_lines(operator_notes)
        return "\n".join(lines)
    lines += [sut_line(runs), ""]
    conditions = conditions_line(runs)
    if conditions:
        lines += [conditions, ""]
    if include_figure:
        # The figure and trend-data.json carry the tagged series only, so
        # the dev page embeds neither — its rows are not in either artifact.
        lines += [FIGURE_EMBED, ""]
        lines += [
            "Machine-readable series: [`trend-data.json`](trend-data.json) —"
            " the same cells as the tables below, regenerated with this page.",
            "",
        ]
    lines += headline_section(runs)
    lines += notes_header_lines(operator_notes)
    note = unmeasured_note({r.task for r in runs})
    if note:
        lines += [note, ""]
    lines += [TREND_INTRO, ""]
    lines += table_section(runs, operator_notes)
    lines += grader_concordance_section(runs)
    lines += escalation_section(runs)
    lines += settled_moves_section(runs, operator_notes)
    lines += roster_section(runs)
    return "\n".join(lines)


# The run page's artifact roster in render order; only present files render.
RUN_PAGE_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("change.patch", "the agent's diff against the baseline commit"),
    ("handoff.jsonl", "the pipeline's handoff ledger, one record per line"),
    ("agent-costs.json", "per-agent and per-stage token and dollar figures"),
    ("run.log", "prep, gradle, and diagnostic tails"),
    ("egress.log", "the confinement proxy's per-request access records"),
    ("manifest.json", "pre-run coordinates: prompt, fingerprint, prep steps"),
    ("result.json", "the raw measurement record this page derives from"),
)

_GREEN = "✔"
_RED = "✘"
SHOWN_SUITE_FAILURES = 20
SUITE_FAILURE_CHARS = 160
SHA_CHARS = 12

# Past this many lines the page links the diff or board instead of inlining it.
EMBED_MAX_LINES = 400
# Control bytes have no place in an embedded diff; newline and tab stay —
# unlike the cell scrub, the fence must preserve line structure. Direction
# controls and zero-width characters go the way of the cell scrub: a bidi
# override in an agent-authored patch line would reorder the rendered diff.
_FENCE_UNSAFE = re.compile(
    r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202e\u2066-\u2069\ufeff]+"
)
_BACKTICK_RUN = re.compile(r"`+")
# A markdown fence is three or more backticks; a line indented four or more
# is a code line, never a fence.
FENCE_MIN_BACKTICKS = 3
CODE_INDENT = 4
SECONDS_PER_MINUTE = 60


# A ledger past this is not a real one; the runner imports the same cap.
MAX_LEDGER_BYTES = 5 * 1024 * 1024


def ledger_records(out_dir: Path) -> list[dict[str, object]]:
    """Parse the folder's handoff ledger, reading a missing or oversized file as empty."""
    # A malformed or non-object line is skipped, and the size cap holds
    # even against a file written into the folder by another path.
    ledger = out_dir / "handoff.jsonl"
    if not ledger.is_file() or ledger.stat().st_size > MAX_LEDGER_BYTES:
        return []
    records: list[dict[str, object]] = []
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except (ValueError, RecursionError):  # deeply nested JSON recurses
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


HANDOFF_VIEW = EVALS.parent / "harness" / "core" / "scripts" / "handoff.py"


def render_pipeline(out_dir: Path) -> str | None:
    """Render the pipeline board from the folder's ledger with the current renderer, or None."""
    # One current implementation reads every version's records, so pages
    # stay comparable across the series. --verbose keeps the finding text
    # the terminal board gists; no --layout, so the reviewer matrix derives
    # from the records rather than a config the folder never captured.
    ledger = out_dir / "handoff.jsonl"
    if (
        not HANDOFF_VIEW.is_file()
        or not ledger.is_file()
        or ledger.stat().st_size > MAX_LEDGER_BYTES
    ):
        return None
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(HANDOFF_VIEW),
                "view",
                "--markdown",
                "--verbose",
                "--file",
                str(ledger),
            ],
            capture_output=True,
            text=True,
            cwd=HANDOFF_VIEW.parent,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and proc.stdout.strip() else None


class Approval(NamedTuple):
    """One reviewer's approved aspects, as its review-feedback record lists them."""

    author: str
    aspects: tuple[str, ...]


def reviewer_approvals(out_dir: Path) -> tuple[Approval, ...]:
    """Read what each reviewer approved from the folder's ledger."""
    # The board renders findings only; the approvals are the only record of
    # what was actually checked.
    approvals: list[Approval] = []
    for record in ledger_records(out_dir):
        if record.get("type") != "review-feedback":
            continue
        aspects = record.get("approved_aspects")
        if not isinstance(aspects, list):
            continue
        kept = tuple(a.strip() for a in aspects if isinstance(a, str) and a.strip())
        author = record.get("author")
        if kept:
            approvals.append(Approval(str(author) if author else "?", kept))
    return tuple(approvals)


def html_safe(text: str) -> str:
    """Scrub a string and escape the `<` that could close a surrounding details block."""
    return scrub(text).replace("<", "\\<")


# A gradle test-failure line: `Class > method() FAILED`, possibly nested.
_SUITE_FAIL_RE = re.compile(r"^(\S.* > .*\S) FAILED$", re.MULTILINE)


def failed_suite_tests(out_dir: Path) -> list[str]:
    """List the failing test names of the post-agent suite section of the run log."""
    # Presentation only: agent-authored test stdout prints into the gradle
    # tail at column 0, so a name here can be fabricated. The section is
    # the last marker occurrence, since earlier ones may quote agent output.
    log = out_dir / "run.log"
    if not log.is_file():
        return []
    text = log.read_text(encoding="utf-8", errors="replace")
    marker = "\n=== suite run (post-agent) ===\n"
    start = text.rfind(marker)
    if start < 0:
        return []
    section = text[start + len(marker) :]
    boundary = section.find("\n=== ")
    if boundary >= 0:
        section = section[:boundary]
    return [
        m.group(1)
        for m in _SUITE_FAIL_RE.finditer(section)
        if not m.group(1).startswith("> ")
    ]


# The grade's vocabulary, the reading depth the human owes the change, and
# the words older ledgers carry for it. The reader maps those words at the
# parse boundary, so every derived view speaks one vocabulary while the run
# folders stay as recorded. A word outside the vocabulary is not a grade.
GRADE_SKIM = "skim"
GRADE_SCRUTINIZE = "scrutinize"
GRADE_ORDER = {GRADE_SKIM: 0, GRADE_SCRUTINIZE: 1}
LEGACY_GRADES = {"clear": GRADE_SKIM, "concern": GRADE_SCRUTINIZE}


def ledger_grader_verdict(out_dir: Path) -> str | None:
    """Return the ledger's last grader verdict in the current vocabulary, or None."""
    # The ledger is the authority: a grading cost row without a backing
    # verdict record does not count as grading, so a stray transcript
    # cannot shrink a delivery cell.
    verdict: str | None = None
    for record in ledger_records(out_dir):
        if record.get("type") != "grader-verdict":
            continue
        value = record.get("verdict")
        if isinstance(value, str) and value.strip():
            word = LEGACY_GRADES.get(value.strip(), value.strip())
            verdict = word if word in GRADE_ORDER else None
    return verdict


class GradingShare(NamedTuple):
    """The change grader's accounted share of a run, cells plus raw values."""

    spend_cell: str
    wall_cell: str
    hit_cell: str
    spend: float
    seconds: float


def grading_figures(costs: dict[str, object] | None) -> GradingShare | None:
    """Return the change grader's accounted share, or None without a grader row of finite cost."""
    # The wall subtraction is direct, since the grader runs serially as the
    # terminal hop; the spend netting is proportional.
    if not isinstance(costs, dict):
        return None
    per_agent = costs.get("per_agent")
    if not isinstance(per_agent, list):
        return None
    spend = 0.0
    wall = 0.0
    hits: list[object] = []
    grader_seen = False
    for entry in per_agent:
        if not isinstance(entry, dict):
            continue
        agent_type = str(entry.get("agent_type") or "")
        if not (agent_type == "change-grader" or agent_type.endswith(":change-grader")):
            continue
        totals_value = entry.get("totals")
        totals = totals_value if isinstance(totals_value, dict) else {}
        cost = finite(totals.get("cost"))
        if cost is None:
            continue
        grader_seen = True
        spend += cost
        hits.append(finite(totals.get("hit_pct")))
        seconds = finite(entry.get("wall_seconds"))
        if seconds is not None:
            wall += seconds
    if not grader_seen:
        return None
    # A cache-hit percentage averages nothing: it renders only when exactly
    # one grader row carries it.
    hit = hits[0] if len(hits) == 1 else None
    hit_cell = f"{hit:.0f}%" if hit is not None else "?"
    return GradingShare(f"${spend:.2f}", _fmt_wall(wall), hit_cell, spend, wall)


def board_section(board: str) -> list[str]:
    """Render the board inline, closing any code fence agent-influenced text left open."""
    # A closer is backticks-only and at least as long as its opener; parity
    # counting would pair a four-backtick opener with a three-backtick line.
    clean = _FENCE_UNSAFE.sub(" ", board).rstrip("\n")
    open_len = 0
    for line in clean.splitlines():
        stripped = line.lstrip()
        if len(line) - len(stripped) >= CODE_INDENT:
            continue
        backticks = len(stripped) - len(stripped.lstrip("`"))
        if not open_len and backticks >= FENCE_MIN_BACKTICKS:
            open_len = backticks
        elif open_len and backticks >= open_len and not stripped.strip("` "):
            open_len = 0
    return [clean, "`" * max(FENCE_MIN_BACKTICKS, open_len)] if open_len else [clean]


def diff_fence(patch: str) -> list[str]:
    """Render the patch as a collapsible diff block no patch content can close."""
    clean = _FENCE_UNSAFE.sub(" ", patch).rstrip("\n")
    longest = max((len(run) for run in _BACKTICK_RUN.findall(clean)), default=0)
    fence = "`" * max(FENCE_MIN_BACKTICKS, longest + 1)
    return [
        "<details>",
        "<summary>Diff (rendered from <code>change.patch</code>)</summary>",
        "",
        f"{fence}diff",
        clean,
        fence,
        "",
        "</details>",
    ]


def _mark(value: object) -> str:
    """Render a boolean fact as a check, a cross, or `?` when unrecorded."""
    if value is None:
        return "?"
    return _GREEN if value else _RED


def _fmt_wall(seconds: object) -> str:
    """Render seconds as minutes and seconds."""
    value = finite(seconds)
    if value is None:
        return "?"
    if value >= SECONDS_PER_MINUTE:
        return f"{int(value // SECONDS_PER_MINUTE)}m {int(value % SECONDS_PER_MINUTE)}s"
    return f"{int(value)}s"


@dataclass(frozen=True)
class AgentEntry:
    """One transcript's accounted figures, parsed out of agent-costs.json."""

    agent_type: str
    models: tuple[str, ...]
    cost: float | None
    wall_seconds: float | None
    hit_pct: float | None
    cache_read: float | None
    total_input: float | None


def _agent_entries(per_agent: list[object]) -> list[AgentEntry]:
    """Parse the accounted per-agent rows, skipping any that is not an object."""
    entries: list[AgentEntry] = []
    for entry in per_agent:
        if not isinstance(entry, dict):
            continue
        totals_value = entry.get("totals")
        totals = totals_value if isinstance(totals_value, dict) else {}
        models = entry.get("models")
        entries.append(
            AgentEntry(
                agent_type=str(entry.get("agent_type") or "?"),
                models=(
                    tuple(sorted(str(m) for m in models))
                    if isinstance(models, list)
                    else ()
                ),
                cost=finite(totals.get("cost")),
                wall_seconds=finite(entry.get("wall_seconds")),
                hit_pct=finite(totals.get("hit_pct")),
                cache_read=finite(totals.get("cache_read")),
                total_input=finite(totals.get("total_input")),
            )
        )
    return entries


def _models_cell(models: tuple[str, ...]) -> str:
    """Render an agent's models, `—` when its ledger row records no API call."""
    return models_label(models) if models else "—"


def _sum_cell(values: list[float | None], fmt: Callable[[float], str]) -> str:
    """Render a total only when every part is known, else `?`."""
    if any(value is None for value in values):
        return "?"
    return fmt(sum(v for v in values if v is not None))


def _hit_cell(group: list[AgentEntry]) -> str:
    """Render the cache-hit rate re-derived from summed tokens, `?` on any unknown part."""
    # Averaging per-transcript percentages would weight a tiny transcript
    # like a huge one.
    reads = [e.cache_read for e in group]
    totals = [e.total_input for e in group]
    if any(v is None for v in reads + totals):
        return "?"
    total = sum(v for v in totals if v is not None)
    if total <= 0:
        return "0%"
    read = sum(v for v in reads if v is not None)
    return f"{round(read * 100 / total)}%"


def _agent_totals_rows(entries: list[AgentEntry]) -> list[str]:
    # An effort variant's transcripts fold into their base role, mirroring
    # accounting.VARIANT_SUFFIX: the tier is an implementation detail of the
    # role, and the deciding cost comparison needs one implementer row.
    """Render the per-agent-type totals, spend-heaviest first."""
    groups: dict[str, list[AgentEntry]] = {}
    for entry in entries:
        agent_type = entry.agent_type
        agent_type = agent_type.removesuffix("-routine")
        groups.setdefault(agent_type, []).append(entry)
    rows: list[tuple[float, str]] = []
    for agent_type, group in groups.items():
        costs = [e.cost for e in group]
        spend = sum(c for c in costs if c is not None)
        models = tuple(sorted({m for e in group for m in e.models}))
        rows.append(
            (
                spend,
                f"| `{scrub(agent_type)}`"
                f" | {len(group)}"
                f" | {_models_cell(models)}"
                f" | {_sum_cell(costs, lambda total: f'${total:.2f}')}"
                f" | {_sum_cell([e.wall_seconds for e in group], _fmt_wall)}"
                f" | {_hit_cell(group)} |",
            )
        )
    return [row for _spend, row in sorted(rows, key=lambda r: -r[0])]


def agents_section(costs: dict[str, object]) -> list[str]:
    """Render the agent roster with its totals and the per-transcript breakdown."""
    per_agent = costs.get("per_agent")
    if not isinstance(per_agent, list):
        return []
    entries = _agent_entries(per_agent)
    if not entries:
        return []
    rows: list[tuple[float, str]] = []
    for entry in entries:
        hit = entry.hit_pct
        rows.append(
            (
                entry.cost or 0.0,
                f"| `{scrub(entry.agent_type)}`"
                f" | {_models_cell(entry.models)}"
                f" | {f'${entry.cost:.2f}' if entry.cost is not None else '?'}"
                f" | {_fmt_wall(entry.wall_seconds)}"
                f" | {f'{hit:g}%' if hit is not None else '?'} |",
            )
        )
    return [
        "",
        "## Agents",
        "",
        "Totals per agent type, spend-heaviest first. Spend is the accounted"
        " (transcript-derived) figure. Wall sums compute time across"
        " transcripts; parallel agents make it exceed elapsed time. Cache hit"
        " re-derives from summed tokens, never averaged percentages.",
        "",
        "| agent | runs | models | spend | wall | cache hit |",
        "|---|---|---|---|---|---|",
        *_agent_totals_rows(entries),
        "",
        "<details>",
        "<summary>Per-transcript breakdown</summary>",
        "",
        "One row per agent transcript, spend-heaviest first. Full token and"
        " per-stage figures: `agent-costs.json`.",
        "",
        "| agent | models | spend | wall | cache hit |",
        "|---|---|---|---|---|",
        *(row for _spend, row in sorted(rows, key=lambda r: -r[0])),
        "",
        "</details>",
    ]


def _quote(text: str) -> list[str]:
    """Render a blockquote neutralized line by line, keeping the prompt's line structure."""
    return ["> " + _CELL_UNSAFE.sub(" ", line).rstrip() for line in text.splitlines()]


def _score_cell(value: object) -> str:
    """Render a judge score for prose, neutralizing a non-numeric record."""
    number = finite(value)
    if number is not None:
        return f"{number:g}"
    return scrub(str(value)) or "?"


@dataclass(frozen=True, slots=True)
class RunFolder:
    """One run folder's records and texts, the whole input of its page."""

    manifest: dict[str, object]
    result: dict[str, object]
    artifacts: list[str]
    patch: str | None = None
    board: str | None = None
    costs: dict[str, object] | None = None
    approved: tuple[Approval, ...] = ()
    suite_failures: list[str] | None = None
    grade: str | None = None
    stalled: bool = False


@dataclass(frozen=True, slots=True)
class _PageFacts:
    """The parsed record sections and derived facts every page section reads."""

    task: dict[str, object]
    version: dict[str, object]
    sut: dict[str, object]
    agent: dict[str, object]
    accounted: dict[str, object]
    oracle: dict[str, object]
    pipeline: dict[str, object]
    judge: dict[str, object]
    diff: dict[str, object]
    tests: dict[str, object]
    kind: str
    label: str
    consultations: int | None
    src_changed: int | None
    ladder: list[tuple[str, bool]]


def _page_facts(folder: RunFolder) -> _PageFacts:
    """Parse the folder's records into the facts the page sections read."""
    manifest, result = folder.manifest, folder.result
    task = _table(manifest, "task")
    agent = _table(result, "agent")
    oracle = _table(result, "oracle")
    pipeline = _table(result, "pipeline")
    diff = _table(result, "diff")
    tests = _table(oracle, "tests")
    kind = str(task.get("kind", ""))
    consultations = _int_or_none(pipeline.get("consultation_requests"))
    src_changed = _int_or_none(diff.get("src_files_changed"))
    ladder = checkpoint_ladder(
        LadderFacts(
            kind,
            str(result.get("status", "error")),
            _int_or_none(diff.get("files_changed")),
            src_changed,
            _bool_or_none(oracle.get("suite_green")),
            {str(name): str(outcome) for name, outcome in tests.items()},
            consultations or 0,
        )
    )
    return _PageFacts(
        task=task,
        version=_table(manifest, "version"),
        sut=_table(manifest, "sut"),
        agent=agent,
        accounted=_table(agent, "accounted"),
        oracle=oracle,
        pipeline=pipeline,
        judge=_table(result, "quality_judge"),
        diff=diff,
        tests=tests,
        kind=kind,
        label=scrub(str(_table(manifest, "version").get("label", "?"))),
        consultations=consultations,
        src_changed=src_changed,
        ladder=ladder,
    )


def _header_lines(folder: RunFolder, facts: _PageFacts) -> list[str]:
    """Render the title, the one-line summary, and the frozen prompt."""
    manifest, task = folder.manifest, facts.task
    task_id = scrub(str(task.get("id", "unknown")))
    status = scrub(str(folder.result.get("status", "error")))
    return [
        f"# {task_id} r{scrub(str(manifest.get('rep', '?')))} — {facts.label}",
        "",
        f"{scrub(str(task.get('title', '?')))} ({scrub(str(task.get('kind', '?')))})"
        f" · started {scrub(str(manifest.get('started', '?')))}"
        f" · exec `{scrub(str(manifest.get('exec_mode', '?')))}`"
        f" · status **{status}**"
        + (
            " · **stalled mid-pipeline** (README § Checkpoints)"
            if folder.stalled
            else ""
        ),
        "",
        "## Prompt",
        "",
        *_quote(str(manifest.get("prompt", ""))),
        "",
    ]


def _oracle_row(facts: _PageFacts) -> str:
    """Render the verdict table's oracle row."""
    if facts.kind == KIND_REFUSAL:
        return "| oracle | — (refusal task: graded by the recorded diff) |"
    # The counts pass the int gate like every other number on the page.
    passed = _int_or_none(facts.oracle.get("passed"))
    total = _int_or_none(facts.oracle.get("total"))
    return (
        f"| oracle | {_mark(facts.oracle.get('oracle_passed'))} "
        f"{'?' if passed is None else passed}"
        f"/{'?' if total is None else total} passed |"
    )


def _verdict_lines(folder: RunFolder, facts: _PageFacts) -> list[str]:
    """Render the verdict table with its grade note, test list, and suite failures."""
    oracle, grade = facts.oracle, folder.grade
    lines = [
        "## Verdict",
        "",
        "| check | result |",
        "|---|---|",
        _oracle_row(facts),
        f"| suite (post-agent) | {_mark(oracle.get('suite_green'))} |",
        f"| suite (pristine baseline) | {_mark(oracle.get('suite_green_base'))} |",
        f"| checkpoints | {sum(1 for _name, hit in facts.ladder if hit)}/{len(facts.ladder)} |",
        f"| reading depth (pipeline grade) | {scrub(grade) if grade else '—'} |",
    ]
    if facts.kind == KIND_REFUSAL:
        src_changed, consultations = facts.src_changed, facts.consultations
        lines += [
            f"| src files changed | {src_changed if src_changed is not None else '?'} |",
            "| consultation-request records (Tier B) |"
            f" {consultations if consultations is not None else '?'} |",
        ]
    if grade:
        lines += [
            "",
            "The pipeline grade estimates how much human review the change"
            " deserves before merge — advisory context from the harness's"
            " change grader (read from the ledger's `grader-verdict`"
            " record), never part of the bar.",
        ]
    if facts.tests:
        lines += [""] + [
            f"- {_mark(outcome == 'passed')} `{scrub(str(name))}` — "
            f"{scrub(str(outcome))}"
            for name, outcome in sorted(facts.tests.items())
        ]
    if folder.suite_failures:
        shown = folder.suite_failures[:SHOWN_SUITE_FAILURES]
        lines += ["", "Post-agent suite failures (from the build log):", ""]
        lines += [f"- `{scrub(name)[:SUITE_FAILURE_CHARS]}`" for name in shown]
        if len(folder.suite_failures) > len(shown):
            lines.append(
                f"- … {len(folder.suite_failures) - len(shown)} more in [`run.log`](run.log)"
            )
    return lines


def _checkpoint_lines(facts: _PageFacts) -> list[str]:
    """Render the ladder under the heading the trend's Ckpt figures link to."""
    return [
        "",
        "## Checkpoints",
        "",
        "The kind's graded ladder, derived from the recorded facts —"
        " context only, outside the quality bar (bench README § Checkpoints).",
        "",
        *(f"- {_mark(hit)} `{scrub(name)}`" for name, hit in facts.ladder),
    ]


def _judge_samples(
    judge: dict[str, object],
) -> tuple[list[dict[str, object]], list[tuple[int, dict[str, object]]]]:
    """Return the parsed samples and the rationale-bearing ones numbered by position."""
    # Rationale-bearing samples keep their position in the parsed list, so a
    # sample number on the page indexes result.json directly.
    parsed = [
        sample for sample in _list(judge.get("samples")) if isinstance(sample, dict)
    ]
    numbered = [
        (number, sample)
        for number, sample in enumerate(parsed, 1)
        if str(sample.get("rationale", "")).strip()
    ]
    return parsed, numbered


def _sample_lines(samples: list[tuple[int, dict[str, object]]]) -> list[str]:
    """Render the per-sample rationales inside a collapsed block."""
    lines = [
        "",
        "<details>",
        "<summary>Per-sample rationales (judge-authored, untrusted text)</summary>",
    ]
    for number, sample in samples:
        scores = " · ".join(
            f"{facet.replace('_', '-')} {_score_cell(sample.get(facet, '?'))}"
            for facet in JUDGE_FACETS
        )
        # The blockquote marker denies column-0 block syntax: a rationale
        # opening with `~~~` or `#` would otherwise start a fence or heading.
        lines += [
            "",
            f"**Sample {number}** — {scores}",
            "",
            "> " + html_safe(str(sample.get("rationale", ""))),
        ]
    lines += ["", "</details>"]
    return lines


def _judge_lines(judge: dict[str, object]) -> list[str]:
    """Render the advisory judge section, empty when the judge did not run."""
    if not judge:
        return []
    median = _table(judge, "median")
    spread = _table(judge, "spread")
    judge_cost = finite(judge.get("cost_usd"))
    judge_spend = f"${judge_cost:.2f}" if judge_cost is not None else "$?"
    parsed, samples = _judge_samples(judge)
    # The median's basis is the parsed sample count; the runner records
    # samples_requested as asked-for, not delivered.
    requested = _int_or_none(judge.get("samples_requested"))
    basis = len(parsed) if parsed else requested
    count = f"{basis if basis is not None else '?'} sample(s)"
    if parsed and requested is not None and requested != len(parsed):
        count += f" ({requested} requested)"
    lines = [
        "",
        "## Judge (advisory)",
        "",
        "| " + " | ".join(facet.replace("_", "-") for facet in JUDGE_FACETS) + " |",
        "|---" * len(JUDGE_FACETS) + "|",
        "| "
        + " | ".join(
            f"{_score_cell(median.get(facet, '?'))} (±{_score_cell(spread.get(facet, '?'))})"
            for facet in JUDGE_FACETS
        )
        + " |",
        "",
        f"Median (spread) over {count}"
        f" · rubric `{scrub(str(judge.get('rubric', '?')))}`"
        f" · `{scrub(str(judge.get('model', '?')))}`"
        f" · {judge_spend}. Advisory context, never part"
        " of the quality bar"
        + ("; rationales below." if samples else "; rationales: `result.json`."),
    ]
    if samples:
        lines += _sample_lines(samples)
    return lines


def _delivery(
    folder: RunFolder, facts: _PageFacts, grading: GradingShare | None
) -> tuple[float | None, float | None]:
    """Return the delivery spend and wall with the grader's share netted out."""
    # Proportional netting, the same rule as Run.agent_spend: the two cost
    # sources price the run differently, so a cross-basis subtraction would
    # over-net.
    cost = facts.agent.get("total_cost_usd")
    wall = folder.result.get("wall_seconds")
    delivery_wall = (
        max(wall - (grading.seconds if grading else 0.0), 0.0)
        if isinstance(wall, (int, float))
        else None
    )
    accounted_total = finite(facts.accounted.get("cost"))
    delivery_spend: float | None = None
    if isinstance(cost, (int, float)):
        delivery_spend = float(cost)
        if grading and accounted_total:
            fraction = min(grading.spend / accounted_total, 1.0)
            delivery_spend = float(cost) * (1.0 - fraction)
    return delivery_spend, delivery_wall


def _figure_lines(folder: RunFolder, facts: _PageFacts) -> list[str]:
    """Render the delivery figures and, when graded, the grader's own share."""
    grading = grading_figures(folder.costs) if folder.grade else None
    delivery_spend, delivery_wall = _delivery(folder, facts, grading)
    hit = facts.accounted.get("hit_pct")
    diff = facts.diff
    lines = ["", "## Figures", ""]
    if grading:
        lines += [
            "Delivery — the change grader's share below excluded from spend and wall:",
            "",
        ]
    lines += [
        "| agent spend | wall | turns | cache hit | diff |",
        "|---|---|---|---|---|",
        "| "
        + " | ".join(
            [
                f"${delivery_spend:.2f}" if delivery_spend is not None else "?",
                f"{delivery_wall / SECONDS_PER_MINUTE:.0f}m"
                if delivery_wall is not None
                else "?",
                scrub(str(facts.agent.get("num_turns", "?"))),
                f"{hit}%" if finite(hit) is not None else "?",
                f"{scrub(str(diff.get('files_changed', '?')))} file(s)"
                f" +{scrub(str(diff.get('insertions', '?')))}"
                f"/−{scrub(str(diff.get('deletions', '?')))}",  # noqa: RUF001
            ]
        )
        + " |",
    ]
    if grading:
        lines += [
            "",
            "The change grader — optional support for the human merge"
            " decision, transcript-accounted like the Agents table:",
            "",
            "| spend | wall | cache hit |",
            "|---|---|---|",
            f"| {grading.spend_cell} | {grading.wall_cell} | {grading.hit_cell} |",
        ]
    return lines


def _change_lines(patch: str | None) -> list[str]:
    """Render the diff, linked instead of embedded past the embed bound."""
    if not patch or not patch.strip():
        return []
    lines = ["", "## Change", ""]
    if patch.count("\n") <= EMBED_MAX_LINES:
        lines += diff_fence(patch)
    else:
        lines.append(
            f"Patch over {EMBED_MAX_LINES} lines — too large to"
            " embed; see [`change.patch`](change.patch)."
        )
    return lines


def approved_lines(approvals: tuple[Approval, ...]) -> list[str]:
    """Render the approvals collapsed beneath the board, each string escaped for it."""
    if not approvals:
        return []
    lines = [
        "",
        "<details>",
        "<summary>What the reviewers approved (from"
        " <code>handoff.jsonl</code>)</summary>",
        "",
    ]
    for author, aspects in approvals:
        lines += [f"**{html_safe(author)}**", ""]
        lines += [f"- {html_safe(aspect)}" for aspect in aspects]
        lines.append("")
    lines.append("</details>")
    return lines


def _pipeline_lines(board: str | None, approved: tuple[Approval, ...]) -> list[str]:
    """Render the board and the approvals, linked instead of embedded past the bound."""
    if not board or not board.strip():
        return []
    lines = ["", "## Pipeline", ""]
    if board.count("\n") <= EMBED_MAX_LINES:
        lines += board_section(board)
    else:
        lines.append(
            f"Board over {EMBED_MAX_LINES} lines — too large to"
            " embed; render it from [`handoff.jsonl`](handoff.jsonl) with"
            " `scripts/handoff.py view --markdown --verbose`."
        )
    return lines + approved_lines(approved)


def _provenance_lines(folder: RunFolder, facts: _PageFacts) -> list[str]:
    """Render the artifact roster and the provenance block that close the page."""
    manifest, version, sut, task = folder.manifest, facts.version, facts.sut, facts.task
    present = set(folder.artifacts)
    models = _list(facts.agent.get("models"))
    return [
        "",
        "## Artifacts",
        "",
        *(
            f"- [`{name}`]({name}) — {reading}"
            for name, reading in RUN_PAGE_ARTIFACTS
            if name in present
        ),
        "",
        "## Provenance",
        "",
        f"- plugin `{scrub(str(version.get('plugin', '?')))}` at"
        f" `{facts.label}` ({scrub(str(version.get('kind', '?')))})",
        f"- model requested `{scrub(str(manifest.get('model_requested', '?')))}`;"
        f" models used: {models_label(tuple(sorted(str(m) for m in models)))}",
        f"- SUT `{scrub(str(sut.get('repo', '?')))}` at"
        f" `{scrub(str(sut.get('sha', '?'))[:SHA_CHARS])}`"
        f" (branch `{scrub(str(sut.get('branch', '?')))}`)",
        f"- task fingerprint `{scrub(str(task.get('fingerprint', '?')))}`"
        f" · `{scrub(str(manifest.get('cc_version', '?')))}`",
        "",
        "Generated by `evals/summarize.py` from this folder's records —"
        " regenerate rather than edit.",
    ]


def render_run_page(folder: RunFolder) -> str:
    """Render one run folder as prose, derived from its records and texts alone."""
    facts = _page_facts(folder)
    lines = [
        *_header_lines(folder, facts),
        *_verdict_lines(folder, facts),
        *_checkpoint_lines(facts),
        *_judge_lines(facts.judge),
        *_run_defect_lines(folder.manifest, folder.patch),
        *_figure_lines(folder, facts),
        *_change_lines(folder.patch),
        *_pipeline_lines(folder.board, folder.approved),
        *(agents_section(folder.costs) if folder.costs else []),
        *_provenance_lines(folder, facts),
    ]
    return "\n".join(lines) + "\n"


def _run_folder(out_dir: Path) -> RunFolder | None:
    """Load one run folder's records and texts, or None when the records are unreadable."""
    result = _read_json(out_dir / "result.json")
    manifest = _read_json(out_dir / "manifest.json")
    if result is None or manifest is None:
        return None
    patch_path = out_dir / "change.patch"
    pipeline = _table(result, "pipeline")
    outcome = Outcome(
        kind=str(_table(manifest, "task").get("kind", "")),
        status=str(result.get("status", "error")),
        oracle_ok=_table(result, "oracle").get("oracle_passed"),
        route=_str_or_none(pipeline.get("route_decision")),
    )
    return RunFolder(
        manifest=manifest,
        result=result,
        artifacts=sorted(
            p.name for p in out_dir.iterdir() if p.is_file() and p.name != "README.md"
        ),
        patch=patch_path.read_text(encoding="utf-8", errors="replace")
        if patch_path.is_file()
        else None,
        board=render_pipeline(out_dir),
        costs=_read_json(out_dir / "agent-costs.json"),
        approved=reviewer_approvals(out_dir),
        suite_failures=failed_suite_tests(out_dir),
        grade=ledger_grader_verdict(out_dir),
        stalled=run_stalled(outcome, out_dir),
    )


def render_run_pages() -> dict[Path, str]:
    """Render every run folder's page, keyed by its README.md path."""
    pages: dict[Path, str] = {}
    for result_path in sorted(RUNS_DIR.glob("*/*/result.json")):
        folder = _run_folder(result_path.parent)
        if folder is not None:
            pages[result_path.parent / "README.md"] = render_run_page(folder)
    return pages


def trend_views(runs: list[Run], notes: tuple[Note, ...] = ()) -> dict[Path, str]:
    """Render the trend views: the committed tagged page and data, plus the dev page when a dev run exists."""
    # A committed row would link folders git never holds, so dev runs stay
    # on the gitignored page; notes validate against the tagged series.
    tagged = [r for r in runs if not r.version.startswith("dev-")]
    validate_notes(notes, tagged)
    views = {
        TREND: render(tagged, operator_notes=notes),
        TREND_DATA: trend_data_json(tagged),
    }
    if len(tagged) < len(runs):
        views[TREND_DEV] = render(
            runs, note=DEV_NOTE, operator_notes=notes, include_figure=False
        )
    return views


def trend_data_json(tagged: list[Run]) -> str:
    """Render the tagged series as per-rep records, the machine-readable contract of the figure."""
    versions = sorted({r.version for r in tagged}, key=version_key)
    order = {v: i for i, v in enumerate(versions)}
    rows = sorted(
        tagged, key=lambda r: (r.task, order[r.version], r.model_requested, r.rep)
    )
    payload = {
        "spec_version": "0.2.0",
        "versions": versions,
        "reps": [
            {
                "task": r.task,
                "task_kind": r.task_kind,
                "version": r.version,
                "model_pin": r.model_requested,
                "models": sorted(m for m in r.models if m != SYNTHETIC_MODEL),
                "rep": r.rep,
                "cleared": r.cleared,
                "agent_spend_usd": round(r.agent_spend, 4),
                "spend_known": r.spend_known,
                "wall_seconds": None if r.wall is None else round(r.wall, 1),
                "delivery_wall_seconds": None
                if r.delivery_wall is None
                else round(r.delivery_wall, 1),
                "judge_facet_medians": r.judge_median,
                "known_defects": r.known_defects,
                "run_folder": r.folder,
            }
            for r in rows
        ],
    }
    return json.dumps(payload, indent=1, sort_keys=True) + "\n"


FIGURE_SOURCE = EVALS.parent / "docs" / "images" / "eval-trend.drawio"


def figure_freshness_notice(
    runs: list[Run], source: Path = FIGURE_SOURCE
) -> str | None:
    """Compare the figure's stamped version against the latest measured release, as a nudge."""
    tags = {r.version for r in runs if not r.version.startswith("dev-")}
    if not tags:
        return None
    if not source.is_file():
        return (
            "note: eval-trend figure missing"
            f" ({source.name}) — render with evals/render_figure.py"
        )
    stamped = re.search(
        r"snapshot through (v[0-9]+(?:\.[0-9]+)*)",
        source.read_text(encoding="utf-8"),
    )
    if stamped is None:
        return (
            "note: eval-trend figure carries no version stamp — a hand save"
            " may have compressed it; regenerate with evals/render_figure.py"
        )
    latest = scrub(max(tags, key=version_key))
    if stamped.group(1) == latest:
        return f"eval-trend figure current (stamped {latest})"
    return (
        f"note: eval-trend figure is stamped {stamped.group(1)}; latest"
        f" measured version is {latest} — when the story changed, redraw"
        " with evals/render_figure.py (update-diagrams skill)"
    )


def _drifted_views(views: dict[Path, str]) -> list[str]:
    """List every committed view that differs from its fresh render, orphans included."""
    drifted = [
        path.relative_to(EVALS).as_posix()
        for path, text in views.items()
        if (path.read_text(encoding="utf-8") if path.is_file() else "") != text
    ]
    # An orphaned page renders from nothing, so the drift compare would skip
    # it; a TREND-dev.md with no dev run folder behind it is the same orphan.
    drifted += [
        f"{page.relative_to(EVALS).as_posix()} (orphaned)"
        for page in sorted(RUNS_DIR.glob("*/*/README.md"))
        if page not in views
    ]
    if TREND_DEV not in views and TREND_DEV.is_file():
        drifted.append(f"{TREND_DEV.relative_to(EVALS).as_posix()} (orphaned)")
    return drifted


def _write_views(views: dict[Path, str]) -> None:
    """Write every derived view, removing a dev trend page no dev run backs."""
    TREND.parent.mkdir(parents=True, exist_ok=True)
    for path, text in views.items():
        path.write_text(text, encoding="utf-8")
    if TREND_DEV not in views:
        TREND_DEV.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """Regenerate the derived views, or with --check report any drift from them."""
    flags = (argv if argv is not None else sys.argv)[1:]
    runs = load_runs()
    try:
        views: dict[Path, str] = {
            **trend_views(runs, load_notes()),
            **render_run_pages(),
        }
    except NotesError as error:
        print(error, file=sys.stderr)
        return 1
    if "--check" in flags:
        drifted = _drifted_views(views)
        if drifted:
            print(
                f"derived view(s) drifted from the run folders:"
                f" {', '.join(drifted)} — regenerate with evals/summarize.py",
                file=sys.stderr,
            )
            return 1
        print(f"{len(views)} derived view(s) match the run folders")
        return 0
    _write_views(views)
    print(views[TREND])
    notice = figure_freshness_notice(runs)
    if notice:
        print(notice, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
