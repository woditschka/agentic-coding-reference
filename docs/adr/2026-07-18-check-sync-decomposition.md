# check-sync.py Becomes a Thin Launcher Over a `check_sync/` Package

**Status:** Accepted

## Context

`harness/check-sync.py` is 2,185 lines and 46 top-level symbols: nine pure text helpers, the `Battery` aggregator with two run helpers, thirty-odd `check_*` step functions, and `main`. Its own banners already draw the seam — `# --- pure helpers ---` and `# --- the battery ---` — and its docstring records the split it half-made: "Pure helpers are unit-tested by test_check_sync.py." The layer map is comment-only. An audit of one check holds the whole file in view, and the nine pure helpers are reachable only by path-loading the 2,185-line module.

This decomposition is not new work; it is parked work. [logic-in-python](2026-07-06-logic-in-python-orchestration-in-bash.md) authorized decomposing maintainer-side `check-sync.py`. [runtime-package-layout](2026-07-17-runtime-package-layout.md) named it explicitly in its Parked section while it restructured the shipped runtime. This ADR unparks it.

It is also the single exception to [producer-side-tests-subdir](2026-07-18-producer-side-tests-subdir.md). That ADR keeps the producer-side tier flat and unpackaged, because its reuse is already factored into `helpers.py` and its tools are already single-purpose files. One file breaks that rule: `check-sync.py` alone carries a real domain seam. So one file alone earns a package — on maintainability grounds, disturbing no other script and renaming no other CLI.

## Options Considered

1. **Keep the flat 2,185-line file, lean on the section banners** — rejected: documents the structure in comments without creating it; one check still opens the whole file, and the pure helpers stay path-load-only.
2. **Flat sibling modules at the harness root** (`check_sync_text.py`, `check_sync_battery.py`, `check_sync_checks.py`) — rejected: re-introduces the prefix-compressed names the runtime ADR retired, and re-clutters the harness root the tests-subdir ADR just cleared. Same move cost, no real namespace.
3. **A `check_sync/` domain package under a thin launcher** (chosen) — the launcher stays an application; the checks become modules grouped by the evidence they read; a graph keeps imports one-directional.

## Decision

**`check-sync.py` becomes a thin launcher over a `check_sync/` package: pure text helpers, the `Battery` aggregator, and the checks grouped by kind. The launcher keeps the authoritative step-list header and the ordered dispatch. The CLI contract is byte-identical.**

```
harness/
├── check-sync.py            # launcher: the authoritative step-list header, argv (--quick/--strict),
│                            #   and the ordered dispatch in main(); hyphen kept (invoked by path)
└── check_sync/
    ├── __init__.py
    ├── text.py              # the 9 pure, unit-tested helpers: strip_frontmatter, norm_links,
    │                        #   section_rows, _fence_state, h2_headings, severity_headings,
    │                        #   github_slug, heading_anchors, tag_findings, is_binary, read_text, rel
    ├── battery.py           # class Battery, git_status, _shell_scripts — the aggregator + run harness
    └── checks/
        ├── __init__.py
        ├── lint.py          # static tools: shellcheck, bandit, ruff_format, ruff_lint,
        │                    #   mypy (+_mypy_scope), import_boundaries (+_import_deps),
        │                    #   stdlib_only, python_syntax
        ├── faithful.py      # rendered-tree parity/content: agent_body_parity, accounting_sync,
        │                    #   render_faithful, faithfulness, layout_invariants, roster_sync,
        │                    #   placeholder_gate, handbook_delta, verdict_enums,
        │                    #   stack_agnostic_core, root_links, parity_gates
        └── suites.py        # subprocess suite runners: sample_suites, build_file_refs,
                             #   sample_doctors, unit_suites, tools_install_complete,
                             #   pod_toolchain_pins, tools_suites, marketplace_faithfulness
```

Load-bearing details:

- **The seam is already drawn.** The file's own banners and its "unit-tested by test_check_sync.py" docstring mark the pure/impure line. The nine pure helpers become `check_sync.text`, importable by name; `test_check_sync.py` — now at `harness/tests/` after the tests-subdir ADR — imports `from check_sync.text import …` instead of path-loading the whole module to reach them.
- **Checks group by the evidence they read, not by step number.** `lint.py` shells out to static tools; `faithful.py` compares re-rendered trees; `suites.py` runs subprocess test suites. The step numbers are a dispatch sequence, not a module boundary — they stay one ordered list in `main()`.
- **The launcher keeps the authoritative header verbatim.** The docstring step list is the canonical enumeration docs reference; it must not move. `main()` keeps `--quick`/`--strict`, the aggregate-don't-stop-at-first-failure behavior, the step 3 bootstrap-abort exception, and the exit codes.
- **The hyphen sidesteps the duplicate-module caveat.** The launcher stays `check-sync.py` — invoked by path from `release-prep.sh`, the pre-push hook, `checks.yml`, and `--quick` callers; nothing imports it. Because `check-sync.py` is not a valid module name, it cannot clash with `check_sync/`. The runtime ADR's same-named-entry "Duplicate module" problem does not arise: the package runs on the pyproject scope, the launcher is mypy-checked as a passed file path, and no solo-entry dance is needed.
- **Scope discipline.** Only `check-sync.py` is touched. No other producer script moves; no CLI is renamed; `helpers.py` stays a flat shared module — its minor registry/layout seam is parked, not opened here. The package's internal graph is one-directional (launcher → checks → battery, text), and is brought under the same import-boundary gate (step 1g) that already guards `scripts/` — extending that gate to a producer-side package is new work this ADR takes on, so the boundary is checker-enforced from the first slice.
- **Behavior-frozen execution.** The battery is its own differential oracle: run the old file and the new package over the same tree, require identical aggregated output and exit code. Slices land lowest-risk-first — lift `text.py`, then `battery.py`, then the three `checks/` modules — with the oracle green after each.

## Consequences

- Positive: the tree is the check taxonomy; the pure helpers are importable, not path-loaded; a change to one check family opens one module, not 2,185 lines; the authoritative step list stays put in the launcher.
- Negative: the harness gains a `check_sync/` tree; the two path-based self-checks the battery runs on its own directory (`stdlib_only`, `import_boundaries`) must learn the new package; the interim flat file is superseded in one migration.
- Non-consequence: the CLI, header step list, flags, output bytes, exit codes, and every path caller are unchanged; no other producer-side script moves; the tier stays flat per its ADR.

## Implementation

The trigger [logic-in-python](2026-07-06-logic-in-python-orchestration-in-bash.md) authorized and [runtime-package-layout](2026-07-17-runtime-package-layout.md) parked is now unparked. mypy runs the pyproject scope (packages plus root modules) and then the launcher as a file-path argument; the hyphen keeps the two disjoint. `__init__.py` is not a manifest, so stdlib-only holds. Each slice keeps the CLI contract identical and is gated by the differential oracle before the next lands.

## References

- [The Shipped Runtime Becomes Domain Packages Under a Composition Root](2026-07-17-runtime-package-layout.md) — the shipped-tier precedent; parked this exact decomposition; its differential-oracle and import-gate techniques carry over.
- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — authorized the `check-sync.py` decomposition; stdlib-only and no-manifest hold.
- [Producer-Side Toolboxes Separate Tests From Source, Without Packaging](2026-07-18-producer-side-tests-subdir.md) — keeps the tier flat because reuse is already factored; this is its single named exception, and it moved `test_check_sync.py` into `harness/tests/`.
- [A Typed, Checker-Enforced Standard for the Harness Python Core](2026-07-17-typed-python-core.md) — the producer-side `mypy --strict` bar the new package must meet.
