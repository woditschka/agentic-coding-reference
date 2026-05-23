---
name: history-update
description: >-
  Update the Project History section in the root README with executive-level
  milestones since the last entry. Walks committed git history and uncommitted
  working-tree changes, filters out non-milestone work (deps bumps, prose
  tightening, mechanical refactors), proposes entries in imperative mood
  (5-15 words) for approval, enforces a 15-entry cap. Use when significant
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

Uncommitted changes matter. Someone running this skill mid-work is often staging or about to commit the very change they want recorded. When working-tree changes look substantial — new files under `docs/`, edits to root `CLAUDE.md`, new root skill directory — include them as candidate milestones and flag them as work-in-flight.

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

## Process

### 1. Read Current State

Read the "Project History" section in the root `README.md`. Capture:

- The latest entry's date — this is the cutoff.
- Total entry count, measured against the 15 cap.
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
- A note if the 15-entry cap will be hit or exceeded, and the proposed roll-up.
- For uncommitted changes: a flag that the entry covers work-in-flight, and a suggestion to reuse the entry text as the commit subject.

Do NOT edit the README without explicit approval.

### 7. Apply and Cap

On approval:

- Insert new entries in chronological order (newest at the bottom).
- If the 15-entry cap is exceeded, apply the agreed roll-up: merge the oldest related cluster into one summarizing bullet dated with the earliest of the group, and drop the originals.

## What This Skill Does NOT Do

- **Track sample-internal features.** Per-feature work inside `go/` and `java-spring-boot/` belongs to those samples' own lifecycle. Only root-level shifts qualify.
- **Auto-apply entries.** Executive-level is a taste judgment; the skill proposes, the user decides.
- **Replace the commit log.** This is a curated highlight reel for returning readers, not a changelog.

## Cap and Pruning

The Project History section is capped at 15 entries. When a new entry would push the count over:

- Identify the oldest 2-3 entries that cover related ground.
- Propose a roll-up: one bullet summarizing the cluster, dated with the earliest of the group.
- Drop the originals.
- Confirm before applying.
