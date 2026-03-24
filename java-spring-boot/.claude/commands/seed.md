# Seed

Push this template's setup into a target project.

**Usage:** `/seed <project-path>` (e.g., `/seed ../new-project`)

## Modes

Detect automatically based on target state:

| Target State | Mode | Behavior |
|---|---|---|
| No `.claude/` directory | **Init** | Full copy, ask for project details |
| Has `.claude/` but outdated | **Upgrade** | Diff and merge, preserve domain content |

## Init Mode

### 1. Gather Project Details

Ask the user for:

| Field | Placeholder | Example |
|---|---|---|
| Project name | `{{PROJECT_NAME}}` | `home-status-page` |
| Project description | `{{PROJECT_DESCRIPTION}}` | `Spring Boot CLI tool for home infrastructure` |

### 2. Copy Structure

Copy these directories and files from this template to the target:

```
.claude/
├── agents/*.md          (all agents including README.md)
├── skills/*/SKILL.md    (all skills)
├── commands/*.md         (lint-docs only — harvest/seed stay in template)
├── templates/*.md        (all templates)
└── settings.local.json

.opencode/
└── agents/*.md           (all agents)
```

### 3. Fill Placeholders

Replace in all copied files:
- `{{PROJECT_NAME}}` → user-provided project name
- `{{PROJECT_DESCRIPTION}}` → user-provided description

### 4. Copy Documentation Scaffolding

If the target has no `docs/` directory, copy the template structure:

```
docs/
├── prd.md
├── system-design.md
├── documentation.md
├── test-philosophy.md
└── adr/
    └── README.md
```

Fill `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}` in these files too.

### 5. Update .gitignore

Ensure the target's `.gitignore` includes:
```
.scratch/
```

If no `.gitignore` exists, copy the template's `.gitignore`.
If one exists, append `.scratch/` if missing.

### 6. Prompt for Security Context

After copying, remind the user:

```
Next steps:
1. Fill in the Security Context in .claude/agents/security-reviewer.md
   and .opencode/agents/security-reviewer.md
   (replace the <!-- PROJECT --> comment with your application's security profile)
2. Review docs/prd.md and fill in your requirements
3. Review docs/system-design.md and fill in your architecture
4. Run /lint-docs to validate documentation coherence
```

## Upgrade Mode

### 1. Identify What Changed

Diff each category between the template and the target project:

| Category | Template | Target |
|---|---|---|
| Skills | `.claude/skills/*/SKILL.md` | `<project>/.claude/skills/*/SKILL.md` |
| Claude Code agents | `.claude/agents/*.md` | `<project>/.claude/agents/*.md` |
| OpenCode agents | `.opencode/agents/*.md` | `<project>/.opencode/agents/*.md` |
| Templates | `.claude/templates/*.md` | `<project>/.claude/templates/*.md` |
| Commands | `.claude/commands/lint-docs.md` | `<project>/.claude/commands/lint-docs.md` |
| Settings | `.claude/settings.local.json` | `<project>/.claude/settings.local.json` |

### 2. Classify Differences

For every difference, classify:

**Template is newer** (push to target):
- New skill not in target
- Improved agent structure (new section, better process)
- New template file
- New permission in settings
- Structural fixes (consistency, parity)

**Target has customization** (preserve):
- Filled-in `<!-- PROJECT -->` blocks
- `{{PROJECT_NAME}}` already replaced with real name
- Real requirement IDs (`REQ-DL-*`) replacing `REQ-XX-*`
- Real file paths replacing generic paths
- Security Context filled in
- Threat model added
- Project-specific config references

**Conflict** (ask user):
- Both template and target changed the same section
- Target removed something the template still has
- Target added content to a section the template also changed

### 3. Present Plan

Show the user what will change:

```
## Seed Plan: <project-name>

### Push (template improvements)
1. **[category] file** — description
   ```diff
   ...
   ```

### Preserve (domain customizations)
- **file** — what's preserved

### Conflicts
1. **file** — both changed. Show both versions, ask which to keep.

### New Files
- **file** — new in template, will be copied

### Summary
- X files to update
- Y customizations preserved
- Z conflicts to resolve
- W new files to copy
```

### 4. Apply

After user confirms:
1. Apply template improvements, preserving domain content.
2. For new skills/agents, copy directly (no domain content to preserve).
3. For upgraded files, merge: keep domain sections, update generic sections.
4. Run the `audit-agents` skill on the target to verify consistency.

## Merge Protocol for Upgraded Files

When updating a file that has domain customizations:

1. **Section-level merge**: Compare by `##` headings, not line-by-line.
2. **Preserve blocks between `<!-- PROJECT -->` markers**: Never overwrite.
3. **Preserve filled placeholders**: If `{{PROJECT_NAME}}` is already `home-status-page`, keep it.
4. **Preserve added sections**: If the target added a `## Security Context` section, keep it.
5. **Update generic sections**: If the template improved `## Review Process` steps, push the update.
6. **Add new sections**: If the template added a new `## Skills` reference, add it.
7. **Never delete target-only content**: If the target has extra sections not in template, keep them.

## Files That Stay in Template Only

Do NOT copy these to the target:
- `.claude/commands/harvest.md` — template management only
- `.claude/commands/seed.md` — template management only
- This file
