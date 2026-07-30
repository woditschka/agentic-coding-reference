# Producer-Side Toolboxes Separate Tests From Source, Without Packaging

**Status:** Accepted

## Context

Two producer-side toolboxes interleave their unit suites with their source. `harness/` holds nine scripts (`check-sync.py`, `materialize.py`, `init.py`, the three `refresh-*.py`, `deps-report.py`, `package-marketplace.py`, `helpers.py`) plus `claude-md/refresh-chapters.py`, with seven `test_*.py` and three `test-*.sh` suites beside them in the same listing. `tools/claude-dev/` holds `egress_rules.py` and `ide_preflight.py` with their two `test_*.py` beside them. `ls harness/` returns source and tests mixed.

This flat layout was never decided. It predates the shipped-runtime restructure ([runtime-package-layout](2026-07-17-runtime-package-layout.md), 2026-07-17), which moved `scripts/` from flat siblings to domain packages with a mirrored `tests/` tree. That ADR is scoped to the shipped runtime and never addresses the producer side; it parks the producer-side `check-sync.py` decomposition explicitly. `test_helpers.py` was added flat on 2026-07-18, after the restructure — the pattern is a leftover carried forward, not a chosen endpoint.

The runtime earned its package for two reasons the producer side lacks. It ships — source-equals-shipped, install-time `unittest` discovery, consumer stack traces must match maintained source. And it was decomposing 4,600-line files with opaque prefix names into a layer map. The producer-side scripts ship nothing and are already single-purpose tools; only `check-sync.py` is large, and its split is separately parked under [logic-in-python](2026-07-06-logic-in-python-orchestration-in-bash.md). The tier sits at the grading-tier bar, not the frozen-dataclass rigor ([typed-python-core](2026-07-17-typed-python-core.md)).

The tier's reuse is already extracted, which removes the second rationale too. `helpers.py` holds the shared spine — the `STACKS`/`TOOLS`/`CHANNELS` registry, `detect_stack`, `read_harness_layout` — as one module imported by name by `check-sync`, `init`, `materialize`, and `package-marketplace`. Every other script imports only `helpers` and the standard library; no tool imports another. The only hyphenated names are leaf entry-points nothing imports. Packaging the tier would therefore add no module boundary and grant an import-by-name the reused code already has — it would only rename CLIs no code calls. The lone file with a real domain seam, `check-sync.py` at 2,185 lines across a `helpers`/`battery` split, is a separate decomposition recorded on its own.

## Options Considered

1. **Keep flat** — rejected: the status quo is a pre-restructure leftover, not a decision, and leaves the interleaving unaddressed.
2. **Full package, like the runtime** — rename the seven hyphenated CLIs to underscores, add `__init__.py`, import by name, mirror a `tests/` tree. Rejected: the rename fans out across about 40 files — CI, the pre-push hook, CLAUDE.md, the skills, a dozen docs — because each name is invoked by path. The runtime paid that tax while decomposing and shipping; the producer side does neither. Renaming user-facing command names to buy import-by-name alone is churn without a payer.
3. **Move `test_*.py` into `tests/`, keep each test's ad-hoc `spec_from_file_location`** — rejected: it unmuxes the folder but scatters the path-load boilerplate the runtime ADR named as the smell. Tidiness without fixing the pattern.
4. **A `tests/` subdir per toolbox plus one shared loader** (chosen) — separates the suites, centralizes the path-load, and leaves source and CLI names untouched.

## Decision

**Each producer-side toolbox gets a `tests/` subdir mirroring its source; a shared `_loader.py` centralizes the path-load for the harness suites that load by module path. Source files and their hyphenated CLI names are untouched; the tier does not become a package.**

