# The Transcript File as the Unit of Cost Attribution

**Status:** Accepted

## Context

The board's cost overlay attributed a step's spend by summing the transcript messages whose timestamps fall inside the step's window — `dispatch-start` to the step's closing record. The window bounded messages.

That window opens mid-dispatch. A dispatch's first message carries the system prompt and the whole inbound context, so it dominates the dispatch's cost. It lands before the agent's first tool call appends the `dispatch-start` record that opens the window. A trailing message can land after the closing record. Message-window summing drops both ends, so every step under-reported its own dispatch.

The undercount is not uniform. It scales with how much of a dispatch precedes its first tool call, which varies by agent type and by how much durable memory the role reads. A figure wrong by a different factor per agent misranks the agents within a slice. That removes the usual defense that a biased number stays directionally useful.

## Options Considered

1. **Leave it; treat the figures as directional.** Rejected: the bias varies by agent type, so the board cannot rank agents within a slice honestly.
2. **Anchor the window at the preceding record** rather than the agent's own `dispatch-start`. Rejected: it attributes less, not more. In a parallel reviewer fan-out the preceding record belongs to a different agent appended seconds earlier, which collapses the window instead of widening it.
3. **Append `dispatch-start` at true dispatch time.** Rejected: the record is prompt-side discipline appended by the dispatched agent itself. No agent can stamp a moment that precedes its own first message, and the router writes nothing.
4. **Whole-file attribution** (chosen).

## Decision

**The transcript file is the unit of cost attribution, not the message.** Claude Code writes one subagent transcript per dispatch, so a file *is* a dispatch. A step's window selects the files it overlaps and sums each in full, including messages outside the window's bounds. The window's role narrows from *which messages* to *which dispatches*.

**Session identity leaves attribution.** Two concurrent sessions over one project sit outside the harness's design space. They would collide on the handoff ledger and the working tree long before their spend was ambiguous. Sessions are sequential, so a dispatch's file is its own whatever session wrote it. The prior multi-session decline is removed.

**The scope is the step lines only.** A step line pairs a timed record to its author's own `dispatch-start`, so it names a dispatch and can price one. The header's roll-up sums authors across a slice's whole span without pairing, so it names no dispatch and stays message-windowed. Whole-file attribution there would sum every overlapping file once per author, over a span that reaches every dispatch in the slice.

**A step's figure is exact only while no two dispatches of one agent type overlap in time.** Two concurrent dispatches of one type write two files whose spans overlap, and every window over either selects both, so each line prints their sum. The pipeline fans out across distinct types — the reviewer roster — so its boards never render this. That is a property of the roster, not of the attribution. The premise is unenforceable: nothing in the log distinguishes two overlapping dispatches of one type from one long one.

Duration keeps its old anchor, running `dispatch-start` → record as an honest work-elapsed. Cost and duration now answer different questions over different spans, and a step's tail shows both.

## Consequences

**Positive:**

- A step's figure is its dispatch's real cost, so a slice's spend reads off its own board.
- A slice resumed in a later session now attributes. The retired session decline nulled its roll-up.
- The header moves closer to the sum of its lines. It always exceeded them, because it caught spend no line could claim; raising the lines to their dispatches narrows the gap it never explained.
- The statusline reads `session_totals`; the cache report reads the pricing multipliers. Neither reads the window index, so neither changes.

**Negative:**

- The header and the lines price a dispatch by different rules, so the two do not reconcile. Reconciling them needs a per-dispatch anchor the roll-up's signature does not carry.
- Concurrent dispatches of one agent type each print their sum, so they become unrankable rather than merely mispriced. The current roster makes this unreachable; a roster fanning out two of one type would restore it with nothing to catch it.
- Two dispatch classes attribute to no line: the `change-grader`, which is dispatch-exempt so no `dispatch-start` anchors a window, and a dispatch that appended no output record at all. The second is a ledger-discipline gap, not an attribution one.
- Dropping the session decline trades a silent omission for a silent overstatement, should two sessions ever run at once. Nothing enforces that; the collision on shared files is what makes it self-limiting.
- A file's span is built from its own message timestamps, which the harness does not control and nothing bounds. Ordinary clock skew is harmless, because the ledger's timestamps come from the same clock and windows move with spans. A single corrupt stamp is not: it widens the span into windows the dispatch never ran in. Clamping the span to the file's mtime would bound the forward half, but it binds attribution to a second clock the ledger never reads, and a filesystem clock running behind would collapse every span and blank the overlay.
- `since_secs` stays correct only because it prunes on file mtime, the last write. Pruning on a first message would silently restore the undercount.

## Implementation

`tools/harness-stats/cc_accounting.py` (canonical) — `WindowIndex`, `_overlapping`, `totals`, `slice_totals`. The vendored copy is `harness/core/scripts/cc_accounting.py`, gated by the battery's cc_accounting vendored-copy sync step. The premise and its failure case are pinned in `harness/core/scripts/test_cc_accounting.py` — `TestWindowIndex`.

## References

- [Single Pricing Source as a Gated Vendored Copy](2026-07-13-single-pricing-source-vendored-copy.md) — the module's two homes, and the gate policing the manual copy this change traverses.
- [Append-Stamped Record Timestamps](2026-07-13-append-stamped-record-timestamps.md) — why a record's `ts` is the append moment, which is what places a window mid-dispatch.
