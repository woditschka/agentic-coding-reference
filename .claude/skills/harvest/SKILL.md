---
name: harvest
description: >-
  Pull generic improvements from a downstream project back into the /harness
  source tree. Detects the source project's stack (Go or Java Spring Boot),
  diffs its harness runtime (.claude/, schemas, scripts) against the
  materialized harness (core plus the stack slice), classifies each change as
  harvest, skip, or ask, generalizes domain patterns on the way back, and
  routes language-agnostic changes to core/ and stack-specific ones to
  stacks/<stack>/. Load when the user invokes `/harvest <project-path>`.
compatibility:
  - claude-code
metadata:
  version: "3.0"
  author: team
---

# Harvest

Pull generic improvements from a real project back into the `/harness` source tree. Runs from the monorepo root. `/harness` is the single canonical runtime: `core/` holds the files every stack shares byte-for-byte; `stacks/<stack>/` holds the stack-specific ones. Harvest writes each improvement to the layer it belongs to; the samples and any other consumer pick it up on the next `materialize`.

**Usage:** `/harvest <project-path>` (e.g., `/harvest ../home-status-page`)

## Stack Selection

Detect the source project's stack the same way `seed` and `materialize` do: `go.mod` → `go`; `pom.xml`, `build.gradle`, or `build.gradle.kts` → `java-spring-boot`; ambiguous → ask. Below, `<stack>` is the detected stack.

The **comparison target** is the materialized harness for that stack — `core/` overlaid with `stacks/<stack>/`. Each runtime file resolves to `harness/core/<path>` when present there, otherwise `harness/stacks/<stack>/<path>`. A diff against that overlay is what a materialized consumer of this stack would see.

## What to Compare

Compare the source project's harness runtime against the materialized harness (core ∪ `stacks/<stack>`) for each category.

Source projects may be seeded with any subset of the four supported tools (see the `seed` skill). For each category below, if the source project does not have the path, skip it — a partial-tool downstream is valid and not a harvest signal.

| Category | Source | Harness (core ∪ stacks/<stack>) |
|---|---|---|
| Skills | `<project>/.claude/skills/` (whole tree: SKILL.md, carried reference docs, doctor templates and manifest, engines) | `.claude/skills/` |
| Claude Code agents | `<project>/.claude/agents/*.md` | `.claude/agents/*.md` |
| Copilot agents | `<project>/.github/agents/*.agent.md` | `.github/agents/*.agent.md` |
| OpenCode agents | `<project>/.opencode/agents/*.md` | `.opencode/agents/*.md` |
| Junie agents | `<project>/.junie/agents/*.md` | `.junie/agents/*.md` |
| Junie config | `<project>/.junie/config.json` | `.junie/config.json` |
| Templates | `<project>/.claude/templates/*.md` | `.claude/templates/*.md` |
| Hooks | `<project>/.claude/hooks/*.sh` | `.claude/hooks/*.sh` |
| Scratch schemas | `<project>/schemas/scratch/*.json` | `schemas/scratch/*.json` |
| Harness scripts | `<project>/scripts/*.py` | `scripts/*.py` |
| Rules | `<project>/CLAUDE.md` | *(stack-specific; compare against `stacks/<stack>` only if carried there)* |

The source project's `docs/` is **not compared file-to-file** — briefs are project-owned and their divergence from the harness defaults is the design, not drift. Two harvest signals still come from there; route them by the table below.

`settings.json` (agent-teams flag plus hook registration) and `settings.local.json` (permission list) are project-owned config in the manifest channel, not materialized runtime — they are not harvested.

## Routing by Kind

Every harvested change lands in the harness layer it belongs to. Core vs stack is the central decision: **does this change apply to every stack, or only this one?**

