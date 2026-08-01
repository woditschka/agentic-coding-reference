# All Plugins Share One Skill Namespace: agent-team

**Status:** Accepted

## Context

The marketplace channel's first external consumer test (spring-petclinic, marketplace channel from GitHub) surfaced a naming complaint: the typed prefix `/spring-boot-claude:doctor` names the packaging, not the addressee. The [2026-06-14 decision](2026-06-14-marketplace-plugin-channel.md) made the plugin name the namespace because one manifest needs nine unique names; a shared short name appeared to force nine repos.

Live-doc verification dissolved that constraint. Claude Code reads two distinct names: the marketplace *entry* name keys installs and `enabledPlugins`, while the plugin.json `name` namespaces components. The two may differ; the plugin manager supports differing names since Claude Code v2.1.195. Install scope is a user-global cache keyed by entry name and version, so side-by-side installs of two stacks' plugins stay distinct on disk.

## Options Considered

1. **Keep `<stack>-<tool>` as the namespace.** Rejected: the prefix is packaging metadata, up to 18 characters (`spring-boot-claude`); the consumer complaint stands.
2. **Drop the tool suffix for Claude plugins (`/spring-boot:doctor`).** Rejected: shorter but still names the stack, not the thing the consumer addresses.
3. **One merged multi-stack plugin.** Rejected: a real redesign of stack delivery for a naming problem the two-name split solves for free.
4. **Share the marketplace name `agentic-harness` as the namespace.** Rejected: it names the distribution artifact, not the actors; the consumer complaint was exactly that the prefix names packaging.
5. **Shared plugin.json name `agent-team`; entry names lead with it.** Accepted.

## Decision

**Every plugin's plugin.json `name` is `agent-team`; marketplace entry names lead with it — `agent-team-<stack>` for Claude Code, `agent-team-<stack>-<tool>` for Copilot and Junie.**

- `agent-team` names the addressee: the specialist agent team — coordinator, experts, implementer, reviewer roster — that executes the request. The prefix reads as directed speech: `/agent-team:new-feature`, `/agent-team:ship`.
- The name does **not** reference Claude Code's experimental agent-teams capability. The harness confines that feature to the bare-`continue` resume ([2026-06-10](2026-06-10-continue-only-resume.md)); coordination stays file-based. The prefix works identically for Copilot and Junie plugins, which have no such capability.
- The canonical constant is `registry.PLUGIN_NAMESPACE`. The renderer stamps it into plugin.json, the `marketplace-setup` skill (`{{PLUGIN_NAMESPACE}}`), and the entry names. `test-marketplace.sh` asserts every plugin.json carries it, the entry set matches the roster-derived scheme, the rendered setup skill contains the substituted invocation, and the adoption guide states the same typed literal — the docs are the independent oracle against a silent constant edit.
- Entry names key installs (`agent-team-spring-boot@agentic-harness`), cache directories, and `enabledPlugins`. Claude — the primary target — drops the tool suffix; the stack token stays, because nine plugins in one manifest need nine unique names and the entry is how a consumer picks the stack and tool.
- The shared prefix collides only when two plugins are *enabled* in one session. Enabling one harness plugin per project is the supported configuration; two at once shadow each other's skills.
- The namespace-safety invariant widens: shared bodies may hardcode neither an entry-name prefix nor `agent-team:` — bodies stay channel-neutral (a copy-channel consumer has no prefix at all).

## Consequences

**Positive:**
- Every consumer types the same prefix regardless of stack and tool; docs can state one invocation form.
- The prefix names the team a consumer addresses, not the packaging.

**Negative:**
- An installed consumer's names move on update. The typed prefix `/<entry>:…` stops resolving in favor of `/agent-team:…`, and the old entry (`spring-boot-claude@agentic-harness`) stops matching the manifest — uninstall it, install the new entry, move any committed `enabledPlugins` key. The adoption guide's upgrade section and the setup skill's upgrade note both state the procedure.
- The two-name split is verified for Claude Code only. How Copilot and Junie handle nine manifests sharing one plugin.json name is an open residual — no deterministic gate covers it.
- The release carrying this change must ship before consumer docs advertise the new prefix; a pre-release cache and the docs would otherwise disagree at the same version stamp.

## Amendment (2026-08-01): The marketplace registers as agent-team

Same-day revision after the first install under the new scheme. The install key read `agent-team-spring-boot@agentic-harness` — two brands in one identifier. The marketplace manifest `name` now comes from `registry.PLUGIN_NAMESPACE`, so the marketplace registers as `agent-team` and the key reads `agent-team-spring-boot@agent-team`.

This does not revisit rejected option 4, which ran the dependency the other way: deriving the namespace *from* the marketplace name would have kept a packaging label as the prefix. Here the namespace stays the source; the marketplace follows it. One name now covers marketplace, entries, and prefix.

Cost: a consumer registered under `agentic-harness` migrates once — remove the old marketplace registration, re-add the repo (it registers as `agent-team`), reinstall the entry, move any `extraKnownMarketplaces` and `enabledPlugins` keys. The adoption guide's upgrade note and the setup skill state the procedure.

## References

- [2026-06-14-marketplace-plugin-channel](2026-06-14-marketplace-plugin-channel.md) — the decision this ADR amends; carries the matching amendment note.
- [2026-06-17-generic-stack-verb-contract](2026-06-17-generic-stack-verb-contract.md) — raised the plugin count to nine.
- [2026-06-10-continue-only-resume](2026-06-10-continue-only-resume.md) — why the name must not be read as the agent-teams capability.
- [Adoption guide § Distribution channels](../adoption-guide.md#distribution-channels) — the consumer-facing statement of the two-name model.
