# The Project Declares What It Owns: Extensions and Tool Surfaces

**Status:** Accepted (channel default, migration, and classification since amended; see note)

> **Amended.** [2026-06-14-copy-channel-default](2026-06-14-copy-channel-default.md) made copy the default channel and the copy → manifest switch manual; the untrack step still excludes declared extensions. [2026-08-20-retired-paths-manifest](2026-08-20-retired-paths-manifest.md) demoted the orphan-vs-extension LLM heuristic to the pre-manifest fallback: manifest-listed paths classify mechanically. The `tools` and `extensions` keys stand as decided.

## Context

Migrating the real ccledger project to the manifest channel exposed two gaps in [complete-replacement materialize](2026-06-13-materialize-complete-replacement.md), both rooted in the same wrong assumption: that the runtime tree is *entirely* harness-owned.

1. **Extensions.** ccledger carries two of its own skills (`dogfood`, `pricing-refresh`) under `.claude/skills/`. `/materialize` correctly classified them as keep, but there was nowhere for them to live: the gitignore ignored `.claude/skills/` wholesale (so an untracked extension is lost on clone), and the doctor's "no runtime tracked" channel check could not tell a project's own skill from harness runtime (so a tracked extension failed the check).
2. **Tool surfaces.** ccledger is claude-only, but `materialize.sh` installed all four tool agent-surfaces (`.github`, `.opencode`, `.junie`) unconditionally — pushing three unwanted toolchains into the project. The retired copy-mode `/seed` had tool selection; the manifest install lost it.

Both are the same shape: the project owns or opts into part of the runtime tree, and the harness machinery overrode that.

## Decision

The `[harness]` table in `layout.toml` gains two optional keys, and `init`, `materialize`, and the doctor all read them. The project declares; the harness respects.

- **`tools`** — the AI tool surfaces installed. claude is always on; copilot, opencode, junie are optional. `init` asks and writes the set; `materialize.sh` installs only these and **never adds a surface on upgrade** (when the key is absent it auto-detects the surfaces already present — an existing project keeps what it has; a greenfield target with no signal gets all four).
- **`extensions`** — runtime-relative paths to skills or agents the project added. `/materialize` keeps them (never prunes them as orphans) and records a newly discovered one here on confirmation; the doctor excludes declared extensions from the untracked-runtime check, so they stay tracked by design; the gitignore runtime block uses the `dir/*` form so a `!path/` negation per extension keeps new files inside them visible; and the copy→manifest untrack excludes them so migration never strips the project's own work.

Both keys are additive and optional — a project that declares neither behaves as before (all tools, no extensions). The orphan-vs-extension classification stays an LLM heuristic over harness history; `extensions` makes a confirmed keep durable so it is never re-litigated.

## Consequences

**Positive:**
- A project with its own skills/agents can run the manifest channel cleanly — extensions stay tracked, the doctor passes, materialize never prunes them.
- An upgrade installs only the toolchains the project uses; no unwanted surfaces.
- The declarations are data, read identically by init, materialize, and the doctor — one source of truth.

**Negative:**
- Two more optional keys to understand in `layout.toml`; mitigated by shipped comments and the doctor's validation.
- The gitignore `dir/*` + `!path/` form is subtler than a flat ignore; the runtime block documents why.
- Recording an extension still rests on the keep decision being right; the heuristic plus "ask when unsure" is the safeguard, and a wrong record is a one-line `layout.toml` fix.

## References

- [Project History](../../README.md#project-history) — the what/when timeline
- [`2026-06-13-materialize-complete-replacement.md`](2026-06-13-materialize-complete-replacement.md) — complete-replacement materialize; this closes the two gaps its first real migration exposed
- [`2026-06-12-docs-as-harness-project-api.md`](2026-06-12-docs-as-harness-project-api.md) — defines the `[harness]` table these keys extend
