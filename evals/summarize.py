#!/usr/bin/env python3
"""summarize.py — regenerate the derived views from the run folders and the
operator notes file: evals/results/TREND.md plus one README.md per run folder.

The folders are the ground truth; every view is derived and deterministic.
Operator commentary lives in `results/notes.toml` — dated, optionally scoped
to a task or one of its cells, validated loudly — and renders into the trend
beside the figures it discusses. Figures never come from notes.
The trend aggregates per (version, requested-model-pin, task) cell against
the binary quality bar and renders cost per pass — the cell's agent spend
divided by its bar-clearing reps. The run page presents one folder — prompt,
verdict, figures, the change and board, agent roster, artifact links — so a
reader lands on prose, not a folder of raw records. Every rendered string is
scrubbed to stay inert in a terminal; agent-authored markdown renders only
inside structure-guarded blocks (adaptive diff fence, balance-checked board).
`--check` renders without writing and fails on drift from any committed view,
orphaned pages included. Runs standalone and at the end of every sweep.
"""

from __future__ import annotations

import datetime
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
# settled — the depth is the evidence bar, however the reps landed. Defined
# before the table bullets, which render the figure.
ESCALATION_CONFIRMED_REPS = 3

# The trend renders one table per task, headed by the task id and its
# description, with versions newest first — the trend reads straight down,
# and each concern holds its own column instead of a sigil packed into a
# grid cell.
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
    " binds only the root agent. The pin renders beside the version only when"
    " rows differ on it.",
    "- The spend columns price one sweep, every task run once: each task cell"
    " contributes its mean spend per rep, failures included, and the row sums"
    " those means across its tasks. Rows with equal task coverage compare on"
    " any rep depth; a task unmeasured in a row adds nothing, so unequal"
    " coverage does not compare.",
    "- Grading spend reports the netted share (accounted basis), so Agent"
    " spend plus Grading spend approximates the whole-sweep figure; the run"
    " pages break each run out.",
    "- Judge spend is the optional Tier C measurement cost: each cell's mean"
    " over its judged reps only, summed across tasks like the other columns."
    " `—` means the judge did not run.",
)

# The refusal task kind: graded by the recorded diff, not a held-out oracle
# (README § Refusal tasks). The constant lives here because run_eval imports
# this module, never the reverse.
KIND_REFUSAL = "refusal"

# The result.json schema stamp the runner writes and this reader expects —
# single-sourced here for the same import-direction reason. load_runs warns
# on a mismatching stamp instead of guessing at a future shape silently.
RESULT_SCHEMA = 1


def checkpoint_ladder(
    kind: str,
    status: str,
    files_changed: int | None,
    src_files_changed: int | None,
    suite_green: bool | None,
    oracle_tests: dict[str, str],
    consultations: int,
) -> list[tuple[str, bool]]:
    """The task kind's graded checkpoint ladder, derived from recorded facts
    (README § Checkpoints). Every step is Tier A except the refusal ladder's
    consultation step, which reads the agent-authored ledger (Tier B) and
    never enters the bar. A missing fact reads as not-hit, fail-closed."""
    if kind == KIND_REFUSAL:
        return [
            ("agent complete", status == "complete"),
            ("no src change", src_files_changed == 0),
            ("suite green", suite_green is True),
            ("consultation recorded", consultations > 0),
        ]
    steps = [
        ("agent complete", status == "complete"),
        ("change produced", bool(files_changed)),
        ("suite green", suite_green is True),
    ]
    steps += [
        (name, outcome == "passed") for name, outcome in sorted(oracle_tests.items())
    ]
    return steps


# The judge facet roster, in render order. Single source: the runner and the
# rubric contract test import it from here, so a facet rename cannot leave
# this table silently rendering `?` columns.
JUDGE_FACETS = ("design_fit", "test_quality", "maintainability", "doc_fit")

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
# A relative link target assembled from on-disk names. Every segment starts
# with a word character — no traversal, no hidden dirs, no scheme, no
# separators beyond `/` — or the name renders as plain text.
_LINK_SAFE = re.compile(r"^\w[\w.-]*(?:/\w[\w.-]*)*\Z")


def finite(value: object) -> float | None:
    """A usable number from an agent-influenceable record, or None. Excludes
    bool (a JSON `true` is not a dollar) and non-finite floats — `json.loads`
    accepts bare `NaN`/`Infinity`, and one such value in one folder must not
    poison arithmetic or abort the whole corpus render."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def scrub(text: str) -> str:
    """Neutralize agent-influenceable bytes before they land in committed
    markdown or the operator's terminal."""
    return _CELL_UNSAFE.sub(" ", text).strip()


@dataclass(frozen=True)
class Run:
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
    # The task fingerprint from the manifest. A clarifying prompt edit keeps
    # the task id (README § task identity), so one task's runs may span
    # fingerprints; the task section calls a span out, never silently mixes.
    fingerprint: str = ""
    # The runner-recorded post-session routing decision; None on runs
    # recorded before the field existed.
    route_decision: str | None = None
    # The session completed while the pipeline still owed work — a stall,
    # not a capability failure. Derived at load time (`run_stalled`).
    stalled: bool = False

    @property
    def agent_spend(self) -> float:
        """Delivery cost only — spend that is not the change, never in the
        cost-per-pass metric: the Tier C judge reports in its own column,
        and the change grader's share (optional support for the human merge
        decision) is netted out here, mirroring the run page.

        The netting is proportional: the grader's fraction of the accounted
        total, applied to whichever total this run reports. The self-report
        and the accounting price the same run differently, so subtracting an
        accounted dollar figure from the self-report would over-net; a
        fraction is basis-free. The fraction is capped at 1, so no share can
        push a figure below zero — a share that owns the whole accounted
        total zeroes the cell and shows itself in the Grading spend column.
        The CLI's self-report is preferred; the transcript-derived figure
        covers timeouts and crashes."""
        total = self.cost if self.cost is not None else (self.accounted_cost or 0.0)
        if self.grading_spend <= 0 or not self.accounted_cost:
            return total
        fraction = min(self.grading_spend / self.accounted_cost, 1.0)
        return total * (1.0 - fraction)

    @property
    def delivery_wall(self) -> float | None:
        """Wall minus the grader's serial terminal hop — the delivery time
        the median-wall cell reads."""
        if self.wall is None:
            return None
        return max(self.wall - self.grading_seconds, 0.0)

    @property
    def spend_known(self) -> bool:
        """False when no cost source recorded anything — the rep burned an
        unknown amount and every figure it enters is a lower bound."""
        return self.cost is not None or self.accounted_cost is not None

    @property
    def cleared(self) -> bool:
        """The quality bar, fail-closed: complete, oracle all-pass, suite
        green. A red pristine baseline gets no waiver — it makes the bar
        unreachable for the base and the sweep loudly worthless until the
        SUT base is fixed (`suite_green_base` attributes it). A refusal
        task's bar reads the recorded diff instead of an oracle: complete,
        suite green, no `src/` change (README § Refusal tasks); a record
        missing the src count fails the bar rather than guessing."""
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
        """(hit, total) on the kind's checkpoint ladder — the graded record
        of how far the rep got (README § Checkpoints)."""
        steps = checkpoint_ladder(
            self.task_kind,
            self.status,
            self.files_changed,
            self.src_files_changed,
            self.suite_green,
            self.oracle_tests,
            self.consultations,
        )
        return sum(1 for _name, hit in steps if hit), len(steps)


def _str_or_none(value: object) -> str | None:
    """A string from an agent-influenceable record, or None — a non-str
    value must read as unknown, never reach a sanitizer that assumes str."""
    return value if isinstance(value, str) else None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _judge_median(value: object) -> dict[str, float] | None:
    """The recorded medians as numbers, validated at the parse boundary. A
    non-dict record or a non-finite score reads as unjudged rather than
    rendering an agent-influenceable string into a committed table."""
    if not isinstance(value, dict):
        return None
    medians: dict[str, float] = {}
    for facet, score in value.items():
        number = finite(score)
        if number is None:
            return None
        medians[str(facet)] = number
    return medians or None


