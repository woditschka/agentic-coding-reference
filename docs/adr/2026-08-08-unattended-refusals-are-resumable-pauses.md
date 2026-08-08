# Unattended Refusals Are Resumable Pauses

**Status:** Accepted

## Context

Scope-lock ([2026-08-08](2026-08-08-scope-lock-the-request-is-never-the-override.md)) made silent narrowing unrepresentable and named the specialist's consultation the designed exit. No rule routed unattended root to that exit: both dev-sweep `visit-cancel` reps declined at intake in the final message — zero ledger entries, checkpoint `consultation recorded` unmet, $0.42 and $0.58. That exit is cheap but terminal three ways. No instruction pins the message's content, so the position — options, recommendation, consequences — is unguaranteed. Nothing is resumable: a later session finds no record to answer. Nothing is auditable: the bench archives the ledger, never the final message.

The operator's requirement is explicit: the team never just refuses cooperation. Interactively the doctrine already delivers that — a disagreement is a position, not a gate, and the human owns the stop. Unattended, the conversation surface is absent and the doctrine went silent.

## Options Considered

1. **Archive the final message.** Observability only: the refusal's tone becomes reviewable, but the exit stays terminal and its content stays unpinned.
2. **Pin the message shape in prose.** A doctrine sentence requiring the decision package in the final message. Unverifiable: no gate reads a chat message, so the promise fails exactly when unattended.
3. **Root appends the `consultation-request` itself.** As cheap as the intake decline, but the resume roundtrip requires a specialist author: `consultation-return` re-dispatches the request's author, and a `human`-authored request leaves no agent to resume. The schema's REQ id is minted by the product-requirements-expert, and the handoff-append contract sanctions root only as scribe of the response. Rejected: the extra dispatch buys the monitored, resumable surface, not only cold judgment.
4. **Route the conflict through the specialist so the ledger records the pause** (chosen). The machinery exists: the pushback exit already produces a `consultation-request` targeting `human`, and `route` already halts it as `human-consultation`. The trigger is prose here too; the difference is the artifact — compliance leaves a verifiable record, and the bench's `consultation recorded` checkpoint detects a miss.

## Decision

**A session never ends on an open scope question in prose. Root dispatches the owning specialist; the specialist's `consultation-request` records the position; the run halts as a resumable pause.**

- The trigger is decidable at the moment root stops. Interactively a question does not end the session — root asks and the conversation continues. A question that would end the session enters the ledger instead: root dispatches the owning specialist with the request as stated. When unsure whether a reply can arrive, root dispatches — a spurious pause costs one roundtrip, an unrecorded refusal loses the position.
- The specialist's side is unchanged. The pushback exit and "Consult once, with a position" already require the options, one recommendation, and the consequence of each answer in the request.
- Any later session resumes the pause: root puts the recorded question to the human and appends the `consultation-response` (author `human`). The next `route` call re-dispatches the specialist — the interactive path's elicitation-pause roundtrip, unchanged.
- The scratch-reset entry points honor the pause. The `next` and `new-feature` skills guard their `.scratch/` wipe behind a `route` check: a pending `human-consultation` surfaces to the user, never silently clears.

## Consequences

- A refusal stops being an outcome and becomes a state: "here is the position, awaiting the owner's decision," durable in the ledger and answerable by any later session.
- Refusal-kind eval reps regain the ledger record the v0.1.22 reps carried; the Tier B `consultation recorded` checkpoint returns to 4/4. The refusal bar itself is unchanged.
- Cost per refusal rep rises from the intake-decline mean $0.50 (dev-51af896 reps: $0.42, $0.58) to the through-pipeline ~$1.20 (v0.1.22 reps: $1.06–$1.35) — the price of a recorded, resumable position.
- The dev-51af896 `visit-cancel` figures predate this rule and measure the intake-decline shape; the next sweep measures the through-pipeline shape.
- The rule covers scope questions. An unattended non-scope refusal — an impossible task, a missing credential — still ends in prose; widening the pause to those exits stays open.

## Implementation

- `docs/agentic-harness.md` § Conversations Stay in Root and the installed copy — the new surface bullet (identical in both; no delta re-pin).
- `harness/claude-md/managed-chapters.md` § Pipeline Routing — the root instruction.
- `harness/core/.claude/skills/next/SKILL.md` and `harness/core/.claude/skills/new-feature/SKILL.md` — the guarded `.scratch/` reset and the no-reply dispatch branch.
- `harness/core/.claude/agents/product-requirements-expert.md` § Working from a Root Elicitation — the attended/unattended opener.
- `evals/results/notes.toml` — the `visit-cancel` condition-boundary note counts this rule among the boundary's changes.

## References

- [Scope-lock: the request is never the override](2026-08-08-scope-lock-the-request-is-never-the-override.md) — the gate this pause is the designed exit for.
- [Append-only handoff records](2026-05-08-append-only-jsonl-handoffs.md) — why the pause is durable and log-distinguishable from a truncation.
