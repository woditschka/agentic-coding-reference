# Agent Mirror Bodies Are Rendered from the Claude Base

**Status:** Accepted (every-body-is-authored premise extended by [2026-09-01 evidence-gated-dynamic-tiering](2026-09-01-evidence-gated-dynamic-tiering.md): a `variant-of:` base's own body renders from its target)

## Context

Every agent exists four times per layer: the base in `.claude/agents/` and three mirrors (`.github/`, `.opencode/`, `.junie/`). The bodies must be byte-identical modulo one link rewrite; battery step 2b gates that. But nothing produced the mirrors — all four copies were authored by hand. Across core and three stacks that is 57 mirror files: ~1,180 base body lines hand-copied into ~3,530 mirror lines. The gate turned a missed copy into a battery failure whose fix was more hand-typing. Frontmatter is different: it encodes real per-tool decisions — Copilot's `handoffs` blocks, OpenCode's `mcp: deny`, Junie dropping the IDE oracle — and cannot be derived from the base.

## Options Considered

1. **Keep hand-authoring, keep the gate** — status quo. Rejected: every body edit costs four edits; the gate detects a miss but never removes the 4× cost.
2. **Generate whole mirror files, frontmatter included** — a per-tool transform plus per-agent sidecar data for the non-derivable parts. Rejected: the sidecar re-encodes the frontmatter in a second format; per-tool policy stays a human decision.
3. **Render bodies, hand-own frontmatter** (chosen) — `refresh-agent-bodies.sh` keeps each mirror's frontmatter and replaces everything below the fence with the base body, rewriting `../skills/` links to the mirror form. This is the authored/managed split that `refresh-chapters.sh` already applies to consumer CLAUDE.md files.

## Decision

- The `.claude/agents/` copy is the authored base for every agent body and the roster's source of truth; the three mirrors' bodies are rendered, never edited.
- `release-prep.sh` runs the render as its first step; battery step 2b now gates a forgotten render or a hand-edited mirror.
- The renderer never creates files. Adding an agent means authoring its three mirror frontmatters once — an explicitly reviewed step, because frontmatter is per-tool policy; a missing mirror fails loud.
- Removal follows the base mechanically: the render prunes any mirror whose base is gone. Wrong-suffix strays are left for step 2b's reverse sweep; mirror-dir READMEs are never touched. A layer with failures is never pruned — a rename reads as missing mirrors plus orphans, and pruning it would destroy authored frontmatter a `git mv` could keep.
- Step 2c runs the renderer's fixture self-test (drift repair, link rewrite, idempotency, fence handling, prune, empty roster).

## Consequences

- An agent-body edit is one file instead of four; the render propagates it mechanically, the way bootstrap propagates samples and package-marketplace propagates plugins.
- The mirrors stay committed and readable per tool — the delivery shape is unchanged; only their body maintenance became mechanical.
- Cross-tool frontmatter drift remains a judgment concern (`/audit-agents`), unchanged by this decision.

## References

- [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](2026-06-24-claude-md-managed-chapters.md)
- [Tiered Maintainer Workflow: One Judgment Skill, Scripted Propagation](2026-07-02-tiered-maintainer-workflow.md)
