# Lock-Free Ledger Appends with Exact Receipts

**Status:** Accepted

## Context

The reviewer roster appends to `.scratch/handoff.jsonl` in parallel; each reviewer's first tool call is its own `dispatch-start` append. No prior decision covered concurrent writes — the transcript-cost ADR (2026-07-15) scoped out concurrent *sessions* while affirming parallel subagents. An external review (2026-08-16) flagged the gap as its top finding. The write itself was already atomic; the verified races sat in the reads around it. The post-append reread printing "appended at line N" could report another writer's line. Agents cite that receipt in `responding_to`, where an off-by-one passes the bounds check and degrades fix attribution silently. The tail-repair check-then-prepend could double-fire. One sanctioned write surface exists (`handoff.py`, hook-enforced), with two code paths behind it: the agent CLI and the grading engine's `append_validated`, each carrying its own repair copy. Line-number domains also diverged: receipts counted raw `b"\n"` while `parse_log` read with universal newlines.

## Options Considered

1. **Advisory locking (`flock`) around the append critical section.** Rejected: the append-only structure makes locks unnecessary, and advisory locks are unreliable on the network filesystems that also break `O_APPEND`.
2. **Private spool files merged by the coordinator.** Rejected: it changes the writer contract, leaves the board and router stale during a fan-out, and adds merge-ordering machinery — buying no correctness the chosen design lacks.
3. **Content-based record IDs replacing line references.** Rejected with a trigger: the migration touches every schema, four reference fields, three pointer gates, and the board. Exact receipts make physical lines reliable in the single-host, single-session scope. Revisit if the ledger ever spans files or sessions, or needs merging.
4. **Lock-free appends on the append-only structure** (chosen).

## Decision

**Both writer paths append with one `write()` on an `O_APPEND` descriptor; the CLI receipt derives from the writer's own end offset.** The guarantee is atomic *placement*, not atomic *visibility*. The kernel serializes regular-file writes on the inode lock, so concurrent records never interleave, at any record size. Signals land between syscalls, so a killed agent process cannot tear a record. Bytes before the end of one's own write never change afterward. `os.lseek(fd, 0, SEEK_CUR)` after the write therefore bounds an immutable prefix whose newline count is this record's exact line number. A short write (disk full) fails hard — a second write could interleave with another writer. The descriptors add `O_NOFOLLOW` (refuse a planted symlink) and `O_BINARY` (no Windows newline translation), zero where absent.

Visibility gets its own treatment, because a multi-page write is reader-visible before its final newline lands. The pre-write tail repair is removed from both paths: a reader cannot tell a crash-damaged tail from a write still in flight, so any check-then-act could dirty a healthy log. An append onto a genuinely damaged tail lands glued, warns on stderr, and leaves the fail-closed halt to `validate` and `route`. `route` re-reads once after 50 ms before concluding `dirty-log` — the bound outlasts any in-flight write, and persistent damage still blocks. In-flight state is thereby never mistaken for damage, and damage never passes.

Every reader moves to the receipt's raw-`\n` domain: `parse_log` and `show` read with `newline=""`, the grading loaders with `newline="\n"`. A bare `\r` then fails parse loudly instead of silently shifting later line numbers — the prior universal-newline readers disagreed with the receipts on exactly that byte.

The `responding_to` bounds check needs no change, only its argument recorded: a concurrent append can only make the observed count lag, so the check may over-reject a referent written an instant ago, never accept a dangling one. A real referent is written before its responder is dispatched.

The atomicity claim is a local-POSIX-filesystem property. The shipped suite carries a multi-process stress test — parallel CLI writers, half writing multi-page records, must land exactly once, validate clean, and receive receipts naming their true lines. A deterministic two-descriptor test pins the offset mechanism itself. Install-time verification thereby proves the property on the consumer's filesystem; network mounts are the known offender, and Windows' CRT-emulated `O_APPEND` is not atomic across processes.

## Consequences

Positive:

- Receipts are exact under any interleaving; the silent `responding_to` off-by-one class closes. The stress test at its shipped setting (4 workers × 6 appends) detected the prior reread defect in 3 of 3 runs — a probabilistic race detector; the two-descriptor test pins the mechanism deterministically.
- In normal operation, including maximal fan-out, the log stays clean and no append-induced halt occurs. Pipeline-designed halts (conflict, non-convergence, consultation) are untouched.
- No migration: across the 188 committed eval ledgers, zero `responding_to` values are out of range and zero bare `\r` bytes exist, so every recorded pointer stays valid.
- Fan-out arrival order is kernel order. Routing is already order-insensitive within a pass: completion reads the latest verdict per seated reviewer. The invariant suite pins that and its neighbors — grade-neutral routing, off-roster approvals never seating, latest-report-wins, cap rounds one past through three past the cap blocking, and route totality over every record type.

Negative:

- A crash-severed tail now always reaches the fail-closed halt; the old repair could silently ride over the narrow newline-only severance. Human intervention stays confined to machine catastrophe — disk full, OS crash, non-atomic filesystem.
- `/materialize` hard-fails on a filesystem without `O_APPEND` atomicity (a network mount): the install gate now enforces what the pipeline silently assumed.
- `route` pays one 50 ms re-read when it catches an in-flight append; a genuinely dirty log pays it once before blocking.

## Implementation

`harness/core/scripts/handoff.py` (`cmd_append`, `cmd_route`, `cmd_show`), `harness/core/scripts/handoff/schema.py` (`parse_log`), `harness/core/scripts/grading/handoff_facts.py` (`append_validated`, `load_records`, `read_handoff`), `harness/core/scripts/tests/test_handoff.py` (`TestConcurrentAppends`), `harness/core/scripts/tests/handoff/test_routing.py` (`TestRoutingInvariants`).

## References

- [Append-Only JSONL Handoffs](2026-05-08-append-only-jsonl-handoffs.md) — the structure whose immutability the receipt leans on.
- [The Transcript File as the Unit of Cost Attribution](2026-07-15-transcript-file-cost-attribution.md) — scoped out concurrent sessions; this decision covers concurrent subagents within one session.
- [Split the Handoff Contract by Role](2026-07-05-handoff-skill-split.md) — the single-sanctioned-surface enforcement the spool option would have complicated.
