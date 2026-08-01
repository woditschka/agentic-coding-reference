# The Marketplace Channel: Per-Tool Plugins, Project-Owned Engines

**Status:** Accepted (plugin count and namespace since amended; see notes)

> **Amended.** The generic stack ([2026-06-17-generic-stack-verb-contract](2026-06-17-generic-stack-verb-contract.md)) raised the plugin count from six to nine — three stacks × three plugin-capable tools. Every "six" below reads as nine; the channel contract is unchanged.

> **Amended.** [2026-08-01-shared-plugin-namespace](2026-08-01-shared-plugin-namespace.md) splits the two names this ADR fused: every plugin.json `name` — and so the typed prefix — is the shared `agent-team`, and the marketplace entry names lead with it: `agent-team-<stack>` (Claude) and `agent-team-<stack>-<tool>` (Copilot, Junie). Two bullets below read accordingly: "The plugin name *is* the slash namespace" no longer holds, and the no-hardcoded-prefix rationale ("each with a different prefix") rests on channel-neutrality now — bodies may hardcode neither an entry-name prefix nor the shared one, since copy-channel consumers have no prefix at all. The renderer fills the `marketplace-setup` invocation from one constant, no longer per plugin.

## Context

Two prerequisites landed first: a [decoupled artifact version](2026-06-14-decoupled-artifact-version.md) and [layout-sourced schema patterns](2026-06-14-layout-sourced-schema-patterns.md). The `marketplace` channel was named in the spec and enforced by the doctor's untracked-runtime invariant, but it was inoperable. `init.sh` rejected it; `materialize.sh` was channel-blind and would copy the full runtime into the tree, which the doctor then fails.

Live-doc verification reshaped the design. Claude Code, Copilot CLI, and Junie CLI all read the `.claude-plugin/marketplace.json` format — so one marketplace can serve three of the four tools. OpenCode uses a different model and is excluded. Agent files differ per tool: Claude `agents/*.md`, Copilot `agents/*.agent.md`, Junie `agents/*.md` with its own frontmatter. Claude and Junie collide on `*.md`.

## Decision

**The marketplace channel delivers tool surfaces as per-tool plugins and keeps engines project-owned.**

- **It is a real, declarable channel.** `init.sh` accepts `marketplace` and gitignores the runtime like `manifest`. `materialize.sh` has a marketplace branch. The doctor's untracked invariant already covers it.
- **Per-tool plugins under one marketplace.** The agent disparity is solved by separation, not fusion — the harness already keeps a per-tool agent directory. Each tool installs the plugin named for it; one marketplace lists them. No collision.
- **One root marketplace; the plugin name is the namespace.** `marketplace add owner/repo` reads `.claude-plugin/marketplace.json` at the repo root *only* — it does not discover subdirectory marketplaces. So GitHub distribution requires a single root manifest, which in turn requires distinct plugin names (six in one manifest must be unique). Names are `<stack>-<tool>` with `java-spring-boot` shortened to `spring-boot` for a terser prefix: `go-claude`, `spring-boot-junie`. A bare `agentic-harness` name for all would force six separate repos; not worth it. The plugin name *is* the slash namespace a consumer types: `/go-claude:marketplace-setup`. Only user-typed entry points carry it; the pipeline's agent-to-agent skill use is by intent, so the prefix stays internal.
- **The shared source carries no plugin prefix — enforced.** One source renders all six plugins, each with a different prefix, so a baked-in `go-claude:` would be wrong for the other five. Bodies name skills in channel-neutral shorthand (`/next`, the `tdd-workflow` skill) that the model resolves to the installed skill; none carry a `<plugin>:` prefix. The lone substitution is the user-typed `marketplace-setup` skill, whose namespaced invocation the renderer fills per plugin. `harness/test-marketplace.sh` asserts no other body hardcodes a prefix.
- **Engines stay project-owned — the boundary.** The plugin delivers the tool-discovered surfaces (skills, agents, hooks). The engine sliver (scripts, schemas, templates, tool config) materializes project-side at project-relative paths. A plugin installs to a tool-specific cache reachable only through a tool-specific variable (`${CLAUDE_PLUGIN_ROOT}`); project-relative paths resolve identically for every tool. Keeping engines project-side preserves the cross-tool guarantee and needs no agent-file rewrites.
- **One lockstep version, forward-only.** `harness/VERSION` stamps every plugin; the marketplace ships as one versioned release. The plugins are projections of one shared source, so independent versioning would be fiction. Releases move forward; a `v<VERSION>` git tag preserves reproducibility and a manual rollback path.

## Consequences

**Positive:**
- The channel is operable on the consumer side; declaring `marketplace` no longer contradicts `init`.
- The cross-tool identity holds — three of four tools share one marketplace, engines resolve uniformly.
- Engine invocation is unchanged from copy/manifest; no agent rewrites.

**Negative:**
- A marketplace consumer still materializes a small engine sliver (~13 files), so the channel is not zero-runtime.
- OpenCode is out of scope for this channel; it stays on copy or manifest.

## Notes

This ADR covers the channel contract and consumer-side delivery; it was landed first. The producer side now realizes the design: `harness/package-marketplace.sh` renders `core ∪ stack` into per-tool plugins under one repo-root `.claude-plugin/marketplace.json`, stamped with `harness/VERSION`. The render is deterministic and `check-sync.sh` guards the committed marketplace against drift. The doctor relocation it depended on is [its own ADR](2026-06-14-doctor-engine-in-scripts.md).

**Engine delivery to a plugin consumer.** A plugin manager installs to a read-only cache and cannot write the project, yet the skills call engines by project-relative path. So each plugin bundles its engine payload under `_engine/` and ships a `marketplace-setup` skill: run once, it installs the engines into the project and gitignores them (the untracked invariant). The runtime path stays project-relative — only this one-time install uses the plugin-root variable, in a skill shell block. Project-owned files (`CLAUDE.md`, `layout.toml`, briefs) remain the consumer's, scaffolded by `init`. Plugin skills load at session start, so a consumer restarts the tool after installing before invoking the namespaced setup skill.

**What the release gate proves, and what it cannot.** Two tests in `check-sync.sh` cover the channel. `harness/test-marketplace.sh` is the dependency-free acceptance test. It checks manifest and `plugin.json` integrity, the namespace-safety invariant, and an install *simulation* for a Go and a Spring plugin. The simulation runs `init` on the marketplace channel and the bundled `setup.sh`, then asserts the doctor's untracked invariant and a live `handoff.py` validation. `harness/test-plugin-install.sh` then drives the *actual* `claude plugin marketplace add` + `install` CLI against the repo as a local marketplace. It runs under a throwaway `HOME`, so it never touches the user's real plugin state — the CLI writes the cache to `$HOME/.claude`, ignoring `CLAUDE_CONFIG_DIR`. It asserts the installed cache carries the surfaces, engine payload, and namespaced setup skill, then runs that installed `setup.sh` end to end. It skips cleanly when the CLI is absent; Claude Code is the channel's primary target, so it runs on a maintainer's machine every release. One thing neither can cover without a running model and a restart: a live agent model-invoking a namespaced plugin skill inside a subagent. That stays a manual release-checklist step; the namespace-safety check is its deterministic stand-in.
