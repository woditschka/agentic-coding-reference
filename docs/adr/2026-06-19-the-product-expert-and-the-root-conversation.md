# The Product Expert and the Root Conversation

**Status:** Accepted

## Context

The product-requirements-expert drives the middle loop: it reads the PRD and prior ADRs, takes the owner's request, and records a `prd-entry` slice. Its first prose optimized for extraction ("Be direct. State facts."), and in practice the agent behaved as a scribe: it organized what the human already knew and conceded at the first restatement. The interview is the stage where the most expensive errors are cheapest to catch: the wrong problem, an unstated non-goal, a scope contradiction. A tidy document of the wrong *what* is the failure this decision targets.

Subagents are non-interactive in every supported tool: one dispatch prompt in, one result out. Two designed interactions were conversations, the requirements interview and the `foundational` triage interview. Both could only run as a relay, root ferrying messages between the human and an agent that cannot hear them. A maintainer reported the felt effect as discussing a feature "through a manager." The relay also paid double context: the conversation accumulated in root, plus the specialist's re-dispatches.

The v0.3.0 sweep (3 reps per arm against v0.2.4) measured the root session as the pipeline's growth point. On visit-edit, median delivery wall rose from 37 to 53 minutes while reviewer spans stayed level; the root's deduplicated output rose from 15–18k to 25–33k tokens. The root composed each reviewer relay from `route-spec.md` prose on every pass. Intake carried the same authorship problem: the owner's request reached the specialist as the root's paraphrase, and every implementing visit-cancel rep on record traced to paraphrase-as-authority.

Every execution stage has a deterministic gate: prohibited patterns and the doc-reviewer for the boundary rule, the `next` skill for slice sizing, the coordinator's structural rejection for the schema. The interview has none, because the no-parking rule removes the only candidate trace in the artifact.

## Options Considered

1. **Leave the specialist a scribe** — rejected: it forfeits the stage where wrong-*what* is cheapest to fix.
2. **Add a persona roster** (security, privacy, cost hats) — rejected: announced personas ossify into a checklist, and the harness prefers traits over rigid rules.
3. **Keep the relay** — rejected: the interview never runs as written, and the partner doctrine is unenforceable from inside a non-interactive dispatch.
4. **Run the expert as the top-level session agent** — rejected: tool-specific, and it abandons the pipeline's routing surface mid-conversation.
5. **Prose-only guidance to relay faithfully** — rejected: a rule without a deterministic carrier drifts.
6. **Interactive intake in a fresh session, cleared before the pipeline** — rejected: subagent isolation already separates the discussion from the specialist, and a fresh session discards the warm root cache.
7. **Root wears the expert contract and authors the `prd-entry`** — rejected: the coordinating context becomes the product authority.
8. **Intake outcome as a scratch file or dispatch-prompt quotes only** — rejected: neither survives a resumed run or passes a gate; only a ledger record is replayable and seedable.
9. **Reviewer continuation across rounds to reuse specialist caches** — deferred: no continuation primitive exists in two of the three supported tools, and a continued reviewer anchors on its prior verdict. It is revisited when a sweep shows fix rounds dominating cost, scoped as a single-tool optimization, never on a `prior-critical` round.
10. **Discussion-partner doctrine executed by root as a channel, the specialist dispatched once on a quoted record** (chosen).

## Decision

**The requirements conversation runs in root under the partner doctrine, and the product-requirements-expert is dispatched once to judge the distilled decisions.** The human holds the only veto.

- **Conversation is root's surface; a dispatch produces an artifact.** The doctrine lives in `docs/agentic-harness.md` § Conversations Stay in Root, and the `intake` skill runs it. Its five behaviors: push back asymmetrically, hold once for a reason, take the angle the feature demands, own the stop, surface never absorb. The discussion ends in an `intake-decision` record quoting the owner's request and decisions verbatim. The specialist's dispatch names that record and treats its quotes as the only owner statements that exist.
- **The specialist judges the distillate cold.** The distillate is input to judge, not a decision to transcribe. A conflicting decision returns as pushback, or as the system-design-expert's `conflicting` verdict, never a silent record. Consensus reached in conversation binds the human, never the specialist. The specialist never converses with the human mid-dispatch.
- **The elicitation pause is a record.** A pushback or `foundational`-question dispatch ends by appending a `consultation-request` targeting `human`. The route halts as `human-consultation` while root converses; a root-appended `consultation-response` with `author: "human"` resumes the requester through the ordinary consultation return. A bare pause would be log-indistinguishable from a truncation, and the questions would die with the session. The pause is sticky until the earliest unanswered human-targeted request has its response.
- **No parking; the human is the carrier.** The record holds requirements and non-goals and zero mechanism. Implementation ideas raised in conversation are not recorded; the human raises one at the design stage. A question the current slice does not need resurfaces later as a `consultation-request`. The what/how boundary and the no-parking rule live in the `prd-authoring` skill § PRD Boundary Rule, which the doc-reviewer enforces.
- **The root is a channel, not an author.** It coordinates, relays, and quotes; it never authors a product, design, or review-contract statement. Four carriers hold that. Reviewer dispatches (`reviews-needed`, `reviewer-stall-retry`, `outstanding-dissent`) carry a `prompt_note` the route engine composes, which root appends verbatim. Only quoted `decisions` text authorizes a scope override at Gate 1; the request stays context. The legacy `dispatch` override source bounces once an intake record exists. A fresh human question belongs to the expert owning its document surface. Scope and behavior go to the product contract, structure and trade-offs to the design contract, ambiguity to the product contract first. Interactive discussion and headless seeding are two front doors to one `intake-decision` record; the eval bench seeds it from the task prompt and the manifest's decision clauses.
- **The gate is the human, not a script.** The partner behaviors are judgment instructions with no automated check and no trace in the artifact. The human present at this stage verifies them. The reference accepts that the interview stage is human-gated where execution stages are machine-gated.

