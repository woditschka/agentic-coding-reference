# Change Grader: Always-On Advisory Risk Read

**Status:** Accepted (vocabulary amended by [2026-06-05-change-grade-report](2026-06-05-change-grade-report.md); always-on made optional by [2026-07-06-optional-change-grading](2026-07-06-optional-change-grading.md))

> **Amended (2026-06-05).** The successor ADR replaces the result vocabulary: facet verdicts `ok` → `clear`, overall verdict `auto`/`review` → `clear`/`concern`, and the compact block gives way to a per-facet report. The role, boundaries, and worst-facet aggregation below are unchanged.
>
> **Amended (2026-07-06).** The always-on dispatch decided below is now optional. `layout.toml [harness] auto_grade = false` skips the automatic run: the pipeline reaches feature-complete on roster approval, and the grader stays runnable by hand. The terminal, advisory, never-routes role is unchanged — that is what makes the skip safe. See [2026-07-06-optional-change-grading](2026-07-06-optional-change-grading.md).

## Context

The review gate answers *is this change correct* — the four reviewers' job, and anything not clean routes back before reaching here. It does not answer a second question: **how much human attention this passing change deserves before it merges.** Without that, every change carries equal review weight, so attention spreads evenly across changes whose real risk is wildly uneven.

This ADR ratifies a `change-grader` that concentrates scarce human review on the changes where judgment pays off and lets the obvious-safe ones move fast — the attention-routing idea production risk-scoring systems use: route low-risk changes to automated handling, higher-risk ones to humans. Two boundaries are load-bearing: it is **not a merge gate** (a human always merges; that click is the approval event) and **not a correctness check** (correctness was judged upstream; this assesses the risk of the residual).

## Options Considered

1. **Two-stage funnel: deterministic scorer decides clear cases, escalates an ambiguous middle to an LLM.** Minimizes tokens, and is the right design at high throughput. Rejected for one failure it cannot close: the deterministic features (size, scatter, churn, paths) are *structural proxies* — they correlate with risk without reading the code and cannot see semantics. A one-line diff inverting `balance >= amount` to `balance > amount` is tiny, low-churn, clean on every axis, and catastrophic; a funnel auto-clears it without a model ever reading it.

2. **Always-on terminal grader (chosen).** Every change gets one semantic read, which is exactly where the dangerous-but-clean-looking defect is caught. The deterministic features are kept — not to *decide*, but to make each read fast and targeted (a map of where to dive), never a verdict. We accept the per-change LLM cost and buy it back with a single terminal node and no routing branch to tune.

3. **Numeric 1–10 score.** Rejected: LLM judges cluster mid-scale, show length bias, and a 73-vs-82 distinction is noise. A hard gate wants a categorical call.

4. **Persisted shadow log + calibration loop now.** Rejected for the first version (see Decision § Advisory-only). Deferred, not refused.

## Decision

An always-on `change-grader` agent, dispatched as the terminal node after the four reviewers approve. It is **not** part of the coordinator's routing logic and its verdict does not route — the coordinator recommends the dispatch, the grader runs, the human reads the result and merges.

**Thin agent, thick skill, deterministic script.** Per repo convention the entire protocol lives in the portable `change-grading` skill; the `change-grader` agent is a wrapper that loads it; the deterministic extraction is `scripts/score-change.py`. The script holds **no verdict logic** — it extracts the structural row and persists it; the grader decides by reading the diff. Classification (test/prod/sensitive/module globs) is the per-project `scripts/layout.toml`, the one file that forks per repo; a changed file matching no rule is `unknown`, never coerced to prod.

**Features are a map, not the answer.** The row tells the grader *where to dive*, never *what to conclude*. The verdict must come from reading the hunks at the flagged coordinates; deriving it from the row alone is forbidden. The grader also reads the raw diff, not only the digested row, so a bug in extraction cannot blind both layers at once.

