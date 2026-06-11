---
name: history-update
description: >-
  Update the Project History section in the root README with executive-level
  milestones since the last entry. Walks committed git history and uncommitted
  working-tree changes, filters out non-milestone work (deps bumps, prose
  tightening, mechanical refactors), proposes entries in imperative mood
  (5-15 words) for approval. Maintains a recency-weighted structure: recent
  entries stay granular one-liners, the oldest compress into era rollups,
  landmarks survive compression on their own line. Use when significant
  root-level work has landed, before committing a milestone change, or as
  part of root maintenance alongside audit-consistency, research-update,
  and deps-upgrade.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## When to Run

- After completing significant root-level work (new conceptual model, structural shift, new cross-cutting capability).
- Before committing a milestone change — the proposed entry doubles as a candidate commit subject.
- As the fourth member of the root maintenance cluster, alongside `audit-consistency`, `research-update`, and `deps-upgrade`.
- Periodically, to catch drift between the README's Project History and what has actually shipped.

## Inputs

Read three sources, in order:

| Source | Purpose |
|--------|---------|
| `README.md` "Project History" section | Cutoff date (latest entry), existing style, current entry count |
| `git log --format="%ad %h %s" --date=short --since="<cutoff>"` | Committed milestones since the cutoff |
| `git status --short` + `git diff --stat` + `git diff --staged --stat` | Work in flight — may be the milestone being prepared right now |

Uncommitted changes matter. Someone running this skill mid-work is likely staging or about to commit the exact change they want recorded. When working-tree changes touch milestone-level paths — new files under `docs/`, edits to root `CLAUDE.md`, a new root skill directory — include them as candidate milestones and flag them as work-in-flight.

## Executive-Level Filter

Not every commit qualifies. An entry should mark a shift a returning reader would actually notice.

### Qualifies

- New conceptual model or framing of the project.
- New cross-cutting capability (new agent role, new pipeline stage, new coordination scheme).
- New supported tool or platform.
- Structural redesign of the harness, handoff scheme, or memory substrate.
- New top-level skill or tooling that changes how users interact with the project.

### Does NOT qualify

- Dependency or tool version bumps.
- Prose tightening, formatting, or documentation rewrites that do not change meaning.
- Bug fixes, even visible ones.
- Mechanical refactors that do not change behavior or interface.
- Internal cleanups, lint-driven changes, hook tweaks.
- Per-feature work inside `go/` or `java-spring-boot/` samples — those have their own lifecycle.

When in doubt, exclude. Six strong entries read better than ten with filler.

## Style Rules

Match existing entries exactly:

| Rule | Example |
|------|---------|
| Date format | `**2026-05-22**` (bold, ISO-8601) |
| Voice | Imperative mood (`Launch`, `Switch`, `Reframe`) |
| Length | 5-15 words after the date |
| Punctuation | End with a period |
| Grouping | Same-day related shifts → one bullet with semicolons, not separate entries |
| Rollup dates | Range format `**2026-04 → 2026-05**` (month or full-date precision as useful) |

## Process

### 1. Read Current State

Read the "Project History" section in the root `README.md`. Capture:

- The latest entry's date — this is the cutoff.
- Total top-level entry count, measured against the 15-line budget.
- Which entries sit in each tier (one-liner / rollup or landmark).
- The exact entry style (verb, punctuation, formatting) for consistency.

### 2. Walk Committed History

```
git log --format="%ad %h %s" --date=short --since="<cutoff-date>"
```

Cutoff is the date of the latest existing entry.

### 3. Inspect Working Tree

```
git status --short
git diff --stat
git diff --staged --stat
```

Identify substantial changes — new top-level files, root doc edits, new skill directories, new agent definitions at root. Treat these as candidate milestones.

### 4. Apply the Executive-Level Filter

For each commit and uncommitted change, decide:

- **Keep** — qualifies; draft an entry.
- **Drop** — does not qualify (deps bump, prose, mechanical refactor).
- **Group with another** — same-day, same conceptual reframing.

### 5. Draft Candidate Entries

For each kept item, draft a bullet matching the style rules. Lead with the imperative verb. Trim to the 5-15 word range. Prefer fewer, stronger entries over more, weaker ones.

### 6. Present for Approval

Show the proposed entries as a diff against the current section. Include:

- Each new entry on its own line, in chronological order (newest at the bottom).
- Reasoning for any non-obvious inclusion or exclusion.
- The aging consequences: if the 15-line budget overflows, which one-liners fold into which era rollup.
- For uncommitted changes: a flag that the entry covers work-in-flight, and a suggestion to reuse the entry text as the commit subject.

Do NOT edit the README without explicit approval.

### 7. Apply and Age

On approval:

- Insert new entries in chronological order (newest at the bottom).
- If the 15-line budget is exceeded, apply the agreed compression: fold the oldest non-landmark one-liners into the adjacent era rollup; landmarks keep their line.

## What This Skill Does NOT Do

- **Track sample-internal features.** Per-feature work inside `go/` and `java-spring-boot/` belongs to those samples' own lifecycle. Only root-level shifts qualify.
- **Auto-apply entries.** Executive-level is a taste judgment; the skill proposes, the user decides.
- **Replace the commit log.** This is a curated highlight reel for returning readers, not a changelog.

## Tier Structure and Aging

The section is recency-weighted: granularity concentrates at the new end, compression at the old end. Budget: 15 lines. Every entry is a one-liner — no sub-bullets; if a headline cannot carry the milestone, the milestone needs a sharper headline.

| Tier | Who | Format |
|------|-----|--------|
| Standard | Everything younger than the rollups | One-liner, 5-15 words |
| Compressed | The oldest entries | Era rollups with range dates; landmarks as standalone lines |

**Landmark rule.** An entry survives compression on its own line when it marks a shift a returning reader still feels in the current harness: the launch, a format or architecture switch, a framing adoption, tool-set growth. Related landmarks may combine into one line when they tell a single arc (date the line with the range). Everything else folds into an era rollup.

**Aging on each run.** A new entry enters as a one-liner. When the 15-line budget overflows, the oldest non-landmark one-liners fold into the adjacent era rollup. A rollup summarizes its members; nothing is silently dropped from the timeline.

Confirm every compression before applying — which lines fold, which survive as landmarks, and the rollup wording are taste judgments the user owns.
