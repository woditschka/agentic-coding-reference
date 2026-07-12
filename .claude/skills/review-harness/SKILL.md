---
name: review-harness
description: >-
  Periodic multi-angle improvement review of the reference. Always fans out all five
  read-only research agents in parallel — maintainer tooling, documentation, runtime cost,
  source duplication, consumer surface — so cross-angle tension informs the synthesis.
  Judges findings by the resilience-first doctrine, consults the ADRs to keep
  settled decisions settled, adversarially verifies structural findings, and delivers one
  prioritized report. Assessment only — never edits. Complements /audit-harness, which
  gates defects against the current bar. Root-only (Claude Code).
---

# Review Harness (improvement scan)

Find opportunities to raise the bar on maintainability, clarity, cost, and resilience — and judge them consistently. `/audit-harness` answers "does the repo meet its current bar" with one verdict; this skill answers "where could the bar move" with one prioritized report.

## Invariants

Output quality and pipeline autonomy are non-negotiable. Never propose a change that weakens a behavioral guarantee or adds a human touchpoint to save cost. Run the review end-to-end without pausing for confirmation; the report is the deliverable. Never edit repository files during the review run. Follow-up work — including step 7's disposition records — lands through the maintainer loop in the root `CLAUDE.md`, after the user dispositions the findings.

## Procedure

1. **Survey (cheap, run at root).** Gather the measurements the agents will anchor on:
   - Sizes: `wc -w` over `docs/*.md`, `harness/core/.claude/{agents,skills}/**/*.md`, one stack's `.claude/`, `.claude/skills/*/SKILL.md`.
   - Churn: `git log --since="6 months ago" --name-only --pretty=format:` filtered of `samples/` and `plugins/`, counted per file.
   - Cross-stack overlap: per shared file, `comm -12` line counts between `harness/stacks/go` and the other stacks.
2. **Read the ADRs.** Scan the `docs/adr/README.md` index for decisions bearing on the angles, starting with the resilience-first doctrine and any ADR a prior review produced. A settled decision is re-examined only when its context measurably changed.
3. **Fan out all five angles in parallel** — one read-only `general-purpose` agent each, dispatched in a single message. Never scope down to fewer angles to save tokens; the cross-angle tension is the value. Each prompt carries: the angle charter (table below), the survey numbers, and the relevant ADR decisions ("do not re-report a settled decision unless its context changed"). It also carries the recent changes: `git log --oneline` since the previous review, defaulting to the last `v*` tag. Each prompt also states the report contract: numbered findings, `file:line` evidence, severity, effort, and doctrine class.
4. **Synthesize.** Dedupe findings across angles. Where two angles collide (cost says trim, resilience says keep), resolve by doctrine — the collision is evidence, not noise.
5. **Skeptic pass.** Each finding that would trigger structural work (a new renderer or script, a surface retirement, a default change) gets one adversarial agent prompted to refute it. Report only confirmed findings as structural; mark everything else as unverified observation.
6. **Report.** Lead with the verdict and the top items by leverage. Then findings by angle with severity, effort, class; then a sequencing table of independent commits, each auditable per the maintainer loop. Close by asking the user to disposition the findings.
7. **After disposition** — maintainer-loop work on the user's decision, outside the assessment run — record each decided finding at the grain it deserves. A generalizable lesson amends the doctrine ADR or this skill. A structural decision gets its own ADR; rejected alternatives land in its § Options Considered with reasons. Anything below ADR grain lives in the report only.

## Angles

| Angle | Surface | Looks for |
|---|---|---|
| Tooling | `harness/*.py`, `*.sh`, `core/scripts/`, `stacks/*/scripts/`, test suites | Duplicated logic, hand-synced tables that could derive, dead code, coverage gaps |
| Documentation | `README.md`, `docs/*.md`, `docs/adr/` | Ownership overlaps, verbosity against the 30-word rule, staleness outside `cross-tool-strategy.md`, reading-path defects |
| Runtime cost | Agents, skills, hooks, sample `CLAUDE.md` | Per-dispatch context anatomy, restated contracts, preload vs on-demand discipline, words per decision governed |
| Source duplication | `harness/stacks/*`, `harness/init/`, `harness/claude-md/` | Hand-parallel prose across stacks, render candidates, drift channels no battery step gates |
| Consumer surface | `docs/adoption-guide.md`, `docs/harness-project-api.md`, init/materialize/doctor, marketplace | Adoption and upgrade friction, ownership ambiguity, doctor blind spots, channel cost versus value |

An `args` value adds a custom sixth angle; it never replaces the five.

## Judging doctrine

The full doctrine lives in [`docs/adr/2026-07-12-resilience-first-improvement-doctrine.md`](../../../docs/adr/2026-07-12-resilience-first-improvement-doctrine.md); apply it to every finding. Summary: classify as deduplication, relocation, or demotion; deduplication is accepted on merit, relocation needs a provably-loading consumer, demotion needs code enforcement underneath or a measured golden-slice proof. Every cut leaves a named anchor. Cost is a tiebreaker, never a justification.

Do-not-cut list: the in-body "Load the `<skill>`" sentences in agent definitions (the only preload mechanism outside Claude Code), and root's confirmation-discipline and pause rules (always-on by construction).
