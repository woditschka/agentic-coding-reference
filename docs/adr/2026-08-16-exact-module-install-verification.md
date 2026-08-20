# Exact-Module Install Verification

**Status:** Accepted (never-removes premise amended by [2026-08-20](2026-08-20-retired-paths-manifest.md))

> **Amended.** The consequence below leans on "the marketplace channel never removes files." Since [2026-08-20-retired-paths-manifest](2026-08-20-retired-paths-manifest.md), `setup.sh` prunes manifest-listed paths inside the engine-sliver namespaces; a stale suite there is removed rather than left inert. Outside the sliver the inert-leftover reasoning still holds, and the exact-module contract itself is unchanged.

## Context

Install-time verification ran `unittest discover` over the target's `scripts/tests/` tree. The runtime-package-layout decision ([2026-07-17](2026-07-17-runtime-package-layout.md)) introduced that as a recorded contract change. It retired the "a project-authored test file is never run as a suite" guarantee from [materialize-time runtime verification](2026-07-13-materialize-time-runtime-verification.md). An external review (2026-08-16) flagged the consequence: an installer executed pre-existing project Python that merely sat under the discovery directory. The `/materialize` skill's prose still stated the retired guarantee, so the skill contradicted the shipped behavior. Discovery also carried two guards for its silent-skip class — a package-chain check for missing `__init__.py`, and a zero-tests check — duplicated across `materialize.py` and the marketplace `setup.sh`.

## Options Considered

1. **Keep discovery, correct the skill doc.** Aligns prose with behavior at zero code risk. Rejected: it keeps an installer executing unrelated project code, and keeps both silent-skip guards in two twins.
2. **Run verification in an isolated copy of the suites.** Rejected: the point of install-time verification is the installed tree on this host; a copy verifies something else.
3. **Name the installed modules exactly** (chosen).

## Decision

**Install-time verification invokes `unittest` with the dotted module names of exactly the suites the install produced.** `verify_runtime` converts each installed `scripts/**/test_*.py` to its module name and runs one `python -m unittest -- <modules...>` from the scripts dir. `import handoff` and `import tests.*` still resolve there — the package-layout rationale for discovery holds unchanged for named modules. `setup.sh` does the same over the engine sliver's file list, sorted to match. This restores the 2026-07-13 guarantee the 2026-07-17 layout change retired: the suite list derives from the install's own file set, never a target-tree glob.

Two argv details are load-bearing. An empty module list must never reach `unittest` — an argument-less `python -m unittest` *is* `discover`; both twins guard the call on a non-empty list. The `--` terminator keeps a module name from ever parsing as an option.

The guarantee is scoped the way 2026-07-13 scoped it: it guards the suite *list*, not the interpreter's import surface. The named suites run with the target's `scripts/` first on `sys.path`, so a target-authored module the install did not produce — including one shadowing a stdlib name — still executes on import. Installers still point only at trusted trees. Three measures narrow that surface. `-E` drops the caller's `PYTHON*` environment; `-B` and a pre-run `__pycache__` purge close the stale-bytecode channel the mtime-preserving copy would keep import-valid. Failure tails print with control characters stripped, so target-influenced output cannot rewrite the operator's terminal.

The package-chain `__init__.py` guard retires with discovery. A missing suite file is a loud import error; a missing `__init__.py` resolves as a namespace package and the suites still run. The doctor's runtime roster pins every shipped `__init__.py`, so package integrity has a deterministic owner. The zero-tests guard stays in both twins, skip-aware: a truncated copy imports clean and runs nothing, while a channel-keyed all-skipped run is healthy.

## Consequences

- A project-authored `test_*.py` anywhere in the target — including inside `scripts/tests/` — is never *run as a suite* by an install. Code it can still reach is the import surface conceded above.
- Both installers drop their package-chain guard; the two verification twins stay mirrored, and materialize's shrinks.
- A top-level `tests` without its `__init__.py` becomes a namespace package merging every `sys.path` root. The doctor roster's `__init__.py` pins are what keep that theoretical.
- A stale suite an older install left behind (the marketplace channel never removes files) is no longer executed; under discovery it ran and could fail loudly. Inert is the intended state for an unowned leftover.
- The 2026-07-17 contract-change line "a target-authored test file executes at install time" is reversed; that ADR carries a pointer here.

## Implementation

`harness/materialize.py` (`verify_runtime`), `harness/marketplace/setup.sh`, `harness/tests/test_materialize.py` (`TestVerifyRuntime`), the `PYTHON_M_ALLOWED` rationale in `harness/verify_harness/checks/confinement_ast.py`. The battery's sample-suite step still discovers, so it gains the zero-collection guard the install run retired (`harness/verify_harness/checks/suites.py`). The `/materialize` skill's guarantee sentence stands unchanged and is accurate again; its failure-output strings update to the aggregate scripts-run line.

## References

- [Materialize-Time Runtime Verification](2026-07-13-materialize-time-runtime-verification.md) — the guarantee this decision restores, at its original scope.
- [The Shipped Runtime Becomes Domain Packages](2026-07-17-runtime-package-layout.md) — the layout whose import needs discovery served; named modules serve them equally.
