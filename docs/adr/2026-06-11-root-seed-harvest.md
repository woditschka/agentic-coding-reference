# Seed and Harvest Move to the Root with Stack Auto-Detection

**Status:** Accepted (seed folded into /materialize by [2026-06-13](2026-06-13-materialize-complete-replacement.md); see note)

> **Amended.** The `seed` skill below is folded into `/materialize`; the root roster today is `init`/`materialize`/`harvest`. The root-owns-maintenance move and stack auto-detection still stand.

## Context

Each sample carried its own `seed` and `harvest` skills, marked "template management only" and never copied to targets. The two seed copies were ~90% identical prose; every harness evolution had to land twice. Shared bugs proved the duplication cost: neither copy listed `scripts/` in its copy structure, so the change-grader extractor and the handoff access tool never seeded. Invocation was also error-prone: `/seed` resolved to whichever sample's skill the session found first. A run against a Go target picked up the Java skill until the user caught it.

## Options Considered

1. **Keep per-sample skills, fix in both** — preserves sample self-containment for a tool nobody downstream uses; keeps the double-maintenance and wrong-template hazards. Rejected.
2. **Thin root dispatcher delegating to sample skills** — fixes invocation, keeps the duplication. Rejected.
3. **Single root skill per direction with stack auto-detection (chosen)** — `go.mod` → Go template; `pom.xml`/`build.gradle` → Spring Boot template; ask only on init (empty target) or ambiguity. Language-specific content stays in marked **[Go]**/**[Java]** sections of one file.

## Decision

`seed` and `harvest` live in the root `.claude/skills/` only; the four sample copies are deleted. The skills are maintainer tooling, matching the root's charter (maintain the reference) rather than the samples' (demonstrate the harness). Root is Claude Code-only, so the cross-tool compatibility frontmatter drops. The unified seed adds `scripts/` to the copy structure and diff categories, closing the gap that left downstream projects without the harness scripts. The unified harvest adds cross-sample routing: language-agnostic improvements apply to both samples; language-specific ones stay in the matching sample.

## Consequences

**Positive:**

- One file per direction to maintain; a fix lands once.
- Wrong-template seeding is structurally impossible for existing targets.
- The "all skills except seed and harvest" exclusion rule disappears from the copy structure — samples no longer contain them.
- Harvest reaches both samples in one pass instead of harvest-then-audit-consistency.

**Negative:**

- One skill file now holds both languages' specifics; **[Go]**/**[Java]** markers must be respected when editing, or one stack's instructions leak into the other.
- Downstream users browsing a sample no longer see seed/harvest in its skills table; the sample READMEs point to the root README instead.

## Implementation

Root `.claude/skills/seed/SKILL.md` and `.claude/skills/harvest/SKILL.md`, version 2.0, `compatibility: claude-code`. The four sample copies are removed; sample CLAUDE.md, README, and agents-README tables updated. `audit-consistency` Section 13 audits the root skill against both sample filesystems.

## References

- [`2026-06-07-adr-placement.md`](2026-06-07-adr-placement.md) — the root-owns-maintenance precedent this follows
- [`2026-06-11-handoff-log-access-tool.md`](2026-06-11-handoff-log-access-tool.md) — the `scripts/` category the unified seed now distributes
