# Judgment Roles Run the Premium Tier; the Ledger Routes Routine Work to the Checklist Tier

**Status:** Accepted

## Context

Each sample runs ten specialists, each pinned to a model and an effort in its agent frontmatter. Current pricing per million input/output tokens: Claude Opus 5.5 $4/$20 with cache reads at 0.05× base input, Claude Sonnet 5.5 $2/$10 with cache reads at 0.10×. The objective ordering is fixed: quality bar first, cost second, wall-clock time third. Two questions follow: which roles justify the premium tier, and whether a dispatch may run below its role's pin.

Dynamic tiering needed local evidence; an outside proposal projected 20–30% savings from routing literature whose citations could not be verified. A replay over the 98 committed v0.3.x eval runs ($1,017.66 accounted spend) joined each requirement's first `design-block` verdict to its stage costs. Covered-verdict work held 3.7% of spend, minor 35.0%, new 25.7%. Build failures per requirement: covered 0.00 (10 requirements), minor 0.74 (39), new 1.04 (24). One below-bar rep in a three-rep cell raises cost per pass by roughly 50%, so a downgrade miss costs more than a downgrade saves. Anthropic positions Sonnet 5.5 as level with Opus 5 on well-scoped everyday tasks and Opus 5.5 as stronger on open-ended work needing sustained judgment. Triage already draws that line per slice.

## Options Considered

1. **Uniform premium.** Rejected: the reviewer fan-out costs 43% more than the mixed one, on facets where the rubric does the work.
2. **Uniform mid-tier.** Rejected: fails the quality bar on open-ended roles; security review hunts what no checklist names.
3. **Deeper frugality** (coordinator or doc-reviewer on Haiku). Rejected: routing hops are short, so the saving is small and ranks below misroute risk.
4. **Fable 5 for judgment roles.** Declined at roughly 2.6× Opus cost for equivalent content, until the bar demonstrably requires it.
5. **Model aliases in frontmatter.** Rejected: a release would shift pins without a deliberate edit.
6. **Static downgrade of covered-verdict slices.** Rejected: 3.7% of spend, netting 1–2%.
7. **Trained per-call router.** Rejected: unverifiable evidence and a policy no script can audit.
8. **Immediate full-roster dynamic routing.** Rejected: the miss asymmetry, with no arm yet cleared.
9. **The design-block verdict as the tier anchor.** Replaced by an explicit rating: the verdict rates the design delta, not the code work.
10. **A `PreToolUse` hook rewriting the dispatch to the tier.** Replaced by router-resident route rules. The hook duplicated a derivation the routing core computes natively, existed in one tool, and left no trace outside the transcript.
11. **Routine initials as a reduced thinking budget on the premium model.** Rejected on measurement. The one cell scored judge 3/3 on design fit and test quality, below every prior record for that task.
12. **Task-type split with a rated, router-owned ladder** (chosen).

## Decision

**Judgment roles pin `claude-opus-5-5`, checklist roles pin `claude-sonnet-5-5`, every pin at effort `medium`, and the router alone moves a dispatch between tiers.**