def load_runs() -> list[Run]:
    runs: list[Run] = []
    if not RUNS_DIR.is_dir():
        return runs
    # A folder without result.json (a run in flight, or one that died before
    # measurement) renders nowhere; skipping it silently would contradict the
    # every-run-persists rule, so the skip is loud.
    for manifest_path in sorted(RUNS_DIR.glob("*/*/manifest.json")):
        if not (manifest_path.parent / "result.json").is_file():
            rel = manifest_path.parent.relative_to(RUNS_DIR.parent).as_posix()
            print(
                f"note: run folder without result.json, skipped: {rel}", file=sys.stderr
            )
    for result_path in sorted(RUNS_DIR.glob("*/*/result.json")):
        manifest_path = result_path.parent / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        stamp = result.get("schema")
        if stamp != RESULT_SCHEMA:
            rel = result_path.parent.relative_to(RUNS_DIR.parent).as_posix()
            print(
                f"warning: result schema {stamp!r} != expected {RESULT_SCHEMA};"
                f" fields this reader does not know may go unrendered: {rel}",
                file=sys.stderr,
            )
        oracle = result.get("oracle") or {}
        agent = result.get("agent") or {}
        judge = result.get("quality_judge") or {}
        diff = result.get("diff") or {}
        pipeline = result.get("pipeline") or {}
        tests_raw = oracle.get("tests")
        oracle_tests = (
            {str(name): str(outcome) for name, outcome in tests_raw.items()}
            if isinstance(tests_raw, dict)
            else {}
        )
        consultations_raw = pipeline.get("consultation_requests")
        judge_median = _judge_median(judge.get("median"))
        if judge.get("median") is not None and judge_median is None:
            rel = result_path.parent.relative_to(RUNS_DIR.parent).as_posix()
            print(
                f"warning: malformed judge median, row renders unjudged"
                f" while its judge cost still enters Judge spend: {rel}",
                file=sys.stderr,
            )
        costs_path = result_path.parent / "agent-costs.json"
        grading = None
        verdict = ledger_grader_verdict(result_path.parent)
        if costs_path.is_file() and verdict:
            try:
                loaded = json.loads(costs_path.read_text(encoding="utf-8"))
            except ValueError:
                loaded = None
            grading = grading_figures(loaded if isinstance(loaded, dict) else None)
        runs.append(
            Run(
                folder=result_path.parent.relative_to(RUNS_DIR.parent).as_posix(),
                rep=_int_or_none(manifest.get("rep")) or 0,
                epoch=(manifest.get("sut") or {}).get("sha", "unknown"),
                sut_repo=(manifest.get("sut") or {}).get("repo", ""),
                sut_branch=(manifest.get("sut") or {}).get("branch", ""),
                version=(manifest.get("version") or {}).get(
                    "label", result_path.parent.parent.name
                ),
                model_requested=manifest.get("model_requested", "(default)"),
                task=(manifest.get("task") or {}).get("id", "unknown"),
                task_kind=(manifest.get("task") or {}).get("kind", ""),
                task_title=(manifest.get("task") or {}).get("title", ""),
                started=manifest.get("started", ""),
                status=result.get("status", "error"),
                oracle_ok=oracle.get("oracle_passed"),
                oracle_tests=oracle_tests,
                suite_green=oracle.get("suite_green"),
                suite_green_base=oracle.get("suite_green_base"),
                files_changed=_int_or_none(diff.get("files_changed")),
                src_files_changed=_int_or_none(diff.get("src_files_changed")),
                consultations=consultations_raw
                if isinstance(consultations_raw, int)
                and not isinstance(consultations_raw, bool)
                else 0,
                models=tuple(sorted(agent.get("models") or [])),
                cost=finite(agent.get("total_cost_usd")),
                accounted_cost=finite((agent.get("accounted") or {}).get("cost")),
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
                fingerprint=_str_or_none(
                    (manifest.get("task") or {}).get("fingerprint")
                )
                or "",
                route_decision=_str_or_none(pipeline.get("route_decision")),
                stalled=run_stalled(
                    (manifest.get("task") or {}).get("kind", ""),
                    result.get("status", "error"),
                    oracle.get("oracle_passed"),
                    _str_or_none(pipeline.get("route_decision")),
                    result_path.parent,
                ),
            )
        )
    return runs


def run_stalled(
    kind: str,
    status: str,
    oracle_ok: object,
    route: str | None,
    folder: Path,
) -> bool:
    """A complete non-refusal run whose pipeline ended with work still owed.
    The runner-recorded route decision is authoritative (`dispatch` = work
    owed). Runs recorded before the field read from the copied ledger: a
    non-empty ledger with no implementer terminal record ended before
    implementation — conservative, so a mid-review stall on an old record
    stays unlabeled rather than guessed. An all-pass oracle is never a
    stall, whatever the ledger shape."""
    if kind == KIND_REFUSAL or status != "complete" or oracle_ok is True:
        return False
    if route is not None:
        return route == "dispatch"
    records = ledger_records(folder)
    if not records:
        return False
    return not any(
        record.get("type") in ("build-pass", "build-failure") for record in records
    )


def _env_prep(prep: object) -> tuple[str, ...]:
    """The operator-injected settings-env lines from a manifest's prep
    array — the prep facts that shape the agent's environment, as opposed
    to the install mechanics around them."""
    if not isinstance(prep, list):
        return ()
    return tuple(
        sorted(
            line
            for line in prep
            if isinstance(line, str) and line.startswith("settings.json: env")
        )
    )


_NOTE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}\Z")
_NOTE_KEYS = frozenset({"date", "text", "task", "version", "model"})


@dataclass(frozen=True)
class Note:
    """One dated operator note from `results/notes.toml` — commentary the
    trend renders beside the figures it discusses. `task` places the note
    under that task's table; `version` (with `task`) narrows it to one
    cell; neither makes it page-level. `model` (with `task`) narrows the
    note's explaining power to one pin's rows in the settled-moves check;
    rendering placement is unchanged. Figures never come from notes."""

    date: str
    text: str
    task: str | None = None
    version: str | None = None
    model: str | None = None


def _note_date(value: object, where: str) -> str:
    """The note's date as `YYYY-MM-DD`, from a bare TOML date or a matching
    string. A datetime is refused — a note carries a day, not a time — and
    a quoted string must name a real calendar day, the same bar tomllib
    holds bare dates to."""
    if type(value) is datetime.date:
        return value.isoformat()
    if isinstance(value, str) and _NOTE_DATE.match(value):
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise SystemExit(f"{where} needs a real calendar date") from None
        return value
    raise SystemExit(f"{where} needs a calendar date (YYYY-MM-DD)")


