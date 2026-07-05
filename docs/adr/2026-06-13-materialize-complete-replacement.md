# Materialize Is a Complete Replacement, Not an Additive Copy

**Status:** Accepted (three Decision edges since amended; see note)

> **Amended.** The `/seed` compatibility alias is retired; `/materialize` is the sole entry point. The "never edits briefs or `layout.toml`" edge is amended by [2026-07-01-generalized-template-reconciliation](2026-07-01-generalized-template-reconciliation.md): a deterministic tier refreshes `.gitignore`, `settings.json`, and the `CLAUDE.md` managed chapters; an advisory tier proposes brief and `layout.toml` deltas on approval. `brief-review` has since become `audit-docs` ([2026-06-14-audit-docs-skill](2026-06-14-audit-docs-skill.md)). The manifest-as-default framing is gone: copy is the default channel and any copy → manifest switch is manual ([2026-06-14-copy-channel-default](2026-06-14-copy-channel-default.md)). The complete-replacement contract for the runtime is unchanged.

## Context

`materialize.sh` copied `core ∪ stacks/<stack>` into a target additively — it never deleted. So when the harness renamed or moved a file (e.g. `doc-review`→`document-writing`, the tdd `SKILL.md` from `stacks/` to `core/`), a re-materialize left the old file behind as an orphan. The doctor's `git ls-files` channel check cannot catch it: on the manifest channel the runtime is gitignored, so an orphan is untracked and invisible. The samples stayed clean only because their gitignored runtime happened to match a pristine materialize.

There was also no self-detecting path to bring an existing project current: a user had to know the stack, whether `init` was needed, and the channel, then run the scripts by hand.

The intended model is *materialize out → evolve in the project → harvest back*. For that loop to be sound, the "out" leg must make the target's runtime **equal** the current harness — not a superset of every harness version it ever saw.

## Options Considered

1. **Keep additive copy; prune in a separate step.** Two commands, easy to forget the second; orphans persist by default.
2. **Stored install manifest.** Record every installed file; prune `old − new` deterministically. Precise, but adds persistent state to maintain and a new gitignored artifact.
3. **Complete replacement via a skill, with LLM-classified extras.** `materialize.sh` reports extras (files an install did not produce); the `/materialize` skill classifies each as orphan (remove) or project extension (keep), asking when unsure.

## Decision

Option 3.

- **`materialize.sh` reports extras, non-destructively.** After installing, it lists files under the harness-owned runtime directories that the install did not produce, between machine-readable markers. It never deletes — it stays a safe primitive. Its scan roots mirror the directory entries of `brief_doctor.py` `RUNTIME_PATHS`; `harness/test-materialize.sh` guards the parity and the detection.
- **A new `/materialize` skill is the complete-replacement front end.** It detects the stack from the build marker, runs `/init` when project-owned scaffolding is missing (greenfield or copy→manifest migration), installs the runtime, then classifies extras: a self-contained unit the harness does not own is a **project extension** (keep); a stray file in a harness-managed unit or a former-harness path is an **orphan** (remove); anything ambiguous is **asked**. It is channel-aware and finishes by running the doctor.
- **No stored manifest.** Classification is an LLM heuristic against `harness/core ∪ harness/stacks/<stack>`, the authoritative unit set — no new persistent artifact.
- **Project-owned version drift stays doctor-guided.** Materialize replaces runtime only; it never edits briefs or `layout.toml`. A contract change to a project-owned file is flagged by the doctor and fixed by the human via `brief-review`. No migration-playbook engine is built until a real breaking change exists.
- **`/seed` becomes a compatibility alias** for `/materialize`; onboarding and upgrading are the same operation under the manifest channel.

## Consequences

**Positive:**
- Re-materialize is idempotent and self-healing — renames and moves no longer leave orphans.
- One self-detecting command onboards and upgrades; the user does not hand-pick stack, channel, or `init`.
- Project extensions are safe: the skill keeps unknown units and asks before touching anything ambiguous.

**Negative:**
- Orphan-vs-extension is a judgment call, not a deterministic diff; the safeguard is "ask, default to keep," and the test covers the clear cases.
- The complete-replacement guarantee lives in the skill, not the raw script — a direct `materialize.sh` call installs and reports but does not prune.

## References

- [Project History](../../README.md#project-history) — the what/when timeline
- [`2026-06-12-docs-as-harness-project-api.md`](2026-06-12-docs-as-harness-project-api.md) — defines the channels and the project-owned/runtime split this builds on
- [`2026-06-11-root-seed-harvest.md`](2026-06-11-root-seed-harvest.md) — moved seed/harvest to the root; this folds seed into `/materialize`
