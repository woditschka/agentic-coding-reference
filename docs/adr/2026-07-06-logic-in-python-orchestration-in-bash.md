# Logic in Python, Orchestration in Bash

**Status:** Accepted (typed-code standard added by [2026-07-17](2026-07-17-typed-python-core.md))

> The language boundary and the stdlib-only contract hold unchanged. The 2026-07-17 ADR adds the typed standard — frozen dataclasses, `assert_never` exhaustiveness, ruff and mypy gates — the Python side must meet.
>
> The "one self-contained script plus a `test_<name>.py` sibling" convention now also admits a flat set of sibling modules with per-module test siblings (handoff.py ships as such a set, split by trust class). The stdlib-only, no-manifest, flat-file rules hold.

## Context

The harness tooling is 4,800 lines of bash across 26 scripts. The two largest — `check-sync.sh` (710 lines) and `statusline.sh` (809 lines) — parse JSON with jq and awk, past the size where shellcheck keeps bash honest. The consumer-shipped hooks guard the pipeline contract yet have no unit tests; bash offers no seam to test their quote-stripping and heredoc parsing in isolation. Meanwhile the runtime already crossed the language line: `handoff.py`, `brief_doctor.py`, and `score-change.py` ship as stdlib Python with `unittest` siblings, and `python3` is a hard consumer dependency — agents call `python3 scripts/handoff.py route` on every hop. The reference's thesis is engineering discipline; its own tooling must model it.

## Options Considered

1. **Keep bash, lean on shellcheck and the `test-*.sh` suites** — rejected: shellcheck catches syntax hazards, not logic defects; bash test suites cannot unit-test a hook's parser, only end-to-end invocations.
2. **Rewrite everything in Python** — rejected: thin command sequencers (`bootstrap.sh`, `release-prep.sh`) are idiomatic bash; porting them adds ceremony without a testability gain. The generic stack's `stack.sh` verb stubs are a consumer-edited binding surface and stay deliberately trivial shell.
3. **A boundary rule with phased migration** (chosen) — anything that parses, transforms, or decides is Python with tests; anything that only sequences commands stays bash.

## Decision

**Logic lives in Python; bash remains only for thin command orchestration.** The rule that draws the line: a script that parses structured data, transforms text, or branches on content is logic and migrates; a script that runs a fixed command sequence and stops on failure is orchestration and stays.

Load-bearing details:

- **Stdlib only, Python 3.11+** for everything, matching `handoff.py`. Consumers install nothing; the battery's toolchain contract stays bash, git, python3.
- **`unittest`, not pytest.** The test runner must be present wherever python3 is; a pip dependency would break the copy channel's file-copy simplicity and the battery's toolchain contract.
- **Shipped runtime convention:** one self-contained script plus a `test_<name>.py` sibling, the existing `scripts/` pattern. Maintainer-side code may grow a package layout where shared fixtures pay for it.
- **Migration order by stakes:** (1) consumer-shipped hooks — highest stakes, zero tests today; (2) logic-heavy maintainer scripts (`materialize`, `init`, `refresh-agent-bodies`, `package-marketplace`, `refresh-chapters`, `refresh-gitignore`) with their test suites; (3) `check-sync` as a Python check-runner, the bash battery kept as oracle until verdicts match, then deleted. `tools/harness-stats` was considered as a fourth phase and descoped: user-level convenience tooling, not harness runtime.
- **Permanent bash:** `bootstrap.sh`, `release-prep.sh`, `release-version.sh`, `helpers.sh`, `marketplace/setup.sh`, the install-simulation suites (`test-marketplace.sh`, `test-generic-stack.sh`, `test-plugin-install.sh`), and the verb surface — `gate.sh` dispatches `verb_*` bash functions the consumer implements in `stack.sh`, so both sides of that contract stay shell.

## Consequences

- Positive: the hooks gain unit tests for their parsing edge cases; JSON is handled by `json`, dropping the hooks' jq dependency and its defer-on-missing gap; each battery check becomes a named, individually tested function; hooks run on Windows without git-bash.
- Negative: the tier-0 gate itself migrates, so a rewrite defect could pass what the old gate caught — mitigated by the oracle phase; every PreToolUse call pays Python startup (~30 ms) where bash paid ~5 ms; the boundary rule is one more convention the audit must hold.

## References

- [Executable Pipeline Contracts](2026-07-02-executable-pipeline-contracts.md) — the same move for the pipeline: contracts enforced by tested code, not prose.
- [Handoff Log Access: Single Deterministic Tool](2026-06-11-handoff-log-access-tool.md) — the precedent this generalizes: the first logic-in-Python script.
- [The Handoff Append Is Pre-Approved Per Tool, via a Hook on Claude Code](2026-06-20-handoff-append-pre-approval.md) — the hooks phase 1 rewrites.
