# Append-Only JSONL Handoffs with Schema Validation Gate

**Status:** Accepted

## Context

Pipeline specialists rework a large fraction of their dispatches: in observed runs, system-design-expert and product-requirements-expert each rework around 88% of dispatches and feature-implementer around 76%. A meaningful portion of total spend goes to cache reinjection driven by these retries. The handoff artifacts in `.scratch/` were markdown, which admits under-specified inputs: downstream specialists discover the gaps mid-design and must be re-dispatched. Markdown also makes schema validation impractical — checking required fields against prose is regex archaeology, while checking them against a structured record is one library call.

The structural fix is "the coordinator refuses malformed handoffs before the next specialist is dispatched." That fix is only practical if the handoff format is structured.

## Options Considered

1. **Keep markdown** — Accept the rework cost. No schema, no gate.
2. **Multi-document YAML** — Append `---`-separated documents. Human-readable, but YAML's loose syntax (indentation drift, ambiguous scalars) is a known LLM hazard.
3. **Append-only JSONL with JSON Schema** — One JSON object per line, each carrying a `type` discriminator. Schema per type. Coordinator validates at agent transitions.
4. **Protobuf or a custom DSL** — Over-engineered for a small handoff surface; high tooling cost.

## Decision

We use option 3: append-only JSONL in `.scratch/handoff.jsonl`, one record per line. Each record carries a `type` discriminator. Per-type JSON Schemas live in `schemas/scratch/`. The pipeline-coordinator validates inbound records at agent transitions; a malformed or missing record bounces back to the upstream agent without consuming a Sonnet/Opus dispatch.

Append-only is non-negotiable: each agent dispatch appends a record, and nothing rewrites prior records. The retry trail this preserves makes "what did dispatch N+1 add that N lacked" directly inspectable — the diagnostic the schema needs to grow on real evidence rather than upfront speculation.

`docs/` markdown (PRD, system-design, ADRs) is unaffected; those stay markdown for human authorship.

### Migrated Record Types

| Type | Producer | Consumer | Replaces (markdown) |
|---|---|---|---|
| `prd-entry` | product-requirements-expert | system-design-expert, feature-implementer | `current-feature.md` |
| `design-block` | system-design-expert | feature-implementer, coordinator | `design-notes.md` |
| `review-feedback` | code-quality-reviewer, test-reviewer, security-reviewer, doc-reviewer | feature-implementer | `reviews/*.md` |
| `build-failure` | feature-implementer | coordinator, system-design-expert (on retry=3 escalation) | `build-failure.md` |
| `build-pass` | feature-implementer | coordinator | (new — replaces "absence of build-failure.md") |

The five record types share one append-only file. The discriminator picks the schema; the latest record per `(req_id, type)` is the active state for routing decisions.

### Out of Scope (intentionally markdown)

- `implementation-plan.md` (implementer self-tracking, no handoff gate)
- `review-summary.md` (derivable from `review-feedback` records via `jq`; dropped, not migrated)
- `escalations.md` (human-read only)
- `eval-<feature>.md` (human-read only)

These artifacts have no rework loop or are human-facing; structuring them adds friction without reducing retry cost.

## Consequences

**Positive:**
- Schema validation converts specialist retries into cheap structural rejections at the gate.
- Append-only preserves the retry trail; humans can diff dispatch N against N+1 to see what was missing.
- Strict JSONL syntax catches LLM formatting drift immediately.
- Tooling consistency: JSONL is easy to parse with standard libraries, `jq`, or a small renderer.

**Negative:**
- Less human-readable than markdown; mid-feature inspection needs `jq` or a small renderer.
- Initial schema field sets are guesses; they grow on observed retry deltas.
- Adds a coordinator validation step at each transition (small latency overhead).
- Migration cost: every pipeline agent except the four review-only sub-agents has at least one read or write target updated.
- One schema per record type carries an upfront design risk; mitigated by keeping required-field sets minimal and treating optional fields as the default.

## Implementation

**Non-goal:** This is a harness architecture decision, not a feature requirement of the project. Implementation lives in `.claude/agents/`, `.claude/skills/`, and a new `schemas/scratch/` directory.

## References

- [`2026-03-22-skill-based-agent-architecture.md`](2026-03-22-skill-based-agent-architecture.md) — establishes the pipeline this ADR refines
- `.claude/agents/README.md` — agent roles
- `.claude/skills/pipeline-handoff/SKILL.md` — current routing logic