## Consequences

Positive:

- The human converses with the expert role directly; no relay, and no double context spend.
- The stage where wrong-*what* is cheapest to fix has a partner that argues instead of a scribe that records.
- The human is an addressable consultation target: specialists hold one sanctioned, schema-validated mid-dispatch escalation.
- The `foundational` interview is runnable as specified: questions out, root interviews, decisions in.
- Consultation-shaped clarifications shrink: the interview front-loads what previously surfaced mid-implementation, where one roundtrip costs two dispatches.
- The record holds zero mechanism; the thin-agent / rich-skill split holds.
- Retiring the root's relay composition recovers an expected 3–5 minutes of root decode and thinking on review-heavy runs. Every `prd-entry` grounds in a quotable record in interactive and headless runs alike.

Negative:

- The interview runs on the session model, not the specialist's pinned tier; the pinned tier still judges at authorship.
- The partner behaviors bind root, where no per-agent frontmatter scopes them; the human gate covers that.
- A model that ignores the behaviors fails silently, caught only by the human; `audit-agents` checks the prose stays judgment-instruction-shaped.
- Each specialist re-dispatch rebuilds 130–300k tokens of prefix, since specialist cache writes land in the 5-minute bucket; the rebuild stays an accepted price of isolation.
- The design-discussion exit stays prompt-carried; the recorded-intake contract covers requirements intake, and extending it is an open edge.
- `author: "human"` is an unverified claim: an agent could forge the response through the sanctioned append, like any authored record. The human-readable audit trail is the backstop.

## Implementation

- The doctrine: `docs/agentic-harness.md` § Conversations Stay in Root; each sample carries the agent-facing copy under `handoff-routing/agentic-harness.md`.
- The front door: `harness/core/.claude/skills/intake/SKILL.md`, which runs the discussion and appends the `intake-decision` record.
- The specialist's contract: `harness/core/.claude/agents/product-requirements-expert.md`.
- The boundary mechanics: `harness/core/.claude/skills/prd-authoring/SKILL.md` § PRD Boundary Rule.
- The pause: `handoff-routing/route-spec.md` gate `human-consultation`, executed by `scripts/handoff.py` and pinned by its suite.
- The record: `harness/core/schemas/scratch/intake-decision.schema.json`; the paste-ready relay: `prompt_note` in `harness/core/scripts/handoff/routing.py`; the headless seed: `evals/run_eval.py` prep.

## References

- [Principles over Rigid Rules](2026-06-03-principles-over-rigid-rules.md) — the partner behaviors are judgment instructions verified by the present human, not contracts verified by a script.
- [The Handoff Ledger](2026-05-08-the-handoff-ledger.md) — the `intake-decision`, `consultation-request`, and `consultation-response` records that carry the conversation into the log.
- [Deterministic Routing Engines](2026-07-02-deterministic-routing-engines.md) — the `human-consultation` halt and the consultation return the router executes.
- [Design Truth Mid-Slice](2026-07-18-design-truth-mid-slice.md) — the `foundational` triage verdict whose interview rides the same root conversation.
- [Review Convergence](2026-07-14-review-convergence.md) — the round ladder whose reviewer relay root now pastes verbatim from `prompt_note`.
- [The Eval Bench](2026-07-15-the-eval-bench.md) — the v0.3.0 sweep that measured the root's growth and the seeded intake path it gained.
- [Model Tiering](2026-06-11-model-tiering.md) — the specialist's pinned tier judges at authorship while the session model runs the interview.
- [`docs/agentic-harness.md`](../agentic-harness.md) — the handbook section that holds the doctrine.
