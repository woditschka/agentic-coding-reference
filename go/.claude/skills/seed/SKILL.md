---
name: seed
description: >-
  Push this template's setup into a target project. Init mode scaffolds a new
  empty target; upgrade mode raises the bar on an existing project by merging
  template improvements while preserving domain customizations. Load when the
  user invokes `/seed <project-path>`.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

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
| Project description | `{{PROJECT_DESCRIPTION}}` | `Kubernetes dashboard for home infrastructure` |

### 2. Copy Structure

Copy these directories and files from this template to the target:

```
CLAUDE.md                  (root rules file; placeholders filled in step 3)

.claude/
├── agents/*.md          (all agents including README.md)
├── skills/*/SKILL.md    (all skills except `seed` and `harvest` — those stay in template)
├── templates/*.md        (all templates)
└── settings.local.json

.opencode/
└── agents/*.md           (all agents)

.github/
└── agents/*.agent.md     (Copilot agents)
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
├── ddd-principles.md
├── tdd-principles.md
├── testing-principles.md
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
1. Review CLAUDE.md — confirm the Toolchain, Build Commands, and Testing Strategy sections match your project
2. Fill in the Security Context in .claude/agents/security-reviewer.md,
   .opencode/agents/security-reviewer.md, and .github/agents/security-reviewer.agent.md
   (replace the <!-- PROJECT --> comment with your application's security profile)
3. Review docs/prd.md and fill in your requirements
4. Review docs/system-design.md and fill in your architecture
5. Run /lint-docs to validate documentation coherence
```

## Upgrade Mode

### 1. Identify What Changed

**First, auto-detect target metadata.** Do not ask the user for values that can be inferred from the target; only prompt if inference fails.

| Value | Detection order |
|---|---|
| Project name | 1. Parse `CLAUDE.md` `## Project Overview` first non-empty line as `<name>: <description>`; 2. `go.mod` `module <path>` (last path segment); 3. target directory name. If any yields `{{PROJECT_NAME}}`, treat as unfilled and ask user. |
| Project description | 1. Same line, after `: `; 2. `README.md` first heading line. If unfilled or `{{PROJECT_DESCRIPTION}}`, ask user. |

**Second, check for missing scaffolding.** A target seeded by an older version of this command may be missing entire files or directories that Init Mode now copies. For each item in Init Mode Step 2 and Step 4, if the target is missing it, mark as **new-copy** (follow Init Mode rules for that item using the auto-detected values above).

Common missing-scaffolding cases (pre-fix targets):
- No `CLAUDE.md` at target root
- No `.github/agents/` directory
- No `docs/ddd-principles.md`, `docs/tdd-principles.md`, or `docs/testing-principles.md`

**Third, diff each category** between the template and the target project:

| Category | Template | Target |
|---|---|---|
| Rules file | `CLAUDE.md` | `<project>/CLAUDE.md` |
| Skills | `.claude/skills/*/SKILL.md` | `<project>/.claude/skills/*/SKILL.md` |
| Claude Code agents | `.claude/agents/*.md` | `<project>/.claude/agents/*.md` |
| OpenCode agents | `.opencode/agents/*.md` | `<project>/.opencode/agents/*.md` |
| Copilot agents | `.github/agents/*.agent.md` | `<project>/.github/agents/*.agent.md` |
| Templates | `.claude/templates/*.md` | `<project>/.claude/templates/*.md` |
| Settings | `.claude/settings.local.json` | `<project>/.claude/settings.local.json` |
| Principles docs | `docs/{ddd,tdd,testing}-principles.md` | `<project>/docs/{ddd,tdd,testing}-principles.md` |
| Doc scaffolding | `docs/{prd,system-design,documentation}.md`, `docs/adr/` | `<project>/docs/{prd,system-design,documentation}.md`, `<project>/docs/adr/` |

Build files (`go.mod`, `go.sum`, `Makefile`) are not diffed — the target's build config is authoritative and seed never pushes changes to them.

Doc scaffolding diff is **structural only**: push template changes to section headers, `<!-- AGENT: ... -->` comments, and table stubs; never overwrite filled-in requirements, architecture, or ADRs. Target's domain content wins every conflict.

### 2. Classify Differences

For every difference, classify:

**Template is newer** (push to target):
- New skill not in target
- Improved agent structure (new section, better process)
- New template file
- New permission in settings
- Structural fixes (consistency, parity)

**Authoritative push** (overwrite target; no domain content preserved):
- `docs/ddd-principles.md` — must be byte-equivalent to root
- `docs/tdd-principles.md` — must be byte-equivalent to root
- `docs/testing-principles.md` generic sections only (see Merge Protocol — language-specific sections below the generic block are preserved)

**Target has customization** (preserve):
- Filled-in `<!-- PROJECT -->` blocks
- `{{PROJECT_NAME}}` already replaced with real name
- Real requirement IDs (`REQ-DL-*`) replacing `REQ-XX-*`
- Real file paths replacing `internal/example/handler.go`
- Security Context filled in
- Threat model added
- Project-specific config references
- CLAUDE.md Toolchain, Build Commands, Project Overview, Testing Strategy body — target's values are authoritative

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
4. For missing scaffolding (from Step 1), copy as in Init Mode and fill placeholders.
5. Verify: grep the target for `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}`. Any hit outside files listed in `audit-consistency` Section 5 means a placeholder was left unfilled — report to the user.
6. Run the `audit-agents` skill on the target to verify consistency.

## Merge Protocol for Upgraded Files

When updating a file that has domain customizations:

1. **Section-level merge**: Compare by `##` headings, not line-by-line.
2. **Preserve blocks between `<!-- PROJECT -->` markers**: Never overwrite.
3. **Preserve filled placeholders**: If `{{PROJECT_NAME}}` is already `home-status-page`, keep it.
4. **Preserve added sections**: If the target added a `## Security Context` section, keep it.
5. **Update generic sections**: If the template improved `## Review Process` steps, push the update.
6. **Add new sections**: If the template added a new `## Skills` reference, add it.
7. **Never delete target-only content**: If the target has extra sections not in template, keep them.

### CLAUDE.md section classification

CLAUDE.md mixes domain content with generic workflow content. Apply per-section rules:

| Section | Treatment |
|---|---|
| `## Project Overview` | Preserve target (real project name/description replaces `{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}`) |
| `## Toolchain` | Preserve target (project-specific versions) |
| `## Build Commands` | Preserve target (project-specific Make/go targets) |
| `## Lint Troubleshooting` | Preserve target if customized; push template improvements if target is still generic |
| `## Testing Strategy` body | Preserve target if customized; push template structure if target is still generic |
| `## Architecture` | Preserve target |
| `## Agent Usage` | Push template (generic workflow) |
| Skills table (under `### Skills`) | Push template — must list every `.claude/skills/` directory |
| `## Writing Standards` | Push template (generic) |
| `## Quality Gate` | Push template structure; preserve target's project-specific commands |
| `## Scratch Directory` | Push template (generic) |
| `## Documentation Updates` | Push template (generic) |
| `## Commit Convention` | Push template (generic) |

### Principles docs (authoritative push)

- `docs/ddd-principles.md` and `docs/tdd-principles.md`: overwrite target with template content. No merge. Target changes are treated as drift.
- `docs/testing-principles.md`: push generic sections (per `audit-consistency` Section 10 list); preserve language-specific content below the generic block.

## Files That Stay in Template Only

Do NOT copy these to the target:
- `.claude/skills/harvest/` — template management only
- `.claude/skills/seed/` — this skill; template management only