def load_notes() -> tuple[Note, ...]:
    """The operator notes, validated loudly: the file is hand-authored, so
    a malformed entry aborts the render instead of silently dropping or
    misplacing prose."""
    if not NOTES.is_file():
        return ()
    try:
        data = tomllib.loads(NOTES.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise SystemExit(f"{NOTES.name}: {error}") from error
    entries = data.pop("note", [])
    if data:
        raise SystemExit(f"{NOTES.name}: unknown top-level keys {sorted(data)}")
    if not isinstance(entries, list):
        raise SystemExit(f"{NOTES.name}: `note` must be an array of tables")
    notes: list[Note] = []
    for index, entry in enumerate(entries, start=1):
        where = f"{NOTES.name}: note {index}"
        if not isinstance(entry, dict):
            raise SystemExit(f"{where} is not a table")
        unknown = sorted(set(entry) - _NOTE_KEYS)
        if unknown:
            raise SystemExit(f"{where} has unknown keys {unknown}")
        text = entry.get("text")
        task = entry.get("task")
        version = entry.get("version")
        model = entry.get("model")
        if not isinstance(text, str) or not text.strip():
            raise SystemExit(f"{where} needs a non-empty text")
        if task is not None and not isinstance(task, str):
            raise SystemExit(f"{where}: task must be a string")
        if version is not None and not isinstance(version, str):
            raise SystemExit(f"{where}: version must be a string")
        if model is not None and not isinstance(model, str):
            raise SystemExit(f"{where}: model must be a string")
        if version is not None and task is None:
            raise SystemExit(f"{where} scopes a version without a task")
        if model is not None and task is None:
            raise SystemExit(f"{where} scopes a model without a task")
        notes.append(
            Note(
                date=_note_date(entry.get("date"), where),
                text=text,
                task=task,
                version=version,
                model=model,
            )
        )
    return tuple(notes)


def validate_notes(notes: tuple[Note, ...], runs: list[Run]) -> None:
    """Every scoped note must name a recorded cell of the committed series —
    a note that outlives its rows is rot, and rot fails loud."""
    tasks = {r.task for r in runs}
    cells = {(r.task, r.version) for r in runs}
    pins = {r.model_requested for r in runs}
    for note in notes:
        if note.task is not None and note.task not in tasks:
            raise SystemExit(f"{NOTES.name}: no recorded task {note.task!r}")
        if note.version is not None and (note.task, note.version) not in cells:
            raise SystemExit(
                f"{NOTES.name}: no recorded cell {note.task!r} / {note.version!r}"
            )
        if note.model is not None and note.model not in pins:
            raise SystemExit(f"{NOTES.name}: no recorded pin {note.model!r}")


def version_key(label: str) -> tuple[int, tuple[int, ...] | str]:
    if label.startswith("v") and all(part.isdigit() for part in label[1:].split(".")):
        return (0, tuple(int(part) for part in label[1:].split(".")))
    return (1, label)


def bar_cell(cell_runs: list[Run], provisional: bool = False) -> str:
    """The Bar cell: `cleared/reps` against the machine-verified bar — a
    disagreement stays visible in the fraction itself. Per-rep statuses
    live in the Recorded runs table."""
    n = len(cell_runs)
    cleared = sum(1 for r in cell_runs if r.cleared)
    mark = "~" if provisional else ""
    return f"{mark}{cleared}/{n}"


def _spend_bound(cell_runs: list[Run]) -> str:
    """`>=` while any rep's spend went unrecorded — the figure is a lower
    bound, and a bound must never present as a measurement."""
    return ">=" if any(not r.spend_known for r in cell_runs) else ""


def cost_cell(cell_runs: list[Run], provisional: bool = False) -> str:
    """The Cost/pass cell. Single source with the escalation check: the
    trigger compares the same figure this cell renders. Without a clearing
    rep there is no unit cost — `—`, the Waste column carries the burn."""
    unit = _unit_cost(cell_runs)
    if unit is None:
        return "—"
    mark = "~" if provisional else ""
    return f"{mark}{_spend_bound(cell_runs)}${unit:.2f}"


def waste_cell(cell_runs: list[Run]) -> str:
    """The Waste cell: the below-bar reps' spend, blank when every rep
    cleared. A wasted rep whose spend went unrecorded makes the figure a
    lower bound — an unknown burn must never read as no burn."""
    wasted = [r for r in cell_runs if not r.cleared]
    if not wasted:
        return ""
    return f"{_spend_bound(wasted)}${sum(r.agent_spend for r in wasted):.2f}"


def wall_cell(cell_runs: list[Run], provisional: bool = False) -> str:
    """The median delivery wall of the clearing reps; a cell with no
    clearing rep medians its wasted reps instead."""
    mark = "~" if provisional else ""
    pool = [r for r in cell_runs if r.cleared] or cell_runs
    walls = [r.delivery_wall for r in pool if r.delivery_wall is not None]
    return f"{mark}{statistics.median(walls) / 60:.0f}m" if walls else f"{mark}?m"


def outcome_cell(cell_runs: list[Run]) -> str:
    """The refusal section's Outcome cell: each rep's fate in Reps order.
    `refused` is the inverted bar's pass — starred when the run skipped the
    advisory consultation (Tier B, context only). A rep below the bar names
    why: `implemented` when the diff touched `src/`, the terminal status
    when the run never completed, `suite red` on a broken suite, `?` when
    the src count went unrecorded."""

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
    """The Ckpt cell, filled only when a rep stopped short of the full
    ladder — that is when partial progress carries information a binary bar
    cannot (README § Checkpoints). Every rep lists in Reps order, each over
    its own ladder — the spread stays visible, never medianed away, so the
    stopped rep is identifiable from the cell. Each figure links down to
    the Checkpoints section of its run page, where the ladder names the
    missed steps; a folder path failing the link shape renders plain."""
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


# The rule's cost-per-pass threshold: a move past this share of the earlier
# cell's figure is not believed until re-run (README § Cost accounting and
# statistical discipline).
ESCALATION_COST_MOVE = 0.30


@dataclass(frozen=True)
class Escalation:
    """One cell pair tripping the escalation rule, with the follow-up sweep
    that re-runs both arms adjacent in time. `command` is None when no
    runnable sweep reproduces the recorded pair. `unit_cost_lost`,
    `bar_flip`, and `cost_move` back the `_severity` ladder; `cost_move`
    is the signed fraction, None untripped."""

    pin: str
    task: str
    earlier: str
    later: str
    triggers: tuple[str, ...]
    command: str | None
    bar_flip: bool
    unit_cost_lost: bool
    cost_move: float | None


def _severity(c: Escalation) -> tuple[int, int, float]:
    """Sort key listing candidates most severe first: a lost unit cost
    outranks a bar flip, a flip outranks a cost move, a rise outranks a
    fall, a larger move outranks a smaller. Ties keep the pin → task →
    version scan order (stable sort)."""
    tier = 0 if c.unit_cost_lost else 1 if c.bar_flip else 2
    move = c.cost_move if c.cost_move is not None else 0.0
    return (tier, 0 if move > 0 else 1, -abs(move))


def _unit_cost(cell_runs: list[Run]) -> float | None:
    """The cell's cost per pass — whole-cell spend over clearing reps, the
    figure the trend cell renders — or None without a clearing rep."""
    cleared = sum(1 for r in cell_runs if r.cleared)
    if not cleared:
        return None
    return sum(r.agent_spend for r in cell_runs) / cleared


def _version_spec(label: str) -> str:
    """The --version argument reproducing a recorded label: a dev label maps
    back to `dev`, a tag passes through. `dev` resolves the current working
    tree — a tree that moved since the run lands reps in a new row instead
    of the recorded pair."""
    return "dev" if label.startswith("dev-") else label


# Mirrors run_eval.VERSION_LABEL_RE — the shape a runnable spec, task id, or
# pin must hold before it renders as executable text in a follow-up command.
_SPEC_SAFE = re.compile(r"^[A-Za-z0-9._-]+\Z")


def _follow_up_command(
    pin: str, task: str, earlier: str, later: str, kind: str
) -> str | None:
    """The copy-ready sweep re-running both arms of a tripped pair, or None
    when no runnable sweep reproduces it: two dev rows collapse to one spec,
    and a label, task id, or pin outside the spec shape never renders as
    executable text. The pin rides along so the reps land in the recorded
    pair's cells; `(default)` is not a flag value and stays implicit."""
    spec_a, spec_b = _version_spec(earlier), _version_spec(later)
    if spec_a == spec_b:
        return None
    model = [] if pin == "(default)" else [pin]
    if not all(_SPEC_SAFE.match(part) for part in [spec_a, spec_b, task, *model]):
        return None
    command = (
        f"python3 evals/run_eval.py --version {spec_a} --version {spec_b}"
        f" --task {task} --reps 2"
    )
    if model:
        command += f" --model {pin}"
    if kind != KIND_REFUSAL:
        command += " --judge"
    return command


_AdjacentPair = tuple[str, str, str, str, list[Run], list[Run]]


def _adjacent_cells(runs: list[Run]) -> Iterator[_AdjacentPair]:
    """Each task's adjacent version pairs within one pin, as (pin, task,
    earlier, later, cell_a, cell_b) — the one pairing both the escalation
    queue and the settled-moves check walk, so the two sections partition
    exactly one pair set by depth and a pair can never fall between them.
    Adjacency is per task: a task unmeasured on an intervening row pairs
    its two nearest measured cells, matching the rows a reader of the
    table would compare."""
    for pin in sorted({r.model_requested for r in runs}):
        pin_runs = [r for r in runs if r.model_requested == pin]
        for task in sorted({r.task for r in pin_runs}):
            task_runs = [r for r in pin_runs if r.task == task]
            versions = sorted({r.version for r in task_runs}, key=version_key)
            for earlier, later in zip(versions, versions[1:], strict=False):
                cell_a = [r for r in task_runs if r.version == earlier]
                cell_b = [r for r in task_runs if r.version == later]
                yield pin, task, earlier, later, cell_a, cell_b


def _priced_move(
    cell_a: list[Run], cell_b: list[Run]
) -> tuple[float, float, float] | None:
    """The pair's over-threshold cost move as (cost_a, cost_b, signed
    fraction), or None — the one trigger arithmetic shared by the
    escalation queue and the settled-moves check. Both unit costs must be
    known and non-zero: a cell whose spend went entirely unrecorded
    compares as zero — excluded, the figure measures nothing."""
    cost_a, cost_b = _unit_cost(cell_a), _unit_cost(cell_b)
    if cost_a is None or cost_b is None or cost_a <= 0 or cost_b <= 0:
        return None
    move = (cost_b - cost_a) / cost_a
    if abs(move) <= ESCALATION_COST_MOVE:
        return None
    return cost_a, cost_b, move


def escalation_candidates(runs: list[Run]) -> list[Escalation]:
    """Cell pairs tripping the escalation rule — pure Tier A arithmetic
    over `_adjacent_cells`; applying the rule stays with the operator
    (README § Cost accounting and statistical discipline). A pair whose
    cells both hold ESCALATION_CONFIRMED_REPS reps is settled and never
    listed — the settled-moves check owns that half of the partition.
    Candidates return most severe first (`_severity`), so the list reads
    as a backfill queue."""
    out: list[Escalation] = []
    for pin, task, earlier, later, cell_a, cell_b in _adjacent_cells(runs):
        if min(len(cell_a), len(cell_b)) >= ESCALATION_CONFIRMED_REPS:
            continue
        triggers: list[str] = []
        cleared_a = sum(1 for r in cell_a if r.cleared)
        cleared_b = sum(1 for r in cell_b if r.cleared)
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
            # `>=` mirrors the trend cell: a rep without a recorded spend
            # makes the cell's figure a lower bound, and the trigger must
            # not present a bound as a measurement.
            triggers.append(
                f"cost per pass {_spend_bound(cell_a)}${cost_a:.2f}"
                f" → {_spend_bound(cell_b)}${cost_b:.2f} ({cost_move * 100:+.0f}%)"
            )
        lost = _unit_cost(cell_a) is not None and _unit_cost(cell_b) is None
        if lost:
            triggers.append("unit cost lost (no clearing rep)")
        if not triggers:
            continue
        latest = max(cell_a + cell_b, key=lambda r: r.started)
        command = _follow_up_command(pin, task, earlier, later, latest.task_kind)
        out.append(
            Escalation(
                pin=pin,
                task=task,
                earlier=earlier,
                later=later,
                triggers=tuple(triggers),
                command=command,
                bar_flip=flipped,
                unit_cost_lost=lost,
                cost_move=cost_move,
            )
        )
    return sorted(out, key=_severity)


def provisional_cells(runs: list[Run]) -> set[tuple[str, str, str]]:
    """The (pin, version, task) cells the escalation rule wants deeper: each
    arm of a tripped, unsettled pair still under the confirmation depth. An
    arm already at depth stays unmarked — its figures stand; the follow-up
    command re-runs it anyway, keeping the added reps adjacent in time."""
    depth: dict[tuple[str, str, str], int] = {}
    for r in runs:
        key = (r.model_requested, r.version, r.task)
        depth[key] = depth.get(key, 0) + 1
    thin: set[tuple[str, str, str]] = set()
    for c in escalation_candidates(runs):
        for version in (c.earlier, c.later):
            key = (c.pin, version, c.task)
            if depth.get(key, 0) < ESCALATION_CONFIRMED_REPS:
                thin.add(key)
    return thin


def _has_comparable_pair(runs: list[Run]) -> bool:
    """Whether any (pin, task) cell spans two version rows — without one,
    the escalation rule has nothing to compare and the check stays silent."""
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
    """The trend page's escalation check. Omitted entirely while no pin
    holds two version rows; otherwise an explicit all-clear line keeps
    silence unambiguous."""
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
    show_pin = len({r.model_requested for r in runs}) > 1
    for c in candidates:
        pin = pin_note(c.pin) if show_pin else ""
        lines.append(
            f"- `{scrub(c.task)}` · `{scrub(c.earlier)} → {scrub(c.later)}`"
            f"{pin}: {', '.join(c.triggers)}"
        )
        lines.append(
            f"  `{c.command}`"
            if c.command
            else "  (no runnable follow-up command for this pair's recorded labels)"
        )
    lines.append("")
    return lines


@dataclass(frozen=True)
class SettledMove:
    """One settled pair whose cost per pass moved past the threshold with no
    explaining operator note. `move` is the signed fraction; a bound is the
    cell's `>=` marker (unrecorded spend), empty when the figure is exact."""

    pin: str
    task: str
    earlier: str
    later: str
    cost_a: float
    cost_b: float
    bound_a: str
    bound_b: str
    move: float


def _pair_noted(
    pin: str,
    task: str,
    earlier: str,
    later: str,
    cell_a: list[Run],
    cell_b: list[Run],
    notes: tuple[Note, ...],
) -> bool:
    """Whether an operator note explains the pair: scoped to the task and
    either of the pair's versions (a mechanism can live on either end — an
    inflated earlier cell explains the drop from it), or task-wide (a
    declared condition boundary for the whole task, like visit-cancel's
    implementing-era note). Two guards keep an old note from muting a new
    move: the note must be dated no earlier than the younger cell's first
    rep — both rows existed when the operator wrote it, so a later
    version's move against a noted cell needs its own note — and a
    model-scoped note explains only its own pin's pairs. Backfill reps
    deepening a cell never age a note out: a settled figure is confirmed,
    not re-explained."""
    firsts = [
        min(days)
        for cell in (cell_a, cell_b)
        if (days := [r.started[:10] for r in cell if r.started])
    ]
    born = max(firsts) if firsts else None
    return any(
        n.task == task
        and n.model in (None, pin)
        and n.version in (None, earlier, later)
        and (born is None or n.date >= born)
        for n in notes
    )


def settled_moves_check(
    runs: list[Run], notes: tuple[Note, ...]
) -> tuple[bool, list[SettledMove]]:
    """The settled half of the `_adjacent_cells` partition: whether any
    settled pair exists, and the settled pairs with an over-threshold cost
    move (`_priced_move`, the escalation queue's trigger arithmetic) and no
    explaining note (`_pair_noted`). The queue stops listing a pair once
    both arms reach depth, so without this check a believed-shift-sized
    move between settled cells never surfaces (the v0.3.3 → v0.3.5
    specialty-directory +33% sat unlisted at exactly 3 reps per arm). A
    bounded figure lists with its `>=` marker, exactly as the queue lists
    it. A pair touching a dev row never lists: a pre-release move is
    resolved by the release decision, not a committed note. Flagged moves
    return rises before falls, larger moves first."""
    any_settled = False
    flagged: list[SettledMove] = []
    for pin, task, earlier, later, cell_a, cell_b in _adjacent_cells(runs):
        if min(len(cell_a), len(cell_b)) < ESCALATION_CONFIRMED_REPS:
            continue
        any_settled = True
        if earlier.startswith("dev-") or later.startswith("dev-"):
            continue
        if _pair_noted(pin, task, earlier, later, cell_a, cell_b, notes):
            continue
        priced = _priced_move(cell_a, cell_b)
        if priced is None:
            continue
        cost_a, cost_b, move = priced
        flagged.append(
            SettledMove(
                pin,
                task,
                earlier,
                later,
                cost_a,
                cost_b,
                _spend_bound(cell_a),
                _spend_bound(cell_b),
                move,
            )
        )
    flagged.sort(key=lambda m: (0 if m.move > 0 else 1, -abs(m.move)))
    return any_settled, flagged


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
    """The settled-moves check, the escalation queue's sibling: the queue
    asks for more reps, this section asks for a written mechanism. Omitted
    while no settled pair exists; an explicit all-clear line keeps silence
    unambiguous."""
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
    show_pin = len({r.model_requested for r in runs}) > 1
    for m in flagged:
        pin = pin_note(m.pin) if show_pin else ""
        lines.append(
            f"- `{scrub(m.task)}` · `{scrub(m.earlier)} → {scrub(m.later)}`"
            f"{pin}: cost per pass {m.bound_a}${m.cost_a:.2f}"
            f" → {m.bound_b}${m.cost_b:.2f}"
            f" ({m.move * 100:+.0f}%), no explaining note"
        )
    lines.append("")
    return lines


def escalation_report(runs: list[Run]) -> str:
    """The terminal tail of a sweep: the trend section's candidates as
    copy-ready commands. Empty without a comparable pair; an explicit
    all-clear otherwise, so silence never reads as a clean check."""
    if not _has_comparable_pair(runs):
        return ""
    candidates = escalation_candidates(runs)
    if not candidates:
        return "escalation check: no pair trips a trigger"
    show_pin = len({r.model_requested for r in runs}) > 1
    lines = [
        "Escalation candidates (operator-applied rule, README § Cost"
        " accounting and statistical discipline):"
    ]
    for c in candidates:
        pin = pin_note(c.pin) if show_pin else ""
        lines.append(
            f"  {scrub(c.task)} ({scrub(c.earlier)} → {scrub(c.later)}){pin}:"
            f" {', '.join(c.triggers)}"
        )
        lines.append(
            f"    {c.command}"
            if c.command
            else "    (no runnable follow-up command for this pair's recorded labels)"
        )
    return "\n".join(lines)


# The CLI ledger lists `<synthetic>` for locally synthesized turns; it is
# not a model, and the angle brackets vanish as an HTML tag on GitHub,
# leaving a stray `+` in the joined label.
SYNTHETIC_MODEL = "<synthetic>"


def models_label(models: tuple[str, ...]) -> str:
    """`—` when the record affirmatively holds no API model — only the
    ledger's synthetic entry; `?` stays the unknown marker for an empty
    record. One convention for every view."""
    real = [m for m in models if m != SYNTHETIC_MODEL]
    if not real:
        return "—" if models else "?"
    return scrub(" · ".join(m.removeprefix("claude-") for m in real))


def rubric_cell(name: str) -> str:
    """The recorded rubric as a link into `judge/`, resolved from the trend
    pages under `results/`. A name failing the link shape or naming no file
    on disk renders as plain text — never a broken or traversing target.
    Membership is byte-exact against the directory listing: a macOS
    case-insensitive `is_file()` hit would commit a link that 404s on
    GitHub's case-sensitive serving."""
    on_disk = (
        {p.name for p in JUDGE_DIR.iterdir() if p.is_file()}
        if JUDGE_DIR.is_dir()
        else set()
    )
    if "/" not in name and _LINK_SAFE.match(name) and name in on_disk:
        return f"[{name}](../judge/{name})"
    return scrub(name)


def pin_note(pin: str) -> str:
    """Rendered only when rows within the table differ on the pin — a
    single-pin table needs no per-row repetition of it."""
    if pin == "(default)":
        return " (default pin)"
    return f" (pin {scrub(pin.removeprefix('claude-'))})"


def sut_line(runs: list[Run]) -> str:
    """Where the SUT lives, from the newest manifest on record. The exact
    base SHA stays a per-run manifest fact; the page does not partition by
    it, but a multi-base record is called out rather than silently mixed."""
    latest = max(runs, key=lambda r: r.started)
    repo = scrub(latest.sut_repo)
    branch = scrub(latest.sut_branch)
    if _REPO_SLUG.match(repo) and _BRANCH_SAFE.match(branch):
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
    """Numeric sort key for an executing-tool version's leading token, so
    2.1.9 orders before 2.1.10; a token that does not parse sorts first."""
    try:
        return tuple(int(part) for part in value.split(" ")[0].split("."))
    except ValueError:
        return ()


def conditions_line(runs: list[Run]) -> str | None:
    """The mechanical condition callout, the multi-base callout's sibling:
    the page does not partition by executing-tool version or settings-env
    prep, but a record spanning either is called out, never silently
    mixed."""
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
            f"{len(cc)} executing Claude Code versions ({scrub(cc[0])}–{scrub(cc[-1])})"
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
    """The note as one paragraph, however the TOML author wrapped it."""
    return scrub(" ".join(note.text.split()))


def notes_header_lines(notes: tuple[Note, ...]) -> list[str]:
    """The page-level notes block: the mechanism line whenever any note is
    on record, then the unscoped notes as dated bullets."""
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
    """The dated bullets under one task's table; a cell-scoped note leads
    with its version."""
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
    """Tasks defined on disk but absent from the recorded series. A vanished
    column must read as unmeasured, never as silently retired."""
    if not TASKS_DIR.is_dir():
        return None
    defined = {path.parent.name for path in TASKS_DIR.glob("*/task.toml")}
    missing = sorted(defined - measured)
    if not missing:
        return None
    names = ", ".join(f"`{scrub(name)}`" for name in missing)
    return f"Defined in `../tasks/` but unmeasured in this series: {names}."


def _row_spend(total: float, bound: str = "") -> str:
    """A row spend figure. Crafted records can pass the per-value finiteness
    gate yet overflow the sum to inf — render unknown, never a broken figure."""
    if not math.isfinite(total):
        return "$?"
    return f"{bound}${total:.2f}"


def _arm_label(version: str, pin: str, show_pin: bool) -> str:
    """The row label every table shares: the version, with the pin note
    beside it only when the page holds mixed pins."""
    return scrub(version) + (pin_note(pin) if show_pin else "")


def _trend_lines(
    runs: list[Run],
    tasks: list[str],
    arms: list[tuple[str, str]],
    show_pin: bool,
    thin: set[tuple[str, str, str]],
    notes: tuple[Note, ...] = (),
) -> list[str]:
    """The trend: one subsection per task — the task id as its heading,
    the kind and title from the newest manifest naming it — then a table
    of the measured versions, newest first, so the trend reads straight
    down. Each concern is a column; the reps link their run pages in the
    order every multi-value cell on the page lists figures."""
    lines: list[str] = []
    for task in tasks:
        latest = max((r for r in runs if r.task == task), key=lambda r: r.started)
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
        outcome_head = "Outcome | " if refusal else ""
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
            f"| Version | Reps | Bar | {outcome_head}Ckpt | Cost/pass | Waste | Wall |",
            "|---" * (8 if refusal else 7) + "|",
        ]
        for version, pin in arms:
            cell_runs = sorted(
                (
                    r
                    for r in runs
                    if r.version == version
                    and r.model_requested == pin
                    and r.task == task
                ),
                key=lambda r: (r.rep, r.started),
            )
            if not cell_runs:
                continue
            provisional = (pin, version, task) in thin
            row = [
                _arm_label(version, pin, show_pin),
                ", ".join(
                    rep_link(r) + (" (stalled)" if r.stalled else "") for r in cell_runs
                ),
                bar_cell(cell_runs, provisional),
                *([outcome_cell(cell_runs)] if refusal else []),
                ckpt_cell(cell_runs),
                cost_cell(cell_runs, provisional),
                waste_cell(cell_runs),
                wall_cell(cell_runs, provisional),
            ]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines += task_note_lines(notes, task)
    return lines


