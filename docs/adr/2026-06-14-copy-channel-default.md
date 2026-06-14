# Copy Is the Default Channel; the Channel Is Detected, Not Asked

**Status:** Accepted

## Context

Materializing onto real projects surfaced friction in the channel choice. Two problems compounded:

1. **The default was wrong for most adopters.** `/init` shipped `channel = "manifest"` (runtime gitignored, materialized from a pinned source). But the common case — and the mode both samples use — is **copy**: the runtime committed into the repo, self-contained and diffable in review. A new adopter had to override the default to get the behavior they wanted.
2. **The choice was a prompt on every onboard.** `/init` asked "manifest or copy?" each time, even when the answer was already determined — an existing project's git state shows which channel it is on, and a greenfield target has an obvious default. The prompt was friction without a decision behind it.

A third, quieter issue: `/materialize` advertised an automatic **copy → manifest** migration as part of orphan removal. That coupled two unrelated operations — pruning stale runtime files and changing the repo's git layout — so a routine upgrade could silently untrack a project's whole runtime.

## Decision

**Copy is the default channel, the channel is resolved rather than asked, and switching is manual.**

- **Default flips to copy.** `init.sh` defaults the channel arg to `copy`; the `init/` template `layout.toml` ships `channel = "copy"`. A greenfield adopter gets a committed, version-controlled runtime with no override.
- **`/init` resolves the channel, never prompts.** Resolution order: a declared `[harness] channel` wins; else infer from git state (runtime tracked → copy, gitignored → manifest); else greenfield → copy; only genuinely conflicting signals fall back to a question. This is the "adapt to what is present" rule — the project's existing layout decides, not a re-asked prompt.
- **`/materialize` respects the declared channel and never flips it.** Orphan removal touches only the confirmed orphan paths: `rm` under manifest, a scoped `git rm` (orphan paths only) under copy. It no longer drives a copy → manifest transition.
- **Switching is a manual, documented step** in both directions — edit `[harness] channel`, adjust `.gitignore`, then untrack (copy → manifest) or commit (manifest → copy). Documented in the root README "Distribution channels" section and the `/init` skill.

The doctor is unchanged: it already passes copy by design (runtime committed) and enforces untracked-runtime only under manifest, so the default flip is doctor-safe.

## Consequences

**Positive:**
- The default matches the common case; an adopter gets a self-contained, reviewable runtime with zero configuration.
- Onboarding drops a prompt — the channel is determined from what the target already is.
- Upgrades no longer change a repo's git layout as a side effect of pruning orphans; channel changes are deliberate and explicit.

**Negative:**
- A project that genuinely wants manifest must now opt in (declare it, or switch manually). Acceptable: manifest is the rarer, more deliberate choice, and the switch is documented.
- Detection adds a small reasoning step to `/init` (inspect git state) in place of a prompt. The script still accepts an explicit channel arg, so the logic stays in the skill, not the installer.

## Notes

Supersedes the manifest-as-default and automatic copy → manifest behavior described in [complete-replacement materialize](2026-06-13-materialize-complete-replacement.md) and [extensions and tool surfaces](2026-06-13-extensions-and-tool-surfaces.md). Those records stand as written; this ADR changes the default and removes the automatic migration.
