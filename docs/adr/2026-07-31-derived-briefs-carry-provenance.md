# Brownfield Briefs Are Derived With Provenance, Never Reconstructed

**Status:** Accepted

## Context

The [docs-as-API](2026-06-12-docs-as-harness-project-api.md) contract makes the seven `docs/` briefs the project's half of the interface. Onboarding scaffolds four as structure-only stubs and three as filled defaults. The doctor then gates their structure, and [`audit-docs`](2026-06-14-audit-docs-skill.md) judges their content. Both gates presuppose that somebody wrote the stubs.

On a greenfield project the owner writes them as the work proceeds. On a **brownfield** project — the case `/materialize` and `/harvest` exist to serve — the content already exists, encoded in the source rather than in prose. Nobody transcribes it. The stubs stay empty, the doctor passes on structure alone, and the pipeline runs its first slice against a PRD with no requirements.

The obvious remedy — an agent that reads the code and fills the briefs — is easy to build and dangerous to ship naively. A codebase records that a decision was made; it never records why. A survey that writes an observed behavior as a settled requirement, or reconstructs a plausible ADR Context, manufactures institutional memory that a later reader cannot distinguish from the record. The briefs' value is that they are the shared memory every agent trusts; a fabricated line in them is worse than an unwritten section.

A trial run on the adopted [`spring-petclinic`](https://github.com/spring-projects/spring-petclinic) codebase measured both halves. The survey recovered 16 requirements, 25 contracts, seven domain terms, and seven ADRs whose Context and Options Considered it recorded as not recoverable. It also exposed a live defect no test observes. Under MySQL the duplicate-pet-name constraint is enforced but unnamed, while the controller detects the violation by that name. A duplicate reaching the database therefore surfaces as an error page instead of a field error. The owner then withdrew one derived requirement as an implementation artifact — the doctrine working in the direction that matters.

## Options Considered

1. **Leave brownfield onboarding to the owner** — rejected: the empty stubs are the single largest adoption cost, and the pipeline's gates are weakest exactly where a project's history is richest.
2. **Fold derivation into `/materialize`** — rejected: materialize is a deterministic runtime replacement that never writes project-owned content. A judgment-heavy survey inside it would make an upgrade unrepeatable and put unreviewed prose one keystroke from every consumer.
3. **Survey into a side artifact, promoting statements into the roster only once ratified** — rejected, though it is the strongest alternative. It removes the risk that an unread draft carries a brief's authority, and it costs the benefit. The briefs stay empty until a human works through a parallel document, which is the transcription nobody does today. Marking provenance inside the roster keeps one document per subject, and makes the unratified state visible where the reader already is.
4. **A survey skill whose every statement carries its provenance** (chosen) — derived, confirmed, or not recoverable; docs-only scope; defects recorded rather than fixed.

## Decision

**Ship `derive-briefs`: a docs-only survey skill that drafts the briefs from an existing codebase and marks every statement with its provenance.**

Load-bearing details:

- **Three marks, stated rather than implied.** *Derived* — read off the code, true of the implementation, silent on intent. *Confirmed* — a human answered, recorded inline with the date. *Not recoverable* — the reasoning predates the repository. Each mark is a fixed token, so an editor, a reviewer, or a future gate recognizes it without judgment. A section recording its reasoning as unrecoverable is finished; filling it with a plausible reconstruction is the failure the skill exists to prevent.
- **Observed behavior is not an intended requirement.** The survey order enforces it: the boundary surface carries intent and yields candidate requirements, while internals carry mechanism and yield the design brief. Two sections a codebase cannot evidence at all are named explicitly — the PRD's Goals and Non-Goals, and each ADR's Context and Options Considered. An absent capability is not a recorded decision to exclude it.
- **Three findings stay apart.** A **defect** contradicts a derived requirement or serves none. A **gap** is code that misses a principle brief's standard — recorded against the principle, never resolved by lowering it. An **open question** is a reading the code cannot settle — put to the owner, and each answer that lands becomes a confirmed, dated statement.
- **Authored content is not the survey's to rewrite.** The three filled principles briefs, and any stub an owner has started, are derived *against*. Every edit to them is proposed as a consented diff. Relief from a shipped principle is a human's grant, recorded as confirmed; a closed kernel property is not the project's to relax.
- **Docs-only scope.** The skill writes `docs/` and nothing else, including for defects it finds. A recorded defect becomes a later slice, run against the requirement the survey wrote.
- **It occupies the empty seat, not a neighbor's.** `doctor` checks the briefs are present and `audit-docs` judges written briefs. `derive-briefs` produces the first draft that gives them something to check, then hands it to `audit-docs` as the first draft it is.

## Consequences

Positive:

- Brownfield adoption gains a first draft instead of a blank page.
- Deriving requirements makes divergences visible that no test observes, as the trial's MySQL finding shows.
- The briefs' trustworthiness survives automated authoring, because unrecoverable reasoning stays visibly unrecovered.

Negative:

- One more consumer skill in the roster to learn.
- A draft carries authority it has not earned unless the owner reads it, so the procedure ends by putting the open questions to a human.
- Provenance marking is judgment-enforced, with no deterministic gate behind it.
- A derived brief is an enforcement input, not only a reader's document. Design triage reads a derived `system-design.md` as written, so derived structure gates new code from the moment it lands. The one counterweight: `design-validation`'s foundational check treats a brief carrying only derived marks as still unanswered, so the first slice reaches a human.

## References

- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the contract whose project half this fills.
- [The Docs Audit Is One Command](2026-06-14-audit-docs-skill.md) — the reviewing neighbor the survey draft is handed to.
- [Materialize Is a Complete Replacement](2026-06-13-materialize-complete-replacement.md) — why derivation stays outside the deterministic upgrade path.