- **Judgment tier:** product-requirements-expert, system-design-expert, feature-implementer, security-reviewer, change-grader. **Checklist tier:** pipeline-coordinator, review-planner, code-quality-reviewer, test-reviewer, doc-reviewer, and the `feature-implementer-routine` variant.
- **Verification asymmetry justifies the split.** Checking a diff against a rubric is easier than generating the code, and the mechanical quality gate precedes every reviewer.
- **Judgment reviewers track the implementer.** security-reviewer and change-grader never sit below either implementer tier; a tier move carries all judgment roles together.
- **Test-reviewer promote trigger.** A defect escaping an approved test review, or two consecutive test-facet failures, promotes it to the judgment tier.
- **The front door stays premium.** The root session, product-requirements-expert, and system-design-expert keep their pins in every mode. The bench measures unattended runs only and cannot license dulling the interactive duties.
- **Pins, not aliases.** Explicit model IDs; a release shifts nothing until a deliberate `upgrade-deps` edit. Per-tool forms: OpenCode `openrouter/anthropic/claude-<model>`, Copilot `Claude <Model> (copilot)` with the prior release as fallback. The effort pin exists on Claude Code alone.
- **The rating is a recorded fact.** The design-block carries `implementation_effort: routine | involved`, rated at triage by the system-design-expert. Absent reads as involved. A slice with no rating on any design-block derives the base tier on every path, so an unrated ledger routes as if no ladder existed.
- **Two routine paths.** A slice whose latest design-block rates `routine` opens on the variant (`tier_reason: initial:rated-routine`). A fix dispatch whose implementer-routed findings are all autofix-tagged runs the variant on any rated slice; dropped or empty findings read as mixed. Recovery and resume dispatches run the base pin.
- **Retirement is monotonic and capped.** A routine initial retires on a build failure or a mixed round. An all-autofix round after it runs the variant once more, and substantive dissent on that pass retires it. A window the fold cannot attribute retires it too. An involved-rated slice whose all-autofix fix round runs the variant retires it on a build failure or substantive dissent in that routine window. Retirement is permanent for the slice; escalation is capped at the static pin after at most two windows on the lower rung.
- **The variant claims the base identity.** `feature-implementer-routine` renders from `variant-of: feature-implementer` with a byte-identical body and records `author: "feature-implementer"`. The battery holds every mirror to its tier's pin; variant chains are refused.
- **The trace is the decision payload plus derivability.** Dispatch decisions carry `tier_reason`. `handoff.py tier` prints the derivation. The board annotates routine sessions, scrubbing any self-claimed tier key first, and flags a transcript whose tier contradicts the derivation. No hook checks the match; adherence is dispatch discipline, verifiable from the ledger on every tool.
- **Every tier change is an eval arm.** Control and candidate run as tag plus dev in one invocation, sharing an epoch. The pass condition is 15/15 on the bar with judge medians inside the control's spread. A miss reverts one route rule and one frontmatter pin.

The reviewer roster gap behind the routine-initial dip closed on both sides, and the closure stands. The `test-review` skill carries a Test Placement section, the twin of the `code-quality-review` design-placement check, with the web-layer exception both share. The review-planner and the roster table name both dimensions, so a focused plan never drops the guard. One gap stays open by decision: reviewers never read the slice's `design-block`. A replay over 147 implementing design-blocks found 140 whose patch touched `docs/system-design.md` and 7 that did not; the 7 carried risks the security checklist covers from the brief. The record is the implementer's briefing and the briefs are the reviewers' wall. A risk no brief implies is a missing principle for its owning brief, never slice detail in the design doc; the reviewer read-set is unchanged.

## Consequences

**Positive:**

- Premium spend concentrates where errors compound: requirements, architecture, involved implementation, off-checklist security, the merge-attention grade.
- The v0.4.8 row cleared the gate on 2026-10-01: 15/15, every judge facet median inside the v0.4.7 spread, rep set $20.08 against $23.77 (−15.5%). The screen at one rep per task read $18.50 against $23.77.
- Wall clock is unaffected by the static split; reviewers fan out in parallel.

**Negative:**

- Checklist reviewers can miss what a premium model catches; the Opus security and grader hops and the promote trigger mitigate.
- Design fit is the watch facet: sweep mean 4.42 against 4.56, with one 3 on a visit-edit rep whose Opus fix round applied a security autofix.
- Retirement lengthens wall clock on a retiring slice. An arm's screening sweep costs about $50, clearing three reps about $160.
- Pins go stale by design; capability gains wait for the next deliberate bump.

## Implementation

Pins live in each agent's frontmatter and the `.claude/agents/README.md` table; the cross-tool ID mapping in `audit-agents`; the ladder in `handoff-routing/route-rules.md` and the routing core; the eval root pin in `evals/config.toml`. `docs/cross-tool-strategy.md` § Agents / Subagents states the policy: the per-tool pin table and the tier ladder on every tool.

## References

- [The change grader](2026-06-05-the-change-grader.md) — the terminal advisory hop kept on the premium tier.
- [Skill-based agent architecture](2026-03-22-skill-based-agent-architecture.md) — rubric knowledge in skills is what makes mid-tier verification viable.
- [Deterministic routing engines](2026-07-02-deterministic-routing-engines.md) — the router that owns the ladder and prints its derivation.
- [The reviewer roster](2026-06-18-the-reviewer-roster.md) — risk-proportional review; the placement checks that closed the gap behind the routine-initial dip are recorded above, in this decision.
- [The eval bench](2026-07-15-the-eval-bench.md) — the cost-per-pass metric whose miss asymmetry sizes the conservatism, and the arm protocol.
- [Resilience-first improvement doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — a tier move is a demotion, accepted only on a measured run.
- `docs/cross-tool-strategy.md` § Agents / Subagents — the per-tool model forms and the Claude Code-only effort knob.
