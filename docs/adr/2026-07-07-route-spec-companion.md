# State Runtime Prose Once; Move the Route Spec Out of the Loaded Skill

**Status:** Accepted

## Context

Every pipeline dispatch preloads its agent's skills, so every line of skill prose is a per-dispatch token cost. A core-runtime review (2026-07-07) measured 25–30% of that prose as duplication: the `handoff-routing` skill (388 lines) restated the Handoff Conditions table, gate field checks, and recovery steps that `handoff.py route` executes and `test_handoff.py` pins; the installed `agentic-harness.md` restated change grading, the record table, and recovery; 17 agent bases carried the same 9-line dispatch-start block (~68 rendered files); the Scoping Pre-Check, slice-sizing rule, roster definition, and feedback-tag semantics each appeared 3–6 times. Duplicated statements also drift — several copies already disagreed in wording.

[2026-07-05 — Handoff skill split](2026-07-05-handoff-skill-split.md) rejected on-demand companion files because recovery correctness would then depend on the model following a pointer. That objection predates [2026-07-06 — Deterministic mid-slice routing](2026-07-06-deterministic-mid-slice-routing.md): since `route` executes the table and the coordinator is forbidden to re-decide it, routing correctness lives in code and tests, not in any agent reading prose.

## Options Considered

1. **Leave the duplication; it reinforces the contract.** Rejected: repetition without a sync mechanism is drift waiting to happen, and the token cost recurs on every dispatch.
2. **Trim each copy in place.** Rejected: keeps N statements to keep synchronized; the cost is the count, not the wording.
3. **One canonical statement per contract, pointers everywhere else; move never-consumed spec text out of the loaded file.** Chosen.

## Decision

**Each runtime contract is stated once, in the file its consumer loads; every other surface carries a one-to-two-line summary plus a pointer.**

- **`route-spec.md`** (new, in the `handoff-routing` skill directory): the normative Handoff Conditions table, gate field checks, Build-Failure Recovery steps, Truncation Recovery mechanics, and the pipeline-flow diagram. `route` executes it; `test_handoff.py` pins it; no agent preloads it. Root reads a named recovery section on demand when assembling a recovery-dispatch prompt — the routing decision itself never depends on any model reading this file. `SKILL.md` keeps every externally-referenced section heading as a judgment-facing stub, so existing `§` pointers stay valid. This is 2026-07-05's rejected option 2 made safe: correctness moved from prose into a deterministic executor; the on-demand read shapes a prompt, never a decision.
- **Canonical homes:** dispatch-start block → `handoff-append` § Dispatch-Start (agents keep author value and typical `responding_to`); Scoping Pre-Check → `tdd-workflow` (review-workflow keeps only reviewer deltas); slice-sizing → `prd-authoring` § Slice-Sizing Rule; roster → `review-workflow` § Review Phase; feedback tags → `review-workflow` (schema descriptions shrink to one clause per enum value plus a pointer).
- **The installed `agentic-harness.md` sheds what its readers never consume there** (change-grading detail, the record table, the recovery-signal table); the root `docs/agentic-harness.md` keeps the long form as the human-facing handbook, and `handbook-delta.expected` re-pins the now-larger intentional divergence.

Cross-tool constraint: only `SKILL.md` loads as a skill body in all four tools; companion files ship but load on explicit Read only. The dispatch-start move relies on `handoff-append` being preloaded (`skills:` frontmatter on Claude Code and Junie) or body-instructed (Copilot, OpenCode); a malformed first append self-corrects because `append` validates and rejects with the schema error.

## Consequences

- A dispatch loading `handoff-routing` sheds ~170 lines; one loading the installed handbook sheds ~90; each agent body sheds ~11; measured across a clean slice, roughly 8–9k tokens per run.
- One statement per contract: an edit lands in the canonical home and the pointers stay true; the battery's parity and faithfulness steps gate the propagation.
- Editing routing behavior now touches three files in one change — `route-spec.md`, `handoff.py`, `test_handoff.py` — stated at the top of the spec.
- On Copilot and OpenCode, an agent may read `handoff-append` before its dispatch-start append; the contract cares about record order in the ledger, not tool-call ordinal, so detection is unaffected.

## References

- [2026-07-05 — Handoff skill split](2026-07-05-handoff-skill-split.md) — split by audience; this ADR removes restatement within an audience and reverses its option-2 rejection under new facts.
- [2026-07-06 — Deterministic mid-slice routing](2026-07-06-deterministic-mid-slice-routing.md) — the executor that makes the spec safe to unload from runtime context.
- [2026-07-02 — Executable pipeline contracts](2026-07-02-executable-pipeline-contracts.md) — the same principle: contracts enforced by code, documented once.
