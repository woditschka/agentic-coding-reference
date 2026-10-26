# The Change-Grader: A Terminal Advisory Read That Names the Reading Depth

**Status:** Accepted

## Context

The review gate answers whether a change is correct; anything not clean routes back before reaching the end of the slice. It does not answer how much human attention a passing change deserves before it merges. Without that answer every change carries equal weight, and attention spreads evenly across changes whose risk is uneven. Production risk-scoring systems route low-risk changes to automated handling and higher-risk ones to humans; the pipeline needed the same concentration of scarce review.

Two boundaries are load-bearing. The grader is not a merge gate: a human always merges, and that click is the approval event. It is not a correctness check: correctness was judged upstream, and the grader assesses the residual.

Three defects showed up in use. The first result block kept one word per facet and discarded the reasoning. Its verdict words, `auto`/`review`, named an internal state, collided with the four reviewers, and later as `clear`/`concern` read as an alarm without an action on the board line. The extractor diffed `merge-base(base, HEAD)..HEAD`, but the grader runs before any commit exists, so every diff facet came back null. The grader also runs on Opus, at `effort: medium` since the v0.4.8 combined arm, the most expensive agent per change. Some projects merge by hand and never read the grade.

## Options Considered

1. **Two-stage funnel: a deterministic scorer clears the obvious, a model reads the middle.** Rejected: size, scatter, churn, and paths are structural proxies. A one-line `>=` to `>` inversion is tiny and clean on every axis; a funnel auto-clears it unread.
2. **Always-on terminal grader** (chosen, later made optional).
3. **Numeric 1 to 10 score.** Rejected: judges cluster mid-scale and show length bias; a 73-versus-82 distinction is noise.
4. **Persisted shadow log and calibration loop.** Deferred: `.scratch/handoff.jsonl` is wiped per feature, and a durable cross-feature log waits on intent to leave advisory mode.
5. **Keep the compact aligned block.** Rejected: discards reasoning and leads with evidence instead of the answer.
6. **Diff the base with per-file handling of untracked files.** Rejected: more subprocess calls and easy drift from git's numstat semantics.
7. **Move the grader after the commit.** Rejected: inverts the order and reframes the advisory node as a gate.
8. **Ask at runtime when grading is off.** Rejected: `route` is a pure function with no channel to prompt, and the reason to disable is cost.
9. **Three modes `auto`/`manual`/`off`.** Rejected: the grader is already runnable by hand, so `manual` names no distinction.
10. **Keep `clear`/`concern` and relabel the display.** Rejected: the board would carry words the schema does not.
11. **`routine`/`engaged`.** Rejected: `routine` is the implementer's effort tier in the same ledger.
12. **`confirm`/`inspect`.** Rejected: they name the human's action, not how closely to read.
13. **`skim`/`scrutinize`** (chosen).

## Decision

**A `change-grader` agent runs as the terminal node after the roster approves and reads the uncommitted change. It records an advisory `skim` or `scrutinize` verdict naming the reading depth the human owes the change. Nothing routes on the verdict and nothing merges on it. `layout.toml [harness] auto_grade = false` skips the automatic dispatch.**

