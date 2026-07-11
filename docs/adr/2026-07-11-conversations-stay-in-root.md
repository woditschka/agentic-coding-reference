# Conversations Run in Root; Dispatches Produce Artifacts

**Status:** Accepted

## Context

Subagents are non-interactive in all four supported tools: one dispatch prompt in, one result out. Yet two designed interactions were conversations — the requirements interview ([2026-06-19](2026-06-19-prd-discussion-partner.md) made the PRD specialist a discussion partner) and the `foundational` triage interview. Both could only run as a relay: root ferrying messages between the human and an agent that cannot hear them. A maintainer reported the felt effect as discussing a feature "through a manager." The relay also pays double context — the conversation accumulates in root anyway, plus the specialist's re-dispatches.

## Options Considered

1. **Keep the relay.** Preserves the agent-owned interview on paper; in practice the interview never runs as written. Rejected: the felt experience contradicts the design intent, and the doctrine is unenforceable from inside a non-interactive dispatch.
2. **Run the expert as the top-level agent.** Some tools can start a session as a named agent. Rejected: tool-specific, and it abandons the pipeline's routing surface mid-conversation.
3. **Elicitation in root, authorship in dispatch.** Root conducts the conversation under the partner doctrine; the owning specialist is dispatched once with the distilled decisions to author the artifact. Chosen.

## Decision

**Conversation is root's surface; a dispatch produces an artifact.** The partner doctrine — push back asymmetrically, hold once, topic-derived angle, own the stop, surface never absorb — moves from the specialist body to `docs/agentic-harness.md` § Conversations Stay in Root, where root executes it. The specialist keeps artifact-level judgment: it judges the distillate cold and returns pushback instead of recording what it disagrees with. A pushback or `foundational`-question dispatch ends by appending a `consultation-request` targeting `human` — the elicitation pause. Route halts (`human-consultation`) while root converses; the root-appended `consultation-response` (author `human`) resumes the requester through the existing consultation return. The record is load-bearing: a bare pause would be log-indistinguishable from a genuine truncation, and the questions would die with the session. The ledger stays the complete audit trail.

**The specialist's bar is pinned unchanged.** Triage and consultation dispatches are untouched. The distillate is input to judge, not a decision to transcribe: a conflicting decision returns as pushback (or the SDE's `conflicting` verdict), never records silently. Consensus reached in conversation binds the human, never the specialist.

## Consequences

**Positive:**

- The human converses with the expert role directly; no relay.
- The human is an addressable consultation target: specialists hold one sanctioned, schema-validated mid-dispatch escalation, reinforcing the pinned critical bar.
- The `foundational` interview becomes runnable as specified: questions out, root interviews, decisions in.
- Consultation-shaped clarifications shrink: the interview front-loads what previously surfaced mid-implementation, where one consultation roundtrip costs two dispatches.

**Negative:**

- The interview runs on the session model, not the specialist's pinned tier; the pinned tier still judges at authorship. Accepted: the human drives the interview.
- The partner behaviors now bind root, where no per-agent frontmatter scopes them. Accepted: they were already human-gated per [2026-06-19](2026-06-19-prd-discussion-partner.md); the gate is unchanged.
- `author: "human"` is an unverified claim: an agent could forge the response via the sanctioned append, like any authored record. Accepted — same trust class; the human-readable audit trail is the backstop, and the forgery is a higher-value review target.

## References

- Amends [2026-06-19 PRD discussion partner](2026-06-19-prd-discussion-partner.md): the five behaviors, the human veto, and the what/how boundary hold; their execution surface moves from the specialist dispatch to root.
- The doctrine: `docs/agentic-harness.md` § Conversations Stay in Root.
- The elicitation pause: `route-spec.md` § Gate 2b (`human-consultation`), executed by `scripts/handoff.py` and pinned by its test suite.
