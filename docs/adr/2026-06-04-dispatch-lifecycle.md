# The Dispatch Lifecycle Is Observable From the Ledger Alone

**Status:** Accepted

## Context

The pipeline must recover from a dispatch that ends before its substantive record. From `.scratch/handoff.jsonl` alone, "dispatched and truncated" was once indistinguishable from "not yet dispatched", so recovery waited for a human signal out of band. That broke the goal of routing from filesystem state alone.

Each creator and verifier agent carries a `toolCallBudget` and runs a Scoping Pre-Check. The first rule keyed two different questions to that one number: whether a slice holds more than one behavior (semantic) and whether one behavior fits one dispatch (mechanical). A single coherent behavior can exceed any budget on file count alone, and re-scoping it produces fragments.

The portable continuation after a truncation is a fresh re-dispatch that re-bills the cached prefix. Claude Code's agent-teams `SendMessage` can resume a stopped sub-agent in place, but an unconstrained payload carries free-text instructions and peer-to-peer coordination the ledger never sees.

Unattended, a scope conflict ended in prose: both dev-sweep `visit-cancel` reps declined in the final message with zero ledger entries, at $0.42 and $0.58. The position was unpinned, unresumable, and unarchived. The v0.3.1 sweep then measured the prose trigger failing at the dispatch hop. In 2 of 5 refusal reps root read the briefs itself and ended the session, `route`'s `intake-ready` decision unfollowed.

## Options Considered

1. **Root-signal truncation trigger.** Rejected: non-deterministic; routing stalls without a human.
2. **Transcript or runtime telemetry.** Rejected: runtime-specific, against the tool-agnostic invariant.
3. **Budget-keyed re-scoping, or raising budgets until overruns vanish.** Rejected: the first re-splits single behaviors; the second hides the problem.
4. **Fresh re-dispatch only.** Rejected: pays full context re-derivation where the runtime could continue in place.
5. **Unrestricted `SendMessage` resume.** Rejected: smuggles instructions off-ledger.
6. **Archive the refusal message, or pin its shape in prose.** Rejected: observability without resumability; no gate reads a chat message.
7. **Root appends the `consultation-request` itself.** Rejected: `consultation-return` re-dispatches the request's author, and a `human`-authored request leaves no agent to resume.
8. **Dispatch-start sentinel, two orthogonal axes, continue-only allowlist, and the recorded pause with a Stop-hook backstop.** Chosen.

## Decision

**Every substantive agent appends a `dispatch-start` as its first tool call; a dispatch ends in a substantive record, a continuation, or a recorded pause, never in prose.**

- **Truncation is a ledger fact.** A `dispatch-start` with no later substantive record for the same `(req_id, author)` is the signal, cause-agnostic. Cap hit, mid-stream cut, abandonment, and network drop read the same. `route` executes the rule and `route-spec.md` § Truncation Recovery re-dispatches on the tree as the dispatch left it, under a three-truncation ceiling.
- **Two axes, two remedies.** Slice size is judged from the inbound records, budget-free. A slice spanning more than one behavior or bounded context stops before starting and files a `consultation-request`. `toolCallBudget` governs dispatch length only and plans the checkpoint; a cap hit is a length signal, never a scope verdict. Recovery continues the same slice; re-split is reserved for the over-size branch and for non-convergence.
- **Continuation has a portable path and a fast path.** The portable path is a fresh re-dispatch reading the ledger and the working tree. On Claude Code with agent teams enabled project-scoped in `.claude/settings.json`, a `PreToolUse` hook admits only the literal `continue` payload to `SendMessage` and denies everything else, failing closed. The resume carries no instructions; all new work enters as a fresh, schema-validated dispatch.
- **An unattended scope question becomes a pause.** A session never ends on an open scope question in prose. Root dispatches the owning specialist; its `consultation-request` targeting `human` records the options, one recommendation, and the consequence of each answer; `route` halts it as `human-consultation`. A later session puts the question to the human, appends the `consultation-response` (author `human`), and the next `route` call re-dispatches the specialist. The `next` and `new-feature` skills guard their `.scratch/` wipe behind a `route` check. A scope decline is never artifact-less work: the conflict record is the deliverable.
- **The hop gets a backstop.** An `intake-stop-guard` Stop hook blocks a model-initiated session end while `route` decides `intake-ready`, once, failing open on malfunction. The guard rule: block only where a refusal can masquerade as an outcome and the pending obligation is ledger-visible.

## Consequences

**Positive:**
- Routing needs no human in the recovery path; truncation, retry, and stall ladders run from state.
- Single behaviors stay whole; commits ship behavior, not fragments of an artificial decomposition.
- Where the runtime allows, cap-hit recovery keeps the context and the ledger trail without re-derivation.
- A refusal becomes a durable state any later session can answer; the Tier B `consultation recorded` checkpoint returned to 4/4.

**Negative:**
- Detection depends on the `dispatch-start`-first discipline; `validate` warns on a substantive record without one.
- A bare `continue` to an over-scoped agent re-runs the overrun; the consecutive-truncation count is the backstop. The hook and `settings.json` ship together, since a missing hook fails open.
- A chronically over-wide behavior surfaces as non-convergence or a budget-tuning signal at re-triage, not as a re-scope request.
- Cost per refusal rep rose from the intake-decline mean of $0.50 to the through-pipeline $1.06–$1.35. A non-scope refusal, an impossible task or a missing credential, still ends in prose.

## Implementation

`harness/core/.claude/hooks/sendmessage-continue-only.py` and `intake-stop-guard.py`, registered in `harness/init/core/.claude/settings.json`; `harness/claude-md/managed-chapters.md` § Pipeline Routing; `harness/core/.claude/skills/handoff-append/SKILL.md` § Dispatch-Start; `harness/core/.claude/skills/handoff-routing/route-spec.md` § Truncation Recovery; `harness/core/.claude/skills/tdd-workflow/SKILL.md` § Scoping Pre-Check; the `next` and `new-feature` skills; the product-requirements-expert agent.

## References

- [The Handoff Ledger](2026-05-08-the-handoff-ledger.md) — the append-only log every lifecycle fact is read from.
- [Deterministic Routing Engines](2026-07-02-deterministic-routing-engines.md) — `route` executes the detection and recovery rules stated here.
- [Slice Sizing and the Checkpoint](2026-10-20-slice-sizing-and-the-checkpoint.md) — the planned checkpoint runs the gate; a cap hit after a green one is a truncation.
- [The Product Expert and the Root Conversation](2026-06-19-the-product-expert-and-the-root-conversation.md) — scope-lock and the consultation with a position that the pause records.
- [The Eval Bench](2026-07-15-the-eval-bench.md) — the sweeps that measured the refusal exit and its cost.
- [Principles Over Rigid Rules](2026-06-03-principles-over-rigid-rules.md) — `dispatch-start`-first is a hard contract under that taxonomy.
- [`docs/agentic-harness.md`](../agentic-harness.md) — § Dispatch-Event Contract and Recovery Paths.
