---
name: release-version
description: >-
  Cut a new harness version. Evaluates the semantic-version bump from the
  conventional commits since the last v* tag, proposes it with reasoning, and
  asks you to confirm or override (forward-only). On confirmation it writes
  harness/VERSION — which restamps every plugin.json and the marketplace — runs
  release-prep to propagate and prove the battery green, then creates the local
  chore(release) commit and the annotated v<VERSION> tag. It STOPS there and
  prints the push commands; it never pushes or publishes unasked. Run on a clean
  tree once the feature work is committed. Root-only (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# release-version

Cut one lockstep version for the whole plugin set: evaluate the bump, restamp,
verify, and tag — leaving the outward push to you. The version stamps every
`plugin.json` file and the marketplace; its release date (`harness/VERSION-DATE`)
stamps every consumer's `CLAUDE.md`; the `v<VERSION>` tag is the reproducible
snapshot and rollback point ([the marketplace ADR](../../../docs/adr/2026-06-14-marketplace-plugin-channel.md)).

## When to run

- To release a new harness version after a batch of `/harness` changes is committed.
- Run on a **clean working tree** — commit the feature work first, so the release commit holds only the version bump and its restamp.

## Precondition

The working tree must be clean. The bump + `release-prep` should be the *only*
diff the release commit captures. If the tree is dirty, stop and ask the user to
commit or stash first — never fold unrelated changes into a release commit.

## Process

1. **Find the baseline.** The latest release tag:
   ```bash
   git tag --list 'v*' | sort -V | tail -1
   ```
   If none exists, this is the first tagged release — survey from the commit that introduced `harness/VERSION`.

2. **Evaluate the bump** from the conventional commits and the diff since the baseline (`git log --pretty='%s' <baseline>..HEAD`). Classify each change:

   | Signal | Trigger |
   |---|---|
   | **breaking** | a removed or renamed skill / agent / channel, an API `spec_version` change, or a commit marked `!` / `BREAKING CHANGE` |
   | **feature** | a `feat:` commit — a new skill, agent, capability, or channel |
   | **fix** | only `fix:` / `docs:` / `refactor:` / `chore:` |

   Then map to a bump. **The current major is 0, so the pre-1.0 rule applies:**
   - **breaking → bump MINOR** (`0.x.0`) — pre-1.0, breaking changes are minor.
   - **feature or fix → bump PATCH** (`0.x.y`).
   - The `1.0.0` jump is a deliberate stability decision the user makes; never propose it automatically.

   (At `>= 1.0.0`, switch to standard semver: breaking → major, feature → minor, fix → patch.)

3. **Propose and confirm.** Present the computed version with its reasoning — list the commits that drove it. Ask the user to confirm or override. Reject any version not strictly greater than the current `harness/VERSION` (releases are forward-only).

4. **Write the version and its release date:**
   ```bash
   printf '%s\n' "<new-version>" > harness/VERSION
   date -u +%Y-%m-%d > harness/VERSION-DATE
   ```
   `harness/VERSION-DATE` is the release date `materialize` stamps into every consumer's `CLAUDE.md` (`<!-- harness: <YYYY-MM-DD> -->`) — a session-attribution token. Set it once here, with the version, so it is fixed and deterministic (never a wall-clock-at-materialize value, which would break the faithfulness battery).

5. **Propagate and verify.** Run **`/release-prep`**. It re-renders the marketplace (every `plugin.json` and the marketplace metadata now carry the new version), re-materializes the samples, and runs the full battery. A non-green battery is a hard stop — fix at the source and re-run.

6. **Commit and tag locally:**
   ```bash
   git add -A
   git commit -m "chore(release): v<new-version>"
   git tag -a "v<new-version>" -m "harness v<new-version>"
   ```
   The annotated tag carries the tagger, date, and message — a reproducible snapshot of the state where every plugin reports this version.

7. **Stop. Print the push commands** for the user to run — do not execute them:
   ```bash
   git push origin <branch>
   git push origin v<new-version>
   ```
   Pushing is outward-facing and the user authorizes it ([push requires approval](../../../CLAUDE.md)). After the tag is pushed, GitHub lists it under Tags; a full GitHub Release can be promoted from the tag later if notes or a prerelease label are wanted.

## Verdict format

```
## release-version: <date>

Baseline:  <last tag or "first release">
Bump:      <current> → <new> (<major|minor|patch>) — <one-line reason>
Propagate: release-prep PASS | FAIL (<step>)
Staged:    commit chore(release): v<new>  +  tag v<new>  (local, unpushed)

Next (you run): git push origin <branch> && git push origin v<new>
```

## What it does NOT do

- **Does not push or publish.** It stages the commit and the local tag, then hands you the push commands ([local commits are provisional](../../../CLAUDE.md)).
- **Does not bump to `1.0.0` on its own** — that is a deliberate stability decision.
- **Does not run on a dirty tree** — the release commit must hold only the version bump and its restamp.
- **Does not re-stamp project-owned sample briefs** — those carry their `init`-time version by the decoupled-version rule; `release-prep` restamps only the harness-owned runtime and the plugins.