**Five binary facets, worst-facet aggregation.** `blast_radius`, `semantic_surprise`, `test_adequacy`, `reviewer_hedging`, `scope_deviation` — each `ok`/`concern`/`unknown`, never numeric. `unknown` counts as a concern. Output order is facets → rationale → verdict (reasoning before the verdict). Aggregation is **worst facet, never average**: any facet `concern` or `unknown` → `review`; all five `ok` → `auto`. Averaging buries the single dangerous facet under benign ones, and the costs are asymmetric — a needless `review` wastes minutes, a wrong `auto` ships an incident.

**Missing data fails toward `review`.** Unresolved base ref, absent/unreadable handoff log, unclassifiable file → the affected facet is `unknown` → `review`. Absence of a risk signal is never evidence of safety. The deterministic facts (`build_passed`, reviewer status, retry/consultation/revision counts) are read from the append-only `.scratch/handoff.jsonl` records — never re-derived, never re-run; a missing `build-pass` reads as not-gated, never as a silent pass.

**Single source, two records.** The grader writes no separate files. `extract` appends one `grader-features` record and the grader appends one `grader-verdict` record to `.scratch/handoff.jsonl` — the same append-only log the rest of the harness uses. Both are ephemeral per-feature working state.

**Advisory-only; the outer loop is deferred.** This version emits a per-change recommendation surfaced to the session; nothing auto-approves. The calibration loop (shadow log, `human_outcome` backfill, holdout, `--live` widening) and a learned Diff Risk Score are **explicitly out of scope**. A durable cross-feature calibration log cannot be `.scratch/handoff.jsonl` (it is wiped per feature), and standing one up plus its tooling is deferred until there is intent to leave permanent-advisory mode. The seam is clean: a future projection step reading the two records into a durable log can be added without reworking the extract/grade path.

**Model.** The grader runs on the same model family as the implementer. A different-family judge — the textbook defense against self-enhancement bias — is unavailable in a single-vendor harness, and a weaker same-family judge trades real capability on the sharpest-reasoning task in the pipeline for only weak decorrelation. The bias is bounded by the verdict being advisory-only; if reliability ever needs hardening the lever is double-grading (grade twice, route disagreement to `review`), not a weaker model.

## Consequences

**Positive.**

- Every change gets one semantic read; the dangerous-but-clean-looking defect the funnel would auto-clear is caught.
- One terminal node, no routing branch to tune; the verdict never gates, so the blast radius of a wrong grade is a wasted human read, never a bad merge.
- Single-source persistence (two `handoff.jsonl` records) matches the repo's append-only convention; no scattered files.
- Portable: the protocol is one skill, the engine is one tool-agnostic script, classification is one per-project data file.

**Negative / accepted.**

- An LLM call per change, including trivial ones. Accepted; bought back by the features making each read fast.
- No learning. The grader never accretes labeled history in this version, so it cannot graduate toward auto-approval until the deferred calibration work lands — and changes graded before that work is added leave no recoverable record.
- Prompt-side discipline only. A grader that skips its read and rubber-stamps a clean row is the central failure mode; the skill forbids row-only verdicts, but there is no runtime enforcement.

## Implementation

**Non-goal:** This is a harness architecture decision, not a feature requirement. Implementation lives in `.claude/agents/change-grader.md`, `.claude/skills/change-grading/SKILL.md`, and `scripts/score-change.py` (with the per-project `scripts/layout.toml`); no code under `internal/` or `cmd/` changes.

## References

- `.claude/skills/change-grading/SKILL.md` — the grading protocol this ADR ratifies
- `.claude/agents/change-grader.md` — the thin agent wrapper
- `scripts/score-change.py` — the deterministic extractor (no verdict logic)
- [`2026-05-08-append-only-jsonl-handoffs.md`](2026-05-08-append-only-jsonl-handoffs.md) — the handoff-record contract this extends with two record types
- `schemas/scratch/grader-features.schema.json`, `schemas/scratch/grader-verdict.schema.json` — the two new record schemas