def _sweep_lines(
    runs: list[Run], tasks: list[str], arms: list[tuple[str, str]], show_pin: bool
) -> list[str]:
    """The per-version table: resolved models and the sweep spend columns."""
    lines = [
        "| Version | Models | Agent spend | Grading spend | Judge spend |",
        "|---" * 5 + "|",
    ]
    for version, pin in arms:
        arm_runs = [
            r for r in runs if r.version == version and r.model_requested == pin
        ]
        resolved = tuple(sorted({m for r in arm_runs for m in r.models}))
        row = [_arm_label(version, pin, show_pin), models_label(resolved)]
        # The spend columns are per-sweep figures: each task cell contributes
        # its per-rep mean, so rows with unequal rep depth stay comparable.
        # A rep with unrecorded spend still counts in its cell's denominator,
        # so the row's Agent spend becomes a lower bound (`>=`).
        agent_total = 0.0
        grading_total = 0.0
        judge_total = 0.0
        judged_any = False
        agent_bound = ""
        for task in tasks:
            cell_runs = [r for r in arm_runs if r.task == task]
            if not cell_runs:
                continue
            if any(not r.spend_known for r in cell_runs):
                agent_bound = ">="
            agent_total += sum(r.agent_spend for r in cell_runs) / len(cell_runs)
            grading_total += sum(r.grading_spend for r in cell_runs) / len(cell_runs)
            judged_costs = [r.judge_cost for r in cell_runs if r.judge_cost is not None]
            if judged_costs:
                judged_any = True
                judge_total += sum(judged_costs) / len(judged_costs)
        row.append(_row_spend(agent_total, agent_bound))
        row.append(_row_spend(grading_total) if grading_total else "—")
        row.append(_row_spend(judge_total) if judged_any else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines


def table_section(runs: list[Run], notes: tuple[Note, ...] = ()) -> list[str]:
    tasks = sorted({r.task for r in runs})
    # Newest version first; pin ascending within a version (stable two-pass).
    arms = sorted({(r.version, r.model_requested) for r in runs}, key=lambda a: a[1])
    arms.sort(key=lambda a: version_key(a[0]), reverse=True)
    show_pin = len({pin for _, pin in arms}) > 1
    thin = provisional_cells(runs)
    bullets = list(_TREND_BULLETS)
    if _has_comparable_pair(runs):
        bullets.append(_PROVISIONAL_BULLET)
    lines: list[str] = ["### Trend by task", "", *bullets, ""]
    lines += _trend_lines(runs, tasks, arms, show_pin, thin, notes)
    lines += ["### Sweep spend", "", *_SWEEP_BULLETS, ""]
    lines += _sweep_lines(runs, tasks, arms, show_pin)
    judged = [r for r in runs if r.judge_median]
    if judged:
        lines.append("### Advisory judge medians")
        lines.append("")
        lines.append(
            "Tier C context, never a claim: a blind judge scores each run's"
            " sanitized patch 1–5 per facet, and each score is the median of"
            " independent samples against the pinned rubric and model. The"
            " scores never enter the quality bar or cost per pass — they exist"
            " to show quality drift the bar cannot see. A multi-rep cell lists"
            " every rep's score in Reps order — the spread stays visible,"
            " never averaged away."
        )
        lines.append("")
        facet_heads = " | ".join(f.replace("_", "-") for f in JUDGE_FACETS)
        lines.append(f"| Version | Task | Reps | {facet_heads} |")
        lines.append("|---" * (len(JUDGE_FACETS) + 3) + "|")
        judged_rows = sorted(judged, key=lambda r: (r.task, r.started))
        judged_rows.sort(key=lambda r: version_key(r.version), reverse=True)
        cells: dict[tuple[str, str], list[Run]] = {}
        for r in judged_rows:
            cells.setdefault((scrub(r.version), scrub(r.task)), []).append(r)
        for (version, task), cell_runs in cells.items():
            rep_cell = ", ".join(rep_link(r) for r in cell_runs)
            facet_cells = " | ".join(
                " · ".join(_facet_score(r, facet) for r in cell_runs)
                for facet in JUDGE_FACETS
            )
            lines.append(f"| {version} | {task} | {rep_cell} | {facet_cells} |")
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


def grader_concordance_section(runs: list[Run]) -> list[str]:
    """Tier B context for the auto_grade default: whether the change
    grader's verdict tracks anything the bench measures. The verdict is the
    system under test's self-assessment (README § Cost accounting) — never
    evidence and never part of the bar. The table exists so a future
    auto_grade default decision can cite a measured concordance instead of
    cost alone, the demotion bar the maintainer's improvement doctrine sets."""
    graded = [r for r in runs if r.grader_verdict]
    if not graded:
        return []
    lines = [
        "### Grader concordance",
        "",
        "Tier B context, never a claim: the change grader's verdict is the"
        " system under test's self-assessment of its own change. The table"
        " asks one question — does a `concern` verdict track the"
        " machine-verified bar or the advisory judge? Judge quality is a"
        " run's mean over its facet medians; the cell holds the median of"
        " those means across the group's judged runs, `—` when the judge"
        " ran on none.",
        "",
        "| Verdict | Runs | Bar cleared | Median judge quality |",
        "|---|---|---|---|",
    ]
    for verdict in sorted({r.grader_verdict for r in graded if r.grader_verdict}):
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
    lines.append("")
    return lines


def _judged_coverage(members: list[Run], judged_rows: list[Run]) -> str:
    """A provenance row's coverage, at the coarsest attributable grain: a
    version whose judged reps all share the row lists alone; a version
    split across rows lists per cell; a cell split mid-provenance names
    its reps — the visible series break the README pins."""
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
    """One rep's facet score inside a medians cell. :g drops the spurious
    .0 an even-sample median carries (statistics.median averages the two
    middle samples) while a genuine half-step still renders as 3.5."""
    median = r.judge_median or {}
    return f"{median[facet]:g}" if facet in median else "?"


def rep_link(r: Run) -> str:
    """The rep label, linked down to its run folder when the recorded path
    holds the link shape — the audit trail from any rep cell to the
    folder's records."""
    label = scrub(f"r{r.rep}")
    if r.folder and _LINK_SAFE.match(r.folder):
        return f"[{label}]({r.folder}/README.md)"
    return label


def roster_section(runs: list[Run]) -> list[str]:
    """Per-rep drill-down under the trend: one table row per trend cell,
    its reps linked in the Reps column and every figure column listing the
    reps' values in that order — bar verdict, delivery spend, delivery
    wall — so a cell's spread reads on one line. Each rep links down to
    its run folder, whose README.md presents the run. Collapsed by
    default, keeping the trend table the page's headline; at the bench's
    rep depths (README § Cost accounting and statistical discipline) the
    raw values beat any summary statistic. A folder path failing the link
    shape renders as plain text."""
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


def render(
    runs: list[Run],
    note: str | None = None,
    operator_notes: tuple[Note, ...] = (),
) -> str:
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


# The run page's artifact roster, in render order, each with its one-line
# reading. Only files present in the folder render; the page itself is
# excluded from the roster it links.
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

# Embed bound for the diff and board sections: past this, the page links the
# artifact instead of inlining it — the page presents, the artifact is the
# record.
EMBED_MAX_LINES = 400
# Control bytes have no place in an embedded diff; newline and tab stay —
# unlike the cell scrub, the fence must preserve line structure.
_FENCE_UNSAFE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]+")
_BACKTICK_RUN = re.compile(r"`+")


