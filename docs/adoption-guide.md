# Adoption Guide

How to run this harness in your own project: onboarding, upgrading, the ownership contract, the distribution channels, and the optional tooling around the pipeline. The [README](../README.md) carries the concepts and the pitch; this guide carries the procedures. Every command runs from a clone of this reference unless noted.

## Adopt in Your Own Project

The monorepo root ships skills that form a bidirectional loop between this reference and real projects. They run from the root in Claude Code and detect the stack from the target's build marker. `go.mod` picks Go, `pom.xml` or `build.gradle` picks Spring Boot, and any other technology falls back to the generic stack (bind it through `scripts/stack.sh`). `/materialize` runs reference → your project; `/harvest` runs the opposite direction, pulling generalizable improvements from your project back into `/harness` — language-agnostic findings land in `core/`, stack-specific ones in `stacks/<stack>/`.

`/materialize` both onboards and upgrades, because complete replacement made them the same operation: it **completely replaces** the project's harness-owned runtime with the current `/harness`. On a fresh target it scaffolds the project-owned files first (via `/init`). On an existing one it reinstalls the runtime, removes stale orphans, and preserves any skill or agent the project added — asking before it touches anything ambiguous. Project-owned files (briefs, `layout.toml`, `CLAUDE.md`) are never rewritten — except the harness-managed chapters inside `CLAUDE.md`, refreshed in place on every upgrade.

| Command | Direction | What it does |
|---------|-----------|--------------|
| `/materialize <project-path>` | Reference → your project | Detect the stack; scaffold project-owned files via `/init` if missing; **completely replace** the runtime from `/harness`; remove stale orphans; keep project extensions (ask when unsure); respect the project's declared channel; verify the installed suites; validate with the doctor. |
| `/harvest <project-path>` | Your project → reference | Diff a real project against the materialized harness. Classify each change as **harvest** (generic improvement), **skip** (domain-specific), or **ask** (ambiguous). Auto-generalize domain patterns on the way back (`REQ-DL-*` → `REQ-XX-*`, `internal/render/render.go` → `internal/example/handler.go`); route language-agnostic improvements to `core/`. |

### Onboard or upgrade: the steps

Skills run inside Claude Code, from the monorepo root, via `/skill-name <args>`. The same command onboards a new project and upgrades an existing one.

