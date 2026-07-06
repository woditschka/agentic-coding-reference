# Change Grading Is Pipeline-Optional via auto_grade

**Status:** Accepted

## Context

The `change-grader` runs as the terminal hop after the reviewer roster approves: `route` dispatches it, it reads the diff, and it records an advisory `clear`/`concern` verdict. The grader runs on Opus at `effort: high` — the most expensive agent per change. In some settings that cost outweighs the value: small teams, low-risk repositories, or projects that already gate correctness through review and merge by hand. Until now the dispatch was unconditional, so those projects paid for a grade they did not use.

The grader's own design makes it uniquely safe to skip. It is terminal and advisory: nothing routes on its verdict, and it is not a merge or correctness gate (see the change-grader ADR). Disabling a reviewer would leave a hole in the correctness gate; disabling the grader only removes one advisory read.

## Options Considered

1. **Always on (status quo)** — rejected: forces the most expensive per-change agent on every project regardless of whether the grade earns its cost.
2. **A boolean, but ask at runtime when off** — rejected: `route` is a deterministic pure function with no channel to prompt mid-loop; an interactive question breaks the unattended-loop property. And the reason to disable is cost — "ask every slice" replaces a token cost with a recurring attention cost.
3. **Three modes (`auto`/`manual`/`off`)** — rejected as redundant: a `manual` mode implies a dedicated trigger, but the grader is already runnable by hand through the `change-grading` skill. "Off" already preserves manual runnability, so the third mode names a distinction that does not exist.
4. **A boolean flag in project data, gating only the automatic dispatch** (chosen).

## Decision

**`layout.toml [harness] auto_grade` gates the terminal change-grader dispatch. It defaults to `true`.** When `false`, `route` reaches feature-complete on roster approval without dispatching the grader.

Load-bearing details:

- **The gate is on the automatic hop only.** The change-grader agent and the `change-grading` skill stay installed and runnable by hand. A hand-run `grader-verdict` still routes to feature-complete through the existing verdict branch, so a manual grade is honored exactly like an automatic one.
- **The refactor-sibling path keys off approval when grading is off.** A refactor slice normally resumes on its `grader-verdict`; with `auto_grade = false` that record never appears, so `route` resumes the original slice on roster approval instead.
- **The router fails open.** An absent or non-boolean value leaves grading on, so an upgrade keeps grading unless a project opts out. The doctor flags a non-boolean value, where it is fixable, rather than the router silently keeping grading on.
- **No `spec_version` bump.** The key is optional with a shipped default; a project declaring the prior contract and omitting the key still validates. Forcing a re-declaration for a backward-compatible addition would fail every consumer's doctor for no contract break.
- **Feature-complete surfaces the skip.** When grading is off, the terminal decision names the reason and points at the manual path, so a missing grade reads as a choice, not a gap.

## Consequences

- Positive: a project drops the most expensive per-change agent with one boolean; the capability survives the toggle, available on demand; existing projects are unchanged on upgrade.
- Negative: the routing prose now carries a conditional the reader must hold. A project that disables grading loses the standing prompt to look at the residual risk — a recurring omission it chose.

## References

- [The Change-Grader: A Terminal Advisory Node](2026-06-05-change-grader.md) — why the grader never routes, the property that makes skipping it safe.
- [Deterministic Mid-Slice Routing](2026-07-06-deterministic-mid-slice-routing.md) — the pure-function router this gate branches inside; why it cannot prompt at runtime.
- [Executable Pipeline Contracts](2026-07-02-executable-pipeline-contracts.md) — the `layout.toml` project-data surface the flag joins.