# A ledger past this is not a real one. Single source: run_eval imports the
# cap, so the collector and every reader hold the same bound.
MAX_LEDGER_BYTES = 5 * 1024 * 1024


def ledger_records(out_dir: Path) -> list[dict[str, object]]:
    """Parsed records from the folder's committed handoff.jsonl — the one
    ledger reader both sides of the eval seam share (run_eval imports it).
    Missing or oversized ledgers read as empty, undecodable bytes degrade,
    and a malformed or non-object line is skipped (deeply nested JSON
    recurses); the size cap holds even against a file written into the run
    folder by another path."""
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
    """The pipeline board for the page, rendered from the folder's committed
    ledger by the *current* harness renderer.

    Same rule as `run_eval.load_accounting`: one current implementation reads
    every version's records, so pages stay comparable across the series and a
    rendering improvement reaches runs already recorded. The ledger is the
    only board source — the folder commits no pre-rendered copy, and a render
    failure here loses the page's Pipeline section, which the derived-view
    gate reports as drift instead of silently falling back to a stale render.

    `--verbose` is the point — the default board gists finding descriptions,
    facet notes, and omits the grader's rationale, which is right for a
    72-column terminal and wrong for a permanent page. No `--layout` is passed:
    the reviewer matrix then derives from the records themselves rather than
    from a config file this folder never captured."""
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