```
harness/
├── check-sync.py, materialize.py, init.py, refresh-*.py, …   # source, names unchanged
├── claude-md/refresh-chapters.py
└── tests/
    ├── _loader.py            # load(name) resolves against the toolbox root, one dir up
    ├── test_check_sync.py, test_materialize.py, test_init.py, test_refresh_*.py
    ├── test-marketplace.sh, test-plugin-install.sh, test-generic-stack.sh
    └── claude-md/test_refresh_chapters.py

tools/claude-dev/
├── egress_rules.py, ide_preflight.py
└── tests/
    ├── __init__.py          # sources are valid module names, imported by name via
    │                        #   `unittest discover` from the toolbox root — no loader needed
    └── test_egress_rules.py, test_ide_preflight.py
```

Load-bearing details:

- **Not packaging is the point, and it is why the names hold.** The harness tests already load their target by path (`spec_from_file_location`), which handles a hyphenated filename that `import` cannot. (The `claude-pod` sources are already valid module names, so those suites import them directly and run via `unittest discover`.) Import-by-name is the only mechanism that would force `check-sync.py` → `check_sync.py`, and it is the only thing this ADR declines. So every invoked command name — `harness/check-sync.py`, `harness/refresh-agent-bodies.py` — stays, and CI, the pre-push hook, the skills, and the docs are not touched.
- **One loader replaces the scattered boilerplate.** Six of the eight suites hand-roll `_HERE = Path(__file__).resolve().parent` then `spec_from_file_location`. After the move the target sits one directory up; rather than spread `.parent` across every file, `tests/_loader.py` owns the resolution and exposes `load("materialize")`. That is the honest improvement that keeps this from being option 3.
- **The bash integration suites move too.** `test-marketplace.sh`, `test-plugin-install.sh`, and `test-generic-stack.sh` are tests muxed into the root as much as the `.py` suites; they join `tests/`. The production orchestrators — `bootstrap.sh`, `release-prep.sh`, `release-version.sh`, `review-survey.sh`, `helpers.sh` — stay at the root; they are not tests.
- **`tests/` mirrors the toolbox tree.** `claude-md/refresh-chapters.py` keeps its test at `harness/tests/claude-md/test_refresh_chapters.py`, matching the runtime's whole-tree mirror. `tools/harness-stats/accounting.py` has no unit suite beside it — it is guarded by the byte-identity gate — so nothing moves there.
- **The battery updates its discovery, not its steps.** Step 6's glob (`HERE.glob("test_*.py") + HERE.glob("*/test_*.py")`) becomes a `tests/`-rooted glob; step 6b runs `unittest discover` over each `tools/*/tests/` from its toolbox root; the shell-suite `run_suite` paths repoint to `harness/tests/`. The step list in the `check-sync.py` header is unchanged.
- **`check-sync.py` stays whole.** This ADR moves its *test* into `tests/`; the engine's own decomposition remains parked under logic-in-python.

## Consequences

- Positive: `ls harness/` and `ls tools/claude-dev/` show source only; every suite lives under one `tests/`; the harness path-load is centralized in a shared loader; both producer-side toolboxes match; zero CLI or caller churn.
- Negative: the battery's two discovery globs and the shell-suite paths update; a new `_loader.py` convention joins the tier; the `harness/README.md` tree and the CLAUDE.md references to `test_*.py` update; the producer side deliberately diverges from the runtime's *packaged* shape, so a reader must know the tier distinction — documented here.
- Non-consequence: no name changes, so nothing fans out to CI, the pre-push hook, the skills, or consumer-facing docs — the surface option 2 would have churned.

## References

- [The Shipped Runtime Becomes Domain Packages Under a Composition Root](2026-07-17-runtime-package-layout.md) — the shipped-tier analog; this is the producer-side counterpart that deliberately stops short of a package because the tier neither ships nor decomposes.
- [A Typed, Checker-Enforced Standard for the Harness Python Core](2026-07-17-typed-python-core.md) — sets the producer-side grading-tier bar; this ADR fixes that tier's test layout.
- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — stdlib-only holds (`_loader.py` adds no dependency); the `check-sync.py` decomposition stays parked there.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — the lowest-churn change that removes the real defect.
