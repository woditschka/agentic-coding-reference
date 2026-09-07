# Experts Record What They Write; Agents Execute From the Current-State Docs

**Status:** Accepted

## Context

Nine of the twelve implementing reps in the v0.3.9 sweep fail the autofix audit on the first build. The rate has held at eight or nine per sweep since v0.3.3. The transcripts show the writer was never the implementer. The design expert wrote `docs/system-design.md` fifty-eight times and ADRs twelve times across the sweep; the PRD expert wrote non-goal ADRs ten times. The audit found the paths uncovered for two reasons. The design expert's block omitted a design-doc path its own dispatch had written, the contracts row in five reps. In six reps the PRD expert's non-goal ADR, its sanctioned write under a scope override, had no covering record at all. The audit accepted only a design-block or a design-doc-autofix. Each bounce cost a superseding block at $1.08 on average, an implementer re-dispatch, and, through the design-revision trigger, a full battery in two reps.

A second cost sits beside it. The design expert read the ADR directory on every triage, and both experts wrote ADRs for micro-decisions such as which cache a filtered read uses. No agent executes from an ADR. The design doc's current-state lines are what the implementer and the reviewers hold the change to; an ADR is the decision log behind one of them.

## Options Considered

1. **Teach the expert to list the paths.** Rejected alone: a prose rule the expert already had in spirit, missed nine times in twelve.
2. **Widen the audit to accept any expert record as cover.** Rejected: the audit's value is that a record names the path it claims.
3. **Check coverage at the expert's append, with the audit's own rule** (chosen), plus the two coverage rules the record set was missing.

## Decision

**`handoff.py append design-block` refuses a block that would leave an uncommitted design-doc path uncovered.** The check is the audit's step two with the candidate block in the entry set, never a stricter rule. An omission surfaces at the one moment the expert can still fix it. An unreadable git state skips the check; the audit still fails closed at the gate.

**A `prd-entry` carrying `scope_overrides` covers the non-goal ADR its change records, and `docs/adr/README.md` is covered whenever every other dirty ADR path is.** Gate 1 already bounces a Non-Goals change without a quoted override, so the scope-overriding entry is the record of the PRD expert's dispatch. The index follows its files.

**ADRs are documentation for the project. Agents execute from the manifested knowledge.** The implementer's read set is the design doc, the PRD entry, the two principle briefs, and the ubiquitous language, never the ADR directory. The design expert reads an ADR by back-link when a slice touches a line that cites one. An ADR is written when a decision constrains future slices or reverses a recorded one; a smaller rationale is one clause on the current-state line.

**A pre-build correction of record is not a design revision.** Recorded as the [2026-09-07 amendment of 2026-08-07](2026-08-07-review-cycle-survives-mid-slice-design-records.md#amendment-2026-09-07-a-correction-of-record-is-not-a-design-revision).

## Consequences

**Positive:** the correction round disappears at its source. The design expert's triage read shrinks by the ADR directory. Fewer ADRs are written, and the ones written carry a decision.

**Negative:** a design-block append now runs two git reads. A project whose design-doc dirt belongs to another in-flight slice sees the refusal at the expert's append rather than at the gate, with the same path list either way.

## Implementation

`handoff.py` (`_covers_path`, `_audited_autofix_lines`, `_uncovered_design_doc_paths`, the design-block branch of `cmd_append`) with tests in `tests/test_handoff.py`. `grading/handoff_facts.py` for the counter. The `design-validation` and `code-quality-gate` skills and the `system-design-expert` agent in every stack. `handoff-routing` and `tdd-workflow` in core.

## References

- [2026-07-18 prd-autofix](2026-07-18-prd-autofix.md): the audit whose covering-record set this decision completes.
- [2026-08-08 scope-lock](2026-08-08-scope-lock-the-request-is-never-the-override.md): the quoted `scope_overrides` that now also cover the non-goal ADR.
- [2026-07-14 mechanical-promises-into-engines](2026-07-14-mechanical-promises-into-engines.md): the doctrine that moves the path rule from prose into the append.
- [2026-09-07 one-construction-api-briefs-before-the-writer](2026-09-07-one-construction-api-briefs-before-the-writer.md): the companion decision on what the writer reads.
