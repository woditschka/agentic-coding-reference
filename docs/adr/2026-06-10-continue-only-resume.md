# Continue-Only Resume: SendMessage Allowlist as the Continuation Fast Path

**Status:** Accepted

## Context

When a dispatch truncates, the default recovery is to continue the same slice ([`2026-06-10-cap-hit-recovery-is-continuation.md`](2026-06-10-cap-hit-recovery-is-continuation.md)). The portable continuation is a fresh re-dispatch reading the partial-artifact record and the working tree. It is correct but re-bills the cached prefix and re-derives context the stopped agent already held. Claude Code's experimental agent-teams capability (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) adds `SendMessage`, which can resume a stopped sub-agent in place with its context intact. Unconstrained, the same tool also carries free-text payloads: a parent could hand a resumed agent new, unrouted instructions, or coordinate agents peer-to-peer. Both bypass the schema-validated `.scratch/handoff.jsonl` ledger that makes the pipeline auditable.

## Options Considered

1. **No resume; fresh re-dispatch only** — portable and safe, but every truncation pays full context re-derivation even when the runtime could continue in place.
2. **Unrestricted SendMessage resume** — cheapest recovery, but free-text payloads smuggle instructions off-ledger and invite peer-to-peer coordination the ledger never sees.
3. **Continue-only allowlist (chosen)** — a `PreToolUse` hook admits the literal `continue` payload and denies everything else, failing closed. A bare `continue` carries no instructions, so the channel cannot smuggle; resume stays available for genuinely interrupted dispatches.

## Decision

We adopt option 3. Both samples enable the agent-teams flag project-scoped (the repo's `.claude/settings.json` `env` block, never `~/.claude/settings.json`) and register `.claude/hooks/sendmessage-continue-only.sh` beside it. The bare `continue` resume is the fast path for the continuation default; the fresh re-dispatch from the ledger remains the portable path when no resume exists. `SendMessage` serves resume only — never peer-to-peer coordination that bypasses the handoff log. All new work enters as a fresh, schema-validated dispatch on `.scratch/handoff.jsonl`.

## Consequences

**Positive:**
- Cap-hit recovery becomes cheap where the runtime allows: same slice, same ledger trail, no context re-derivation.
- Payload smuggling is structurally impossible; the resume channel carries no instructions.
- The ledger remains the single inspectable source of truth; off-ledger coordination stays blocked.

**Negative:**
- A bare `continue` to a silently over-scoped agent re-runs the over-scope and re-truncates without a new record; non-convergence bounding (consecutive-truncation count) is the backstop.
- The hook and `settings.json` must ship together — a missing hook file fails the guard open.

## Implementation

**Non-goal:** This is a harness coordination decision, not a feature requirement. The hook and flag live in each sample's `.claude/` directory. The recovery ordering lives in each sample's `CLAUDE.md` (§ Tool-call budget, § Agent teams and the continue hook) and the `pipeline-handoff` skill (§ Truncation Recovery). The root project carries none of this machinery — it maintains the reference and runs no pipeline dispatches.

## References

- [`agentic-harness.md`](../agentic-harness.md) — § Dispatch-Event Contract and Recovery Paths
- [`2026-06-10-cap-hit-recovery-is-continuation.md`](2026-06-10-cap-hit-recovery-is-continuation.md) — the continuation default this fast-path serves
- [`2026-05-08-append-only-jsonl-handoffs.md`](2026-05-08-append-only-jsonl-handoffs.md) — the ledger the allowlist protects
