# Model Tier Assignment: Judgment Roles Premium, Checklist Roles Mid-Tier

**Status:** Accepted (extended by [ADR 2026-09-01](2026-09-01-evidence-gated-dynamic-tiering.md): the implementer role gains a router-selected effort variant within its pinned model tier — the pins themselves stay operative)

## Context

Each sample runs nine specialists, each pinned to a model in its agent frontmatter. Current pricing per million input/output tokens: Opus 4.8 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5, Fable 5 $10/$50. Fable 5 additionally tokenizes the same content to roughly 30% more tokens. The selection question: which roles justify the premium tier, and how assignments respond to new model releases. The governing objective ordering is fixed: quality bar first, cost second, wall-clock time third.

## Options Considered

1. **Uniform premium (all Opus)** — maximizes per-hop capability. The four-reviewer fan-out costs 43% more than the mixed one, on facets where the rubric, not the model, does the work.
2. **Uniform mid-tier (all Sonnet)** — cheapest uniform option; fails the quality bar on open-ended roles. Security review hunts vulnerabilities no checklist names. The residual bugs in premium-written code are exactly the subtle ones a weaker reviewer misses.
3. **Task-type split (chosen)** — judgment roles on Opus 4.8: product-requirements-expert, system-design-expert, feature-implementer, security-reviewer, change-grader. Checklist and routing roles on Sonnet 4.6: pipeline-coordinator, code-quality-reviewer, test-reviewer, doc-reviewer.
4. **Deeper frugality (rejected for now)** — coordinator or doc-reviewer on Haiku 4.5. Routing hops are short, so absolute savings are small; the quality-first ordering gives that saving no priority over misroute risk.
5. **Fable 5 for judgment roles (declined)** — roughly 2.6× Opus cost for equivalent content (2× per token, ~30% more tokens). Declined until the quality bar demonstrably requires it.

## Decision

We adopt option 3, with the rules that keep it stable:

- **Verification asymmetry justifies the split.** Checking a diff against an explicit rubric is an easier task than generating the code. The mechanical quality gate (build, test, lint) precedes every reviewer as the correctness oracle.
- **Judgment reviewers track the implementer.** On any tier bump, security-reviewer and change-grader move with the feature-implementer — never below it. A reviewer judging output it cannot comprehend is the configuration this forbids.
- **Promote trigger for the borderline role.** Test-quality review sits between checklist and judgment. A defect escaping an approved test review, or two consecutive test-facet failures, promotes test-reviewer to the judgment tier.
- **Pins, not aliases.** Explicit model IDs in frontmatter; a model release shifts nothing until a deliberate `deps-upgrade` run. Lower per-tool ceilings (Copilot at Opus 4.7, Junie alias-only) are documented exceptions, not drift.

## Consequences

**Positive:**

- Premium spend concentrates where errors compound: requirements, architecture, implementation, off-checklist security, the terminal merge-attention grade.
- The mixed reviewer fan-out costs 70% of a uniform-Opus one with no rubric-facet quality loss.
- Wall-clock is unaffected. Reviewers fan out in parallel; the critical path is the Opus security review, which the quality bar locks regardless.

**Negative:**

- Checklist reviewers can miss findings a premium model would catch. Mitigations: the Opus security and grader hops, and the test-reviewer promote trigger.
- Pins go stale by design. Capability gains from new releases wait for the next `deps-upgrade` decision.

## Implementation

**Non-goal:** This is a harness configuration decision, not sample content. Assignments live in each sample's agent frontmatter and `.claude/agents/README.md` table; the cross-tool ID mapping lives in the `audit-agents` skill. The root README (§ Model Tier Assignment) states the current policy; this ADR records why. No sample prose duplicates the rationale.

## References

- [`2026-06-05-change-grader.md`](2026-06-05-change-grader.md) — the terminal advisory hop this policy keeps on the premium tier
- [`2026-03-22-skill-based-agent-architecture.md`](2026-03-22-skill-based-agent-architecture.md) — rubric knowledge lives in skills, which is what makes mid-tier verification viable
