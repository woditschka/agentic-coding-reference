# A Stack Ships Its Brief Realization as a Fragment

**Status:** Accepted

## Context

[Open-Closed DDD](2026-06-26-ddd-open-closed.md) made `docs/architecture-principles.md` the single surface for tactical style: the core doctor template ships the language-neutral default, and enforcers apply the brief as written. The template is stack-agnostic by the battery's rule. So the Spring realization of the catalog lived only as hand-written prose in the Spring sample's brief, under a heading the template never carried. A consumer scaffolded by `/init` got no realization. One that copied the sample got a table mapping the repository and the domain service both to `@Component`.

Two consequences followed. First, Spring enforcer lines carried tactics of their own. Code-quality bullets named `@Component` / `@Service` for stateless services, `@ConfigurationProperties` for config binding, and Jackson annotation tolerance; a design-validation bullet named `internal/` sub-packages. The first states a rule the maintainer no longer holds. The others are stack realizations of kernel properties, which the audit-agents check that ADR promised allowed inside an enforcer, because the brief had no section to own them. Second, a downstream project sharpened the Spring placement rule and recorded it in its ADRs: beans orchestrate, plain classes decide, internals in role-named sub-packages, the stereotype names the bean's role. Nothing carried that sharpening back into the shipped default. `/materialize` had nothing to carry to other projects either: its brief diff-check ([Materialize Keeps Every Template-Seeded File Current](2026-07-01-generalized-template-reconciliation.md)) compares against the core template alone.

## Options Considered

1. **Keep the realization in the sample's prose.** Nothing to build. A new project copies by hand, an existing project never hears of a change, and the sample drifts from the maintainer's rule unnoticed.
2. **Write the sharpened rule into the core template in neutral words.** One template, every stack. The neutral words would carry Spring-shaped reasoning (what a bean holds) into the Go and generic defaults with no evidence those stacks want it.
3. **A stack overlay that replaces the whole brief template.** Plain copy semantics. The overlay duplicates the language-neutral part of the template, and the two copies of the catalog drift.
4. **A stack fragment that fills one section of the core template.** The core template gains a `## Language Realization` slot. A stack ships `<brief>.realization.md` beside its doctor templates. `init.py` writes the fragment into the slot, materialize's diff-check reads template plus fragment, and the battery pins each sample's section to its fragment.

## Decision

Option 4.

- **The slot.** The core `architecture-principles` template carries `## Language Realization` with a comment naming what belongs there. The section is not doctor-required: the Go and generic defaults ship it empty for the owner, and no gate fails on an empty slot.
- **The fragment.** A stack's `.claude/skills/doctor/templates/<brief>.realization.md` is the section's body, headings below H2 included. The runtime copy is `core ∪ stacks/<stack>`, so the fragment reaches every consumer and every plugin beside the core templates with no new copy path. `init.py` replaces the slot's body with it; a fragment whose template has no slot fails init loudly.
- **One slot convention.** The `security-principles` template's `## Realization` and the samples' `## <Stack> Realization` headings become `## Language Realization` too, so a security fragment ships by the same convention.
- **The Spring fragment** carries the sharpened default. It maps each building block to the stereotype that marks its bean role, or to a plain class. It names the four things a bean holds and the three that leave it. It places internals in role-named sub-packages behind the Modulith verify test, and keeps the Java idiom rows the sample carried. "Domain service" stays the catalog term; a project may alias it.
- **Enforcers defer.** The stereotype and `internal/` lines come out with no replacement. The code-quality skill's Design Placement section already judges placement against the brief, and the `internal/` bullet duplicated the neutral line above it. The config-binding and annotation lines become deference lines that cite the brief's section. No enforcer states a tactic.
- **The guard gains a mechanical half.** The battery lists every checklist line in a stack enforcer skill that names a DDD building block or a framework annotation without citing the brief. It holds that set to `harness/enforcer-tactics.expected`. The pinned lines are the closed-kernel checks and framework wiring, each a judged entry. A new line fails the battery until it cites the brief or is added as a decision. Whether a line is floor, kernel, or tactic stays judgment; the pin makes the moment of judgment unavoidable. The same shape as the handbook-delta pin.
- **Transport.** `/init` fills the slot for a new project. `/materialize` step 8 diffs an existing brief against template plus fragment and proposes the delta as a consented edit. A deliberate divergence is classified and left alone, as the reconciliation ADR decided. The battery's roster-sync step pins each stack sample's section to the fragment verbatim.

## Consequences

**Positive:**
- The maintainer's Spring style ships as a default, reaches new projects at init and existing projects on upgrade, and stays open: a project edits its own section.
- The open-closed split is intact and four breaches of it are closed. The kernel is unchanged; no enforcer carries a tactic, and the next one that uses the catalog's vocabulary cannot enter unnoticed.
- Any stack can ship a realization for any brief by the same file convention, with no new plumbing.

**Negative:**
- The bookstore workspace predates the default. Its umbrella brief carries the slot heading but still maps the domain service to `@Component`, and both members keep an `internal/` package in code. The umbrella is a generic-stack consumer, so the pin does not reach it. The conversion, code and docs together, is the slice that follows this commit.
- The marketplace channel has no `/materialize`. Its upgrade procedure gains a manual comparison step against the bundled fragment; the transport there is a human reading a diff, not a proposal.
- The Go design-validation skill keeps its two `internal/` lines. Go's compiler enforces `internal`, so they are language wiring, not a tactic the brief owns.
- `/harvest` diffs runtime only, so a brief-level improvement made downstream still has no automated path back to the fragment. The sharpening this decision ships arrived by conversation. Extending harvest to diff a project's section against its stack fragment is the pre-authorized next step.
- The pin is a vocabulary match, so a tactic phrased without the catalog's words or an annotation still passes it. The judgment check remains the authority; the pin narrows what it can miss.
- A fragment change re-scaffolds nothing on its own; the samples are updated by hand to satisfy the pin, and the pin is what makes the gap visible.
- The Go and generic samples carry an empty slot with a guiding comment. A Go fragment arrives when there is a Go preference to record, never as a placeholder.

## Implementation

`harness/init.py` gains the fill and its tests. `verify_harness/checks/sync.py` gains the realization pin under the roster-sync step and the enforcer tactic pin as its own step, with `harness/enforcer-tactics.expected` as the reference. The Spring fragment lands under `harness/stacks/java-spring-boot/.claude/skills/doctor/templates/`. The three stack samples' briefs carry the slot, the Spring one filled, and the Spring sample's `system-design.md` package tree shows the role-named layout. The doctor, init, and materialize skills and `docs/ddd-principles.md` state the fragment rule. Verified by `harness/propagate-harness.sh`.

## References

- [Open-Closed DDD](2026-06-26-ddd-open-closed.md) — the single adaptation surface this keeps; its judgment guard gains a mechanical half here
- [Materialize Keeps Every Template-Seeded File Current](2026-07-01-generalized-template-reconciliation.md) — the advisory diff-check that now reads the fragment
- [`../ddd-principles.md`](../ddd-principles.md) — the kernel/tactical taxonomy the fragment sits under