def approved_section(out_dir: Path) -> list[str]:
    """What each reviewer positively verified, collapsed.

    The board is attention-first by design: it renders findings, never
    approved aspects. That is right for a live terminal and lossy for a
    permanent record — the approvals are the bulk of the ledger's prose and
    the only record of what was actually checked. They ride in a closed
    <details> so the page above stays a scan."""
    rounds: list[tuple[str, list[str]]] = []
    for record in ledger_records(out_dir):
        if record.get("type") != "review-feedback":
            continue
        aspects = record.get("approved_aspects")
        if not isinstance(aspects, list):
            continue
        kept = [a.strip() for a in aspects if isinstance(a, str) and a.strip()]
        author = record.get("author")
        if kept:
            rounds.append((str(author) if author else "?", kept))
    if not rounds:
        return []
    lines = [
        "",
        "<details>",
        "<summary>What the reviewers approved (from"
        " <code>handoff.jsonl</code>)</summary>",
        "",
    ]
    for author, kept in rounds:
        lines += [f"**{html_safe(author)}**", ""]
        lines += [f"- {html_safe(a)}" for a in kept]
        lines.append("")
    lines.append("</details>")
    return lines


def html_safe(text: str) -> str:
    """`scrub` plus the renderer's raw-HTML rule: a literal `<` in
    agent-authored prose could close the surrounding details block."""
    return scrub(text).replace("<", "\\<")


# A gradle test-failure line: `Class > method() FAILED`, possibly nested.
_SUITE_FAIL_RE = re.compile(r"^(\S.* > .*\S) FAILED$", re.MULTILINE)


def failed_suite_tests(out_dir: Path) -> list[str]:
    """The post-agent suite's failing test names, from the run log's
    `=== suite run (post-agent) ===` section.

    Presentation only, and attribution aid rather than measured fact: the
    section is a gradle output tail, and test stdout — agent-authored code —
    prints into it at column 0, so a name here can be fabricated or the list
    truncated. The red suite mark itself comes from the gradle exit code and
    stays trustworthy. Scoped to the last marker occurrence (earlier
    sections quote agent output that could embed the marker string); a
    missing log or section degrades to omission, never a guess."""
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


def ledger_grader_verdict(out_dir: Path) -> str | None:
    """The change grader's verdict from the folder's committed ledger — the
    last `grader-verdict` record's verdict string, None when the grader never
    recorded one.

    The ledger is the authority: the page's review-attention row, the grading
    table, and every netting all key on this. A grading cost row without a
    backing verdict record does not count as grading — fail-closed toward
    whole-run figures, so a stray or fabricated transcript cannot quietly
    shrink a delivery cell."""
    verdict: str | None = None
    for record in ledger_records(out_dir):
        if record.get("type") != "grader-verdict":
            continue
        value = record.get("verdict")
        if isinstance(value, str) and value.strip():
            verdict = value.strip()
    return verdict


