# Three Distribution Channels Deliver One Agent-Team

**Status:** Accepted

## Context

A consumer adopts the harness runtime on one of three channels. Copy commits the runtime into the repository, self-contained and diffable in review. Manifest gitignores it and materializes from a pinned source. Marketplace delivers the tool surfaces as a plugin installed to a read-only, tool-specific cache.

The plugin cache shapes the marketplace design. Claude Code and Copilot CLI read the `.claude-plugin/marketplace.json` format; OpenCode uses a different model. `marketplace add owner/repo` reads one manifest at the repository root and never discovers subdirectory marketplaces. A plugin manager cannot write the project, yet every skill calls engines by project-relative path. Claude Code reads two names: the marketplace entry keys installs and `enabledPlugins`, while the `plugin.json` name namespaces typed skills.

Three field lessons reshaped the first design. The first external marketplace consumer (spring-petclinic) found the typed prefix `/spring-boot-claude:doctor` named packaging, not the addressee. Onboarding took three sessions in two repositories because `init` lived only at the reference root. The eval backfill of 2026-08-11 found 49 of 49 security-reviewer transcripts (v0.1.1 through v0.2.4) loading Claude Code's bundled `security-review` skill instead of the harness one. A bare name resolves enterprise, personal, project, then bundled; a plugin skill wins it only when nothing above claims it. The copy channel is unaffected, so the failure ran silent for eight versions.

Three names circulate for overlapping things: the reference, the harness, and agent-team. A first-time reader met all three before meeting the thing they name.

## Options Considered

1. **Manifest as the default channel, asked on every onboard.** Rejected: both samples and the common adopter use copy; a prompt restated a decision git state already shows.
2. **One plugin name for all stacks, one repository per plugin.** Rejected: GitHub distribution needs one root manifest, so entries must be unique within it.
3. **The plugin name `<stack>-<tool>` as the typed namespace.** Rejected: up to 18 characters of packaging metadata; dropping the tool suffix (`/spring-boot:doctor`) still names the stack.
4. **One merged multi-stack plugin.** Rejected: a redesign of stack delivery for a naming problem the two-name split solves.
5. **The marketplace name `agentic-harness` as the namespace.** Rejected: it names the distribution artifact, not the actors.
6. **Bundle the engines inside the plugin and invoke them through `${CLAUDE_PLUGIN_ROOT}`.** Rejected: the variable is tool-specific; project-relative paths resolve identically for every tool.
7. **Keep `init` root-only and document the clone.** Rejected: the double-install trap (a bare `/init` infers manifest, a later `/materialize` installs the full runtime beside the plugin) survives any prose.
8. **Fold scaffolding into `marketplace-setup`.** Rejected: setup re-runs per upgrade and stays idempotent; scaffolding asks identity questions once.
9. **Namespace the frontmatter skill reference (`plugin:skill`).** Rejected: undocumented for preloading, and the copy channel has no namespace, so one body could not serve both channels.
10. **Report the bundled-skill shadowing upstream and wait.** Insufficient alone: the shipped harness must resolve on the tools consumers run today.
11. **Rename everything to agent-team, or leave the three names undeclared.** Rejected: churn across the battery and the source tree buys no clarity; an undeclared vocabulary misleads from the first paragraph.
12. **Keep Junie CLI as an unverified target, or keep only its config file.** Rejected: unrun frontmatter invites misplaced trust; a half surface fails the layout invariants.
13. **Retire the manifest channel as spent.** Rejected on 2026-08-02. The manifest channel was re-founded on 2026-06-14 as the deliberate default for a project that owns its runtime, not as a stepping stone to the marketplace.

## Decision

**Copy is the default channel, the channel is resolved rather than asked, and the marketplace channel ships per-tool plugins under the shared `agent-team` namespace with project-owned engines.**

