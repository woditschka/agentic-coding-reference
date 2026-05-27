# Java Spring Boot Reference Implementation

Agentic coding patterns applied to Spring Boot. 8 specialist agents, 18 portable skills, and a Gradle-based toolchain — configured for Claude Code, GitHub Copilot CLI, OpenCode, and Junie CLI.

## Build and Test

```bash
./gradlew build              # Build project
./gradlew test               # Run all tests
./gradlew checkJavaFormat    # Verify formatting
./gradlew formatJava         # Auto-format with google-java-format
```

## Toolchain

| Tool | Version |
|------|---------|
| Java | 25 |
| Gradle | 9.5.0 |
| Spring Boot | 4.0.6 |

## Use with an Agent

Open this directory in your agent tool. Configuration loads automatically.

```bash
claude          # Claude Code
copilot         # Copilot CLI
opencode        # OpenCode
junie           # Junie CLI
```

Start a feature: *"Add a health check endpoint."* The pipeline coordinator reads `.scratch/` state and routes to the correct specialist.

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
| code-quality-reviewer | Sonnet | Java/Spring Boot conventions |
| test-reviewer | Sonnet | JUnit 5, AssertJ, no-mocks policy |
| security-reviewer | Sonnet | OWASP, dependency scanning |
| doc-reviewer | Sonnet | Documentation coherence |

Agents are thin wrappers. Workflow logic lives in portable skills under `.claude/skills/`. See [`.claude/agents/README.md`](.claude/agents/README.md) for handoff conditions and scratch directory lifecycle.

## Template Skills

This implementation doubles as a project template.

| Skill | Purpose |
|---------|---------|
| `/seed <path>` | Push agent pipeline into a new project (init) or raise the bar on an existing one (upgrade) |
| `/harvest <path>` | Pull generic improvements back from a real project |
| `/lint-docs` | Validate documentation coherence |

## Customization After Seeding

1. Fill `docs/prd.md` with requirements
2. Fill `docs/system-design.md` with architecture
3. Add Security Context to the `security-reviewer` agent for each tool you use — `.claude/agents/security-reviewer.md`, `.github/agents/security-reviewer.agent.md`, `.opencode/agents/security-reviewer.md`, `.junie/agents/security-reviewer.md` (replace `<!-- PROJECT -->` comment)
4. Run `/lint-docs` to validate

## Structure

```
.
├── CLAUDE.md                       # Project rules (all 4 tools read this)
├── build.gradle                    # Gradle build with Spring Boot plugin
├── src/main/                       # Production code
├── src/test/                       # Test code
├── .claude/
│   ├── agents/                     # 8 Claude Code agents
│   ├── skills/                     # Portable skills (incl. seed, harvest, lint-docs)
│   └── templates/                  # Scratch file templates
├── .github/agents/                 # 8 Copilot agents
├── .opencode/agents/               # 8 OpenCode agents
├── .junie/agents/                  # 8 Junie agents
├── docs/                           # PRD, system design, ADRs
└── .scratch/                       # Agent workspace (git-ignored)
```

## More Information

- **Agent harness overview (loops, agents, handoff contract):** [`docs/agentic-harness.md`](docs/agentic-harness.md)
- **Full agent reference:** [`.claude/agents/README.md`](.claude/agents/README.md)
- **Project instructions:** [`CLAUDE.md`](CLAUDE.md)
