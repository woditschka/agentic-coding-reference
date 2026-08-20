# Retirements Are Recorded Once: The Retired-Paths Manifest

**Status:** Accepted

## Context

Orphan classification was per-file judgment. `/materialize` ran `git log` against the harness clone per extra, with a degraded ask-the-user mode when the source is a plugin (no history). The marketplace `setup.sh` copied additively and never removed; its setup skill accreted hand-written delete lists — 16 files across two upgrade notes by v0.3.6. A 2026-08-20 review confirmed the finding: the maintainer knows every retirement mechanically (the runtime the last tag produced minus what the tree produces now), yet no artifact recorded it.

## Options Considered

1. **Keep judgment, grow the hand lists.** Rejected: the lists already demonstrated unbounded growth, and the plugin channel's degraded mode stays.
2. **Per-release delta files.** Rejected: a consumer skipping versions needs the union; one cumulative file gives it by construction.
3. **Consumer-side git archaeology against the plugin.** Rejected: plugins carry no history — the exact gap that forced the ask-mode.
4. **One cumulative, append-only manifest, derived at release, gated by the battery** (chosen).

## Decision

**`harness/retired-paths.txt` records every consumer-relative runtime path the harness once produced and no longer does; classification becomes set arithmetic: present − produced − extensions − retired.**

- **Derivation is mechanical.** `retired_paths.py update <since-tag> <label>` appends the produced-set difference; `release-version.sh` runs it before every propagate, so no human memory is load-bearing.
- **The battery gates both directions** (verify-harness step 3k): a runtime path the last `v*` tag produced that is gone without an entry fails; an entry the source produces again fails. Tagless checkouts fail under `--strict` (CI fetches full history), note-skip otherwise.
- **Consumers act on it per channel.** `materialize.py` annotates manifest-covered extras `[retired]`; the `/materialize` skill removes them without history checks, keeping the git-log fallback only for what the manifest predates. The marketplace `setup.sh` prunes via the bundled `prune-retired.py`.
- **Marketplace deletion is bounded.** The pruner deletes only inside the engine-sliver namespaces the channel's installs provably own (`registry.ENGINE_SLIVER`), never under `.claude/agents/`, and only paths that resolve inside the target (symlinks skipped — `write_guard`'s follow=False rule, restated because the cache-shipped script cannot import it). Entries outside the sliver are report-only there: a consumer-authored file at a colliding retired name is indistinguishable from debris, and on this channel it is gitignored — deletion would be unrecoverable. Guards: currently-produced wins (reintroduction), declared `[harness] extensions` are kept and reported, an unparseable `layout.toml` prunes nothing, a pruner failure warns and never aborts the install.

This amends two recorded premises: the marketplace channel now removes files (within the bounds above), and the orphan-classification heuristic of [extensions-and-tool-surfaces](2026-06-13-extensions-and-tool-surfaces.md) is demoted to the pre-manifest fallback.

## Consequences

**Positive:** consumer upgrades lose the git archaeology and the hand-delete lists; the plugin channel's degraded ask-mode disappears for listed paths; drift is gated by construction (a forgotten append fails tier 0).

**Negative:** a mid-cycle clone sees renames one release before the manifest carries them (judgment fallback covers the window). A path one stack retires while another still ships never enters the manifest — that stack's consumers keep the judgment path. Strict battery runs now require reachable `v*` tags.

## Implementation

`harness/retired-paths.txt`, `harness/retired_paths.py`, `verify_harness/checks/sync.py` (step 3k), `harness/marketplace/prune-retired.py` + `setup.sh`, `package-marketplace.py` (bundles both), `release-version.sh`; suites `test_retired_paths.py`, `test_prune_retired.py`, the step-3k pins in `test_verify_harness.py`, and the prune scenarios in `test-marketplace.sh`.

## References

- [Mechanical Promises Move Into Engines](2026-07-14-mechanical-promises-into-engines.md) — the class this decision instantiates: recorded judgment becomes executable arithmetic.
- [Extensions and Tool Surfaces](2026-06-13-extensions-and-tool-surfaces.md) — the classification heuristic this demotes to fallback; the `extensions` declaration it leans on as the keep-guard.
- [Exact-Module Install Verification](2026-08-16-exact-module-install-verification.md) — leaned on "the marketplace channel never removes files"; bounded removal now exists, and inert-leftover reasoning applies only outside the sliver.
- [The Harness Glue Is Provably Confined](2026-07-19-network-write-confinement-gate.md) — the containment rule the pruner restates for the one deleter that cannot import `write_guard`.
