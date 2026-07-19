---
name: review-harness
description: >-
  Periodic multi-angle improvement review of the reference. Always fans out all five
  read-only research agents in parallel — maintainer tooling, documentation, runtime cost,
  source duplication, consumer surface — so cross-angle tension informs the synthesis.
  Every agent carries the challenge charter: question the design against the README's
  stated philosophy, recommend removals that pay for themselves. Judges findings by the
  resilience-first doctrine; a settled ADR decision is rebuttable with a new argument,
  never silently suppressed. "/review-harness challenge" drops the ADR anchoring from
  the agent prompts for a zero-based outside look. Adversarially verifies structural findings and delivers
  one prioritized report. Assessment only — never edits. Complements /audit-harness,
  which gates defects against the current bar. Root-only (Claude Code).
---

# Review Harness (improvement scan)

Find opportunities to raise the bar on maintainability, clarity, cost, and resilience — and judge them consistently. `/audit-harness` answers "does the repo meet its current bar" with one verdict; this skill answers "where could the bar move" with one prioritized report. The default run is doctrine-anchored; the `challenge` arg (§ Challenge mode) trades that anchor for a zero-based outside look.

## Challenge charter

Every step 3 research-agent prompt carries this charter, verbatim; the step 5 skeptics never receive it — their mandate is refutation:

> Challenge assumptions rather than preserving the current design. Judge the repository against the philosophy and goals its README states. Look for ways to improve software quality, agent reliability, developer experience, and long-term maintainability. Reduce complexity, ambiguity, token usage, and execution time without sacrificing outcomes. Recommend removing or consolidating guidance that does not pay for itself. Prioritize high-impact improvements over minor editorial feedback.

At synthesis, the Invariants and the do-not-cut list outrank the charter.

## Invariants

Output quality and pipeline autonomy are non-negotiable. Never propose a change that weakens a behavioral guarantee or adds a human touchpoint to save cost. Run the review end-to-end without pausing for confirmation; the report is the deliverable. Never edit repository files during the review run. Follow-up work — including step 7's disposition records — lands through the maintainer loop in the root `CLAUDE.md`, after the user dispositions the findings.

## Procedure

1. **Survey (cheap, run at root).** Run `harness/review-survey.sh` — it emits the measurements the agents anchor on: word sizes per doc surface, 6-month churn per file, cross-stack overlap line counts, and the commits since the last `v*` tag. One script, one set of numbers — every agent prompt quotes the same survey.
2. **Read the ADRs.** Scan the `docs/adr/README.md` index for decisions bearing on the angles, starting with the resilience-first doctrine and any ADR a prior review produced. A settled decision is a rebuttable presumption, not a gag order. A finding may challenge one only by engaging its recorded rationale — stating what changed, or what the rationale missed. Synthesis suppresses a challenge only for failing that bar: no new argument, including a restated § Options Considered entry. Step 6 names every suppressed challenge — suppression is never silent.
3. **Fan out all five angles in parallel** — one read-only `general-purpose` agent each, dispatched in a single message. Never scope down to fewer angles to save tokens; the cross-angle tension is the value. Each prompt carries: the angle charter (table below), the challenge charter, the survey numbers, and the relevant ADR decisions with the rebuttal bar from step 2. It also carries the recent changes: `git log --oneline` since the previous review, defaulting to the last `v*` tag. Each prompt also states the report contract: numbered findings, `file:line` evidence, severity, effort, doctrine class, expected impact, trade-offs, and a concrete proposal.
4. **Synthesize.** Dedupe findings across angles. Where two angles collide (cost says trim, resilience says keep), resolve by doctrine — the collision is evidence, not noise.
5. **Skeptic pass.** Each finding that would trigger structural work (a new renderer or script, a surface retirement, a default change) gets one adversarial agent prompted to refute it. Report only confirmed findings as structural; mark everything else as unverified observation.
6. **Report.** Lead with the verdict and the top items by leverage. Then findings by angle with severity, effort, class; then a sequencing table of independent commits, each auditable per the maintainer loop. Name every challenge suppressed under the step 2 bar. Close by asking the user to disposition the findings, and always offer `/review-harness challenge` as the standing zero-based follow-up.
7. **After disposition** — maintainer-loop work on the user's decision, outside the assessment run — record each decided finding at the grain it deserves. A generalizable lesson amends the doctrine ADR or this skill. A structural decision gets its own ADR; rejected alternatives land in its § Options Considered with reasons. A rejected challenge to an existing ADR lands in that ADR's § Options Considered. Anything below ADR grain lives in the report only.

## Angles

| Angle | Surface | Looks for |
|---|---|---|
| Tooling | `harness/*.py`, `*.sh`, `core/scripts/`, `stacks/*/scripts/`, test suites | Duplicated logic, hand-synced tables that could derive, dead code, coverage gaps |
| Documentation | `README.md`, `docs/*.md`, `docs/adr/` | Ownership overlaps, verbosity against the 30-word rule, staleness outside `cross-tool-strategy.md`, reading-path defects |
| Runtime cost | Agents, skills, hooks, sample `CLAUDE.md` | Per-dispatch context anatomy, restated contracts, preload vs on-demand discipline, words per decision governed |
| Source duplication | `harness/stacks/*`, `harness/init/`, `harness/claude-md/` | Hand-parallel prose across stacks, render candidates, drift channels no battery step gates |
| Consumer surface | `docs/adoption-guide.md`, `docs/harness-project-api.md`, init/materialize/doctor, marketplace | Adoption and upgrade friction, ownership ambiguity, doctor blind spots, channel cost versus value |

An `args` value starting with `challenge` selects challenge mode (below); any remaining text adds a custom sixth angle. Any other value adds a custom sixth angle only. Neither replaces the five.

## Challenge mode

`/review-harness challenge` lifts the ADR anchoring from the agent prompts for a zero-based look. The procedure changes in exactly three places; every other step runs as numbered.

- **Step 2 moves after the fan-out.** No ADR content reaches the research agents; they judge against the README alone. Step 4 then reads the ADR index and labels each finding with the settled decision it challenges — cited for the disposition, never for suppression. The step 2 bar suppresses nothing in this mode.
- **Step 3 prompts drop one element.** The relevant-ADR-decisions element is omitted; the angle charter, challenge charter, survey numbers, recent changes, and report contract all stay.
- **Step 6 drops the suppression list** — nothing was suppressed — and offers the default run as the follow-up instead of this mode.

The doctrine still classifies findings at synthesis, and a finding may challenge the doctrine itself. The skeptic pass (step 5) and disposition recording (step 7) apply unchanged. A dispositioned rejection lands in an ADR § Options Considered and starves repeats in later default runs; a below-ADR-grain rejection lives only in its report. Every default report offers this mode in its close; run it at least once per release cycle.

## Judging doctrine

The full doctrine lives in [`docs/adr/2026-07-12-resilience-first-improvement-doctrine.md`](../../../docs/adr/2026-07-12-resilience-first-improvement-doctrine.md); apply it to every finding. Summary: classify as deduplication, relocation, or demotion; deduplication is accepted on merit, relocation needs a provably-loading consumer, demotion needs code enforcement underneath or a measured golden-slice proof. Every cut leaves a named anchor. Cost is a tiebreaker, never a justification.

Do-not-cut list: the in-body "Load the `<skill>`" sentences in agent definitions (the only preload mechanism outside Claude Code), and root's confirmation-discipline and pause rules (always-on by construction).
