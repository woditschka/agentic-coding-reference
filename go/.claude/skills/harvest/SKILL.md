---
name: harvest
description: >-
  Pull generic improvements from a downstream project back into this template.
  Diff the target project's .claude/ and docs/ against the template, classify
  each change as harvest, skip, or ask, and generalize domain patterns on the
  way back. Load when the user invokes `/harvest <project-path>`.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

# Harvest

Pull generic improvements from a real project back into this template.

**Usage:** `/harvest <project-path>` (e.g., `/harvest ../home-status-page`)

## What to Compare

Compare the source project against this template for each category:

| Category | Source | Template |
|---|---|---|
| Skills | `<project>/.claude/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md` |
| Claude Code agents | `<project>/.claude/agents/*.md` | `.claude/agents/*.md` |
| OpenCode agents | `<project>/.opencode/agents/*.md` | `.opencode/agents/*.md` |
| Copilot agents | `<project>/.github/agents/*.agent.md` | `.github/agents/*.agent.md` |
| Templates | `<project>/.claude/templates/*.md` | `.claude/templates/*.md` |
| Settings | `<project>/.claude/settings.local.json` | `.claude/settings.local.json` |
| Rules | `<project>/CLAUDE.md` | `CLAUDE.md` |
| Agent README | `<project>/.claude/agents/README.md` | `.claude/agents/README.md` |

## Classification Rules

For every difference found, classify it:

### Generic (harvest into template)
- New skill not in template
- New section added to an existing skill (e.g., a new checklist category)
- Structural improvement to an agent (new section, better process steps, added tool)
- New template file
- New permission in settings.local.json
- Improved wording that isn't domain-specific

### Domain-Specific (do NOT harvest)
- Filled-in `<!-- PROJECT -->` comment blocks (e.g., Security Context)
- Requirement IDs with real scope prefixes (`REQ-DL-*`, `REQ-SP-*` — template uses `REQ-XX-*`)
- Project name replacing `{{PROJECT_NAME}}`
- Specific file paths (`internal/render/render.go` — template uses `internal/example/handler.go`)
- Threat models referencing specific technologies (WebSocket, gRPC, etc.)
- Specific container/deployment details
- References to project-specific config fields

### Ambiguous (ask the user)
- Content that mixes generic structure with domain examples
- Changes to existing template wording where intent is unclear
- Removed sections (might be intentional cleanup or accidental)

## Process

1. Read the source project path from the argument: `$ARGUMENTS`
2. Verify the source project exists and has `.claude/` directory.
3. For each category in the table above, diff the source against the template.
4. Classify every difference using the rules above.
5. Present findings to the user in three groups:
   - **Harvest** — generic improvements to apply. Show the diff for each.
   - **Skip** — domain-specific content. List briefly with reason.
   - **Ask** — ambiguous changes. Show the diff and ask for a decision.
6. Wait for user confirmation before applying any changes.
7. Apply confirmed changes to the template files.
8. After applying, run the `audit-agents` skill to verify consistency.

## Generalization Rules

When harvesting, transform domain content to template form:

| Domain Pattern | Template Form |
|---|---|
| `home-status-page`, `dirigera-exporter`, etc. | `{{PROJECT_NAME}}` |
| `REQ-DL-001`, `REQ-SP-002`, etc. | `REQ-XX-001` |
| `internal/render/render.go:87` | `internal/example/handler.go:87` |
| Filled `## Security Context` block | `<!-- PROJECT: Add a "Security Context" section ... -->` |
| `make security` (project has govulncheck) | `go mod verify` with govulncheck as optional |
| `GitHub API responses` | `External responses` |
| `valid_outlet.json` | `valid_input.json` |
| `ParseDevice` | `ParseInput` |
| `NNN-short-title.md` (project ADR convention) | `YYYY-MM-DD-title-in-kebab-case.md` (template default) |

If a new pattern appears that isn't in this table, ask the user how to generalize it.

## Output Format

```
## Harvest Report: <project-name>

### Harvest (generic improvements)
1. **[category] file** — description of change
   ```diff
   ...
   ```

### Skip (domain-specific)
- **file** — reason (e.g., "filled-in Security Context")

### Ask (ambiguous)
1. **file** — description. Harvest or skip?

### Summary
- X changes to harvest
- Y domain-specific skipped
- Z need your decision
```
