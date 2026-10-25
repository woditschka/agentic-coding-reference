# The Pre-Check Line Is Retired

**Status:** Accepted

## Context

The Scoping Pre-Check asks every creator and verifier dispatch for two
things before its first edit or finding. One is a scope decision, which
stops the dispatch with a `consultation-request` when the slice spans two
behaviors. The other is a length estimate with a planned checkpoint. The
plan-file ADR of 2026-10-20 made the estimate and the checkpoint one
transcript line beginning `Pre-Check:`; the checkpoint ADR of 2026-10-24
moved that line after the reads, before the first edit.

The sweeps show the line is not written. Implementer dispatches carrying
it: 15 of 23 under the old anchor in v0.4.9, then 3 of 25 on the dev arm
and 2 of the 24 implementer transcripts captured for v0.4.10 under the new
one. The behaviour behind it holds: in v0.4.10 the checkpoint gate
ran where due in 8 of 9 multi-cycle dispatches, and every scope stop is a
record. Nothing reads the line; its only consumer was offline analysis,
and that analysis reads the gate run instead.

## Options Considered

1. **Re-anchor the line** to the turn that makes the first edit. Rejected:
   a guess about model behaviour, verifiable only by the next sweep, for a
   line with no reader.
2. **Carry the estimate on the build record.** Rejected: written after the
   fact, so no longer a pre-edit estimate; a schema change for a
   retrospective number.
3. **Retire the line, keep the check** (chosen).

## Decision

**The Scoping Pre-Check keeps its scope decision and its planned
checkpoint; the `Pre-Check:` transcript line is retired.** The estimate and
the checkpoint are held in the dispatch, not written. The audit trail is
what already exists: the checkpoint gate run as a tool call in the
transcript, `cycles` on every build record, and the `consultation-request`
of a scope stop. The canonical text in `tdd-workflow`, the five role
restatements, the agent bodies, the handoff-append and review-workflow
skills, and the handbook say so; the pin file is regenerated.

## Consequences

**Positive.** The contract describes what runs. One obligation with no
consumer leaves every creator and verifier dispatch, at zero cost to the
behaviour it anchored.

**Negative.** The pre-edit trace of the estimate is gone. A checkpoint that
drifts later is read from where the gate run sits in the transcript, one
step downstream of a declared plan. That is where the v0.4.10 reading was
taken, so the loss is small.

## References

- [2026-10-24 the-checkpoint-runs-the-gate](2026-10-24-the-checkpoint-runs-the-gate.md):
  the checkpoint and the gate run this ADR keeps; its status records the
  retired line.
- [2026-10-20 the-implementer-keeps-no-plan-file](2026-10-20-the-implementer-keeps-no-plan-file.md):
  named the line as the slice-size gate's observable; its status records
  the replacement.
- [2026-10-25 convention-checks-carry-their-evidence](2026-10-25-convention-checks-carry-their-evidence.md):
  the same lesson from the other side, an output with no consumer is not
  produced; there the consumer was added, here the output is removed.
