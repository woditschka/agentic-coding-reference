# Java Spring Boot Reference Implementation

Agentic coding patterns applied to Spring Boot. 10 specialist agents, 23 portable skills, and a Gradle-based toolchain — configured for Claude Code, GitHub Copilot CLI, OpenCode, and Junie CLI.

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
| Gradle | 9.6.1 |
| Spring Boot | 4.1.0 |

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
coordinator → requirements-expert → design-expert → implementer → review-planner (gray zone only) → reviewer roster (parallel) → change-grader (advisory)
```

| Agent | Model | Role |
|-------|-------|------|
| pipeline-coordinator | Sonnet | Classify requests, route to specialists |
| product-requirements-expert | Opus | Write PRD, define scope |
| system-design-expert | Opus | Validate architectural fit |
| feature-implementer | Opus | TDD implementation |
| review-planner | Sonnet | Size the review roster for gray-zone changes |
| code-quality-reviewer | Sonnet | Java/Spring Boot conventions |
| test-reviewer | Sonnet | JUnit 5, AssertJ, no-mocks policy |
| security-reviewer | Opus | OWASP, dependency scanning |
| doc-reviewer | Sonnet | Documentation coherence |
| change-grader | Opus | Advisory grade: how much human attention the passing change deserves |

Agents are thin wrappers. Workflow logic lives in portable skills under `.claude/skills/`. See [`.claude/agents/README.md`](.claude/agents/README.md) for handoff conditions and scratch directory lifecycle.

## Template Skills

This implementation doubles as a project template. Materializing and harvesting run from the monorepo root, which auto-detects the target's stack — see the [Adoption Guide](../../docs/adoption-guide.md).

| Skill | Purpose |
|---------|---------|
| `/materialize <path>` (root) | Push agent pipeline into a new project (init) or raise the bar on an existing one (upgrade) |
| `/harvest <path>` (root) | Pull generic improvements back from a real project |

## Customization After Materializing

1. Fill `docs/prd.md` with requirements
2. Fill `docs/system-design.md` with architecture
3. Add Security Context to the `security-reviewer` agent for each tool you use — `.claude/agents/security-reviewer.md`, `.github/agents/security-reviewer.agent.md`, `.opencode/agents/security-reviewer.md`, `.junie/agents/security-reviewer.md` (replace `<!-- PROJECT -->` comment)
4. Run the `doctor` skill (blocking) and `/audit-agents` to validate

## Structure

```
.
├── CLAUDE.md                       # Project rules (all 4 tools read this)
├── build.gradle                    # Gradle build with Spring Boot plugin
├── src/main/                       # Production code
├── src/test/                       # Test code
├── scripts/                        # Harness tooling (handoff log access, change-grader extractor)
├── .claude/
│   ├── agents/                     # 9 Claude Code agents
│   ├── skills/                     # Portable skills (incl. doctor, audit-agents)
│   └── templates/                  # Scratch file templates
├── .github/agents/                 # 9 Copilot agents
├── .opencode/agents/               # 9 OpenCode agents
├── .junie/agents/                  # 9 Junie agents
├── docs/                           # Project-owned briefs: PRD, system design, ADRs, vocabulary, testing + architecture principles
└── .scratch/                       # Agent workspace (git-ignored)
```

## More Information

- **Agent harness overview (loops, agents, handoff contract):** [`.claude/skills/handoff-routing/agentic-harness.md`](.claude/skills/handoff-routing/agentic-harness.md)
- **Full agent reference:** [`.claude/agents/README.md`](.claude/agents/README.md)
- **Project instructions:** [`CLAUDE.md`](CLAUDE.md)
