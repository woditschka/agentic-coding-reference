---
name: change-grading
description: >-
  Grade a passing change for how much human attention it deserves before merge.
  Load when running the change-grader after the reviewer roster approves. Holds
  the full grading protocol: the five facets, worst-facet aggregation, the
  facets-rationale-verdict order, persistence, and scope/non-goals.
compatibility:
  - claude-code
  - github-copilot
  - opencode
metadata:
  version: "1.0"
  author: team
---

## What this grades, and what it does not

The reviewer roster answers *is this change correct*. This grader answers the different question the gate does not: **how much human attention this passing change deserves before it merges.** The verdict names that reading depth: `skim` or `scrutinize`. It concentrates scarce review on the changes where judgment pays off and lets the obvious-safe ones move fast.

Two boundaries are load-bearing and must never erode:

- **Not a merge gate.** A human always merges; that click is the approval event. The grader only decides how closely the human reads before merging: `skim` (a glance confirms it) or `scrutinize` (read the flagged hunks first).
- **Not a correctness check.** Correctness was judged upstream by the reviewers. This assesses the risk of the residual — a change can be correct and still warrant a careful read for *where it lands*.

The grader is a terminal, advisory node. Nothing routes on its verdict; the router does not consume it. The routing table dispatches it as the terminal hop and the human acts on it.

Because nothing routes on it, the automatic dispatch is optional: `layout.toml [harness] auto_grade = false` tells `route` to reach feature-complete on roster approval without dispatching the grader. That gates only the pipeline hop — this skill stays runnable by hand at any time, and a hand-run `grader-verdict` still routes to feature-complete like an automatic one. Default is `true`; a project opts out when the per-change grade is not worth its cost.

## The protocol, and the skill drives it

You are dispatched once. Inside that one dispatch you run the whole protocol. The deterministic script produces the structural row; you read the diff and decide.

1. **Extract.** Run the deterministic extractor:

   ```
   python3 scripts/grading.py extract --feature <REQ-ID>
   ```

   You run before the human commits, so by default the extractor snapshots the live working tree — staged, unstaged, and untracked changes — and diffs it against `HEAD`. That uncommitted delta is the change under review; no commit exists yet, and the slice never commits mid-flight (only `/ship` does, terminally), so `HEAD` is the right base. It is the same change set a reviewer reads through `scripts/changeset.sh`, so your row and their view agree. It appends one `grader-features` record to `.scratch/handoff.jsonl` (the structural row, carrying `head_kind: "worktree"`). Pass `--base <ref>`/`--head <ref>` only to grade an already-committed range after the fact. Add `--churn` when commit/author history is wanted and the clone is complete. The script holds **no verdict logic** — it extracts facts and persists one record; you decide.

2. **Grade by reading the diff.** Read the `grader-features` record *and* the raw diff at the coordinates it flags. Form the five facet notes, the rationale, and the verdict — in that order (§ Output).

3. **Record the verdict.** Append one `grader-verdict` record via `python3 scripts/handoff.py append grader-verdict` (heredoc form per the `handoff-append` skill; summary, facets, rationale, verdict, `responding_to` the grader-features line), then return the change-grade report (§ Surface the verdict to the session) as your final message.

Both records are ephemeral per-feature working state. There is no calibration log in this version (§ Scope and non-goals).

## Features are a map, not the answer

The extractor's row — per-file added/deleted/kind, modules touched (scatter), test/prod line ratio, hunk count, churn, sensitive paths, build/review status, retries, consultations, design revisions — tells you **where to dive**, never **what to conclude.**

> A clean feature row is permission to read FAST. It is never permission to skip the read.

The anchoring risk is specific and it is the failure this whole grader exists to prevent: handed a clean-looking row, a model rubber-stamps `skim` without opening the diff — silently rebuilding the cheap scorer's blind spot while paying to *not look*. A one-line diff inverting `balance >= amount` to `balance > amount` is tiny, low-churn, clean on every structural axis, and catastrophic. The defense is structural: **the verdict must come from reading the hunks at the flagged coordinates.** Deriving it from the row alone is forbidden. You read the raw diff, not only the digested row, so a bug in extraction (shallow clone, wrong base) cannot blind both layers at once.

**Recompute, don't trust.** The row is evidence to direct your reading, not a conclusion to ratify. Where the row and the diff disagree, the diff wins and the disagreement is itself a signal worth noting in the rationale.

## The five facets

Each facet is one real failure mode, judged on its own. A facet's value is **skim, scrutinize, or unknown** — never numeric. No 1–10, no scores. Judges cluster mid-scale and a 73-vs-82 distinction is noise; a hard gate wants a categorical call. `unknown` means genuinely insufficient information to judge, and it counts as `scrutinize`, never a coerced pass. Write a one-line plain-prose note for each facet — the reason for its verdict — and persist it beside the verdict.

