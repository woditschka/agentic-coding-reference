---
name: harvest
description: >-
  Pull generic improvements from a downstream project back into the sample
  templates. Detects the source project's stack (Go or Java Spring Boot),
  diffs its .claude/ and docs/ against the matching sample, classifies each
  change as harvest, skip, or ask, generalizes domain patterns on the way
  back, and routes language-agnostic improvements to both samples. Load when
  the user invokes `/harvest <project-path>`.
compatibility:
  - claude-code
metadata:
  version: "2.0"
  author: team
---

# Harvest

Pull generic improvements from a real project back into the sample templates. Runs from the monorepo root.

**Usage:** `/harvest <project-path>` (e.g., `/harvest ../home-status-page`)

## Template Selection

Detect the source project's stack the same way `seed` does: `go.mod` → compare against `go/`; `pom.xml`, `build.gradle`, or `build.gradle.kts` → compare against `java-spring-boot/`; ambiguous → ask. `<template>` below is the matching sample; template paths resolve relative to it.

## What to Compare

Compare the source project against `<template>` for each category:

Source projects may be seeded with any subset of the four supported tools (see the `seed` skill). For each category below, if the source project does not have the path, skip it — a partial-tool downstream is valid and not a harvest signal.

| Category | Source | Template |
|---|---|---|
| Skills | `<project>/.claude/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md` |
| Claude Code agents | `<project>/.claude/agents/*.md` | `.claude/agents/*.md` |
| Copilot agents | `<project>/.github/agents/*.agent.md` | `.github/agents/*.agent.md` |
| OpenCode agents | `<project>/.opencode/agents/*.md` | `.opencode/agents/*.md` |
| Junie agents | `<project>/.junie/agents/*.md` | `.junie/agents/*.md` |
| Junie config | `<project>/.junie/config.json` | `.junie/config.json` |
| Templates | `<project>/.claude/templates/*.md` | `.claude/templates/*.md` |
| Settings | `<project>/.claude/settings.local.json` | `.claude/settings.local.json` |
| Agent-teams settings | `<project>/.claude/settings.json` | `.claude/settings.json` |
| Hooks | `<project>/.claude/hooks/*.sh` | `.claude/hooks/*.sh` |
| Rules | `<project>/CLAUDE.md` | `CLAUDE.md` |
| Agent README | `<project>/.claude/agents/README.md` | `.claude/agents/README.md` |
| Scratch schemas | `<project>/schemas/scratch/*.json` | `schemas/scratch/*.json` |
| Harness scripts | `<project>/scripts/*.py` | `scripts/*.py` |
| ADRs | `<project>/docs/adr/*.md` | `docs/adr/*.md` |

## Classification Rules

For every difference found, classify it. Decide by one principle: harvest what generalizes across projects, skip what encodes one project's domain, and ask when generic structure and domain detail are entangled. The buckets below list the common cases; when a diff matches none, fall back to that principle rather than pattern-matching the examples.

### Generic (harvest into template)
- New skill not in template
- New section added to an existing skill (e.g., a new checklist category)
- Structural improvement to an agent (new section, better process steps, added tool)
- New template file
- New permission in settings.local.json
- Bugfix or improvement in a harness script
- Improved wording that isn't domain-specific

