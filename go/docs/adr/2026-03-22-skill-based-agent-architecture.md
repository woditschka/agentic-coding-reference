# Skill-Based Agent Architecture

**Status:** Accepted

## Context

The agent pipeline (product-requirements-expert, system-design-expert, feature-implementer, reviewers) embedded all workflow logic in two places: `CLAUDE.md` and `.claude/agents/README.md`. This created three problems:

1. **Not portable.** Pipeline routing, handoff conditions, and feedback tags were Claude Code-specific. OpenCode and GitHub Copilot could not reuse them.
2. **Duplicated.** Routing tables appeared in both `CLAUDE.md` and the README. Changes required updating both.
3. **Monolithic.** Agents mixed persona (who they are) with procedural knowledge (how the pipeline works). Adding a new tool meant rewriting agent definitions.

## Options Considered

1. **Keep inline** — Leave pipeline logic in `CLAUDE.md` and agents README. Accept duplication.
2. **Move to skills** — Extract portable workflow knowledge into `.claude/skills/`. Agents reference skills. All three tools discover skills from this location.
3. **Move to docs/** — Put pipeline logic in `docs/` alongside PRD and system-design. Conflates project documentation with workflow orchestration.

## Decision

We use option 2: skill-based architecture with a pipeline coordinator.

Three layers separate concerns:

| Layer | What It Contains | Where It Lives |
|-------|-----------------|----------------|
| Rules | Project context, conventions, always-on guidance | `CLAUDE.md` |
| Skills | Reusable procedural knowledge, loaded on demand | `.claude/skills/` |
| Agents | Role definitions, tool permissions, model selection | `.claude/agents/` |
| Project docs | Requirements, architecture, ADRs | `docs/` |

Skills are the only layer all three tools (Claude Code, OpenCode, GitHub Copilot) discover from the same location. Agent definitions are tool-specific and stay thin. `CLAUDE.md` points to skills instead of embedding pipeline details.

A `pipeline-coordinator` agent (Sonnet) reads `.scratch/` state and the `pipeline-handoff` skill to route requests. It never implements anything.

## Consequences

**Positive:**
- Pipeline logic lives in one place (skills), not duplicated across `CLAUDE.md` and README.
- Skills are portable across Claude Code, OpenCode, and GitHub Copilot.
- Adding a new tool requires only new agent definitions in the tool-specific directory. Skills and docs stay unchanged.
- Coordinator agent provides consistent routing without manual handoff checking.

**Negative:**
- Agents must load skills at runtime, adding one step to each invocation.
- Skill discovery depends on all three tools continuing to read `.claude/skills/`.

## Implementation

**Non-goal:** This is a workflow architecture decision, not a feature requirement.

## References

- [`.claude/agents/README.md`](../../.claude/agents/README.md) — agent roles, architecture overview
- [`.claude/skills/pipeline-handoff/SKILL.md`](../../.claude/skills/pipeline-handoff/SKILL.md) — routing table
