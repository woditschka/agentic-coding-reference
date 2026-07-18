# The Deterministic Battery Is Renamed `verify-harness`

**Status:** Accepted

## Context

`harness/check-sync.py` names one of its steps. Its own PASS line reads "lint, syntax, parity, faithfulness, invariants, tests, doctors, marketplace" — eight categories, of which "sync" (parity plus faithfulness) is two. Across the ~25 steps the launcher dispatches, "sync" describes roughly one; the rest are static analysis, type checking, unit and integration suites, the doctor, the real plugin install, and marketplace acceptance. The name frames the whole battery as a narrow derived-tree parity check. A reader cannot tell from it that this is the tier-0 gate every commit and push must pass.

This is inaccuracy, not opacity. [producer-side-tests-subdir](2026-07-18-producer-side-tests-subdir.md) deliberately declined to rename the hyphenated leaf CLIs — `refresh-settings.py`, `refresh-gitignore.py`, `deps-report.py` — because those names are correct; renaming them is churn without benefit. `check-sync` is the opposite case: its name is wrong about what it does. That is the exact criterion [runtime-package-layout](2026-07-17-runtime-package-layout.md) used to retire three names — `score-change → grading`, `brief_doctor → doctor`, `cc_accounting → accounting` — when it held that names must self-describe. So this rename applies an established repo standard, not a new preference.

A self-describing name already exists in the maintainer vocabulary. Two sibling commands frame the reference's checks: `audit-harness` (judgment, tiers 1–2) and `review-harness` (improvement review). The deterministic tier-0 gate is their missing sibling. `verify-harness` completes the family, and the relationship is real, not cosmetic — `audit-harness` runs this tool as its layer-1, so "audit-harness invokes verify-harness" reads correctly.

This rename follows [check-sync decomposition](2026-07-18-check-sync-decomposition.md); it renames the launcher that ADR produced and the `check_sync/` package beneath it. It lands as its own change so the decomposition stays behavior-frozen and the rename stays purely mechanical.

## Options Considered

1. **Keep `check-sync`** — rejected: it preserves the status-quo defect, a name that describes one step and mis-frames the battery.
2. **`verify.py` over a `verify/` package** — rejected: a bare, importable entry name reintroduces the same-named-entry "Duplicate module" caveat the hyphen sidesteps, forcing the runtime ADR's pyproject-then-solo mypy dance. It also drops the `-harness` family symmetry.
3. **`verify-reference`** — rejected: the project is "Agentic Coding Reference," so the word fits, but the `audit-harness`/`review-harness` family symmetry outweighs avoiding a repeated word.
4. **`verify-harness.py` over a `verify_harness/` package** (chosen) — self-describing, joins the family, keeps the hyphen and its mypy benefit.

## Decision

**`check-sync.py` is renamed `verify-harness.py`, and its package `check_sync/` is renamed `verify_harness/`. The CLI contract — flags, output bytes, exit codes, and the authoritative header step-list — is unchanged; only the name and the package directory change.**

Load-bearing details:

- **The hyphen is kept on purpose.** `verify-harness.py` is invoked by path and imported by nothing, so the hyphen costs nothing at call sites. Because it is not a valid module name, it cannot clash with `verify_harness/` — the "Duplicate module" problem does not arise, exactly as under `check-sync`. The launcher is mypy-checked as a file-path argument; the package runs on the pyproject scope; no solo-entry dance.
- **The package renames, its contents do not.** `verify_harness/` carries over the [decomposition](2026-07-18-check-sync-decomposition.md) unchanged: `text.py`, `battery.py` (with `class Battery`), and `checks/{lint,faithful,suites}.py`. Only the directory name and the intra-package import prefix (`check_sync` → `verify_harness`) change. The one-directional import graph and its step-1g boundary gate move with it.
- **The step-list header is preserved verbatim.** The launcher's docstring enumeration is the canonical list other docs reference; the rename does not touch its text.
- **Every path caller is rewritten in one pass.** The tool is referenced by path across the repo; each reference moves to `harness/verify-harness.py` in the same change, so no caller points at a missing file.

## Consequences

- Positive: the tier-0 gate self-describes and completes the `verify`/`audit`/`review`-harness family; a reader learns the tool's job from its name; the maintainer-loop prose reads as three named tiers.
- Negative: the rename fans out across about 40 files that name the tool by path — CI (`.github/workflows/checks.yml`), the pre-push hook (`.githooks/`), the root `CLAUDE.md` and its maintainer loop, the skills (`audit-harness`, `deps-upgrade`, `research-update`), `harness/README.md`, `docs/`, `release-prep.sh`, and `bootstrap.sh`. The change is mechanical but wide, and the battery must be green under the new name before it can gate its own rename.
- Non-consequence: the CLI contract is identical — flags, output, exit codes, the header step-list, and behavior are unchanged; no other producer script is renamed; the decomposition's structure is untouched. Historical ADRs keep their `check-sync` references; the decision log is a historical record, not a living reference, per repo precedent.

## Implementation

The rename lands after the decomposition commits, as one mechanical pass: `git mv harness/check-sync.py harness/verify-harness.py`, `git mv harness/check_sync harness/verify_harness`, the intra-package prefix rewrite, and the ~40-file path-reference sweep. The pyproject mypy scope and the step-1g boundary table follow the package name. Verification is `release-prep.sh` green under the new name — the renamed battery linting, type-checking, and import-gating its own renamed package is the self-test.

## References

- [check-sync.py Becomes a Thin Launcher Over a `check_sync/` Package](2026-07-18-check-sync-decomposition.md) — produces the launcher and package this ADR renames; lands first.
- [The Shipped Runtime Becomes Domain Packages Under a Composition Root](2026-07-17-runtime-package-layout.md) — the rename precedent: names must self-describe; retired `score-change`, `brief_doctor`, `cc_accounting`.
- [Producer-Side Toolboxes Separate Tests From Source, Without Packaging](2026-07-18-producer-side-tests-subdir.md) — declined to rename accurate hyphenated CLIs; this rename clears the higher bar of a name that is wrong.