1. **Provide a build skeleton — the harness adopts a project, it never scaffolds one.** The target must already hold a build marker: `go.mod` (Go), or `pom.xml` / `build.gradle` / `build.gradle.kts` (Spring Boot). `/materialize` detects the stack from it and never generates build files. Create one with `go mod init`, `gradle init`, or Spring Initializr — or copy a `samples/` implementation as a starting template. A target with no recognized marker falls back to the **generic** stack: run `/materialize`, then bind the build in `scripts/stack.sh`.
2. **Run `/materialize <project-path>`** from the reference root. On a new target it answers two prompts — project name and description — and asks which tool surfaces to install. The channel is **not** prompted: it is detected, defaulting a greenfield target to **copy** (see [Distribution channels](#distribution-channels)).
3. **It scaffolds, installs, and validates.** A new target gets its project-owned files first (via `/init`): `CLAUDE.md`, `.claude/settings.json`, `scripts/layout.toml`, the seven `docs/` briefs, and the `.gitignore` block. Then it installs the runtime, removes stale orphans, keeps any skill or agent you added, and runs the doctor.
4. **Commit.** Under the copy channel the runtime is committed with your project; under manifest it stays gitignored.

```bash
$ cd agentic-coding-reference
$ claude

# Onboard a new project — scaffolds project files, then installs the runtime.
> /materialize ../my-service

# Upgrade an existing project — same command. Reinstalls the runtime, prunes
# orphans, keeps your own skills/agents, runs the doctor.
> /materialize ../my-existing-service

# Harvest — pull improvements from your project back into the reference.
> /harvest ../my-existing-service
```

### Options you control

Seven knobs live in the target's `scripts/layout.toml` `[harness]` table. `/init` writes the first five at onboarding; to change one later, edit the table and re-run `/materialize`.

| Option | Values | Effect |
|---|---|---|
| `channel` | `copy` *(default)* · `manifest` · `marketplace` | Whether the runtime is committed, gitignored, or shipped as a plugin. Detected on onboarding (marketplace is declaration-only); switching is manual ([Distribution channels](#distribution-channels)). |
| `tools` | `claude` (always on) + any of `copilot`, `opencode`, `junie` | Which AI-tool agent surfaces are installed. `/materialize` installs only these and never adds one on upgrade. |
| `extensions` | runtime-relative paths | Skills or agents you added under the runtime tree. `/materialize` keeps them, never prunes them, and the doctor leaves them tracked. |
| `extra_reviewers` | reviewer names (`*-reviewer`) | Reviewers added to the parallel review gate, on top of the mandatory four-reviewer floor. Additive only — the floor cannot be dropped. Naming, body, and extension constraints: [the API spec](harness-project-api.md#briefs-feed-agents-data-files-feed-engines). |
| `auto_grade` | `true` *(default)* · `false` | Whether the pipeline auto-dispatches the terminal, advisory change-grader after the roster approves. Semantics and the fail-open rule: [the API spec](harness-project-api.md#briefs-feed-agents-data-files-feed-engines). |
| `prd_max_words` · `system_design_max_words` | word counts | Raise the doctor's doc word ceilings (defaults 18000 and 12000); absent means the defaults. `/init` does not write them. Semantics: [the API spec](harness-project-api.md#briefs-feed-agents-data-files-feed-engines). |

One more surface, the optional `[review]` table in the same file, sizes review dispatch. `mode = "risk"` *(default)* lets a deterministic engine plan each pass's roster from the changeset; `mode = "always-full"` reproduces the unconditional full battery. `size_threshold` and the `docs`/`config` surface globs tune the risk ladder; an absent table uses the engine defaults, and anything unclassifiable fails closed to the full roster. Mechanics and rationale: [Risk-Proportional Review Dispatch](adr/2026-07-09-risk-proportional-review.md).

### Customize after onboarding

The scaffolded files are yours to fill — `/materialize` never rewrites them on upgrade (the one exception: the harness-managed `CLAUDE.md` chapters, refreshed deterministically). Run **`/audit-docs`** to check the content: it runs the structural doctor first, then the advisory judgment review, and reports both. See [The Harness–Project Contract](#the-harnessproject-contract) for the ownership split.

1. **Fill the four structure-only briefs** — `docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`, and `docs/adr/` carry your requirements, architecture, vocabulary, and decisions.
2. **Tune the three house-default briefs if your rules differ** — `docs/testing-principles.md`, `docs/architecture-principles.md`, and `docs/security-principles.md` arrive filled with the harness's default policy and work as-is. They are the extension points for testing, architecture, and security principles: change them here when your project's rules differ from the defaults.
3. **Fill the Security Context** in `docs/system-design.md` — the security-reviewer reads the project's security profile from the brief.
4. **Adjust `scripts/layout.toml`** — set the module-derivation rules and `prod_roots` to your package layout. Classify generated sources deliberately. Code generated from external API models (OpenAPI, protobuf) matches neither `test` nor `prod_roots`, so it falls to kind "unknown" and flows to concern in the grader. Exclude it from `prod_roots`, or give it its own module rule if you track it.
5. **Run `/audit-docs`** once the briefs have content — it runs the doctor (structure) then the judgment review, auditing each doc on its own and against the others.

Improvements discovered while shipping real features flow back into the template via `/harvest`. Template improvements flow out to every downstream project via `/materialize`. Neither direction overwrites domain work.

## The Harness–Project Contract

The dependency runs both ways. Agents enforce a project's briefs as their own convictions, so a vague or self-contradicting brief degrades every dispatch that reads it. The project, in turn, accumulates truth no upgrade may clobber: requirements, decisions, policies. The boundary that protects both is a versioned API — [`harness-project-api.md`](harness-project-api.md), spec 0.1.0 — not a convention. Why an API rather than shared documents: [the docs-as-API ADR](adr/2026-06-12-docs-as-harness-project-api.md).

The API is an **open–closed boundary**. The opinionated core is closed: a project never edits it, and an upgrade replaces it wholesale. The project extends from outside instead — rewriting the three house-default briefs to its own testing, design, and security philosophy, adding its own skills and agents, and selecting its tool surfaces. Each extension is a declaration the project owns, so an upgrade refreshes the core without ever colliding with it. This is what keeps the harness maintainable across many consumers: one source evolves, and no project forks it to specialize.

A project owns seven briefs under `docs/`. Four arrive as structure only — `prd.md`, `system-design.md`, `adr/`, `ubiquitous-language.md` — their content is yours from the first line. Three arrive as filled defaults carrying the harness's house policy — `testing-principles.md`, `architecture-principles.md`, `security-principles.md` — the **adaptation points** a project rewrites to its own philosophy. The full roster and owning agents are specified in [`harness-project-api.md` § File Roster](harness-project-api.md#file-roster); each brief's required sections follow it there.

A rewritten default is policy, not drift. The three defaults open by naming what the project may rewrite and what is kernel-fixed. The harness materializes a missing brief from its template and never writes an existing one.

Upgrades replace only the runtime: skills, agents, hooks, schemas, scripts. A project that needs its own skill or agent declares it in `[harness] extensions`. The harness keeps it beside its own runtime and never prunes it on upgrade — the runtime-side counterpart of a rewritten brief.

That runtime executes on your machine: the `scripts/*.py` engines and the `.claude/hooks/*.py` that fire on your tool calls. What it carries, and what checks it, is part of the contract.

It carries **no third-party dependencies**. Every import resolves to the Python standard library or a module in the same directory, and it ships no dependency manifest. A battery step enforces both, so the claim cannot go quietly stale. A CI workflow runs that battery on every push to `main` and every pull request. At install, `/materialize` runs the vendored suites it just copied and fails loudly when one breaks.

Each check bounds what it guards: [materialize-time verification](adr/2026-07-13-materialize-time-runtime-verification.md) states its own limits. None of it replaces your own evaluation; the [Disclaimer](../README.md#disclaimer) and the [MIT License](../LICENSE) govern use.

Underneath the briefs, four disciplines are kernel — TDD-first, strategic DDD, spec-driven delivery, and the form contract — fixed because the machinery breaks without them. What each fixes, what stays project-owned, and the admission test are specified in [`harness-project-api.md` § The Kernel](harness-project-api.md#the-kernel--what-no-brief-can-vary).

### The architecture default

`architecture-principles.md` ships an opinionated default: the domain core is the fixed point, infrastructure a swappable boundary around it. A request crosses four layers in one direction:

1. **UI / API** — carries its own request/response model; an anti-corruption mapper translates it to and from the domain, which never sees the external shape.
2. **Application (service)** — owns the transaction boundary: it loads aggregates through repositories or external services, calls the domain to run the business logic, then persists the result. No business logic lives here.
3. **Domain core** — entities and value objects inside aggregates, reached only through the aggregate root; the business logic runs here.
4. **Repository / external services** — load, persist, and reach other systems behind an anti-corruption mapper — unless the project owns both ends and persistence tracks the model closely, where the model may be mapped directly.

Persistence is a spectrum — event-sourced to direct mapping — with the default catalog in the shipped brief itself. The five closed protections are owned by [`ddd-principles.md` § Properties Are Kernel](ddd-principles.md#properties-are-kernel-patterns-are-brief-variable); everything outside them — mapping mechanism, ACL implementation, persistence ideology, annotation policy — is adapted by editing that one brief. Rationale and the open–closed decision: [`ddd-principles.md`](ddd-principles.md) and [its ADR](adr/2026-06-26-ddd-open-closed.md).

Enforcement follows the same ownership split. The `doctor` skill is deterministic and blocking. It checks all seven briefs present, required sections and numeric slots filled, the reviewer-roster floor intact, and no harness-owned handbook docs left in `docs/` — stdlib Python, CI-runnable. It verifies structure, never your choices. The `audit-docs` skill is the human-facing entry point: it runs the doctor first, then adds the judgment and advisory pass. That pass asks whether your principles are enforceable, contradiction-free, and carry their rationale — each on its own and against the others. It can question a policy; it cannot override one. It is also how harness evolution reaches a project-owned file: a new expectation arrives as a finding with an offered draft, applied only on your consent — never as a write.

Facts enforced by judgment live in briefs; facts consumed by deterministic engines live in `scripts/layout.toml` — test file globs, the test-name regex, and the `[harness]` table's channel, tool surfaces, and declared extensions. Each skill declares the briefs it reads in frontmatter; the doctor audits those declarations against the expectations manifest.

### Distribution channels

The contract holds on every distribution channel; only the delivery of the runtime differs, and the project-owned files stay committed on all of them.

<p align="center">
  <img src="images/harness-lifecycle.drawio.png" width="720" alt="One /harness source fans into three channels — copy, manifest, and per-stack-per-tool marketplace plugins — feeding a consumer project, with a harvest return path back to the source.">
</p>

| Channel | Runtime delivery | Git state | When |
|---|---|---|---|
| **Copy** *(default)* | committed into the project | runtime tracked | The default. Self-contained, version-controlled, diffable in code review — the mode all three samples use. |
| **Manifest** | materialized from the `/harness` source into the project's native tool locations | runtime gitignored, doctor-enforced untracked | Opt in to keep the repo lean and pin the runtime to a single source. |
| **Marketplace** | tool surfaces (skills, agents, hooks) ship as a plugin; the plugin bundles the engine sliver (scripts, schemas, templates) and a `marketplace-setup` skill installs it project-side | runtime gitignored, doctor-enforced untracked | `harness/package-marketplace.py` renders the runtime into per-tool plugins under one `.claude-plugin/marketplace.json`. Read by Claude Code, Copilot CLI, and Junie CLI. |

`/init` **resolves the channel — it does not prompt.** It uses what is already declared in `[harness] channel`; failing that, it infers from git state (a runtime that is committed → copy, gitignored → manifest); a greenfield target defaults to **copy**. `/materialize` then respects whatever is declared and never flips it.

**Switching is manual** and rare:

- **copy → manifest:** set `[harness] channel = "manifest"`, append the runtime block from `harness/init/core/gitignore-runtime.txt` to `.gitignore`, then untrack the now-ignored runtime: `git rm -r --cached --ignore-unmatch <runtime paths>`.
- **manifest → copy:** set `[harness] channel = "copy"`, remove that runtime block from `.gitignore` (keep `.scratch/`), then `git add` the runtime and commit.

**Installing from the marketplace.** The reference repo *is* the marketplace — one root `.claude-plugin/marketplace.json` listing one plugin per (stack, tool): `go-claude`, `go-copilot`, `go-junie`, `spring-boot-claude`, `spring-boot-copilot`, `spring-boot-junie`, `generic-claude`, `generic-copilot`, `generic-junie`. A consumer adds it, installs the plugin for their stack and tool, restarts, then runs the one-time engine setup:

```bash
claude plugin marketplace add woditschka/agentic-coding-reference   # or a local clone path
claude plugin install go-claude@agentic-harness
# restart your tool — plugin skills load at session start
/go-claude:marketplace-setup                                     # namespaced by the plugin
```

Plugin skills and commands are **namespaced by the plugin name** — a consumer types `/go-claude:…`, not `/…`. Only user-typed entry points carry the prefix; the pipeline's own agent-to-agent skill use is by intent, so the namespace stays internal. The skill and agent bodies never hardcode a prefix (the source is shared across all plugins); `harness/test-marketplace.sh` enforces that. The `marketplace-setup` skill installs the engine sliver project-side and gitignores it. Project-owned files come from `/init`, which runs from a clone of the reference — the plugin does not ship it.

All three samples are consumers of their own harness on the copy channel and pass their own doctor.

## Pipeline Maintenance

One pattern keeps the pipeline healthy between features: `doc-sync` detects and fixes drift between `docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`, and the codebase after features merge. Run it after implementing features, before starting a new cycle, or periodically. The process and the change-grader's maintenance-loop inputs are in [§5 of the workflow doc](specialist-agent-workflow.md#5-pipeline-maintenance-patterns).

## JetBrains Semantic Oracle

Optional tooling that connects a JetBrains IDE's MCP server to the agent as a **read-only semantic oracle and verifier** — IntelliJ IDEA for the Java sample, GoLand for the Go sample. The motivation is grounding. An agent reasons over text, so it answers semantic questions from its priors — plausible guesses that need not match this codebase. *What does this name resolve to? Where is it really used? Does this wire up? Does the edit compile?* The oracle replaces the guess with the IDE's computed answer.

What the agent gains, ordered by how firmly each holds:

| Gain | What it means |
|------|---------------|
| **Grounded information** | Answers come from the IDE's resolved model of *this* project: inferred types, semantic usages, the compiler's verdict, framework-aware inspections (Spring wiring, JPA, nullability in Java; vet-class, unused, shadowing in Go), and the resolved dependency graph. None of this is readable off disk — a text-only agent would have to simulate the compiler and type-checker. The agent acts on facts, not priors. |
| **Determinism** | The same code yields the same answer — a lookup, not a probabilistic judgment. |
| **Fewer detours** | A compact resolved answer can spare the agent from reading and reasoning across multiple files to reconstruct the same fact. |

The server is read-only by policy: no exposed tool mutates a file. The agent stays the sole writer, so the oracle adds a verification signal without a new failure mode. It is optional and degrades cleanly. When the IDE is absent or its index is stale, every workflow falls back to native tools plus the project build — the canonical gate. The grounding is only as fresh as the IDE's index, so a one-command health check (`intellij-idea-doctor` for Java, `goland-doctor` for Go) guards against trusting a stale model.

Today the oracle is wired and working for Claude Code and wired for Copilot CLI (gated by an upstream bug). Junie CLI runs in headless mode on the native baseline; OpenCode is the next wiring target. The Go and Java samples demonstrate it — IntelliJ IDEA in the Java Spring Boot sample, GoLand in the Go sample. See [`samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md`](../samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md) and [`samples/go/.claude/skills/goland/goland-mcp-integration.md`](../samples/go/.claude/skills/goland/goland-mcp-integration.md) for the exposed tool set, the exposure policy, setup, and per-client status.

**Consider it if** your agents work in an IDE-backed language and you want a grounded, deterministic check in the loop. The pattern transfers to any editor exposing an MCP server; the Go and Java samples are instances.

## Harness Stats

Running a constellation of specialists has a cost the chat UI does not surface. How many tokens are flowing? Is the prompt cache amortizing the repeated specialist fires? Which subagent is about to hit its tool ceiling and truncate? Harness Stats makes it visible — a live statusline on every turn and an on-demand per-agent report. This is the feedback loop turned on the harness itself: the instrument for the cost-effectiveness question the README raises up front.

A statusline mid-fan-out, with agent teams enabled (project shown as `sample`):

```text
sample ⎇ main │ opus ▤ 47% │ Σ ▲4.2M ▼91k $11.40 │ ⛁ 95% ⊖3.9M ⊕210k $84% │ ⇲ 12 context7·8 │ ⇉ 3 │ ⟳ 9 │ ↺ doc-reviewer ⊕9k ⚒18 ⟳2 │ ↗ feature-implementer ⚒54 ⟳7
```

Read left to right:

- Project directory and git branch.
- Parent model and context-window usage (`▤`), color-coded as it fills.
- Session totals (`Σ`) — input (`▲`), output (`▼`), and list-price API cost (`$`), summed across the parent and every subagent.
- Cache (`⛁`) — hit rate, tokens read (`⊖`) versus written (`⊕`), and spend change versus uncached (`$%`).
- MCP usage (`⇲`) — total calls and the busiest server, shown only when the session calls MCP.
- Parallel fan-out (`⇉`) — subagents active in the last 5 minutes (a 3-wide burst of one agent type reads as `⇉ 3`).
- Continuation total (`⟳`) — session-wide accepted re-engagements, shown only when agent teams is on.
- Last turn (`↺`) and any at-risk hot agent (`↗`) — agent name, cache writes (`⊕`), cumulative tool count (`⚒`), and continues (`⟳`) when agent teams re-engages it.

A subagent nearing the SDK's per-invocation tool ceiling turns its `⚒` count yellow then red, with a `⚠` when it hits — unless agent teams is actively re-engaging it (`⟳`), in which case the count is coordinator-driven and the alarm is suppressed. The on-demand `cache-report` breaks the same figures down per agent — runs, warm-start %, net savings % — exposing which specialists pay for their cache writes and which fire too sporadically to amortize.

| Skill | Purpose |
|-------|---------|
| `harness-stats-setup` | Install or update the tooling. Detects drift between this repo and `~/.claude/`, applies on approval, merges the `statusLine` block into `~/.claude/settings.json` without clobbering other keys. |
| `cache-report` | Run the per-agent report on demand (installed by the setup skill). |

See [`tools/harness-stats/README.md`](../tools/harness-stats/README.md) for the full cell reference, metric formulas, and platform support.

## Claude Pod

Long autonomous runs want Claude Code's permission prompts off (`--dangerously-skip-permissions`); the trade is an agent that can touch anything you can. Claude Pod confines the session in a disposable Linux container that sees the project directory, your shared `~/.claude` (read-write), and read-only git config — nothing else of the host. Credentials stay pod-private — one `/login` inside the pod, persisted outside `~/.claude`. The image bakes the toolchains the samples build with (JDK 25, Node 24, current Go).

```bash
tools/claude-pod/install.sh   # command -> ~/.local/bin/claude-pod
claude-pod                    # from a project directory: builds the image once, then runs confined
```

| Skill | Purpose |
|-------|---------|
| `claude-pod-setup` | Install or update the tooling. Runs the installer's check mode, shows drift, applies on approval; never overwrites your `claude-pod.cfg`. |

**Consider it if** you run the pipeline unattended and want the permission gates off without handing an autonomous agent your host. See [`tools/claude-pod/README.md`](../tools/claude-pod/README.md) for the security model, mount and network flags, and platform support.
