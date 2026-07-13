# Single Pricing Source as a Gated Vendored Copy

**Status:** Accepted

## Context

Three consumers price Claude Code usage: the statusline, the cache report, and the handoff board's cost overlay. Before this decision each shell script carried its own pricing constants, guarded only by keep-in-sync comments. The consumers live in two install domains with no shared path: harness-stats is user-level tooling (`~/.claude/`, standalone, no harness required), while the board runs project-level from the vendored runtime (`scripts/`). The repo's established mechanism for shared artifacts is a deterministic render (agent mirror bodies) gated by a faithfulness check.

## Options Considered

1. **A render step** across `tools/` and `harness/`. Rejected: the mirror-body renderer exists for many files with per-tool variation; one byte-identical module needs no transformation, and a new render family adds machinery for a single file.
2. **A runtime read from one location.** Rejected: no path exists on a consumer host that both the user-level statusline and a project-level board can rely on.
3. **A Python package.** Rejected: the runtime is stdlib-only by contract; consumers have no packaging step.
4. **A byte-identical vendored copy with a battery gate** (chosen).

## Decision

**`cc_accounting.py` is authored once and vendored once; a deterministic gate polices the manual hop.** The canonical home is `tools/harness-stats/cc_accounting.py` — the module was extracted from the statusline, and harness-stats must stand alone. The vendored copy is `harness/core/scripts/cc_accounting.py`, from which the samples and plugins derive mechanically. The maintainer syncs the one manual hop with a plain `cp`; battery step 2d byte-compares the pair and fails on any drift, even under `--quick`. `cache-report.sh` reads the multipliers from the module at run time, keeping literals only as a python3-less fallback; `statusline.sh` carries no pricing at all and drops its cost cells when the module is unavailable.

## Consequences

- A pricing change is a one-file edit plus a gated copy; no shell script, skill, or doc carries a rate value.
- The gate converts the vendored copy's drift risk from silent to loud; the failure message asks which side holds the intended edit before copying.
- `cache-report.sh`'s fallback literals can drift only on hosts without python3, where the module cannot be read.
- A second vendored module would repeat this pattern; at that point a render step (option 1) becomes the cheaper mechanism and this decision should be revisited.

## Implementation

`tools/harness-stats/cc_accounting.py` (canonical), `harness/core/scripts/cc_accounting.py` (vendored), `harness/check-sync.py` step 2d, the module docstrings naming both homes.

## References

- [Roster and Vocabulary Gates for Hand-Owned Parallel Files](2026-07-12-parity-gates-for-hand-owned-parallels.md) — the gate-family precedent: hand-owned parallels get deterministic gates at the level the contract forces identical; here the contract forces whole-file identity.
- [Rendered Agent Mirror Bodies](2026-07-03-rendered-agent-mirror-bodies.md) — the render doctrine this decision deliberately deviates from, for a single file with no per-copy variation.
- [Materialize-Time Runtime Verification](2026-07-13-materialize-time-runtime-verification.md) — the same change set; the vendored copy is part of the runtime it verifies.