- **Thin agent, thick skill, deterministic script.** The protocol lives in the `change-grading` skill and the agent loads it. `grading.py extract` appends one `grader-features` record and the grader appends one `grader-verdict` record to `.scratch/handoff.jsonl`. The script holds no verdict logic. File classification is the project's `scripts/layout.toml`; a file matching no rule is `unknown`, never coerced to prod.
- **Features are a map, never the answer.** The row says where to dive; the verdict must come from reading the hunks. The grader reads the raw diff as well, so an extraction bug cannot blind both layers.
- **The extractor snapshots the working tree.** It stages tracked edits, deletions, and untracked non-ignored files into a throwaway index under `.scratch/tmp`, writes a tree object, and diffs `merge-base(base, HEAD)..<tree>`. The default base is `HEAD`. The real index is never touched. `head_kind` records `worktree` for the snapshot or `commit` for the `--head <ref>` escape hatch; `head_ref` holds the tree SHA, so an unchanged tree grades to the same row.
- **Five facets, worst-facet aggregation.** `blast_radius`, `semantic_surprise`, `test_adequacy`, `reviewer_hedging`, `scope_deviation`, each `skim`/`scrutinize`/`unknown`. Any `scrutinize` or `unknown` makes the verdict `scrutinize`; all five `skim` make it `skim`. Never average: a needless `scrutinize` wastes minutes, a wrong `skim` ships an incident. Missing data (unresolved base, unreadable ledger, unclassifiable file) reads as `unknown`; a missing `build-pass` reads as not gated.
- **The record holds the reasoning; the report leads with the verdict.** The `grader-verdict` record carries a `summary`, a `{verdict, note}` pair per facet, and a prose `rationale`, produced facets-then-rationale-then-verdict. The rendered report opens with `## Verdict — Skim` or `## Verdict — Scrutinize: <facets>`, then an `Extracted:` facts line, then one `## <Facet> — <Verdict>` section each.
- **The vocabulary maps at the parse boundary.** Committed eval run folders carry `clear`/`concern` and are never rewritten. The board renderer and the eval reader in `summarize.py` map them to `skim`/`scrutinize` permanently, so every derived view speaks one vocabulary.
- **Plan-aware.** The `review_roster` feature names the reviewers the pass dispatched, so a floor reviewer silent under a focused plan is expected, not a hedge. The hedging facet reads `recommendations` on approved verdicts.
- **Optional dispatch, fail-open.** `auto_grade` defaults to `true`; an absent or non-boolean value leaves grading on and the doctor flags the non-boolean. When `false`, `route` reaches feature-complete on roster approval, names the skip and the manual path in its decision, and a refactor sibling resumes on approval instead of on the verdict. A hand-run verdict still routes to feature-complete.
- **Model.** The grader runs on the implementer's model family. A different-family judge is unavailable in a single-vendor harness; the bias is bounded by the verdict being advisory, and the hardening lever is double-grading, not a weaker model.

## Consequences

**Positive**
- Every graded change gets one semantic read, which is where the dangerous-but-clean-looking defect is caught.
- A wrong grade costs a wasted human read, never a bad merge.
- The board line `grader-verdict · REQ — scrutinize` answers the operator's question on its own; `semantic_surprise: scrutinize` points at the hunk to read.
- A project drops the most expensive per-change agent with one boolean; existing projects are unchanged on upgrade.

**Negative**
- An LLM call per graded change, including trivial ones.
- No learning: the grader accretes no labeled history, so it cannot graduate toward auto-approval.
- Prompt-side discipline only: a grader that rubber-stamps a clean row is the central failure mode, with no runtime enforcement.
- Determinism is conditioned on working-tree content, not a pinned commit; the correct contract for a pre-commit advisory.
- A project with grading off loses the standing prompt to look at residual risk, and narrowed fix rounds run with no cold backstop.
- A reader opening a pre-rename ledger directly sees `clear`/`concern` beside the pages' `skim`/`scrutinize`. The grade is the one ledger enum whose values are imperatives.

## References

- [The reviewer roster](2026-06-18-the-reviewer-roster.md) — the plan-aware grader is the terminal backstop for a focused review pass.
- [Review convergence](2026-07-14-review-convergence.md) — the narrowed fix rounds whose cold backstop this read is, and the `recommendations` the hedging facet reads.
- [Fresh-eyes review of the changeset](2026-06-21-fresh-eyes-review-changeset.md) — moved the extractor's default base to `HEAD` and made the snapshot the shared change-set primitive.
- [The handoff ledger](2026-05-08-the-handoff-ledger.md) — the append-only log the two grader records join.
- [Layout declares the project](2026-06-14-layout-declares-the-project.md) — the `layout.toml` surface holding the classification globs and `auto_grade`.
- [Deterministic routing engines](2026-07-02-deterministic-routing-engines.md) — the pure-function router the gate branches inside and why it cannot prompt.
- [Model tiering](2026-06-11-model-tiering.md) — the `routine` effort tier the rejected vocabulary collided with.
- [The eval bench](2026-07-15-the-eval-bench.md) — the rule that run folders are never rewritten, which forces the parse-boundary mapping.
