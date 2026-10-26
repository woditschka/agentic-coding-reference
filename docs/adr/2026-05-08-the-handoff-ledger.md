# The Handoff Ledger Is Append-Only JSONL Written Through One Tool

**Status:** Accepted

## Context

Pipeline specialists reworked a large share of their dispatches: system-design-expert and product-requirements-expert around 88%, feature-implementer around 76%. The markdown handoffs in `.scratch/` admitted under-specified inputs that downstream specialists found mid-design, and prose cannot be schema-checked. The structural fix, refusing a malformed handoff before the next dispatch, needs a structured format.

A format alone did not hold. Agents improvised writes with `cat >>`, hand-escaped `echo`, and `Edit` calls; one missing newline glued two records and stopped the file parsing. Gate queries were re-derived from prose with divergent results. The heredoc append embeds the record, so no prefix allow-rule matches it and every append prompted for permission. The 4,599-word `pipeline-handoff` skill bundled routing, writing, and root procedures, charging each Opus writer about 6k tokens for routing it never used. The author-supplied `ts` field was invented: one slice logged an 8.5-hour timeline for 55 minutes of transcripts. The reviewer roster appends in parallel, and the post-append reread could report another writer's line number, which `responding_to` then cited.

## Options Considered

1. **Keep markdown** or **multi-document YAML.** Rejected: no schema gate; YAML's loose syntax is a known model hazard.
2. **Protobuf or a custom DSL.** Rejected: over-engineered for a small surface.
3. **Prose rules for the write mechanics.** Rejected: the improvised workarounds are the evidence prose does not hold.
4. **A bash + jq tool.** Rejected: no schema validation without new dependencies, and the same quoting machinery that corrupts.
5. **Broader agent tool grants**, **a prefix allow-rule**, or **a content-free file argument** for the append. Rejected: grants govern availability not approval, prefix rules miss the heredoc, and a file argument needs a write tool read-only reviewers lack.
6. **Trim the bundled skill in place** or **extract recovery to on-demand companion files.** Rejected: the cost is the audience mix, and routing correctness must stay always-loaded.
7. **Instruct agents to run `date -u`** or **validate `ts` plausibility at append.** Rejected: an instruction is not a guarantee, and a tolerance keeps a wrong field.
8. **`flock` around the append**, **private spool files merged by the coordinator**, or **content-based record IDs.** Rejected. Locks are unreliable on network mounts, spools stale the board mid-fan-out, and content IDs touch every schema and gate. Content IDs are revisited if the ledger ever spans files or sessions.
9. **Append-only JSONL, one stdlib tool, hook-guarded, engine-stamped, lock-free** (chosen).

## Decision

**The ledger is `.scratch/handoff.jsonl`, append-only, one schema-validated JSON record per line, and `scripts/handoff.py` is its only sanctioned writer and its reader.**

