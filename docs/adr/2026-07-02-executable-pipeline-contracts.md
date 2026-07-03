# Executable Pipeline Contracts

**Status:** Accepted

## Context

A correctness sweep found five contract defects the deterministic battery cannot see. A reviewer's planned-checkpoint finding carried `tag: "escalate"`, which § Blocking treats as a pipeline-halting human decision. The `dispatch-start` schema pinned `author` to a closed seven-agent enum, so a declared extra reviewer could not append its contractual record. The autofix audit told "the coordinator" to author a `review-feedback` record its schema rejects and its shell restriction cannot execute. Three files disagreed on who writes `.scratch/escalations.md`, while the coordinator's body claims it never creates files. The doctor crashed instead of failing cleanly when `scripts/layout.toml` was missing.

## Options Considered

1. **Carve-outs in prose** — exempt the checkpoint finding from § Blocking by description matching. Rejected: gates must catch deterministically; description text is not a discriminator.
2. **Widen schemas to admit the coordinator** — let it author records and keep its Write grant. Rejected: routing judgment stays neutral only if the coordinator writes nothing.
3. **Dedicated record semantics** (chosen) — new `truncation` tag, pattern-validated authors, implementer-run audit, single writer roster.

## Decision

- A reviewer checkpoint emits a `truncation` finding: a progress marker that never halts the pipeline, never touches `.scratch/escalations.md`, and no longer pollutes the grader's hedging facet.
- `dispatch-start.author` validates by pattern — three specialists plus `*-reviewer` — extending the pattern-over-enum rationale of [Additive Reviewer Roster](2026-06-18-additive-reviewer-roster.md); the doctor owns roster membership. Extra-reviewer bodies must carry the First Tool Call stanza.
- The feature-implementer runs the autofix audit as a gate check. A failure appends `build-failure` with `failed_check: "autofix-audit"` and `abort_reason: "design-mismatch"`; system-design-expert reconciles and closes with a superseding `design-block`. Step 1 audits only records after the latest `design-block` — the supersession terminates the audit loop.
- `.scratch/escalations.md` has two writers: the feature-implementer (escalate-tag findings) and root on the coordinator's recommendation (prerequisite-missing aborts, reviewer stalls). The coordinator's Write grant is removed on every tool surface.

## Consequences

- Every prescribed record is now schema-admissible by its prescribed author; every halt rule has one deterministic trigger.
- An in-flight `.scratch/handoff.jsonl` holding an old escalate-tagged checkpoint finding still validates but halts once for a human decision; new records use `truncation`.
- Author patterns anchor with `\Z`, restoring the exact-match strictness the enum had.

## References

- [Additive Reviewer Roster: Floor Plus Declared Extras](2026-06-18-additive-reviewer-roster.md)
- [Deterministic Truncation Detection via Dispatch-Start](2026-06-04-deterministic-truncation-detection.md)
- [Append-Only JSONL Handoffs](2026-05-08-append-only-jsonl-handoffs.md)
