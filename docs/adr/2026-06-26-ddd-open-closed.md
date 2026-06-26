# Open-Closed DDD: An Opinionated Default Over a Closed Kernel

**Status:** Accepted

## Context

The harness's DDD guidance lived at four altitudes — the `ddd-principles.md` handbook, the `architecture-principles` doctor template, the per-stack `design-validation` skill, and the project's scaffolded brief. The same rule was *restated*, not referenced, and the wordings had drifted: the handbook said "no framework dependencies"; the Java enforcer said "no framework annotations" — different claims. Because the enforcers carried their own tactical copies, a consumer who edited the brief was silently overruled by the skill. Two needs follow: the harness should ship one **opinionated** DDD default, and a consumer should adapt the tactical style **within limits** without editing harness-owned runtime.

## Options Considered

1. **Status quo** — tactics duplicated across handbook, template, and enforcers. Drifts; no single default; editing the brief does not change enforced behavior.
2. **One locked style** — hard-code a single DDD style in the enforcers, no adaptation. Simplest to enforce; forces every consumer into one taste; breaks the within-limits goal.
3. **Open-closed split** — a closed kernel enforced for everyone, an opinionated tactical default shipped in the template, the brief as the single adaptation surface, and enforcers that defer to the brief for tactics.

## Decision

We adopt option 3.

- **Closed kernel** (enforced for every consumer, not brief-editable): the four kernel properties; a domain core free of infrastructure logic; business logic in the model, not orchestration; aggregates as consistency boundaries entered only through their root and referenced by identity; anti-corruption at every boundary the project does **not** control.
- **Open tactical catalog** (defaulted to the maintainer's style, overridable): persistence ideology (event-sourced / in-memory default, relational allowed), mapping policy, ACL implementation, framework-annotation tolerance, naming and transaction conventions.
- **Single adaptation surface:** `docs/architecture-principles.md` is the one file a consumer edits to adapt the DDD/architecture style. Enforcers (`design-validation`, reviewers) hard-check the kernel and otherwise enforce the brief *as written*; they carry no tactical copies. Consumers never edit harness-owned runtime.
- **Controlled vs uncontrolled boundary:** the ACL obligation is scoped to boundaries the project does not control. When the project owns both ends and persistence follows the model closely, **direct OR/JSON annotations on the model are the sanctioned substitute for an explicit ACL** — compliant, not a missing ACL.

Authority placement, no duplication: `ddd-principles.md` owns the *why* and the kernel/tactical taxonomy; the `architecture-principles` template owns the *default tactical catalog*; the README carries a short signpost chapter pointing to both.

## Consequences

**Positive:**
- One adaptation surface; editing the brief actually changes enforced behavior. The four-altitude drift is closed.
- The harness ships an opinionated, coherent default; peers adapt per-project within the kernel.
- The ACL / annotation boundary is explicit, resolving the contradiction an earlier attempt reverted.

**Negative:**
- The maintainer's taste is the universal default; a peer who prefers a different style edits `architecture-principles.md` on every new project — an accepted cost.
- The kernel is partly judgment-enforced (`design-validation`, `audit-docs`), not fully mechanical.
- "Single surface" rots back to duplication unless guarded: an `audit-agents` / `audit-docs` check must flag any tactical rule that re-enters an enforcer.
- "Edit only the brief" holds *within the kernel*; a non-DDD architecture is out of scope by design.

## Implementation

De-duplicate tactics out of `design-validation` (and reviewer skills) into the brief; author the maintainer's default in the `architecture-principles` template; tighten `ddd-principles.md` to pure kernel; add the README signpost chapter; demonstrate in the three sample briefs; add the drift guard. Verify with `/audit-harness`, then cut a version. Pairs with a Project History entry.

## References

- [`2026-06-03-principles-over-rigid-rules.md`](2026-06-03-principles-over-rigid-rules.md) — the closed-contract / open-judgment layering this extends to DDD guidance
- [`2026-06-12-docs-as-harness-project-api.md`](2026-06-12-docs-as-harness-project-api.md) — project-owned briefs as the adaptation API
- [`2026-06-17-generic-stack-verb-contract.md`](2026-06-17-generic-stack-verb-contract.md) — precedent for a single binding/adaptation surface
- [`ddd-principles.md`](../ddd-principles.md) — the kernel/tactical taxonomy this decision sharpens
