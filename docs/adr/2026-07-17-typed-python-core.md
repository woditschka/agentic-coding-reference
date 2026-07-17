# A Typed, Checker-Enforced Standard for the Harness Python Core

**Status:** Accepted

## Context

The harness core — `handoff.py`, `brief_doctor.py`, `score-change.py`, roughly 5,500 lines of logic — carries zero type annotations across 117 functions. Records travel as raw dicts from parse to routing. Fail-closed routing is therefore a tested property only: nothing but the suite notices a record type no `match` arm handles. Readability and audit confidence lag the discipline the code otherwise shows, and every new contributor — human or agent — re-learns record shapes from usage.

## Options Considered

1. **Status quo** — rejected: dict-shaped records leave the exhaustiveness and readability gaps open, and the suite alone carries properties a checker could hold.
2. **Rewrite the core in a language with compiler-enforced sealed types (Java 25; one-shot CLI, daemon, and MCP variants designed)** — rejected: a JDK lands in every consumer's toolchain, the runtime gains its first third-party dependency, and the copy channel must ship a binary or a build. The enforceable gains are recoverable in typed Python with no new consumer toolchain. Reverses [logic-in-python](2026-07-06-logic-in-python-orchestration-in-bash.md).
3. **Modernize the Python in place** (chosen) — typed records, checked exhaustiveness, gated formatting; zero consumer-facing change.

## Decision

**The harness core adopts a typed standard: frozen dataclasses for records, a union type routed by `match` with `assert_never`, full annotations under a strict type checker, ruff formatting.**

Load-bearing details:

- **Statically exhaustive routing.** `HandoffRecord` is a union of frozen dataclasses; every `match` over it ends in `typing.assert_never`. Adding a record type fails the type check until every match handles it — fail-closed becomes a checked property, not a tested one.
- **Dicts survive at the parse boundary and three sanctioned routing uses.** One lenient lift per record type turns any dict into its dataclass. Every field is optional because every reader of the log is lenient by contract — route bounces malformed records, view renders holes. The schema validator alone owns requiredness; the model gives typed `.get()` semantics, not schema-requiredness. The routing core reads raw dicts only for schema gates, decision payloads, and gate-message finding indexes.
- **Strict parsing hardens.** Duplicate-key rejection (`object_pairs_hook`) joins `loads_strict`; every `open()` pins `encoding="utf-8"`.
- **Gates join the battery.** `ruff format --check`, `ruff check`, and `mypy --strict` run as check-sync steps — skip-if-missing, FAIL under `--strict` — the shellcheck/bandit precedent. Tool config lives at the repo root; the stdlib-only scan keeps manifests out of every shipped tree.
- **The shipped contract is unchanged.** Stdlib-only, Python 3.11+, `unittest`, single-file scripts or flat sibling-module sets with test siblings — [logic-in-python](2026-07-06-logic-in-python-orchestration-in-bash.md) holds; this ADR layers a code standard on top of it. (This migration splits handoff.py into such a set by trust class.)
- **Migration is behavior-frozen.** Golden-log byte-identity tests pin canonical output first; typing then lands module by module under the existing suites.

## Consequences

- Positive: routing exhaustiveness is enforced by the checker; typed records document shapes where prose and usage did; consumers see no change; the standard is held by battery gates, not review attention.
- Negative: the maintainer toolchain grows ruff and mypy (required under `--strict`, so the push-time gates need them installed); annotations add lines; a rewrite question returns only if the typed core still resists audit.

## References

- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — the language decision this ADR extends with a code standard.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — the tier logic applied: a deterministic gate outranks style prose.
- [Mechanical Promises Move Into Engines](2026-07-14-mechanical-promises-into-engines.md) — precedent for enforcing a convention by engine, not reviewer memory.
- [Deterministic Mid-Slice Routing via handoff.py route](2026-07-06-deterministic-mid-slice-routing.md) — the fail-closed routing property the type system now guards.
