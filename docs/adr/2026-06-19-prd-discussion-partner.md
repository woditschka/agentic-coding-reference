# The PRD Specialist Is a Discussion Partner, Gated by the Human, Not a Script

**Status:** Accepted

## Context

The product-requirements-expert drives the middle loop: it reads the PRD and prior ADRs, interviews the human, and records a `prd-entry` slice. Its prose optimized for extraction — "Be direct. State facts." — and its skills enforce a write-time what/how boundary. In practice the agent behaved as a scribe: it organized what the human already knew and conceded at the first restatement. The interview is the stage where the most expensive errors are cheapest to catch: the wrong problem, an unstated non-goal, a scope contradiction. A scribe catches none of them. Success at this stage is a PRD that captures the right *what* clearly; a tidy document of the wrong *what* is the failure the change targets.

## Options Considered

1. **Leave it a scribe.** Lowest surface, but forfeits the stage where wrong-*what* is cheapest to fix.
2. **Add a persona roster.** Give the agent named reviewer hats — security, privacy, cost. Rejected: announced personas ossify into a checklist, and the harness already prefers traits over rigid rules.
3. **Discussion-partner disposition, human-gated.** A thin behavioral layer on the agent — asymmetric pushback, hold-once, feature-derived angle, owned stop, surface-never-block — with the conversational what/how permission moved into the `prd-authoring` skill.

## Decision

**The product-requirements-expert is a discussion partner. The human drives and holds the only veto; the agent never blocks the handoff. The interview disposition lives on the agent; the what/how boundary lives in the `prd-authoring` skill.**

- **Disposition on the agent, mechanics in the skill.** Five judgment instructions stay in the agent body as its job description. They are: push back asymmetrically, hold once for a reason, take the angle the feature demands, own the stop, surface never absorb. The conversational what/how permission and the no-parking rule move into `prd-authoring` § PRD Boundary Rule, the skill the doc-reviewer already enforces. The thin-agent / rich-skill split holds: no new skill, no schema change.
- **No parking; the human is the carrier.** The record carries only requirements and non-goals — no *how*, not even as a note. Implementation ideas raised in conversation are not recorded. The human is in the loop at the design stage and can raise one there. A question the current slice does not need resurfaces later as a `consultation-request`. Recording a *how* would pre-empt the design stage and leak mechanism into the requirement.
- **Surface, never block.** The agent names every contradiction and problem explicitly and holds its position once against mere restatement. It never holds the handoff hostage. The human's decision resolves into a requirement, a non-goal, or a deliberate omission the human owns.

## The Gate Is the Human, Not a Script — and That Is Deliberate

Every other behavior in the harness has a deterministic gate: the boundary rule has prohibited-patterns and the doc-reviewer, slice-sizing has the `next` skill, the schema has the coordinator's structural rejection. These five behaviors have none. They are judgment instructions with no automated check, and they leave no trace in the artifact — by design, since the no-parking decision removed the only candidate trace. The enforcing gate is the human in the loop at this stage. This applies [principles over rigid rules](2026-06-03-principles-over-rigid-rules.md): the behaviors are written as judgment instructions, not contracts, and are verified by the human who is present, not by a script. The reference accepts that the interview stage is human-gated where execution stages are machine-gated.

## Consequences

**Positive:**
- The stage where wrong-*what* is cheapest to fix now has an agent that argues, not just records.
- The what/how boundary is purer: the record holds zero mechanism; the human carries the rest forward.
- The thin-agent / rich-skill split is preserved — no new skill, no schema change, one boundary paragraph added to an existing skill.

**Negative:**
- The five behaviors are unenforced and unobservable in the artifact. A model that ignores them fails silently, caught only by the human. Accepted: the human gates this stage, and `audit-agents` checks the prose stays judgment-instruction-shaped rather than vague mood.
- One agent now reads richer than the execution agents. Accepted: elicitation differs from execution; `audit-consistency` confirms the thin-agent discipline still holds across every agent.

## References

- The disposition: `harness/core/*/agents/product-requirements-expert*.md` § Working as a Partner.
- The boundary mechanics: `harness/core/.claude/skills/prd-authoring/SKILL.md` § PRD Boundary Rule.
- The consultation backstop: `pipeline-handoff` skill (a `Requirement gap` returns as a `consultation-request`).
- Applies [principles over rigid rules](2026-06-03-principles-over-rigid-rules.md) to the requirements interview.
