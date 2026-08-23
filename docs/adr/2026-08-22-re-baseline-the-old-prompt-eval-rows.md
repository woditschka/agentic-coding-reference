# Re-Baseline the Old-Prompt Eval Rows

**Status:** Accepted

## Context

The eval bench measures harness versions; the frozen tasks are the instrument. The three feature prompts were clarified on 2026-08-07 after a discarded v0.2.1 run stalled on an undecided control question (the TREND note of that date). Seven measured versions — v0.1.1 through v0.2.1 — were swept only under the earlier prompts. The bench's own validity rule applies: a prompt defensible both ways measures ambiguity, not judgment.

Those seven rows mix prompt ambiguity into the harness signal the trend exists to isolate. The runner never re-runs a version when conditions move ("versions are swept once"), so the flaw cannot age out. Topping the rows up with new reps would mix two task fingerprints inside one row. Deleting the folders would erase recorded ground truth the trend's dated notes and callouts cite.

## Options Considered

1. **Leave the rows as recorded.** Rejected: the flaw is known and dated; the headline series would keep measuring prompt ambiguity across half its span.
2. **Top up the old rows to three reps.** Rejected: the added reps run a different task fingerprint, moving the row mean for non-harness reasons.
3. **Delete the old folders and re-sweep.** Rejected: run folders are the bench's ground truth; deletion erases the provenance of recorded claims.
4. **Re-sweep the old-prompt versions under the current frozen tasks; archive the superseded folders** (chosen).

## Decision

Re-measure v0.1.1, v0.1.18, v0.1.22, v0.1.28, v0.1.29, v0.2.0, and v0.2.1 under the current task fingerprints: three reps per (version, task) cell, judge on. Arms run against one epoch; concurrent invocations started together share it, and each manifest records its resolution.

The superseded run folders move to `evals/results/archive/<version>/<run>/`, outside every scanner glob (`results/runs/*/*`). They stay committed and citable; TREND rebuilds each re-swept row from the re-baseline runs alone. The archive move lands in the same change as the new runs, so a row never mixes campaigns.

Rows from v0.2.2 onward already carry the current fingerprints and stay as recorded.

## Consequences

- The headline series holds one task fingerprint end to end; cost deltas across the 2026-08-07 boundary attribute to the harness, not the prompt wording.
- The re-swept rows share one epoch and one executing Claude Code version — fewer recorded condition spans than the rows they replace.
- Dated notes and ADR figures citing superseded runs keep resolving: the folders remain in the tree under `archive/`.
- The escalation check re-evaluates against the re-based rows; a new pair is reviewed under the standing rule, never suppressed.
- Cost: ~105 reps at the current ~$53 per version rep-set across the five tasks, an estimated $750–1,100; older harness versions ran somewhat higher.

## Amendment (2026-08-22): era contract and engagement guard

The first re-baseline attempt exposed a validity gap the decision needs closed. A v0.1.1 arm completed in 188 seconds at $0.57 with no ledger record: the parent judged the SUT's newer-era project files unexecutable under the old runtime ("`handoff.py route` doesn't exist") and fixed the bug bare. A same-day v0.1.22 arm engaged the full pipeline. Era mismatch resolves per rep by parent improvisation — and the archived v0.1.x rows carried the same condition: a 2026-08-05 parent worked around a `layout.toml` schema its era's extractor rejected.

Two mechanisms land in `run_eval.py`:

- **`--era-contract`**: prep replaces the workspace `CLAUDE.md` and `scripts/layout.toml` with the version's own init skeletons, before the baseline commit; the manifest records the swap. The re-baseline arms run with the flag on. The raw skeletons proved insufficient: their copy-channel phrasing (agents under `.claude/` in the tree) read as "harness not installed" on the marketplace channel, and skeleton-only arms went bare where the SUT's newer files had engaged. Prep therefore appends a channel chapter to the rules file, worded from the era's own setup skill — the plugin ships the surfaces into the tool's read-only plugin cache; their absence from the tree is expected. The channel fact alone still left entry to interpretation: the era mandate names "feature development", the probe task is a bugfix, and the skeleton carries no operational routing chapter. The appended contract closes with an explicit pipeline-entry instruction — every change dispatches the `pipeline-coordinator` first. This is the file-level form of the mechanism `seed_intake` already provides for versions shipping its schema: the bench deterministically enters the pipeline, and the row measures the pipeline's work. The engagement decision is substrate, not the measured pipeline; fixing it removes a nuisance variable without touching what the row measures.

