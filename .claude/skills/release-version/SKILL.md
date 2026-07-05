---
name: release-version
description: >-
  Cut a new harness version. Evaluates the semantic-version bump from the
  conventional commits since the last v* tag, proposes it with reasoning, and
  asks you to confirm or override (forward-only). On confirmation it runs
  harness/release-version.sh, which stamps harness/VERSION (+ release date),
  runs release-prep.sh (propagate + full battery), then creates the local
  chore(release) commit and the annotated v<VERSION> tag. It STOPS there and
  prints the push commands; it never pushes or publishes unasked. Run on a
  clean tree once the feature work is committed. Root-only (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "2.0"
  author: team
---

# release-version

Cut one lockstep version for the whole plugin set: evaluate the bump (judgment,
below), then hand the mechanical rest to `harness/release-version.sh`. The
version stamps every `plugin.json` and the marketplace; its release date
(`harness/VERSION-DATE`) stamps every consumer's `CLAUDE.md`; the `v<VERSION>`
tag is the reproducible snapshot and rollback point
([the marketplace ADR](../../../docs/adr/2026-06-14-marketplace-plugin-channel.md)).

## Precondition

A **clean working tree** — the script refuses anything else, so the release
commit holds only the bump and its restamp. Commit the feature work first.

## Process

1. **Find the baseline.** The latest release tag:
   ```bash
   git tag --list 'v*' | sort -V | tail -1
   ```
   If none exists, survey from the commit that introduced `harness/VERSION`.

2. **Evaluate the bump** from the conventional commits since the baseline
   (`git log --pretty='%s' <baseline>..HEAD`):

   | Signal | Trigger |
   |---|---|
   | **breaking** | a removed or renamed skill / agent / channel, an API `spec_version` change, or a commit marked `!` / `BREAKING CHANGE` |
   | **feature** | a `feat:` commit — a new skill, agent, capability, or channel |
   | **fix** | only `fix:` / `docs:` / `refactor:` / `chore:` / `build:` |

   **The current major is 0, so the pre-1.0 rule applies:** breaking → bump
   MINOR; feature or fix → bump PATCH. The `1.0.0` jump is a deliberate
   stability decision the user makes; never propose it automatically. (At
   `>= 1.0.0`, standard semver: breaking → major, feature → minor, fix → patch.)

3. **Propose and confirm.** Present the computed version with the commits that
   drove it. Ask the user to confirm or override.

4. **Run the script** with the agreed version:
   ```bash
   harness/release-version.sh <new-version>
   ```
   It guards: MAJOR.MINOR.PATCH shape, strictly greater than `harness/VERSION`,
   clean tree. It stamps `VERSION` + `VERSION-DATE` and runs `release-prep.sh`,
   then creates the `chore(release)` commit and the annotated tag.
   `VERSION-DATE` is the deterministic release date `materialize` writes into
   consumer `CLAUDE.md` files; a wall-clock-at-materialize value would break
   the faithfulness battery. A battery failure reverts the stamp and its
   propagation wholesale (mechanics in the script), then aborts with nothing
   committed — fix at source, re-run the same version.

5. **Stop.** Relay the push commands the script prints — do not execute them
   ([push requires approval](../../../CLAUDE.md)). After the tag is pushed, a
   GitHub Release can be promoted from it later.

## Verdict format

```
## release-version: <date>

Baseline:  <last tag or "first release">
Bump:      <current> → <new> (<major|minor|patch>) — <one-line reason>
Propagate: release-prep PASS | FAIL (<step>)
Created:   commit chore(release): v<new>  +  tag v<new>  (local, unpushed)

Next (you run): git push origin <branch> && git push origin v<new>
```

## What it does NOT do

- **Does not push or publish.** The script creates the commit and the local tag, then prints the push commands.
- **Does not bump to `1.0.0` on its own** — that is a deliberate stability decision.
- **Does not run on a dirty tree** — the script enforces this.
- **Does not re-stamp project-owned sample briefs** — those carry their `init`-time version by the decoupled-version rule; the restamp covers only the harness-owned runtime and the plugins.
