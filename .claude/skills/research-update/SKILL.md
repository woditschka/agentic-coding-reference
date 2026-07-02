---
name: research-update
description: >-
  Check upstream tool documentation for changes that affect
  docs/specialist-agent-workflow.md. Fetches source URLs, compares
  claims against current doc, and reports drift. Use when updating
  the cross-tool strategy guide or checking for tool changes.
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

## Scope

| Scope | What It Checks |
|-------|---------------|
| *(all)* | All sources |
| `claude-code` | Claude Code docs only |
| `copilot` | GitHub Copilot CLI docs only |
| `opencode` | OpenCode docs only |
| `community` | Community resources only |

## Sources

Fetch each URL listed in `docs/specialist-agent-workflow.md` Section 10 (Sources), filtered by the selected scope. **That section is the single authoritative source list** — do not invent URLs, and do not maintain a copy here. A URL added to or retired from the doc is automatically in or out of scope.

## Process

### 1. Fetch Sources

Fetch each URL in the selected scope. If a URL returns an error (404, 403, timeout), note it as a potential doc restructure.

### 2. Extract Key Claims

For each source, extract the current state of:

| Category | What to Look For |
|----------|-----------------|
| **Frontmatter fields** | New, renamed, or deprecated YAML fields for agents/skills |
| **Discovery paths** | Changes to where tools look for agents, skills, rules files |
| **Tool permissions** | New tool names, permission syntax changes |
| **Model support** | New models, changed model IDs, deprecated models |
| **Multi-agent** | Agent Teams status changes, new orchestration features |
| **Compatibility** | Changes to cross-tool behavior (CLAUDE.md reading, AGENTS.md fallback) |
| **New features** | Capabilities not mentioned in the current doc |
| **Deprecations** | Features marked deprecated or removed |

### 3. Compare Against Current Doc

Read `docs/specialist-agent-workflow.md` and compare each claim against what the sources say now. Flag:

- **Outdated**: Doc says X, source now says Y
- **Missing**: Source describes feature not mentioned in doc
- **Deprecated**: Doc recommends something the source marks deprecated
- **Broken URL**: Source URL returns error or redirects
- **Version drift**: Doc references old version numbers or dates

### 4. Present Findings

```
## Research Update: [date]

### Scope: [all | claude-code | copilot | opencode | community]

### Outdated Claims
1. **Section N.N [title]** — line NN
   - **Current doc:** [what it says]
   - **Source says:** [what the source now says]
   - **Source URL:** [url]
   - **Suggested fix:** [specific edit]

### New Features (not in doc)
1. **[tool] [feature name]**
   - **What:** [description]
   - **Source URL:** [url]
   - **Where to add:** Section N.N
   - **Impact on projects:** [does this affect samples/go or samples/java-spring-boot configs?]

### Deprecations
1. **Section N.N [title]** — line NN
   - **What:** [feature] is now deprecated
   - **Source URL:** [url]
   - **Suggested fix:** [specific edit]

### Broken URLs
1. **Section N.N** — line NN
   - **URL:** [url]
   - **Status:** [404 | redirect to X | timeout]

### Version Drift
1. **Section N.N** — line NN
   - **Current doc:** [old version/date]
   - **Current:** [new version/date]

### No Changes
- [list sections that are still accurate]

### Summary
- X outdated claims
- Y new features to document
- Z deprecations
- W broken URLs
- V version updates needed
```

### 5. Propose Edits

For each finding, propose a specific edit to `docs/specialist-agent-workflow.md`:
- Quote the exact text to replace
- Provide the replacement text
- Note which section tables (2, 6, 7) need updates

Do NOT apply edits automatically. Present them for review.

### 6. Cascade Check

After edits are applied, recommend:

1. Run `/audit-harness` — its battery plus consistency layer catch any effect on the sample configs.
2. Check if any new frontmatter fields should be added to project agent definitions.
3. Check if any new skill discovery paths change the compatibility rules.
4. Update the `Version:` date at the top of the doc.

## What NOT to Change

- **Architecture decisions** (file-based coordination, agent thinness) — design choices, not tool documentation.
- **Maturity level recommendations** — only change if Agent Teams exits experimental or a tool adds new orchestration.
- **Migration playbook phases** — only change if tool installation or setup steps change.
- **Cross-tool strategy matrix** — only change if a tool's strengths/weaknesses shift materially.

## Handling Conflicting Sources

If two sources disagree:
1. Prefer official documentation over blog posts.
2. Prefer newer docs over older docs.
3. If unclear, flag as ambiguous and ask the user.
4. Note the conflict in the findings so the user can verify.
