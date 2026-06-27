# A Decoupled Harness Artifact Version

**Status:** Accepted. The `harness@<version>` provenance stamp (below) is amended by [Stamp the Harness Release Date into Every Session via CLAUDE.md](2026-06-27-harness-version-stamp.md): materialized targets now carry the release date, not the semver. The decoupled artifact version itself — `harness/VERSION`, feeding `plugin.json` and the marketplace — still stands.

## Context

The `marketplace` channel — the harness runtime shipped as a plugin — is a named value in the spec and a doctor invariant, but no packaging exists yet. A marketplace plugin needs a real, pinned, upgradeable version. This is a prerequisite for building that channel.

The harness had no source-of-truth version. `{{HARNESS_VERSION}}` was substituted only by `init.sh` from a positional argument, which `bootstrap.sh` and `materialize.sh` never passed. The committed samples carried the literal token `harness@{{HARNESS_VERSION}}` in 12 provenance lines — what a file looks like when substitution never ran.

The version a release ships under is a different fact from the API contract revision. The artifact advances every release; `spec_version` advances only when the contract changes. Conflating them would force an API-compat bump on every plugin release.

## Decision

**The harness carries a decoupled artifact version in `harness/VERSION`.**

- **`harness/VERSION` is the single source of truth.** A semver file, read by `init.sh` when the version argument is omitted — so callers no longer supply it. An explicit argument still overrides. An empty or missing file is a hard error, not a blank stamp.
- **It is informational provenance.** The version is stamped into each materialized file as `harness@<version>`. The doctor validates `spec_version` and nothing else; the artifact version is never a gate. The two numbers move independently.
- **The samples are re-stamped once.** The 12 project-owned `docs/*.md` briefs had their literal token replaced with `0.1.0`. These files are owned by the project and never re-materialized, so this is a deliberate one-time correction, not a channel-rule violation. The `doctor/templates/*` keep the token — they are templates, filled at materialization.

## Consequences

**Positive:**
- The harness has a real version to pin a marketplace release to, distinct from the API contract it implements.
- The committed samples now show what a real consumer sees (`harness@0.1.0`), not an unsubstituted token.

**Negative:**
- A sample's provenance line freezes at the version that produced it; a later `harness/VERSION` bump does not update it. This is correct — provenance records the producing version — but means the reference samples and the harness version can differ until a deliberate re-stamp.

## Notes

This is a prerequisite for the marketplace channel, not the channel itself. Plugin packaging — the manifest, the install flow, a generator that pins `harness/VERSION`, and the `materialize.sh` marketplace path — remains future work. Paired with [layout-sourced schema patterns](2026-06-14-layout-sourced-schema-patterns.md), landed together as that groundwork.
