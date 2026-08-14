# The Root Is a Channel, Not an Author

**Status:** Accepted

## Context

The v0.3.0 sweep (3 reps per arm against v0.2.4) measured the root agent as the pipeline's growth point. On visit-edit, median delivery wall rose 37m to 53m while reviewer spans stayed level. The root's deduplicated output rose from 15–18k to 25–33k tokens, and its dispatch turns gained extended thinking that v0.2.4's dispatch turns lack. The mechanism is contractual: the round ladder made `reviews-needed` a mapped-section rule, so the root composes each reviewer relay from `route-spec.md` prose on every pass.

Intake carries the same authorship problem in a different form. The owner's request reaches the product-requirements-expert as the root's paraphrase of a root-hosted discussion. Every implementing visit-cancel rep on record traces to paraphrase-as-authority; the scope-lock ADR ([2026-08-08](2026-08-08-scope-lock-the-request-is-never-the-override.md)) closed that path for Non-Goals rows only. The rest of the intake remains ungated, and the discussion rides in the root's context for the whole run.

Fresh human questions have no owner rule: the root (or the pipeline-coordinator on `escalate`) judges which expert a question belongs to, while review findings already route by the deterministic document-ownership map (`_finding_owner`).

Subagents are non-interactive in all four supported tools; the root session is the only dialogue channel. A specialist can already question the human asynchronously (`consultation-request`, `target: "human"`), and the router returns the answer to the requester by ledger state.

## Options Considered

1. **Prose-only guidance for each mechanism.** Tell the root to relay faithfully and think less. Rejected: the harness ran this experiment; a rule without a deterministic carrier drifts ([2026-08-11](2026-08-11-bounded-review-convergence.md) rejected prose-only for the same reason).
2. **Interactive intake in a fresh session, cleared before the pipeline.** Preserves separation by session boundary. Rejected: subagent isolation already guarantees the separation — a dispatched specialist sees only its prompt and the disk — while a fresh session discards the warm 1h-TTL root cache for nothing.
3. **Root wears the expert contract and also authors the `prd-entry`.** Rejected: the coordinating context becomes the product authority, the exact inversion this decision removes.
4. **Intake outcome as a scratch artifact or dispatch-prompt quotes only.** Cheaper than a record. Rejected: prompt-only quoting does not survive a resumed run, and a scratch file sits outside the gated log. Only a ledger record is replayable, gate-checkable, and seedable.
5. **Reviewer continuation across rounds to reuse specialist caches.** Specialist cache writes land in the 5-minute bucket (`cc5`), so every re-dispatch rebuilds 130–300k tokens of prefix. Continuation would keep reviewer context across rounds. Rejected for now: no continuation primitive exists in three of four tools. A continued reviewer also anchors on its prior verdict where the plan engine deliberately re-reviews cold after a critical finding. The rebuild cost stays an accepted price of isolation.
6. **The channel doctrine with four deterministic carriers** (chosen below).

## Decision

**The root coordinates, relays, and quotes; it never authors a product, design, or review-contract statement. Four mechanisms carry the doctrine:**

- **Paste-ready relay.** Routing decisions that map prompt context (`reviews-needed`, `reviewer-stall-retry`, `outstanding-dissent`) carry a `prompt_note` string composed by the route engine. The root appends it verbatim; the mapped-section composition step is retired. `round` and `finding_bar` stay structured decision fields, machine-readable and test-pinned; the board recomputes its display round from the ledger.
- **Verbatim intake.** The record that opens a slice carries the owner's request and decisions as quotes, never as summary. Only `decisions` text authorizes a scope override at Gate 1 — the request stays context, so the request is never the override. The legacy `dispatch` override source bounces once an intake record exists. A specialist grounds its records in quoted owner statements or asks.
- **Consultation ownership.** A fresh human question belongs to the expert owning its document surface — the boundaries the finding router already uses. Scope and behavior belong to the product contract, structure and trade-offs to the design contract, ambiguity to the product contract first. The root's judgment collapses to that table lookup; the discussion then runs in session under the owning contract, and a scope-changing outcome exits through intake.
- **Recorded intake with a live front door.** The intake skill loads the owning expert's skills (`prd-authoring`; `design-validation` on demand) into the root session for a real-time discussion — same session, warm cache, no clearing. The discussion ends by appending an `intake-decision` record: the owner's decisions, quoted. The product-requirements-expert dispatch reads that record. Headless preparation seeds the same record from the task prompt and its manifest-declared decision clauses. Interactive and unattended intake run one contract with two front doors.

## Consequences

- The root's review-relay composition and its per-pass re-derivation retire; expected recovery is 3–5 minutes of root decode and thinking on review-heavy feature runs. The security review's ~2 minutes stay, paid deliberately.
- Intake provenance becomes uniform: every `prd-entry` grounds in a quotable `intake-decision` record, in both interactive and headless runs. The bench gains a seedable intake path, and the seed also removes the fresh-intake classification hop from measured runs — the next sweep's notes must name both conditions. Churn tails (superseded prd-entries and design-blocks, 5-vs-1 on record) are the measured target. The expected signal is a tighter rep spread before a lower floor.
- The design-discussion exit stays prompt-carried: the recorded-intake contract covers requirements intake today. Extending it to design exits is a named open edge, revisitable when a sweep shows design-side paraphrase costing runs.
- An interactive owner discusses with the expert contract in real time; the specialists still receive only records, so no authority flows through the root's memory of a chat.
- A new record type fans out: schema, gates, routing awareness, handbook, glossary, battery. The change lands as a tier-2 audited unit and warrants its own eval sweep.
- Cross-dispatch specialist cache rebuild is named an accepted cost. Reviewer continuation stays a recorded alternative, revisitable when a sweep shows fix rounds dominating cost — scoped, if ever, as a single-tool optimization that never runs on a `prior-critical` round.

## Implementation

- `harness/core/scripts/handoff/routing.py` — `prompt_note` in `reviews-needed`, `reviewer-stall-retry`, and `outstanding-dissent` decision context.
- `harness/core/.claude/skills/handoff-routing/SKILL.md` and `route-spec.md` — the relay instruction becomes append-verbatim; the mapped-section sentence for review dispatches retires.
- `harness/core/schemas/scratch/intake-decision.schema.json` — the new record; `records.py` and the routing gates learn it.
- `harness/core/.claude/skills/` — the intake skill (product-expert persona, exit protocol); `prd-authoring` gains the quoted-grounding rule; `handoff-routing` gains the consultation-ownership table.
- `evals/run_eval.py` and the task manifests — prep seeds `intake-decision` from the task prompt (`request`) and the manifest's verbatim decision clauses (`decisions`).
- `docs/agentic-harness.md`, `docs/glossary.md` — the doctrine sentence, the record row, the intake entry.
- `harness/core/scripts/tests/handoff/` — ladder suite gains `prompt_note` assertions; new intake-record suite.

## References

- [2026-08-08 Scope-Lock](2026-08-08-scope-lock-the-request-is-never-the-override.md) — the quoted-decision principle this doctrine generalizes.
- [2026-08-11 Bounded Review Convergence](2026-08-11-bounded-review-convergence.md) — the ladder whose relay becomes paste-ready; the prose-only rejection this decision reuses.
- [2026-08-07 Trend Operator Notes](2026-08-07-trend-operator-notes-and-condition-callouts.md) — the bench evidence channel that measured the root's growth.
