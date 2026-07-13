# Materialize-Time Runtime Verification

**Status:** Accepted

## Context

Consumer builds were wired to the harness's own test suites. Gradle `check` depended on three `Exec` tasks running vendored script tests; `make ci` carried a `test-scripts` target; the CLAUDE.md quality gates named the suites. The runtime under `scripts/` is a byte-copied artifact of a released harness version, tested by the battery before release and immutable between materializations. Re-running its suites on every project build verified nothing new. The wiring fanned every suite change across five surfaces in two ownership domains: build.gradle, the Makefile, CLAUDE.md, the quality-gate skill, and the init skeleton. Adding one module (`cc_accounting`) missed two of them.

## Options Considered

1. **Keep the wiring, gate the roster.** A parity check pinning the suite list across all five surfaces. Rejected: it hardens a coupling that should not exist — an infrastructure self-test still blocks unrelated feature work, and harness churn still edits project-owned files.
2. **Drop verification entirely.** Rejected: a partial copy or a host python incompatibility would surface only as a mid-pipeline failure.
3. **Verify at materialize time** (chosen).

## Decision

**Project builds verify project code only; the harness verifies its runtime at the one lifecycle point where it changes.** `materialize.py` runs the vendored test suites its install produced (`scripts/test_*.py`, `.claude/hooks/test_*.py`) once after copying and fails loudly when one breaks. The marketplace channel's `setup.sh` performs the same verification over the engine sliver it copies. The suite list derives from the install's own file set, never a target-tree glob, so a project-authored test file is never run as a suite. That guards the list, not the interpreter's import surface: the suites run inside the target tree and import from it — point materialize or setup only at trees you trust. `--no-verify` exists for harness-internal callers whose battery runs the same suites in its own step. The suites still ship with the runtime for manual runs.

The ledger sweep (`python3 scripts/handoff.py validate`) stays in the project quality gate. It validates the project's own `.scratch/handoff.jsonl` — data no harness-side check can reach, and the only corruption catch for tools without hook enforcement.

## Consequences

- A harness suite change touches only `/harness`; no project-owned build file, gate text, or skeleton moves with it.
- A harness self-test failure can no longer block a consumer's feature work mid-slice; it surfaces at install or upgrade, where the fix (re-materialize, report upstream) is obvious.
- Battery step 4b narrows to dangling-reference detection; zero `.py` refs in build files is the norm.
- A host python upgraded *between* materializations is no longer exercised by the build; a breakage there surfaces on first pipeline use of the affected script, which fails loud.
- Two suites self-skip where their fixtures cannot exist: `test_score_change.py` on a pre-init tree (no `layout.toml`), `test_brief_doctor.py` on the marketplace channel (templates are plugin-delivered). The skips are channel-keyed; a copy-channel tree missing its fixtures still fails loud.
- The go schemas dropped the `test-scripts` gate check. A pre-upgrade ledger carrying it fails `handoff.py validate`; clear `.scratch/` (`/new-feature`) when upgrading mid-slice.

## Implementation

`harness/materialize.py` (`verify_runtime`, `--no-verify`), `harness/marketplace/setup.sh`, `harness/bootstrap.sh`, `harness/check-sync.py` step 4b, both sample build files, the go build schemas, the CLAUDE.md quality gates and init skeletons, and the `code-quality-gate` and `change-grading` skills.

## References

- [Executable Pipeline Contracts](2026-07-02-executable-pipeline-contracts.md) — the suites remain the contract; this decision moves only where they run.
- [Materialize as Complete Replacement](2026-06-13-materialize-complete-replacement.md) — the install step this verification extends.
- [Handoff Log Access Tool](2026-06-11-handoff-log-access-tool.md) — superseded in one aspect: the suite is no longer wired into `make test-scripts` or the gradle `check` task.