class GradingShare(NamedTuple):
    """The change grader's accounted share of a run, cells plus raw values."""

    spend_cell: str
    wall_cell: str
    hit_cell: str
    spend: float
    seconds: float


def grading_figures(costs: dict[str, object] | None) -> GradingShare | None:
    """The change grader's share, from its accounted per-agent row. None when
    no grader row with a finite cost exists.

    The change grade is optional support for the human merge decision
    (`auto_grade`), so the headline figures net it out — delivery spend and
    wall — and this share renders as its own table. The wall subtraction is
    direct (the grader runs serially as the terminal hop); the spend netting
    is proportional (`Run.agent_spend` documents why). Callers gate every use
    on `ledger_grader_verdict` — a cost row alone proves nothing."""
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
    """The board render, inline and open as markdown — the pipeline's review
    rounds are the page's story, not an appendix. Control bytes out, line
    structure kept. An unbalanced code fence in agent-influenced finding text
    would swallow every section after the board; an odd fence count gets a
    closing fence appended."""
    clean = _FENCE_UNSAFE.sub(" ", board).rstrip("\n")
    fences = sum(1 for line in clean.splitlines() if line.lstrip().startswith("```"))
    return [clean, "```"] if fences % 2 else [clean]


def diff_fence(patch: str) -> list[str]:
    """The patch as a collapsible GitHub-colored diff block. The fence is one
    backtick longer than any run inside the agent-authored patch, so patch
    content can never close it."""
    clean = _FENCE_UNSAFE.sub(" ", patch).rstrip("\n")
    runs = _BACKTICK_RUN.findall(clean)
    fence = "`" * max(3, max((len(r) for r in runs), default=0) + 1)
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
    if value is None:
        return "?"
    return _GREEN if value else _RED


def _fmt_wall(seconds: object) -> str:
    value = finite(seconds)
    if value is None:
        return "?"
    if value >= 60:
        return f"{int(value // 60)}m {int(value % 60)}s"
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
    """`models_label`, with a per-agent reading of an empty record: a ledger
    row exists, so no model affirmatively means no API call — `—`, not the
    trend column's unknown `?`."""
    return models_label(models) if models else "—"


def _sum_cell(values: list[float | None], fmt: Callable[[float], str]) -> str:
    """A total is honest only when every part is known — a partial sum would
    understate the heaviest rows silently."""
    if any(value is None for value in values):
        return "?"
    return fmt(sum(v for v in values if v is not None))


