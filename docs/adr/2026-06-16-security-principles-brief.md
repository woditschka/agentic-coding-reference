# Security Principles as a Producer Brief and a Ninth Conjunctive Clause

**Status:** Accepted

## Context

The feature-implementer authors against principle briefs and walks the conjunctive bar in a mandatory self-review before reviewers run (`tdd-workflow` § Self-Review Pass). Three of the four review dimensions — architecture, testing, legibility — have a producer-facing principle layer the self-review reaches. Security did not. Its principles lived only inside the `security-review` checklist, which the producer never loads. So the self-review never walked security, and the security-reviewer was the first agent to reason about abuse — the one dimension where findings were structurally avoidable rather than caught upstream.

This continues the layered model of [`2026-06-03-principles-over-rigid-rules.md`](2026-06-03-principles-over-rigid-rules.md): producers get principles that generalize; validators keep the exhaustive checklist. It preserves the floor/ceiling split behind [`2026-06-11-model-tier-assignment.md`](2026-06-11-model-tier-assignment.md) — the producer is better-informed, the reviewer stays an independent reasoner, not a checklist-matcher.

## Options Considered

1. **Status quo** — security principles stay inside the reviewer skill. Cheapest; leaves security the one dimension the producer designs blind.
2. **Load the full `security-review` checklist into the implementer.** Closes the gap but makes the producer write to the reviewer's rubric, eroding reviewer independence and bloating generation-time context with an exhaustive list.
3. **Extract a producer brief plus a conjunctive-bar clause.** A `docs/security-principles.md` brief carries the principles; a ninth `secure-by-design` clause wires them into the existing self-review; the reviewer keeps the exhaustive checklist.

## Decision

We adopt option 3.

- The four security laws — security as an emergent property, defense in depth, least privilege, fail secure — are **harness-owned non-negotiables**, defined in `tdd-principles.md` § Secure by Design. They re-materialize on every upgrade and are denylisted from project rosters, so a project decides how it meets them, never whether.
- `docs/security-principles.md` is a **project-owned** brief (`kind = "default"`), peer to `testing-principles.md` and `architecture-principles.md`, per [`2026-06-12-docs-as-harness-project-api.md`](2026-06-12-docs-as-harness-project-api.md). It carries the tunable specialization: the project's trust-boundary map and the stack's state-of-the-art high-bar defaults, derived from the project's own dependency policy and threat model.
- A ninth clause, `secure-by-design`, joins the conjunctive bar. The mandatory self-review walks it; the `bar_clause` schema enum and the `review-checklist` mapping gain the slug.
- The `security-review` skill drops its embedded principles and references the brief — the pattern `test-review` already uses for `testing-principles.md`. The exhaustive checklist, severity table, and supply-chain steps stay reviewer-only.
- The `design-validation` skill — the system-design-expert's triage gate — reads the brief and validates trust-boundary placement against it, replacing its embedded security list. Trust-boundary placement is a design decision, so the brief reaches the middle loop too, the same way the skill already sources architecture from `architecture-principles.md`. This makes security a producer concern at both the design and implementation stages, not only at review.

## Consequences

**Positive:**
- Security is shaped into the first draft and self-reviewed before the gate, moving avoidable findings upstream.
- One source of truth: producer and reviewer reference the same brief; the checklist no longer duplicates the principles.
- Reviewer independence holds — the validator keeps the exhaustive list the producer never optimized to.
- The universal laws are tamper-proof from the project side: a consumer specializes controls but cannot weaken a law. The laws live in re-materialized harness runtime, not an editable brief.

**Negative:**
- A ninth clause is asked of every slice, including those with no security surface, where it holds trivially. The one-line self-review question bounds the cost.
- Adding a required brief expands the harness-project API surface; existing consumers receive the brief on their next materialize.

## References

- [`2026-06-03-principles-over-rigid-rules.md`](2026-06-03-principles-over-rigid-rules.md) — the producer-principles / validator-checklist split this applies
- [`2026-06-11-model-tier-assignment.md`](2026-06-11-model-tier-assignment.md) — the floor/ceiling reasoning preserved here
- [`2026-06-12-docs-as-harness-project-api.md`](2026-06-12-docs-as-harness-project-api.md) — project-owned briefs and the roster this adds to