The rules-file route alone proved insufficient even so: with container delivery canary-verified and the entry chapter loaded, a parent still fixed a probe directly with no ledger record. The instruction therefore also rides the system prompt — `--era-contract` appends the entry instruction via `--append-system-prompt`, the strongest channel the runner owns; the frozen task prompt passes verbatim either way, so fingerprints hold. The manifest records the appended instruction beside the file swaps.

Most of the observed flakiness then traced to the operator, not the model: parallel invocations are unsafe. The eval marketplace registration is a single user-scope writer, and three concurrent terminals re-registered it against each other — sessions lost their agent roster mid-run, produced bare or improvised reps, and one v0.1.22 cell recorded a sibling arm's plugin version pointing at a deleted source. The campaign runs as one invocation, version-interleaved, per the bench's standing single-invocation doctrine; the README states the constraint. A completion gate lands beside the entry gate: a completed implementing run whose ledger shows a build without a converged review cycle re-statuses `truncated-pipeline` and quarantines — part of the contract is not the contract. Convergence is each era's own stated rule ("all four must approve before the pipeline closes", v0.1.1 handbook), not today's; the archived campaign silently recorded at least one rep violating it (v0.1.1 owners r2, final doc-reviewer verdict `changes_requested`). The gate holds re-baseline rows to the version's contract fully executed; a contract-legal unconverged halt (the escalation valve) landing in quarantine is the signal to refine it.

An adversarial review scoped both gates before the campaign relied on them. They guard `--era-contract` arms only: a current version's engagement and halts are the measured behavior, and replaying the truncation rule over the committed record would have discarded 19 legitimate current-version runs. The refusal task is exempt from the no-pipeline gate — a correct refusal can decline at intake with no ledger record (the committed v0.2.2 visit-cancel r2 did). The entry instruction's wording is outcome-neutral for the same reason: the pipeline's rules decide whether a request implements, consults, or declines. A collection failure never voids a paid rep — the gates run only on a successfully collected ledger.

The re-baseline also roots each arm on its version's own era model. The uniform root pin (claude-opus-5) served cross-version control, but a v0.1.x row rooted on today's model is not the system its era shipped — and the era models (claude-opus-4-8, claude-sonnet-4-6) resolve only while they are still served, a closing window. `--era-contract` reads the root model from the version's implementer-tier frontmatter pin: v0.1.x arms root on their 4-family, v0.2.x-era sources pin the current family, so the rule reproduces the kept rows' root unchanged. The manifest records the era pin per run; rows differing on the pin render it, and cross-pin comparisons carry the model condition under the standing discipline. The judge model stays pinned bench-wide — Tier C scores never mix provenances.

The refinement signal arrived on the campaign's first cell, and it demoted the truncation gate entirely. A fresh v0.1.1 rep ran the full pipeline and stopped at a final doc-reviewer `changes_requested` — the same reviewer, the same verdict, the same version as the archived r2 under the previous executor generation. Two independent executors stopping at the same place is not substrate: it is v0.1.1's prose-enforced routing failing to force the fix round, the weakness the later route engine exists to close. Convergence is therefore a measurand. `result.pipeline.incomplete` records the gap on every run; nothing quarantines for it.

Abandonment is not convergence. A specialty-directory arm implemented, passed its oracle at a fifth of the task's recorded cost, and left its ledger ending on an unanswered `dispatch-start` — the contract's own deterministic truncation signal, which every measured era answers with continue-the-slice recovery. An executor ending the session there declined the contract mid-dispatch: substrate, like entry, and the only such shape in the committed record. Era arms gate on it (`truncated-pipeline`, quarantined); the entry instruction states the recovery rule. The line stands: a version's *visible decisions* (verdicts taken, halts chosen) are measured; an *unanswered dispatch* is not a decision.
- **The no-pipeline gate**: a complete run whose collected ledger holds no record is re-statused `no-pipeline` and quarantined like a leak. It measured the bare model; it must never clear the bar or reach the committed record.

## Amendment (2026-08-22): the superseded folders leave the tree

The decision's archive mechanism is replaced before its first commit. The superseded run folders are deleted with the campaign commit, not moved to `evals/results/archive/`: the doubly flawed campaign (old prompts, era mismatch resolved by per-rep improvisation) carries too little claim value for permanent tree weight, and git history already preserves every folder at every commit before the deletion — the citable form this repository uses elsewhere. Version-scoped notes pinned to superseded cells leave `notes.toml` the same way. A claim needing an old run cites the pre-deletion commit.
