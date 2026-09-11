# Retire the Junie Target

**Status:** Accepted

## Context

The reference maintains one base agent body per agent and a mirror per secondary tool. Junie CLI was one of three secondary targets. Its surface was a hand-owned mirror frontmatter per agent per stack, a `.junie/config.json` pointing the tool at `CLAUDE.md` and the skills, a plugin per stack, and a column in every cross-tool table. None of it is exercised. The maintainer runs Claude Code, the eval bench measures the Spring Boot plugin under Claude Code, and no sweep or manual run has driven a Junie mirror since the effort ladder landed. An unverified surface still costs a render, a parity gate, a frontmatter vocabulary, a plugin build, and a sentence in every doc that counts the tools.

## Options Considered

1. **Keep the target and mark it unverified.** Rejected: a documented-but-untested mirror invites a consumer to trust frontmatter nobody has run.
2. **Keep the config file only, drop the agents.** Rejected: a half surface fails the layout invariants and the doctor's roster check, and the config alone delivers nothing.
3. **Retire the target entirely** (chosen).

## Decision

**Junie CLI is no longer a tool target.** Removed: the registry row, the `.junie/` runtime surface in core and every stack, the config file, and the three `agent-team-<stack>-junie` plugins. Removed with them: the `junie-cli` compatibility value, the reviewer tool-dir mapping, the frontmatter vocabulary, the variant `reasoningLevel` gate, and the tool's column in every cross-tool table. The supported tools are Claude Code, Copilot CLI, and OpenCode; two of them read the plugin format.

## Consequences

**Positive:** one fewer hand-owned frontmatter set per agent, one fewer plugin per stack, and every cross-tool count states what the bench verifies.

**Negative:** a consumer that installed the Junie surface keeps working until its next upgrade. `.junie/` is a retired path. On the copy and manifest channels the next materialize reports the leftover tree as a retired orphan, and the `/materialize` skill removes it. On the marketplace channel the setup reports it for removal by hand, since the pruner deletes only inside the engine sliver. A layout declaring `tools = [..., "junie"]` is rejected by init and materialize with the valid list. The effort-variant gate keeps only the `.claude` pin's assertion; the mirrors carry no effort knob. A consumer that wants Junie keeps the last release that shipped it.

## Implementation

The registry row and the `.junie/` trees are deleted. The doctor's runtime paths, `doctor-expectations.toml`, the init `.gitignore` block, and `planner.py`'s trust surface lose their entries. The sync checks lose the Junie gate and gain a skill-compatibility gate against the registry. `package-marketplace.py`, `render-agent-mirrors.py`, the skill compatibility lists, the layout skeletons, and the cross-tool docs count three tools. `retired-paths.txt` gains `.junie/`, and materialize scans retired directories for orphans.

## References

- [2026-06-13 extensions-and-tool-surfaces](2026-06-13-extensions-and-tool-surfaces.md): the `tools` key this decision narrows.
- [2026-07-03 rendered-agent-mirror-bodies](2026-07-03-rendered-agent-mirror-bodies.md): the mirror contract, now two mirrors.
- [2026-06-14 marketplace-plugin-channel](2026-06-14-marketplace-plugin-channel.md): the plugin fan-out, now two plugin targets.
