# Handoff Log Access: Single Deterministic Tool, Not Free-Form Writes

**Status:** Accepted

## Context

Agents read and write `.scratch/handoff.jsonl` as the pipeline's single source of truth. The skill prose defined what to append (record types, schemas, gate queries) but not how. Agents improvised the mechanics: `cat >>` heredocs, `echo` with hand-escaped JSON, `Edit` tool calls on the raw file. Each improvisation risks corruption — a missing trailing newline glues two records onto one line and the whole file stops parsing. Gate queries (latest record per `(req_id, type)`, the retry counter) were re-derived per agent from prose, with divergent results. Humans also inspect the raw file; alphabetically sorted keys would bury the `type` discriminator mid-line.

## Options Considered

1. **Prose rules only** — cheapest; leaves the failure mechanism (shell quoting under pressure) in place. Rejected: the inventive workarounds are the evidence prose does not hold.
2. **Bash + jq tool** — handles canonical output and queries; cannot validate against the JSON Schemas without adding `ajv` or hand-translating 11 schemas into jq assertions. Also receives multi-line JSON through the same quoting machinery that causes the corruption. Rejected.
3. **Python stdlib tool (chosen)** — `scripts/handoff.py`, following the `score-change.py` precedent already wired into both samples' CI gates. Python 3 is an existing toolchain dependency, not a new one.
4. **Runtime hook enforcement** — a `PreToolUse` hook denying raw writes to the log. Deferred: Claude Code-only; the other three tools rely on skill prose either way.

## Decision

One tool, five operations: `append` (schema-validate, then write canonically), `validate` (whole-file check), `latest` and `next-retry` (the gate queries), `show` (human inspection). Canonical form is schema declaration order — `type`, `req_id`, `ts`, `author` first, payload next, optional fields last — chosen over sorted keys because humans inspect the raw file. Validation is a closed draft-07 subset matching exactly the keywords the schemas use; any other keyword fails loudly, and a test sweeps every repo schema against the subset. The `pipeline-handoff` skill owns the mechanics section; agent bodies keep saying *what* to append, the skill says *how*. `score-change.py extract` keeps its direct append under its own determinism contract.

## Consequences

**Positive:**

- Same logical record yields the same bytes regardless of which agent or tool wrote it; the file always parses.
- Schema violations surface at write time with the schema error, not at the next gate as a routing mystery.
- The retry-counting rule lives in one tested function instead of being re-derived from prose per dispatch.
- `append` returns the new line number, feeding `responding_to` references without a separate read.

**Negative:**

- Enforcement is prompt-side discipline plus the skill's prohibition; nothing stops a raw `>>` at runtime. The deferred hook closes this for Claude Code if discipline proves insufficient.
- The mini-validator is a subset; schema authors must extend it before using new keywords. The schema-sweep test converts that risk into a build failure.

## Implementation

`scripts/handoff.py` and `scripts/test_handoff.py`, byte-equivalent across both samples, wired into `make test-scripts` and the Gradle `check` task. The `pipeline-handoff` skill § Log Access owns the mechanics; every log-writing agent's allowlist names the tool. Each sample's `schemas/scratch/` stays the validation source.

## References

- [`2026-05-08-append-only-jsonl-handoffs.md`](2026-05-08-append-only-jsonl-handoffs.md) — the ledger this tool guards
- [`2026-06-05-change-grade-extractor-worktree.md`](2026-06-05-change-grade-extractor-worktree.md) — the stdlib-Python tooling precedent
- [`2026-06-11-root-seed-harvest.md`](2026-06-11-root-seed-harvest.md) — distributes the tool to downstream projects
