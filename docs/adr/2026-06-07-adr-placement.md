# ADR Placement: Single Seed ADR in Samples, Decision Log at Root

**Status:** Accepted; sample-seed clause superseded by [2026-06-12-docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md) — samples ship no ADRs; a consumer's `adr/` starts with only the README stub

## Context

The reference accumulated one ADR per harness capability — append-only JSONL handoffs, principles-over-rules, deterministic truncation detection, and the change-grader trio. Each sample (`samples/go/`, `samples/java-spring-boot/`) carried a near-identical copy of all of them.

The samples exist to **seed** new and existing projects via `/seed`. Carrying the reference's own build history into a seed is wrong on two counts. An adopting project inherits decision records about *how this harness was built*, not about *their* domain. And every new harness capability multiplies ADR copies across both samples.

Deleting the history is also wrong: the options considered and the trade-offs behind each capability are the most valuable part of an evolving reference.

## Options Considered

1. **All ADRs in both samples** — status quo. Seeds carry build history; every decision is duplicated per sample.
2. **Delete the build-history ADRs** — clean seeds, but the *why* survives only in git history.
3. **Split** — one consolidated architecture ADR in each sample; the full decision log at root.

## Decision

Option 3.

- **Samples** ship exactly one ADR: `YYYY-MM-DD-skill-based-agent-architecture.md`, refreshed to the current harness state and dated to the latest harness change. It demonstrates the ADR format and records the architecture an adopter starts from. Refresh it in place on each milestone; do not append per-capability ADRs to a sample.
- **Root `docs/adr/`** is the reference's canonical decision log — every harness decision, at its original date, with options and trade-offs. New harness decisions are recorded here, not in the samples.
- The root README **Project History** stays the *what/when* timeline; the root ADRs are the *why*.

## Consequences

**Positive:**
- Seeds stay clean: an adopting project starts with one example ADR and adds its own.
- The evolution rationale is preserved and discoverable at the reference root.
- A new harness capability adds one root ADR, not two sample copies.

**Negative:**
- The sample architecture ADR is refreshed in place, so its own change history lives in git rather than a chain of superseding ADRs.
- Root ADRs describe implementations that live in the samples; their artifact references are code spans, not links, to stay sample-agnostic.

## References

- [Project History](../../README.md#project-history) — the what/when timeline these ADRs explain
- [`../../samples/go/docs/adr/`](../../samples/go/docs/adr/), [`../../samples/java-spring-boot/docs/adr/`](../../samples/java-spring-boot/docs/adr/) — README stub only since the 2026-06-12 ADR
- [`2026-03-22-skill-based-agent-architecture.md`](2026-03-22-skill-based-agent-architecture.md) — the architecture this log opens with