### Domain-Specific (do NOT harvest)
- Filled-in `<!-- PROJECT -->` comment blocks (e.g., Security Context)
- Requirement IDs with real scope prefixes (`REQ-DL-*`, `REQ-SP-*` — template uses `REQ-XX-*`)
- Project name replacing `{{PROJECT_NAME}}`
- Specific file paths (e.g. `internal/render/render.go` or `src/main/java/com/example/render/Render.java` — generalize to the template's placeholder style)
- Threat models referencing specific technologies (WebSocket, gRPC, etc.)
- Specific container/deployment details
- References to project-specific config fields
- Trimmed tool-surface prose (a claude-only downstream dropping cross-tool references is its opt-out, not an improvement)

### Ambiguous (ask the user)
- Content that mixes generic structure with domain examples
- Changes to existing template wording where intent is unclear
- Removed sections (might be intentional cleanup or accidental)

### Deleted in Source (ask the user)

A file or template entry that exists in the template but **does not exist** in the source project. Two valid causes:

- **Intentional deletion** — the source project replaced the file with something better (e.g., migrated a markdown handoff template to a JSON Schema in `schemas/scratch/`). The template should drop the file too.
- **Out-of-scope omission** — the source project never adopted the file (e.g., a doc the user did not need). The template keeps it.

Procedure: list every template-only file alongside the harvest report. For each, ask the user "delete from template, keep, or skip this category". Default to keep when unsure — deletion is irreversible from harvest's perspective.

This category is essential for refactors that *remove* artifacts. Examples that have come up: replacing markdown handoff templates with JSONL+schema (which deletes `.claude/templates/current-feature.md`, `design-notes.md`, `review.md`, `review-summary.md`).

## Process

1. Read the source project path from the argument: `$ARGUMENTS`
2. Verify the source project exists and has `.claude/` directory; select `<template>` per Template Selection.
3. For each category in the table above, diff the source against `<template>`.
4. **Detect deletions:** for each template file in every category, check whether the source has the same file. Files present in template but missing in source are candidates for the "Deleted in Source" classification.
5. Classify every difference using the rules above.
6. Present findings to the user in four groups:
   - **Harvest** — generic improvements to apply. Show the diff for each.
   - **Skip** — domain-specific content. List briefly with reason.
   - **Ask** — ambiguous changes. Show the diff and ask for a decision.
   - **Deleted in Source** — template-only files. For each, ask delete / keep / skip-category.
7. Wait for user confirmation before applying any changes.
8. Apply confirmed changes to `<template>`. Deletions remove the file from the template; harvested additions write new files.
9. **Propagate cross-sample:** for each applied change, decide whether it is language-agnostic (harness mechanics, skill process steps, schema structure, script logic) or language-specific (lint rules, build commands, naming-convention regexes). Apply language-agnostic changes to the sibling sample too, keeping shared files byte-equivalent where the samples already mirror each other. Language-specific changes stay in `<template>`.
10. After applying, run each touched sample's `audit-agents` skill, then the root `audit-consistency` skill to verify cross-sample alignment.

## Generalization Rules

When harvesting, transform domain content to template form. Use the path and naming style of the sample being written to:

| Domain Pattern | Template Form |
|---|---|
| `home-status-page`, `dirigera-exporter`, etc. | `{{PROJECT_NAME}}` |
| `REQ-DL-001`, `REQ-SP-002`, etc. | `REQ-XX-001` |
| `internal/render/render.go:87` (Go source) | A placeholder path (e.g. `internal/example/handler.go:87`) |
| `src/main/java/com/example/render/Render.java:87` (Java source) | `src/main/java/com/example/project/{package}/{Class}.java:87` |
| Filled `## Security Context` block | `<!-- PROJECT: Add a "Security Context" section ... -->` |
| `make security` (Go target with govulncheck) | `go mod verify` with govulncheck as optional |
| Project-specific responses (`GitHub API responses`) | `External responses` |
| `valid_outlet.json` | `valid_input.json` |
| `ParseDevice` | `ParseInput` |
| `NNN-short-title.md` (project ADR convention) | `YYYY-MM-DD-title-in-kebab-case.md` (template default) |

If a new pattern appears that isn't in this table, ask the user how to generalize it.

### JSON Schema Files (`schemas/scratch/*.json`)

Schemas carry both **structural** content (record types, required-field lists, the shape of `properties` and `items`) and **language-specific** content (regex patterns, naming conventions, example values). Harvest each layer differently:

| Schema Element | Treatment |
|---|---|
| `required` field list | Harvest verbatim — structural |
| `properties` keys | Harvest verbatim — structural |
| Field-level `description` | Harvest verbatim — generic prose |
| `enum` values for agent names (e.g. `"product-requirements-expert"`) | Harvest verbatim — these match agent files |
| `$id` namespace (e.g. `ccledger://...`) | **Skip** — each project owns its namespace |
| Regex `pattern` constrained to one language (e.g. Go `^Test[A-Z]`, JUnit `@Test`-tagged method names) | **Skip** — different across language templates; let each template own its language-specific patterns |
| Path-shaped strings in examples | Generalize per the path rows above |
| File `description` mentioning specific tooling (e.g. `make ci`, `./gradlew test`) | Preserve language-neutral wording when possible; otherwise leave per-template |

When a schema field is genuinely language-agnostic (e.g. ISO 8601 timestamps, requirement-ID patterns shared across templates), harvest it — into both samples per Process step 9. When it embeds language conventions, leave it.

### Harness Scripts (`scripts/*.py`)

The scripts are byte-equivalent across both samples by design. A harvested script improvement is always language-agnostic unless it touches `layout.toml` parsing defaults — apply it to both samples and run both samples' script test suites (`test_handoff.py`, `test_score_change.py`). `scripts/layout.toml` itself is project configuration: never harvest its module rules. `test_score_change.py` fixtures are layout-coupled the same way — harvest logic changes, never a downstream's fixture paths or sensitive-path cases.

### ADR Files (`docs/adr/*.md`)

ADRs document decisions, not template scaffolding. Harvest only when the decision is *generic* (e.g. "use append-only JSONL handoffs"); skip when the decision is *project-specific* (e.g. "use this particular pricing table format"). When in doubt, classify as Ask. ADRs are dated `YYYY-MM-DD-*` filenames; preserve the original date when copying — do not retroactively re-date.

## Output Format

```
## Harvest Report: <project-name>  (template: <template>)

### Harvest (generic improvements)
1. **[category] file** — description of change  [both samples | <template> only]
   ```diff
   ...
   ```

### Skip (domain-specific)
- **file** — reason (e.g., "filled-in Security Context")

### Ask (ambiguous)
1. **file** — description. Harvest or skip?

### Deleted in Source (template-only files)
1. **[category] file** — present in template, missing in source.
   Possible cause: <inferred>.
   Action: delete / keep / skip-category?

### Summary
- X changes to harvest (C of them cross-sample)
- Y domain-specific skipped
- Z need your decision
- D template-only files awaiting delete / keep
```