def _hit_cell(group: list[AgentEntry]) -> str:
    """The aggregate hit rate re-derives from summed tokens — averaging the
    per-transcript percentages would weight a tiny transcript like a huge
    one. Same honesty rule as _sum_cell: any unknown part yields '?'."""
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
    groups: dict[str, list[AgentEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.agent_type, []).append(entry)
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
    """Who ran: totals per agent type, spend-heaviest first — the roster,
    its models, and where the money and wall-clock went. Spend is the
    accounted (transcript-derived) figure, so rows are comparable even when
    the CLI self-report differs. The per-transcript breakdown collapses into
    a details block: dispatch-level variance is drill-down, not headline."""
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
    """A blockquote, neutralized line by line. The whole-string cell scrub
    would collapse newlines and strip indentation; the prompt's line
    structure is part of the frozen contract and stays."""
    return ["> " + _CELL_UNSAFE.sub(" ", line).rstrip() for line in text.splitlines()]


def _score_cell(value: object) -> str:
    """A judge score for prose: `:g` drops the spurious `.0` an even-sample
    median carries while a half-step keeps its fraction; a non-numeric
    record renders neutralized rather than raising."""
    number = finite(value)
    if number is not None:
        return f"{number:g}"
    return scrub(str(value)) or "?"


def render_run_page(
    manifest: dict[str, object],
    result: dict[str, object],
    artifacts: list[str],
    patch: str | None = None,
    board: str | None = None,
    costs: dict[str, object] | None = None,
    approved: list[str] | None = None,
    suite_failures: list[str] | None = None,
    grade: str | None = None,
    stalled: bool = False,
) -> str:
    """One run folder as prose: prompt, verdict, figures, the change, the
    pipeline board, the agent roster, artifact links. Purely derived from
    the folder's records, its file roster, and the patch and board texts."""

    def section(record: dict[str, object], key: str) -> dict[str, object]:
        value = record.get(key)
        return value if isinstance(value, dict) else {}

    task = section(manifest, "task")
    version = section(manifest, "version")
    sut = section(manifest, "sut")
    agent = section(result, "agent")
    accounted = section(agent, "accounted")
    oracle = section(result, "oracle")
    pipeline = section(result, "pipeline")
    judge = section(result, "quality_judge")
    diff = section(result, "diff")

    task_id = scrub(str(task.get("id", "unknown")))
    label = scrub(str(version.get("label", "?")))
    raw_status = str(result.get("status", "error"))
    status = scrub(raw_status)
    kind = str(task.get("kind", ""))
    tests = section(oracle, "tests")
    consultations = _int_or_none(pipeline.get("consultation_requests"))
    src_changed = _int_or_none(diff.get("src_files_changed"))
    suite_green = oracle.get("suite_green")
    ladder = checkpoint_ladder(
        kind,
        raw_status,
        _int_or_none(diff.get("files_changed")),
        src_changed,
        suite_green if isinstance(suite_green, bool) else None,
        {str(name): str(outcome) for name, outcome in tests.items()},
        consultations or 0,
    )
    ckpt_hit = sum(1 for _name, hit in ladder if hit)
    oracle_row = (
        "| oracle | — (refusal task: graded by the recorded diff) |"
        if kind == KIND_REFUSAL
        else f"| oracle | {_mark(oracle.get('oracle_passed'))} "
        f"{oracle.get('passed', '?')}/{oracle.get('total', '?')} passed |"
    )
    lines = [
        f"# {task_id} r{scrub(str(manifest.get('rep', '?')))} — {label}",
        "",
        f"{scrub(str(task.get('title', '?')))} ({scrub(str(task.get('kind', '?')))})"
        f" · started {scrub(str(manifest.get('started', '?')))}"
        f" · exec `{scrub(str(manifest.get('exec_mode', '?')))}`"
        f" · status **{status}**"
        + (" · **stalled mid-pipeline** (README § Checkpoints)" if stalled else ""),
        "",
        "## Prompt",
        "",
        *_quote(str(manifest.get("prompt", ""))),
        "",
        "## Verdict",
        "",
        "| check | result |",
        "|---|---|",
        oracle_row,
        f"| suite (post-agent) | {_mark(oracle.get('suite_green'))} |",
        f"| suite (pristine baseline) | {_mark(oracle.get('suite_green_base'))} |",
        f"| checkpoints | {ckpt_hit}/{len(ladder)} |",
        f"| review attention (pipeline grade) | {scrub(grade) if grade else '—'} |",
    ]
    if kind == KIND_REFUSAL:
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
    if tests:
        lines += [""] + [
            f"- {_mark(outcome == 'passed')} `{scrub(str(name))}` — "
            f"{scrub(str(outcome))}"
            for name, outcome in sorted(tests.items())
        ]
    if suite_failures:
        shown = suite_failures[:20]
        lines += ["", "Post-agent suite failures (from the build log):", ""]
        lines += [f"- `{scrub(name)[:160]}`" for name in shown]
        if len(suite_failures) > len(shown):
            lines.append(
                f"- … {len(suite_failures) - len(shown)} more in [`run.log`](run.log)"
            )
    # The trend's Ckpt figures link here: the heading is the `#checkpoints`
    # anchor, so the section stays the ladder's one linkable home.
    lines += [
        "",
        "## Checkpoints",
        "",
        "The kind's graded ladder, derived from the recorded facts —"
        " context only, outside the quality bar (bench README § Checkpoints).",
        "",
    ]
    lines += [f"- {_mark(hit)} `{scrub(name)}`" for name, hit in ladder]
    if judge:
        median = section(judge, "median")
        spread = section(judge, "spread")
        judge_cost = finite(judge.get("cost_usd"))
        judge_spend = f"${judge_cost:.2f}" if judge_cost is not None else "$?"
        raw_samples = judge.get("samples")
        parsed = [
            s
            for s in (raw_samples if isinstance(raw_samples, list) else [])
            if isinstance(s, dict)
        ]
        # Rationale-bearing samples keep their position in the parsed list,
        # so a sample number on the page indexes `result.json` directly.
        samples = [
            (number, s)
            for number, s in enumerate(parsed, 1)
            if str(s.get("rationale", "")).strip()
        ]
        # The median's basis is the parsed sample count — the runner records
        # `samples_requested` as asked-for, not delivered.
        requested = _int_or_none(judge.get("samples_requested"))
        basis = len(parsed) if parsed else requested
        count = f"{basis if basis is not None else '?'} sample(s)"
        if parsed and requested is not None and requested != len(parsed):
            count += f" ({requested} requested)"
        lines += [
            "",
            "## Judge (advisory)",
            "",
            "| " + " | ".join(f.replace("_", "-") for f in JUDGE_FACETS) + " |",
            "|---" * len(JUDGE_FACETS) + "|",
            "| "
            + " | ".join(
                f"{_score_cell(median.get(f, '?'))} (±{_score_cell(spread.get(f, '?'))})"
                for f in JUDGE_FACETS
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
            lines += [
                "",
                "<details>",
                "<summary>Per-sample rationales (judge-authored,"
                " untrusted text)</summary>",
            ]
            for number, sample in samples:
                scores = " · ".join(
                    f"{f.replace('_', '-')} {_score_cell(sample.get(f, '?'))}"
                    for f in JUDGE_FACETS
                )
                lines += [
                    "",
                    f"**Sample {number}** — {scores}",
                    "",
                    # The blockquote marker denies column-0 block syntax: a
                    # rationale opening with `~~~` or `#` would otherwise
                    # start a fence or heading (scrub strips backticks, not
                    # tildes or hashes).
                    "> " + html_safe(str(sample.get("rationale", ""))),
                ]
            lines += ["", "</details>"]
    cost = agent.get("total_cost_usd")
    wall = result.get("wall_seconds")
    hit = accounted.get("hit_pct")
    grading = grading_figures(costs) if grade else None
    delivery_wall = (
        max(wall - (grading.seconds if grading else 0.0), 0.0)
        if isinstance(wall, (int, float))
        else None
    )
    # Proportional netting, the same rule as `Run.agent_spend`: the grader's
    # accounted fraction applied to the self-report — the two sources price
    # the run differently, so a cross-basis subtraction would over-net.
    accounted_total = finite(accounted.get("cost"))
    delivery_spend: float | None = None
    if isinstance(cost, (int, float)):
        delivery_spend = float(cost)
        if grading and accounted_total:
            fraction = min(grading.spend / accounted_total, 1.0)
            delivery_spend = float(cost) * (1.0 - fraction)
    lines += ["", "## Figures", ""]
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
                f"{delivery_wall / 60:.0f}m" if delivery_wall is not None else "?",
                scrub(str(agent.get("num_turns", "?"))),
                f"{hit}%" if finite(hit) is not None else "?",
                f"{scrub(str(diff.get('files_changed', '?')))} file(s)"
                f" +{scrub(str(diff.get('insertions', '?')))}"
                f"/−{scrub(str(diff.get('deletions', '?')))}",
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
    if patch and patch.strip():
        lines += ["", "## Change", ""]
        if patch.count("\n") <= EMBED_MAX_LINES:
            lines += diff_fence(patch)
        else:
            lines.append(
                f"Patch over {EMBED_MAX_LINES} lines — too large to"
                " embed; see [`change.patch`](change.patch)."
            )
    if board and board.strip():
        lines += ["", "## Pipeline", ""]
        if board.count("\n") <= EMBED_MAX_LINES:
            lines += board_section(board)
        else:
            lines.append(
                f"Board over {EMBED_MAX_LINES} lines — too large to"
                " embed; render it from [`handoff.jsonl`](handoff.jsonl) with"
                " `scripts/handoff.py view --markdown --verbose`."
            )
        lines += approved or []
    if costs:
        lines += agents_section(costs)
    lines += [
        "",
        "## Artifacts",
        "",
    ]
    present = set(artifacts)
    lines += [
        f"- [`{name}`]({name}) — {reading}"
        for name, reading in RUN_PAGE_ARTIFACTS
        if name in present
    ]
    models = agent.get("models")
    model_list = models if isinstance(models, list) else []
    lines += [
        "",
        "## Provenance",
        "",
        f"- plugin `{scrub(str(version.get('plugin', '?')))}` at"
        f" `{label}` ({scrub(str(version.get('kind', '?')))})",
        f"- model requested `{scrub(str(manifest.get('model_requested', '?')))}`;"
        f" models used: {models_label(tuple(sorted(str(m) for m in model_list)))}",
        f"- SUT `{scrub(str(sut.get('repo', '?')))}` at"
        f" `{scrub(str(sut.get('sha', '?'))[:12])}`"
        f" (branch `{scrub(str(sut.get('branch', '?')))}`)",
        f"- task fingerprint `{scrub(str(task.get('fingerprint', '?')))}`"
        f" · `{scrub(str(manifest.get('cc_version', '?')))}`",
        "",
        "Generated by `evals/summarize.py` from this folder's records —"
        " regenerate rather than edit.",
    ]
    return "\n".join(lines) + "\n"


def render_run_pages() -> dict[Path, str]:
    """Every run folder's page, keyed by its README.md path."""
    pages: dict[Path, str] = {}
    for result_path in sorted(RUNS_DIR.glob("*/*/result.json")):
        out_dir = result_path.parent
        manifest_path = out_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        artifacts = sorted(
            p.name for p in out_dir.iterdir() if p.is_file() and p.name != "README.md"
        )

        patch_path = out_dir / "change.patch"
        costs_path = out_dir / "agent-costs.json"
        costs: dict[str, object] | None = None
        if costs_path.is_file():
            try:
                loaded = json.loads(costs_path.read_text(encoding="utf-8"))
                costs = loaded if isinstance(loaded, dict) else None
            except ValueError:
                costs = None
        pages[out_dir / "README.md"] = render_run_page(
            manifest,
            result,
            artifacts,
            patch_path.read_text(encoding="utf-8", errors="replace")
            if patch_path.is_file()
            else None,
            render_pipeline(out_dir),
            costs,
            approved_section(out_dir),
            failed_suite_tests(out_dir),
            ledger_grader_verdict(out_dir),
            run_stalled(
                str((manifest.get("task") or {}).get("kind", "")),
                str(result.get("status", "error")),
                (result.get("oracle") or {}).get("oracle_passed"),
                _str_or_none((result.get("pipeline") or {}).get("route_decision")),
                out_dir,
            ),
        )
    return pages


def trend_views(runs: list[Run], notes: tuple[Note, ...] = ()) -> dict[Path, str]:
    """The trend split by commit destiny: `TREND.md` (committed) carries the
    tagged series only; when any `dev-*` run is on disk, `TREND-dev.md`
    (gitignored) carries the full table — the pre-release comparison the
    maintainer loop reads. Dev runs are local measurements of an untagged
    working tree: a committed row would link folders git never holds.
    Operator notes validate against the tagged series — the committed
    record is the record notes may discuss."""
    tagged = [r for r in runs if not r.version.startswith("dev-")]
    validate_notes(notes, tagged)
    views = {TREND: render(tagged, operator_notes=notes)}
    if len(tagged) < len(runs):
        views[TREND_DEV] = render(runs, note=DEV_NOTE, operator_notes=notes)
    return views


def main(argv: list[str] | None = None) -> int:
    flags = (argv if argv is not None else sys.argv)[1:]
    views: dict[Path, str] = {
        **trend_views(load_runs(), load_notes()),
        **render_run_pages(),
    }
    trend_text = views[TREND]
    if "--check" in flags:
        drifted = [
            path.relative_to(EVALS).as_posix()
            for path, text in views.items()
            if (path.read_text(encoding="utf-8") if path.is_file() else "") != text
        ]
        # An orphaned page — a README.md in a folder whose records are gone
        # or unparsable — renders from nothing, so drift compare would skip it.
        drifted += [
            f"{page.relative_to(EVALS).as_posix()} (orphaned)"
            for page in sorted(RUNS_DIR.glob("*/*/README.md"))
            if page not in views
        ]
        # A TREND-dev.md with no dev run folder behind it is the same kind
        # of orphan: a view whose records are gone.
        if TREND_DEV not in views and TREND_DEV.is_file():
            drifted.append(f"{TREND_DEV.relative_to(EVALS).as_posix()} (orphaned)")
        if drifted:
            print(
                f"derived view(s) drifted from the run folders:"
                f" {', '.join(drifted)} — regenerate with evals/summarize.py",
                file=sys.stderr,
            )
            return 1
        print(f"{len(views)} derived view(s) match the run folders")
        return 0
    TREND.parent.mkdir(parents=True, exist_ok=True)
    for path, text in views.items():
        path.write_text(text, encoding="utf-8")
    if TREND_DEV not in views:
        TREND_DEV.unlink(missing_ok=True)
    print(trend_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