| Kind of insight | Destination |
|---|---|
| Harness mechanics, language-agnostic (skill process, cross-stack agent structure, script logic, schema shape) | `harness/core/` — every stack inherits it on the next materialize |
| Harness mechanics, stack-specific (lint rules, build commands, naming regexes, a stack's agent prose) | `harness/stacks/<stack>/` |
| Policy insight (a better *default* value, section, or wording for a brief) | `harness/stacks/<stack>/.claude/skills/doctor/templates/` — defaults are stack-indexed; consumer briefs are never touched |
| Project-specific content | Stays downstream; not harvested |
| Kernel- or spec-level change (roster, required sections, ownership or channel rule) | Root ADR + `docs/harness-project-api.md` + spec version bump — never a silent core edit |
| Generic harness *decision* recorded downstream | Root `docs/adr/` (the handbook decision log) — consumers no longer ship harness ADRs |

**Layer moves.** A change may not match where the file currently lives. If a file in `core/` gains a stack-specific change, that fact must split out to `stacks/<stack>/` (the core copy stays shared); if a file in both stacks converges, it may lift to `core/`. Note any such move explicitly in the report — it changes what every other stack sees.

## Classification Rules

For every difference found, classify it. Decide by one principle: harvest what generalizes across projects, skip what encodes one project's domain, and ask when generic structure and domain detail are entangled. The buckets below list the common cases; when a diff matches none, fall back to that principle rather than pattern-matching the examples.

### Generic (harvest into the harness)
- New skill not in the harness
- New section added to an existing skill (e.g., a new checklist category)
- Structural improvement to an agent (new section, better process steps, added tool)
- New template file
- Bugfix or improvement in a harness script
- Improved wording that isn't domain-specific

### Domain-Specific (do NOT harvest)
- Filled-in `<!-- PROJECT -->` comment blocks in any runtime file
- Requirement IDs with real scope prefixes (`REQ-DL-*`, `REQ-SP-*` — the harness uses `REQ-XX-*`)
- Project name replacing `{{PROJECT_NAME}}`
- Specific file paths (e.g. `internal/render/render.go` or `src/main/java/com/example/render/Render.java` — generalize to placeholder style)
- Threat models referencing specific technologies (WebSocket, gRPC, etc.)
- Specific container/deployment details
- References to project-specific config fields
- Trimmed tool-surface prose (a claude-only downstream dropping cross-tool references is its opt-out, not an improvement)

### Ambiguous (ask the user)
- Content that mixes generic structure with domain examples
- Changes to existing wording where intent is unclear
- Removed sections (might be intentional cleanup or accidental)

### Deleted in Source (ask the user)

A file that exists in the harness but **does not exist** in the source project. Two valid causes:

- **Intentional deletion** — the source project replaced the file with something better (e.g., migrated a markdown handoff template to a JSON Schema in `schemas/scratch/`). The harness should drop the file too.
- **Out-of-scope omission** — the source project never adopted the file (e.g., a doc the user did not need). The harness keeps it.

Procedure: list every harness-only file alongside the harvest report. For each, ask the user "delete from harness, keep, or skip this category". Default to keep when unsure — deletion is irreversible from harvest's perspective. A deletion in `core/` removes the file for every stack; a deletion in `stacks/<stack>/` affects only that stack.

## Process

1. Read the source project path from the argument: `$ARGUMENTS`
2. Verify the source project exists and has a `.claude/` directory; detect `<stack>` per Stack Selection.
3. For each category in the table above, diff the source against the materialized harness (core ∪ `stacks/<stack>`).
4. **Detect deletions:** for each harness file in every category, check whether the source has the same file. Files present in the harness but missing in source are candidates for "Deleted in Source".
5. Classify every difference using the rules above; for each, decide its destination layer (core vs stack) per Routing by Kind.
6. Present findings to the user in four groups:
   - **Harvest** — generic improvements to apply, each tagged with its destination layer. Show the diff.
   - **Skip** — domain-specific content. List briefly with reason.
   - **Ask** — ambiguous changes. Show the diff and ask for a decision.
   - **Deleted in Source** — harness-only files. For each, ask delete / keep / skip-category.
7. Wait for user confirmation before applying any changes.
8. Apply confirmed changes to the harness, each to its destination layer: language-agnostic → `harness/core/`; stack-specific → `harness/stacks/<stack>/`. Perform any layer move noted in step 5. There is no cross-sample copying — `core/` is the one shared place.
9. **Verify:** re-materialize the affected samples (`harness/bootstrap.sh`) and run their doctors and script-test suites to confirm the harvest did not break a stack. A change applied to `core/` must leave *both* stacks passing.

## Generalization Rules

When harvesting, transform domain content to harness form:

| Domain Pattern | Harness Form |
|---|---|
| `home-status-page`, `dirigera-exporter`, etc. | `{{PROJECT_NAME}}` |
| `REQ-DL-001`, `REQ-SP-002`, etc. | `REQ-XX-001` |
| `internal/render/render.go:87` (Go source) | A placeholder path (e.g. `internal/example/handler.go:87`) |
| `src/main/java/com/example/render/Render.java:87` (Java source) | `src/main/java/com/example/project/{package}/{Class}.java:87` |
| `make security` (Go target with govulncheck) | `go mod verify` with govulncheck as optional |
| Project-specific responses (`GitHub API responses`) | `External responses` |
| `valid_outlet.json` | `valid_input.json` |
| `ParseDevice` | `ParseInput` |
| `NNN-short-title.md` (project ADR convention) | `YYYY-MM-DD-title-in-kebab-case.md` (default) |

If a new pattern appears that isn't in this table, ask the user how to generalize it.

### JSON Schema Files (`schemas/scratch/*.json`)

Schemas carry both **structural** content (record types, required-field lists, the shape of `properties` and `items`) and **language-specific** content (regex patterns, naming conventions, example values). The structural layer is shared (`core/schemas/`); the language-specific layer is stack-owned (`stacks/<stack>/schemas/`). Harvest each accordingly:

| Schema Element | Treatment |
|---|---|
| `required` field list | Harvest to `core/` — structural |
| `properties` keys | Harvest to `core/` — structural |
| Field-level `description` | Harvest to `core/` — generic prose |
| `enum` values for agent names (e.g. `"product-requirements-expert"`) | Harvest to `core/` — these match agent files |
| `$id` namespace (e.g. `ccledger://...`) | **Skip** — each project owns its namespace |
| Regex `pattern` constrained to one language (e.g. Go `^Test[A-Z]`, JUnit `@Test`-tagged method names) | Route to `stacks/<stack>/` — the stack owns its language-specific patterns |
| Path-shaped strings in examples | Generalize per the path rows above |
| File `description` mentioning specific tooling (e.g. `make ci`, `./gradlew test`) | Prefer language-neutral wording; otherwise keep in the stack |

A schema that is structurally identical across stacks lives in `core/`; one that embeds a stack pattern lives in `stacks/<stack>/`. If a `core/` schema gains a language-specific pattern, split that schema to the stacks (see Layer moves).

### Harness Scripts (`scripts/*.py`)

The engines `handoff.py`, `test_handoff.py`, and `score-change.py` live in `core/scripts/` — shared by every stack. A logic improvement to any of them is harvested to `core/`. `test_score_change.py` is layout-coupled and lives per stack (`stacks/<stack>/scripts/`): harvest logic changes, never a downstream's fixture paths or sensitive-path cases. `scripts/layout.toml` is project configuration: never harvest its module rules. After a `core/` script change, run *both* stacks' script-test suites via re-materialize, not just the source stack's.

### ADR Files (`docs/adr/*.md`)

The downstream decision log is project-owned and is not diffed against the harness. Harvest a downstream ADR only when it records a *generic harness* decision (e.g. "use append-only JSONL handoffs") — and route it to the **root** `docs/adr/` handbook log, generalized, per the Routing by Kind table. Skip project-specific decisions. When in doubt, classify as Ask. Preserve the original date when copying — do not retroactively re-date.

## Output Format

```
## Harvest Report: <project-name>  (stack: <stack>)

### Harvest (generic improvements)
1. **[category] file → core | stacks/<stack>** — description of change
   ```diff
   ...
   ```

### Skip (domain-specific)
- **file** — reason (e.g., "filled-in PROJECT block")

### Ask (ambiguous)
1. **file** — description. Harvest or skip?

### Deleted in Source (harness-only files)
1. **[category] file (core | stacks/<stack>)** — present in harness, missing in source.
   Possible cause: <inferred>.
   Action: delete / keep / skip-category?

### Summary
- X changes to harvest (C to core, S to stacks/<stack>)
- Y domain-specific skipped
- Z need your decision
- D harness-only files awaiting delete / keep
```
