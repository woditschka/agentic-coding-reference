# Tiered Maintainer Workflow: One Judgment Skill, Scripted Propagation

**Status:** Accepted

## Context

The maintainer workflow ran through four audit and release skills with overlapping boundaries. `audit-harness` step 2 reduced to a dispatch to `audit-consistency`, whose step 0 dispatched back to the battery. The `release-prep` skill restated a 27-line self-documenting script. The loop's order — edit, propagate, judge, commit, release — was stated in four places with differing sequences. Every substantive change paid a full three-sample consistency audit, even when the diff touched one skill. The root skill tables in `CLAUDE.md` and the README had no mechanical gate, unlike the samples' tables (check-sync step 3c).

## Options Considered

1. **Keep four skills, add cross-references** — rejected: the restatements are the drift source; references beside them do not remove them.
2. **Tier via separate skills** (`audit-lite` / `audit-full`) — rejected: two more table rows and rosters to keep in sync for one shared three-layer process.
3. **One judgment skill with a `full` mode, scripted propagation, one canonical loop** (chosen).

## Decision

- `audit-consistency`'s six checks become `audit-harness` Layer 2; the separate skill is deleted. Battery comments now cite `/audit-harness` Layer 2 (step 3c names check 5).
- Three tiers, stated once in the root `CLAUDE.md` maintainer loop. Tier 0 — the battery after every edit (`release-prep.sh` after a `/harness` edit). Tier 1 — `/audit-harness` before committing a substantive change, judgment scoped to the diff. Tier 2 — `/audit-harness full` before a release.
- On a `full` run, agent depth uses the identity the battery proves: `/audit-agents` runs fully in one sample plus stack deltas in the other two, since core-sourced bodies are byte-identical.
- The `release-prep` skill is deleted; the maintainer loop names `harness/release-prep.sh` directly. `harness-stats-setup` stays: it is the sole entry point for a rare user-global install, and its approval gate lives in the skill, not the script.
- check-sync step 3c gains a root gate: the `CLAUDE.md` "Root-Level Skills" and README "Reference Upkeep" tables must match `.claude/skills/`, both directions.
- Root-skill `compatibility:` frontmatter narrows to `claude-code` (`research-update`, `deps-upgrade`, `history-update`), matching the "root is Claude Code only" rule.

## Consequences

- The root roster shrinks from 12 skills to 10; the audit path is one skill with two run modes.
- A tier-1 run skips consistency checks the diff does not touch and names them in the verdict — the gap is visible, never silent.
- The root skill tables can no longer drift silently; a missed row is a battery FAIL.
- ADRs referencing `audit-consistency` stay as written — intentional history.

## References

- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — root is the source; samples are materialized instances.
- [The Docs Audit Is One Command](2026-06-14-audit-docs-skill.md) — the same consolidation move, applied earlier to the sample-side docs audit.
