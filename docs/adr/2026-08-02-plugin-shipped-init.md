# The Marketplace Plugin Ships Its Own Init

**Status:** Accepted

## Context

Marketplace onboarding was a three-session, two-repo procedure: install the plugin in the project, clone the reference and run `/init <path> marketplace` there, return to the project for `marketplace-setup`. The clone existed only because `init` lived at the reference root. The trap it enabled was documented in two places: a bare `/init` infers `manifest`, and a later `/materialize` installs the full runtime beside the plugin — every surface loaded twice. The plugin cache already bundled the doctor's brief templates and the managed chapters; only the init skeletons and `init.py` were missing. No ADR argued the placement: the root-seed-harvest decision (2026-06-11) predates the marketplace channel, and its rationale — sample deduplication, wrong-template hazards — does not apply to a per-stack plugin.

## Options Considered

1. **Keep init root-only, improve the documentation.** Rejected: the friction is structural, not textual; the double-install trap survives any prose.
2. **Fold scaffolding into `marketplace-setup`.** Rejected: setup is re-run per upgrade and must stay idempotent-mechanical; scaffolding asks identity questions once. Two verbs, two skills.
3. **Bundle init in the plugin as its own skill** (chosen).

## Decision

**Each plugin bundles the scaffolder — `init.py`, `registry.py`, `write_guard.py`, its stack's `init/` skeletons, `VERSION` — cache-side, plus an `init` skill that runs it with the channel pinned to `marketplace`.** `init.py` gains one layout fallback: the doctor templates resolve from `skills/` when `core/.claude/skills/` is absent — the same file serves both trees. Everything is rendered by `package-marketplace.py`, so no hand-sync surface arises. The marketplace acceptance test scaffolds through the bundled copy, proving the clone-free path per battery run. The channel pin makes the manifest-inference trap unreachable from this skill; a reference clone's `/init <path> marketplace` stays equivalent.

## Consequences

- Marketplace onboarding is one repo and one restart: install → `/agent-team:init` → `/agent-team:marketplace-setup`.
- The plugin grows by the skeleton payload (tens of KB), and three maintainer modules ship in a second (generated) location.
- The init skill is stack-pinned per plugin; a wrong-stack target is refused at step 1 rather than mis-scaffolded.

## Implementation

`harness/package-marketplace.py` (bundle + skill render), `harness/marketplace/init-skill.md`, the templates fallback in `harness/init.py`, the bundled-init scaffold step in `harness/tests/test-marketplace.sh`, and the adoption-guide/setup-skill prose.

## References

- [Seed and Harvest Move to the Root with Stack Auto-Detection](2026-06-11-root-seed-harvest.md) — the placement this amends for the marketplace channel; its rationale predates plugins.
- [Marketplace Plugin Channel](2026-06-14-marketplace-plugin-channel.md) — the channel whose onboarding this completes.
- [All Plugins Share One Skill Namespace](2026-08-01-shared-plugin-namespace.md) — the `/agent-team:init` entry point's namespace.
