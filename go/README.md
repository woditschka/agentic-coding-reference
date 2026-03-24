# Go Reference Implementation

Agentic coding patterns applied to Go. 8 specialist agents, 13 portable skills, and a Makefile-based toolchain — configured for Claude Code, OpenCode, and GitHub Copilot.

## Build and Test

```bash
make test        # Run all tests
make lint        # Run golangci-lint
make ci          # Full pipeline: tidy, fmt, vet, lint, test, build
```

## Toolchain

| Tool | Version |
|------|---------|
| Go | 1.26 |
| golangci-lint | v2.7.2 |

## Use with an Agent

Open this directory in your agent tool. Configuration loads automatically.

```bash
claude          # Claude Code
opencode        # OpenCode
copilot         # Copilot CLI
```

Start a feature: *"Add a health check HTTP endpoint."* The pipeline coordinator reads `.scratch/` state and routes to the correct specialist.

## Agent Pipeline

```
coordinator → requirements-expert → design-expert → implementer → 4 reviewers (parallel)
```

| Agent | Model | Role |
|-------|-------|------|
| pipeline-coordinator | Sonnet | Classify requests, route to specialists |
| product-requirements-expert | Opus | Write PRD, define scope |
| system-design-expert | Opus | Validate architectural fit |
| feature-implementer | Opus | TDD implementation |
| code-quality-reviewer | Sonnet | Google Go Style Guide compliance |
| test-reviewer | Sonnet | Test pyramid, coverage, edge cases |
| security-reviewer | Sonnet | OWASP, supply chain, Go-specific |
| doc-reviewer | Sonnet | Documentation coherence |

Agents are thin wrappers. Workflow logic lives in 13 portable skills under `.claude/skills/`. See [`.claude/agents/README.md`](.claude/agents/README.md) for handoff conditions and scratch directory lifecycle.

## Template Commands

This implementation doubles as a project template.

| Command | Purpose |
|---------|---------|
| `/seed <path>` | Push agent pipeline into a new project |
| `/harvest <path>` | Pull generic improvements back from a real project |
| `/lint-docs` | Validate documentation coherence |

## Customization After Seeding

1. Fill `docs/prd.md` with requirements
2. Fill `docs/system-design.md` with architecture
3. Add Security Context to `.claude/agents/security-reviewer.md` and `.opencode/agents/security-reviewer.md` (replace `<!-- PROJECT -->` comment)
4. Run `/lint-docs` to validate

## Structure

```
.
├── CLAUDE.md                       # Project rules (all 3 tools read this)
├── Makefile                        # Build, test, lint, ci targets
├── main.go                         # Entry point
├── internal/                       # Application packages
├── .claude/
│   ├── agents/                     # 8 Claude Code agents
│   ├── skills/                     # 13 portable skills
│   ├── templates/                  # Scratch file templates
│   └── commands/                   # seed, harvest, lint-docs
├── .opencode/agents/               # 8 OpenCode agents
├── .github/agents/                 # 8 Copilot agents
├── docs/                           # PRD, system design, ADRs
├── deploy/                         # Dockerfile
└── .scratch/                       # Agent workspace (git-ignored)
```

## More Information

- **Agent workflow and cross-tool strategy:** [`docs/specialist-agent-workflow.md`](../docs/specialist-agent-workflow.md)
- **Full agent reference:** [`.claude/agents/README.md`](.claude/agents/README.md)
- **Project instructions:** [`CLAUDE.md`](CLAUDE.md)
