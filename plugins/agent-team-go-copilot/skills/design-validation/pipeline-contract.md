# Design Validation: Pipeline Position and Input Contract

This file is the stack-agnostic head of the design-validation skill, shipped once from the harness core beside each stack's `SKILL.md`. The stack `SKILL.md` instructs this read before any triage or consultation.

## Pipeline Position

This skill operates inside the **middle loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). See [`agentic-harness.md`](../handoff-routing/agentic-harness.md) for the loop model.

The system-design-expert operates in two demand-driven modes plus the fix dispatch, all covered by this skill:

- **Triage** — runs on every `prd-entry`. Read durable memory, decide one of six verdicts (`covered`, `minor`, `new`, `foundational`, `conflicting`, `refactor-first`), append a `design-block` record.
- **Consultation** — runs on demand when the implementer appends a `consultation-request`. Read the question and durable memory, answer focused, optionally record memory, append a `consultation-response` record. The router routes control back to the requester after the response.
- **Fix dispatch** — runs when a review round routes design-doc findings back. Resolve them and append a fresh `design-block` (§ Input Contract holds the supersession rule).

Most thoughts stay in the head — the cross-feature mental model. The durable memory captures only the load-bearing parts.

## Input Contract

You are dispatched in one of four situations, distinguished by which record is the latest entry in `.scratch/handoff.jsonl`:

- **Triage dispatch.** Latest record is a `type: "prd-entry"`. Schema: [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json). This is the active slice scope.
- **Consultation dispatch.** Latest record is a `type: "consultation-request"` targeting `system-design-expert`. Schema: [`schemas/scratch/consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json). The active scope is the focused question; the originating slice is the most recent `prd-entry` whose `req_id` matches.
- **Fix dispatch.** Latest record is a `type: "review-feedback"` whose `blocked`/`clarify` findings target the design docs. The scope is those findings; resolve them in `docs/system-design.md` or `docs/adr/`, then append the `design-block` for the round. Set `supersedes_record_at` only when the resolution is a true re-triage of the slice — it resets the review cycle (voids the round's approvals and dissent), so a prose fix never carries it.
- **Foundational resume.** Latest record is a `type: "consultation-response"` (author `human`) answering a `foundational` interview. Continue the triage from the recorded answer, anchored to that line. A response that only restates the request text decides nothing — re-raise the questions as a fresh `consultation-request` instead of proceeding.

**Read discipline:**

1. Read `.scratch/handoff.jsonl`. Identify which dispatch type you're in.
2. The routing gate validates the inbound record against the schema before dispatching you; you may assume the required fields are present and well-typed. If a sanity check fails (e.g. `req_id` does not match the PRD), append a `design-block` record with `verdict: "conflicting"` (for triage) or a `consultation-response` flagging the inconsistency (for consultation) rather than papering over malformed input.
3. For triage: use `acceptance_criteria`, `file_targets`, and `test_names` from the prd-entry verbatim. Do not re-derive them; the JSONL handoff exists to break that rework loop.
4. For consultation: read the `question`, `context`, and `stop_state` fields. Answer narrow. Broad open-ended questions belong in a triage, not a consultation.

**Forbidden:** re-reading `docs/prd.md` to reconstruct scope when the prd-entry record is present. The record is the contract.
