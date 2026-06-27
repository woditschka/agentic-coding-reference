# Stamp the Harness Release Date into Every Session via CLAUDE.md

**Status:** Accepted

## Context

We analyze Claude Code transcripts to compare how the harness performs across versions — cost per work unit, rework rate, escalation effectiveness, communication tax. That comparison needs each session attributed to the harness version that produced it.

Today the version reaches a transcript only through the line-1 provenance comment (`harness@<semver>`) on materialized docs (prd.md, system-design.md, others). Those files load into a session only when an agent opens one, so the version is present in roughly 3% of transcripts — too sparse to attribute reliably.

`CLAUDE.md` is the one file injected into every session's context, on every channel, across all four supported tools. Putting an attribution token there raises coverage from ~3% to every session. [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](2026-06-24-claude-md-managed-chapters.md) already made `CLAUDE.md` a hybrid file that `refresh-chapters.sh` rewrites on every materialize — the natural carrier for a refreshed token.

## Options Considered

1. **Keep the docs provenance only.** Rejected: it covers ~3% of transcripts; the docs load occasionally, not every session.
2. **A managed chapter (`## Harness Version`).** Rejected: a heading plus body for one machine token adds context noise the goal explicitly bars, and the chapter model fits human-facing prose, not a one-line token.
3. **A single sentinel line, upserted by `refresh-chapters.sh`.** Accepted as the carrier. One greppable HTML comment near the top of `CLAUDE.md`, refreshed wherever chapters are. This is the `.gitignore`-block precedent — a machine token with no natural heading — not the chapter case the prior ADR reserved for headings.

For the **payload** inside that line, three forms were weighed:

- **Git SHA.** Rejected: a SHA cannot be ordered into a trend. A HEAD short-SHA also changes on every commit, so it would break `check-sync.sh` step 3 — committed samples must equal a fresh re-materialize — between releases.
- **Semver (`0.1.10`).** Viable: it directly names the version and needs no new source (`harness/VERSION` exists). But it reads as internal version coupling stamped into a project file, and the value is only the version number.
- **Release date (`2026-06-26`).** Chosen. The date the version was cut is orderable and maps one-to-one to the version, so downstream recovers the version via the release timeline. It is also the least project-invasive token — a neutral "as of" date, not an exposed internal version scheme. It is faithfulness-safe **only as the release date**, never a wall-clock-at-materialize value, which would differ on every run.

## Decision

**Option 3, release date only.** `refresh-chapters.sh` writes one line as the first line of `CLAUDE.md`:

```
<!-- harness: 2026-06-26 -->
```

- **Single source, single line.** The date comes from `harness/VERSION-DATE`, written once by `release-version` alongside `harness/VERSION` when a version is cut. One occurrence, near the top, so the token costs one line of context.
- **Release date, never run date.** The stamp is fixed per version. `release-version` records it at cut time; `materialize` only copies it. A wall-clock date would be non-deterministic and fail the faithfulness battery — the same trap that rejected the git SHA.
- **Refreshed on every channel.** `materialize.sh` and `init.sh` pass the harness root, where `refresh-chapters.sh` reads `VERSION-DATE`; `package-marketplace.sh` bundles `VERSION-DATE` at each plugin root, where `setup.sh` finds it on the marketplace channel. All three resolve it without threading it through, and a plugin upgrade re-stamps to the new date.
- **Upsert, never duplicate.** The writer drops any existing `harness:` line, then prepends the current one. Re-running on an unchanged version is byte-identical, so the samples' faithfulness check stays green.
- **Validated structurally.** A new doctor check, `harness-stamp`, fails if the stamp is missing, duplicated, or not a well-formed `YYYY-MM-DD`. "Matches the materializing version" is not checkable in a consumer — it has no `harness/VERSION-DATE` — so `check-sync.sh` step 3 enforces that for the samples by re-materializing and diffing.

## Consequences

**Positive:**
- The harness identity lands in every session's context, lifting attribution coverage from ~3% to 100% of transcripts.
- The token is greppable with one regex (`harness:\s*(\d{4}-\d{2}-\d{2})`), so a downstream tool extracts it unambiguously, then joins the date to the version via the release timeline.
- The date is the least project-invasive token: a neutral "as of" date, orderable, with no internal version scheme exposed in a project-owned file.
- The mechanism reuses the existing refresh path; the only new source is one committed file `release-version` already has reason to write.
- The doctor and the faithfulness check make a missing, malformed, or stale stamp impossible to ship silently.

**Negative:**
- `CLAUDE.md` gains a machine token on line 1 — one line of context noise on every turn, accepted as the cost of full coverage. It renders to nothing in markdown.
- Recovering the version *name* needs a date→version lookup (the release timeline), where a semver would have named it directly. Accepted: the timeline is small and ccledger holds it anyway, and the date is the softer token in the project file.
- The date advances only on a release, so two commits at the same version are indistinguishable by the stamp alone — acceptable, since version-level attribution is the goal.
- A new invariant: `release-version` must write `harness/VERSION-DATE` in lockstep with `harness/VERSION`. The doctor's structural check and the faithfulness battery catch a drifted or stale date.

## Implementation

`refresh-chapters.sh` gains `stamp_date` (heading-independent: it upserts the first line) and resolves the date from an explicit third argument or `VERSION-DATE` at the harness/plugin root. `package-marketplace.sh` writes `VERSION-DATE` to each plugin root for `setup.sh`. `release-version` writes `harness/VERSION-DATE` next to `harness/VERSION` at cut time. `brief_doctor.py` gains `check_harness_stamp` wired into `run()`, with tests for present, missing, malformed, and duplicate. `bootstrap.sh` re-materializes the samples, which adds the stamp to each sample `CLAUDE.md`. The root `CLAUDE.md` is not a harness consumer, so it carries no stamp and the doctor never checks it.

The same move removes the semver from the **other** place it reached a target: the briefs' line-1 provenance comment. It collapses from `materialized by harness@<semver>, template …, spec …` to the same token `CLAUDE.md` carries — `<!-- harness: <date> -->` (the `{{HARNESS_DATE}}` template token, filled by `init` from `VERSION-DATE`). The semver now lives only where versioning is real — `plugin.json` and the marketplace. One token, everywhere a stamp reaches a target. The brief records the date it was scaffolded. `CLAUDE.md`, refreshed every materialize, records the harness that ran the session — so in an upgraded consumer a brief can carry an older date. Session attribution keys on the `CLAUDE.md` stamp, present in every session's context block; the brief copy is per-file provenance, not the attribution source.

## References

- [A Decoupled Harness Artifact Version](2026-06-14-decoupled-artifact-version.md) — the `harness@<version>` provenance stamp this amends to the release date
- [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](2026-06-24-claude-md-managed-chapters.md) — the hybrid `CLAUDE.md` and the `refresh-chapters.sh` path this extends
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the provenance line the stamp complements
- [Project History](../../README.md#project-history) — the what/when timeline
