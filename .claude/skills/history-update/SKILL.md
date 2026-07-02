---
name: history-update
description: >-
  Update the Project History section in the root README with executive-level
  milestones since the last entry. Walks committed git history and uncommitted
  working-tree changes, filters out non-milestone work (deps bumps, prose
  tightening, mechanical refactors), proposes entries in imperative mood
  (one concise clause, ~8-20 words) for approval. Keeps a linear timeline: one
  dated milestone per line, oldest to newest, with no entry cap and no era
  rollups — every era stays as granular as its real activity, and each date is
  a real git commit or ADR date, never invented or given as a month range. Use
  when significant root-level work has landed, before committing a milestone
  change, or as part of root maintenance alongside audit-harness,
  research-update, and deps-upgrade.
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

## When to Run

- After completing significant root-level work (new conceptual model, structural shift, new cross-cutting capability).
- Before committing a milestone change — the proposed entry doubles as a candidate commit subject.
- Alongside the other root maintenance skills — `audit-harness`, `research-update`, and `deps-upgrade`.
- Periodically, to catch drift between the README's Project History and what has actually shipped.

## Inputs

Read four sources, in order:

| Source | Purpose |
|--------|---------|
| `README.md` "Project History" section | Cutoff date (latest entry) and existing entry style |
| `git log --format="%ad %h %s" --date=short --since="<cutoff>"` | Committed milestones since the cutoff, and the real date for each entry |
| `docs/adr/` filenames (`YYYY-MM-DD-*.md`) | The authoritative date for a decision milestone; pair the history line with its ADR's date |
| `git status --short` + `git diff --stat` + `git diff --staged --stat` | Work in flight — may be the milestone being prepared right now |

Uncommitted changes matter. Someone running this skill mid-work is likely staging or about to commit the exact change they want recorded. When working-tree changes touch milestone-level paths — new files under `docs/`, edits to root `CLAUDE.md`, a new root skill directory — include them as candidate milestones and flag them as work-in-flight.

Every date comes from one of these sources. A decision dates to its ADR; a shipped capability dates to its commit. Never invent a date and never collapse several milestones under a month range — if a span had three milestones, it gets three dated lines.

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
- Per-feature work inside `samples/go/` or `samples/java-spring-boot/` samples — those have their own lifecycle.

When in doubt, exclude. Six strong entries read better than ten with filler.

## Style Rules

Match existing entries exactly:

| Rule | Example |
|------|---------|
| Date format | `**2026-05-22**` (bold, full ISO-8601 date — never a month or range) |
| Voice | Imperative mood (`Launch`, `Switch`, `Reframe`) |
| Length | One concise clause, ~8-20 words after the date |
| Punctuation | End with a period |
| One per line | One milestone per line. Distinct milestones on the same day each get their own line; fold onto one line with semicolons only when they are facets of a single shift |
| Release tags | Fold a version tag into its feature line — `… (v0.1.2)` — rather than a separate entry |

## Process

### 1. Read Current State

Read the "Project History" section in the root `README.md`. Capture:

- The latest entry's date — this is the cutoff.
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

- **Keep** — qualifies; draft a dated entry, the date taken from its commit or ADR.
- **Drop** — does not qualify (deps bump, prose, mechanical refactor).
- **Fold onto one line** — only when two changes are facets of a single shift on the same day; distinct same-day milestones stay separate lines.

### 5. Draft Candidate Entries

For each kept item, draft a bullet matching the style rules. Lead with the imperative verb. Trim to one concise clause (~8-20 words). Prefer fewer, stronger entries over more, weaker ones — but never compress a real milestone away to save a line; there is no line budget.

### 6. Present for Approval

Show the proposed entries as a diff against the current section. Include:

- Each new entry on its own line, in chronological order (newest at the bottom).
- Reasoning for any non-obvious inclusion or exclusion.
- For uncommitted changes: a flag that the entry covers work-in-flight, and a suggestion to reuse the entry text as the commit subject.

Do NOT edit the README without explicit approval.

### 7. Apply

On approval, insert each new entry in chronological order (newest at the bottom). Existing entries are never compressed, re-dated, or folded — the timeline only grows. Touch an existing line only to correct a wrong date or a factual error.

## What This Skill Does NOT Do

- **Track sample-internal features.** Per-feature work inside `samples/go/` and `samples/java-spring-boot/` belongs to those samples' own lifecycle. Only root-level shifts qualify.
- **Auto-apply entries.** Executive-level is a taste judgment; the skill proposes, the user decides.
- **Replace the commit log.** This is a curated highlight reel for returning readers, not a changelog.

## Linear Timeline

The section is a flat, linear timeline: one dated milestone per line, oldest at the top, newest at the bottom. There is no line budget, no recency weighting, and no era rollups. Every entry is a single line — no sub-bullets, no paragraphs; if a headline cannot carry the milestone, the milestone needs a sharper headline, not more words.

Density follows reality, not a target. A month that shipped six milestones gets six lines; a quiet month gets none. June reading denser than April is honest — it reflects what actually happened — and is not a problem to smooth out. The executive-level filter is the only thing that limits length: it controls *which* shifts qualify, never *how many* lines an era may keep.

Two failure modes this replaces, both retired:

- **Range rollups** (`**2026-04 → 2026-05** — …`) that cram several milestones into one undated bullet. Un-bundle them: each milestone gets its own line at its real date.
- **Recency-weighted aging** that compressed older entries to stay under a budget. The past stays as granular as the present; existing lines are never folded or re-dated.

The filter and the wording are taste judgments the user owns — propose, never auto-apply.
