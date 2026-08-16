# External-Review Recommendations: Dispositions

**Status:** Accepted

## Context

An external review of the repository (2026-08-16) rated the architecture strong and made ten improvement recommendations plus a documentation suggestion. Two implementation findings had already landed the same day as their own decisions — [lock-free ledger appends](2026-08-16-lock-free-ledger-appends.md) and [exact-module install verification](2026-08-16-exact-module-install-verification.md). The rest need explicit dispositions so a declined recommendation is not re-litigated fresh at the next review. The deciding constraints: a single-maintainer budget where eval reps cost $4–19 each, Claude Code as the primary target with other tools secondary, and the kernel's admission test.

## Options Considered

Per recommendation, the options were the review's proposal, a trimmed variant, or a reasoned decline. The disposition table in the Decision carries each outcome with its reason; a separate options list would duplicate it.

## Decision

**Each recommendation gets one of four dispositions — landed, queued, deferred with a trigger, or declined with a reason.**

| Recommendation | Disposition |
|---|---|
| Docs: a request-to-merge walkthrough | **Landed** — [`feature-walkthrough.md`](../feature-walkthrough.md), narrating a committed eval run |
| Per-kind cost judgment (the accepted core of "statistical reporting") | **Landed** — the rise verdict scopes to the task's declared `kind`; [`evals/README.md`](../../evals/README.md) § Cost accounting |
| Routing state table generated from the source, plus routing invariant tests | **Queued** — next substantive docs work; the table lands with a battery drift-gate |
| Handbook legibility pass (Level-1 openers) | **Queued** — after the routing table, so routing prose can lean on it |
| A Go SUT and broader eval task diversity | **Deferred** — trigger: the first Go-stack harness change that needs eval feedback; no matrix on spec |
| Continuous cross-tool conformance | **Deferred** — a manual smoke check when cross-tool surfaces change; no standing accounts or CI |
| Bootstrap confidence intervals, p50/p90 reporting | **Declined** — meaningless at 3–6 reps per cell; ledger-named mechanism attribution stays the practice |
| Runtime profiles (`core`/`team`/`full`) | **Declined** — contradicts the kernel admission test and multiplies the tested surface; the adoption pain is met by the walkthrough and guide instead |
| Generated `AGENTS.md` shims | **Declined** — all four supported tools read `CLAUDE.md`; revisit only when a target tool does not |
| Go/Java build jobs in server-side CI | **Declined** — lean publication surface; the samples build locally and the bench exercises the Java stack |
| Generating router code from a declarative source | **Declined** — the table and docs generate from the source; the router stays hand-written, typed, `assert_never`-exhausted |

API stabilization toward 1.0 is accepted as direction, not as an item: reduce contract churn before widening the roster.

## Consequences

**Positive:** declined items carry their reasons in the decision log, so the next improvement review argues against a recorded position instead of rediscovering the proposal. The two queued items have an agreed order.

**Negative:** the deferred items depend on their triggers being noticed; nothing mechanical watches for them.

## References

- [ADR 2026-08-16: Lock-Free Ledger Appends](2026-08-16-lock-free-ledger-appends.md) — the review's concurrency finding, decided separately
- [ADR 2026-08-16: Exact-Module Install Verification](2026-08-16-exact-module-install-verification.md) — the review's verification finding, decided separately
- [ADR 2026-08-16: Agent-Team Names the Product](2026-08-16-agent-team-names-the-product.md) — the naming decision the same review's legibility finding motivated
- [ADR 2026-07-12: Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — the standing frame for judging improvement findings, applied here