- **Format.** Each record carries a `type` discriminator; per-type JSON Schemas live in `schemas/scratch/`. Nothing rewrites a prior record, so the retry trail stays inspectable. The latest record per `(req_id, type)` is the active state. `docs/` stays markdown; `escalations.md` stays human-read markdown.
- **The tool.** `scripts/handoff.py` is stdlib Python with the operations `append`, `validate`, `audit`, `latest`, `next-retry`, `route`, `tier`, `show`, and `view`. `append` validates against a closed draft-07 subset, writes canonical key order (`type`, `req_id`, `ts`, `author`, payload, optionals), and returns the record's line number for `responding_to`. A schema keyword outside the subset fails loudly; a test sweeps every schema against it.
- **The append form.** A record is a quoted heredoc on the tool's stdin, and the command line begins with `python3 scripts/handoff.py append <type>`. That form needs no file-write tool, so every agent uses it.
- **Pre-approval per tool.** Claude Code ships `handoff-allow.py`, a `PreToolUse` hook that allows a command that is solely a `handoff.py` invocation and defers everything else, never denying. `refresh-settings.py` ensures its matcher in `.claude/settings.json` on every materialize, additively. OpenCode pipeline agents declare `bash: allow`. Copilot keeps a documented one-time launch flag; the Adoption Guide § Handoff Append Pre-Approval holds the per-tool table.
- **Raw writes are blocked.** `handoff-log-guard.py` denies `Write`/`Edit` calls and shell redirection or `tee` onto the log on Claude Code. On every tool the quality gate runs `handoff.py validate`, so a corrupted log fails before review.
- **The contract is split by reader.** `handoff-append` holds the writer contract and is preloaded by every record-writing agent. `handoff-routing` holds the coordinator contract plus the root-applied procedures. `review-workflow` holds the review-loop contract. The first-tool-call stanza stays inline in every agent body as the exact pre-approved command.
- **`ts` is engine-stamped.** `append` overwrites any author-supplied `ts` with `datetime.now(timezone.utc)`; schemas keep it required so `validate` still rejects a raw-written record. Engine writers that bypass stdin, such as `append_validated` in `grading/handoff_facts.py`, stamp through the same `ts_now`.
- **Appends are lock-free.** Both writer paths issue one `write()` on an `O_APPEND | O_NOFOLLOW` descriptor (`O_BINARY` where present); a short write fails hard. The receipt derives from the writer's own end offset, so it names the record's exact line under any interleaving. No pre-write tail repair exists; a damaged tail reaches the fail-closed halt in `validate` and `route`. `route` re-reads once after 50 ms before concluding `dirty-log`. Every reader counts raw `\n`, so a bare `\r` fails parse loudly. A shipped multi-process stress test proves the property on the consumer's filesystem at install time.

## Consequences

**Positive:**

- Schema violations surface at write time with the schema error, and the same logical record yields the same bytes from any agent.
- Writer dispatches shed about 3,830 preloaded words (~5k tokens) each; reviewers net +312 words to carry the write contract inline.
- Ledger time is wall-clock time, so board durations and transcript cost windows measure real work.
- Receipts are exact under fan-out: the stress test (4 workers × 6 appends) detected the prior reread defect in 3 of 3 runs. Across 188 committed eval ledgers, zero `responding_to` values are out of range and zero bare `\r` bytes exist, so no migration was needed.

**Negative:**

- Mid-feature inspection needs the tool (`show`, `view`) rather than a text editor.
- Copilot coverage is a documented manual step, since it keeps command approval in user space.
- A crash-severed tail always halts fail-closed; human intervention stays confined to machine catastrophe.
- `/materialize` hard-fails on a filesystem without `O_APPEND` atomicity, such as a network mount.
- The validator is a subset; a new schema keyword needs the validator extended first.

## Implementation

`harness/core/scripts/handoff.py` with `handoff/schema.py` and `grading/handoff_facts.py`; `harness/core/.claude/hooks/handoff-allow.py` and `handoff-log-guard.py`; `harness/init/core/.claude/settings.json` for the registrations; the `handoff-append`, `handoff-routing`, and `review-workflow` skills; `schemas/scratch/`; the suites under `harness/core/scripts/tests/`.

## References

- [Skill-based agent architecture](2026-03-22-skill-based-agent-architecture.md) — the pipeline whose handoffs the ledger carries.
- [Deterministic routing engines](2026-07-02-deterministic-routing-engines.md) — `route` and `tier` read the ledger; the `dirty-log` halt is theirs.
- [Review convergence](2026-07-14-review-convergence.md) — routing is order-insensitive within a pass, which is why kernel arrival order suffices.
- [The change grader](2026-06-05-the-change-grader.md) — the grading engine's writer, which stamps through `ts_now`.
- [Materialize](2026-06-11-materialize.md) — installs the runtime, registers the hook matcher, and runs the stress test on the consumer's filesystem.
- [The doctor](2026-06-14-the-doctor.md) — gates a delivered-but-unregistered hook.
- [Slice sizing and the checkpoint](2026-10-20-slice-sizing-and-the-checkpoint.md) — the implementer keeps no plan file, which closed the ledger's last markdown exemption.
- `docs/adoption-guide.md` § Handoff Append Pre-Approval — the per-tool pre-approval table.