- **blast_radius** — how far the change reaches. Scatter across modules, a high hunk count, edits under sensitive paths, churn touching many files. Wide, cross-stack, or sensitive reach is `scrutinize`. A contained edit in one module is `skim`. `unknown` when the diff could not be read (no base ref).

- **semantic_surprise** — does the code do something the diff's size or description would not lead you to expect. The inverted operator, the flipped boundary, the silent behavior change inside a "rename", the off-by-one in a conditional, the deleted or weakened guard. This is the facet the change-grade read exists for; spend the most attention here. Any plausible behavioral surprise you cannot rule out by reading is `scrutinize`. `unknown` when you could not read the relevant hunks.

- **test_adequacy** — are the tests real or tautological. `build_passed: true` proves the suite is **green**, but the implementer wrote those tests TDD-style, so a green suite the author also authored is **weak evidence**. Judge whether the tests actually exercise the changed behavior (assert real outcomes, cover the boundary the code changed) or merely restate the implementation. Tests absent for changed prod behavior, or tests that would pass against a broken implementation, are `scrutinize`. `unknown` when `build_passed` is null/absent — a missing pass record means the change did not clear the gate (read it as not gated), never as a silent pass.

- **reviewer_hedging** — did the roster reviewers approve cleanly or with reservations. An approval whose findings list lingering worries, an `escalate` tag, or a `bar_clause`-flagged clause that was reworked under pressure is a hedge. So is a `recommendations` list on a late-round approval — the critical-only rounds park residual polish there, and this facet is where it reaches the human. A recommendation that restates a standing project gap the security brief already records (an unconfigured scanner, a check the run could not execute) is context, not a hedge. An approval whose aspects or recommendations assert an absence or a verified value without naming what they were checked against (a grep or a `file:line`) is a hedge: the claim carries no evidence. So is a citation that does not resolve to the file it names; check one, and a fabricated line number costs the approval more than an uncited claim. Clean unanimous approval is `skim`; approval-with-caveats is `scrutinize`. Judge silence against `review_roster` — the reviewers the risk-proportional review-plan actually dispatched: a floor reviewer null because a focused plan scoped it out is **expected, not a hedge and not unknown**. `unknown` only when a reviewer the plan *did* dispatch has null status, or when `review_roster` is null (full battery) and a floor reviewer is silent.

- **scope_deviation** — did the change stay within its triaged scope. The agentic-PR literature finds design revisions and mid-flight consultations the most predictive scope signals: `design_revisions > 0`, high `consultations`, or `build_retries` near the cap mean the slice fought its triage. Reading the diff against the requirement's stated surface, a change that wandered past it is `scrutinize`. So is a fix-round delta that changed behavior on a route or flow the slice's bullets do not name with no `consultation-response` recording it, whichever requirement's rule it resembles. A clean within-scope change is `skim`.

## Aggregation: worst facet, never average

This is the one place generic LLM-judge guidance does not transfer, because the costs are asymmetric: a needless `scrutinize` wastes minutes, a wrong `skim` ships an incident. Averaging buries the single dangerous facet under benign ones — the inverted-operator change scores `skim` four times and `scrutinize` once, and a mean says `skim`.

> **Any facet `scrutinize` or `unknown` → `scrutinize`. All five `skim` → `skim`.** Do not average. Do not let four `skim`s outvote one `scrutinize`.

`unknown` and missing data fail toward `scrutinize`. Absence of a risk signal is never evidence of safety.

## Output: facet notes, then rationale, then verdict — in that order

Reasoning before the verdict improves judgment, so the per-facet notes and the rationale are the reasoning that *produces* the verdict, written before it — not a justification written after. Append one `grader-verdict` record via `python3 scripts/handoff.py append grader-verdict` (schema: `schemas/scratch/grader-verdict.schema.json`):

```json
{
  "type": "grader-verdict",
  "req_id": "<REQ-ID>",
  "author": "change-grader",
  "responding_to": [<grader-features line>],
  "summary": "<short imperative name of the change, e.g. tighten retry-counter reset>",
  "facets": {
    "blast_radius":      { "verdict": "skim",   "note": "<one plain-prose explanation>" },
    "semantic_surprise": { "verdict": "scrutinize", "note": "<one plain-prose explanation>" },
    "test_adequacy":     { "verdict": "skim",   "note": "<one plain-prose explanation>" },
    "reviewer_hedging":  { "verdict": "skim",   "note": "<one plain-prose explanation>" },
    "scope_deviation":   { "verdict": "skim",   "note": "<one plain-prose explanation>" }
  },
  "rationale": "<20-60 words: the decisive point and what the human should do>",
  "verdict": "scrutinize"
}
```

Each facet carries a `verdict` (`skim`/`scrutinize`/`unknown`) and a one-line `note`. The `verdict` must equal the worst-facet aggregation — any facet `scrutinize` or `unknown` → `scrutinize`; all five `skim` → `skim`. A verdict that contradicts its own facets or rationale (a `skim` whose prose lists worries) is a visible reliability flag and is wrong by construction.

### Surface the verdict to the session