- **Channel resolution.** A declared `[harness] channel` in `layout.toml` wins; else git state decides (runtime tracked: copy, gitignored: manifest); else a greenfield target gets copy. Only conflicting signals raise a question. `materialize` respects the declared channel and never flips it; orphan removal touches only confirmed orphan paths. Switching is a manual, documented step in both directions.
- **One artifact version, one release date.** `harness/VERSION` is the single semver source, distinct from `spec_version`, the API contract revision. Materialized targets carry the release date from `harness/VERSION-DATE` as provenance; the doctor never gates on either stamp. Releases are lockstep and forward-only; a `v<VERSION>` git tag preserves reproducibility and a manual rollback path.
- **Six plugins, one root manifest.** `package-marketplace.py` renders `core ∪ stack` into three stacks by two plugin tools (Claude Code, Copilot CLI). Every `plugin.json` name is `registry.PLUGIN_NAMESPACE`, `agent-team`; the marketplace registers under the same name. Entries are `agent-team-<stack>` for Claude Code and `agent-team-<stack>-copilot`, so an install key reads `agent-team-spring-boot@agent-team`. Enabling one harness plugin per project is the supported configuration.
- **Bodies carry no prefix.** Shared skill and agent bodies name skills in channel-neutral shorthand and hardcode neither an entry name nor `agent-team:`. The renderer fills the one typed `marketplace-setup` invocation from the constant.
- **Engines stay project-owned.** The plugin delivers skills, agents, and hooks; the engine sliver (scripts, schemas, templates) installs project-side at project-relative paths and is gitignored. Each plugin bundles the sliver under `_engine/` and the `marketplace-setup` skill installs it through one explicit Bash run of `setup.sh`, re-run after every plugin update.
- **The plugin ships its own init.** Each plugin bundles `init.py`, `registry.py`, `write_guard.py`, its stack's skeletons, and `VERSION`, plus an `init` skill pinned to the marketplace channel. Onboarding is one repository and one restart: install, `/agent-team:init`, `/agent-team:marketplace-setup`.
- **Bundled skill names are reserved.** No shipped skill preloaded by agent frontmatter carries a Claude Code bundled skill or command name; the security skill is `security-checks`. Battery check 2g compares every agent surface's `skills:` list against the pinned `CLAUDE_CODE_BUNDLED_SKILLS` roster and fails on a zero-scan.
- **Three tools, two of them plugin-capable.** The supported tools are Claude Code, Copilot CLI, and OpenCode. Junie CLI is retired: its registry row, `.junie/` surfaces, frontmatter vocabulary, and plugins are gone, and `.junie/` is a retired path the pruners report or remove.
- **One register per name.** Agent-team is the product a consumer installs and talks to, leading on the README, adoption guide, walkthrough, and marketplace. The harness is the machinery inside it: runtime, engines, schemas, the `/harness` source. The reference is this repository. No file or script is renamed; the glossary pins all three.

## Consequences

**Positive:**
- A greenfield adopter gets a committed, reviewable runtime with zero configuration and no onboarding prompt.
- Every consumer types the same `/agent-team:` prefix regardless of stack and tool, so the docs state one invocation form.
- Engine invocation is identical across channels and tools; no agent body is rewritten per channel.
- The next bundled-name collision fails the battery instead of running silent across sweeps.
- Every cross-tool count states what the eval bench verifies.

**Negative:**
- A marketplace consumer still materializes an engine sliver of about 13 files; the channel is not zero-runtime. Each plugin carries the init skeleton payload (tens of KB) and three maintainer modules in a generated second location.
- OpenCode stays on copy or manifest.
- A consumer's project-owned `docs/security-principles.md` keeps its old skill pointer until edited; materialize never rewrites briefs.
- The root-invoked `doctor` and `init` skills share bundled command names; they are never frontmatter-preloaded, and the plugin channel reaches them by typed prefix.
- The two-name split is verified for Claude Code only; how Copilot handles six manifests sharing one `plugin.json` name has no deterministic gate.
- A live model invoking a namespaced plugin skill inside a subagent stays a manual release-checklist step.

## Implementation

`harness/package-marketplace.py` renders `.claude-plugin/marketplace.json` and `plugins/`; `harness/registry.py` holds `PLUGIN_NAMESPACE`; `harness/marketplace/` holds `setup.sh`, `prune-retired.py`, and the setup and init skill sources. `harness/tests/test-marketplace.sh` checks manifest integrity, the namespace-safety invariant, and an install simulation; `harness/tests/test-plugin-install.sh` drives the real `claude plugin` CLI under a throwaway `HOME`. `harness/verify_harness/checks/sync.py` carries the bundled-skill roster; `harness/retired-paths.txt` carries `.junie/`. Channel resolution lives in `harness/init.py`; the consumer statement is the adoption guide's Distribution channels section.

## References

- [2026-06-11-materialize](2026-06-11-materialize.md) — the installer that respects the declared channel and removes orphans without flipping it.
- [2026-06-14-the-doctor](2026-06-14-the-doctor.md) — enforces the untracked-runtime invariant under manifest and marketplace and the reason engines resolve project-side.
- [2026-06-14-layout-declares-the-project](2026-06-14-layout-declares-the-project.md) — `layout.toml` holds the `[harness] channel` key, and the generic stack it added is the third plugin stack.
- [2026-06-12-docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md) — `spec_version`, the contract revision the artifact version is decoupled from.
- [2026-07-15-the-eval-bench](2026-07-15-the-eval-bench.md) — measures the Spring Boot plugin under Claude Code, the condition that surfaced the bundled-skill shadowing.
- [Adoption guide, Distribution channels](../adoption-guide.md#distribution-channels) — the consumer-facing statement of the channels, the two-name model, and the switching procedure.
- [Glossary](../glossary.md) — pins the Agent-team, Harness, and Reference entries.