A subagent's final message is returned to the caller, not shown to the user. So your **returned summary** is the change-grade report the human reads at the decision point. Render it as Markdown from the record you persisted — root relays it as the closing line of the loop:

```markdown
# Change Grade — <REQ-ID>: <summary>

## Verdict — Skim
<rationale prose>
_Advisory only; nothing auto-merges._

Extracted: <facts line from the grader-features row>

## Blast Radius — Skim
<blast_radius note>

## Semantic Surprise — Skim
<semantic_surprise note>

## Test Adequacy — Skim
<test_adequacy note>

## Reviewer Hedging — Skim
<reviewer_hedging note>

## Scope Deviation — Skim
<scope_deviation note>
```

Rendering rules:

- **Verdict first.** The report leads with the verdict and its rationale (the answer), then the `Extracted:` facts, then the five facet sections (the evidence). A reader can stop after the verdict.
- **Verdict heading.** `skim` renders `## Verdict — Skim`. `scrutinize` names the flagged facets in plain words: `## Verdict — Scrutinize: semantic surprise` (or several, comma-joined). An `unknown` facet counts as `scrutinize` and is named here too.
- **Facet headings.** Each facet's verdict renders capitalised after an em-dash — `Skim`, `Scrutinize`, or `Unknown`.
- **`Extracted:` line.** A one-line subset of the deterministic `grader-features` row — files, modules, added/removed lines, sensitive paths, build and review status, retries. The working-tree snapshot populates the row in the normal pre-commit flow, so this line renders. Omit it only in the degenerate case where the row is empty (no resolvable base, or a failed snapshot).
- **Plain prose.** Write the notes and rationale as plain prose. Do not hard-wrap; the display wraps.

This report is display-only. It must never feed routing or gate logic: the verdict is what the human reads at the decision point; nothing acts on it.

## Persistence

Both records live in the append-only `.scratch/handoff.jsonl` — the single source the rest of the harness already uses, no separate files:

| Record | Written by | Contents |
|---|---|---|
| `grader-features` | `grading.py extract` | the deterministic structural row; null for any missing input |
| `grader-verdict` | you (the grader) | the change summary, the five facet verdicts and notes, the rationale, and the verdict |

Schemas: `schemas/scratch/grader-features.schema.json`, `schemas/scratch/grader-verdict.schema.json`. Both records are ephemeral per-feature working state, cleared with `.scratch/` between features. Nothing persists across features in this version (§ Scope and non-goals).

## Determinism and the `unknown` contract

The feature row is a pure function of pinned inputs: the resolved base ref, the head (a `--head` commit, or the content-addressed tree of the working-tree snapshot — identical worktree content hashes to the identical tree, so two runs over an unchanged tree agree), the append-only `.scratch/handoff.jsonl` records, and `scripts/layout.toml`. The script reads git under a canonical environment and sorts every list. **Missing data emits null, never a false zero:** unresolved base or a failed snapshot → diff facets `unknown`; absent/unreadable handoff log → build/review/retry facts null → the dependent facets `unknown` → `scrutinize`.

Classification is `scripts/layout.toml` — per-project globs for test/prod/sensitive and module-derivation rules. A changed file matching no test/prod rule is kind `unknown`: recorded, never coerced to prod. Fix misclassification in the shared layout/engine so the fix helps every project.

The engine's classification contract is pinned against this project's own `scripts/layout.toml` by `scripts/tests/grading/test_features_layout.py` (stdlib `unittest`, run from the scripts dir with `python3 -m unittest tests.grading.test_features_layout`); the stack-agnostic engine pins live in `scripts/tests/grading/test_features.py`. The suite is not wired into the project build: the vendored runtime changes only at install time, and the install (materialize, or the marketplace setup) verifies every suite it copies. Run it manually when investigating a classification.

## Scope and non-goals

This version is **advisory-only**. The grader emits a per-change recommendation (`skim` = a glance confirms it, `scrutinize` = read the flagged hunks closely) for the human at the decision point. Nothing auto-approves, nothing routes on the verdict, and no record persists across features.

Deliberately **out of scope** (future work, not built):

- **No calibration loop and no shadow log.** There is no durable accreting record of (features → verdict → human outcome), no backfill from merge/revert history, no holdout, and no path to `--live` auto-approval. Adding any of these means re-introducing a durable cross-feature log — which `.scratch/handoff.jsonl` cannot be, since it is wiped per feature — plus the calibration tooling over it.
- **No learned Diff Risk Score.** The grader's value is the semantic read; a learned structural score would sharpen the map, never replace reading the code.

### Reliability note

A single-model-family harness cannot use the textbook cross-family defense against self-enhancement bias (the implementer is also opus). Two things bound that here: the verdict is **advisory-only** — nothing auto-approves — and the lever if reliability ever needs hardening is **double-grading** (grade twice, route any disagreement to `scrutinize`), not a weaker judge. Capability is kept because the semantic read is the pipeline's sharpest-reasoning task.
