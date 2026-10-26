# The Harness Core Is Typed, Stdlib-Only Python in Domain Packages

**Status:** Accepted

## Context

The harness is Python glue in two trust tiers. The shipped runtime (`harness/core/scripts/`, the stack slices, the hooks) executes on a consumer's machine on every pipeline hop; `python3` is its one hard dependency. The producer tooling (`harness/*.py`, the battery, `tools/`) runs on the maintainer's. Before this decision the tooling was 4,800 lines of bash across 26 scripts, the two largest parsing JSON with jq and awk. The hooks guarding the pipeline contract had no unit tests. The Python that did exist carried zero annotations across 117 functions, so fail-closed routing was a tested property only. Three consumers price Claude Code usage from two install domains with no shared path: user-level `~/.claude/` tooling and the project-level vendored runtime. Every install runs the suites it copies in the consumer's tree, where `scripts/layout.toml` is a project-owned file the consumer is told to edit. The reference's thesis is engineering discipline; its own code must model it.

## Options Considered

1. **Keep bash, lean on shellcheck and bash test suites.** Rejected: shellcheck catches syntax hazards, not logic defects; a hook's parser cannot be unit-tested from bash.
2. **Rewrite everything in Python.** Rejected: thin command sequencers are idiomatic bash, and the generic stack's `stack.sh` verb stubs are a consumer-edited shell surface.
3. **Rewrite the core in Java 25 with sealed types.** Rejected: a JDK lands in every consumer's toolchain and the copy channel must ship a build. Typed Python recovers the enforceable gains.
4. **Keep dict-shaped records, trust the suite.** Rejected: nothing but the suite notices a record type no `match` arm handles.
5. **Keep `scripts/` flat; add a README layer map and an import gate.** Rejected: documents a structure without creating it.
6. **Author packages, materialize flattened.** Rejected: a consumer stack trace would no longer match the maintained source.
7. **Entry shims delegating into per-package `cli.py` modules.** Rejected: puts the application layer inside a module; Modulith puts launchers above the modules.
8. **A render step, a runtime read, or a package for the pricing module.** Rejected: one byte-identical file needs no transform; no path serves both install domains; the runtime is stdlib-only.
9. **Package the producer tier like the runtime.** Rejected: renaming seven path-invoked CLIs fans out across about 40 files to buy an import-by-name the tier already has through `registry.py`.
10. **Flat sibling modules for the battery** (`check_sync_text.py`, …). Rejected: re-introduces prefix-compressed names and re-clutters the harness root.
11. **Vendored layout suites that skip, that the project owns, or that restate the skeleton.** Rejected: a skip asserts nothing. A project-owned test under the harness tree is the orphan materialize prunes. A restated parallel is deleted, not guarded.
12. **A language boundary, a typed checker-held standard, domain packages under a composition root, gated vendoring, and suites that assert only harness-owned facts** (chosen).

## Decision

**Logic is typed, stdlib-only Python under battery gates; bash only sequences commands; the shipped runtime is domain packages under a composition root; a vendored suite asserts nothing a project owns.**

**The language boundary.** A script that parses structured data, transforms text, or branches on content is logic and is Python with tests. A script that runs a fixed command sequence and stops on failure is orchestration and stays bash. The permanent bash: `materialize-samples.sh`, `propagate-harness.sh`, `release-version.sh`, `registry.sh`, `review-survey.sh`, `marketplace/setup.sh`, the three `test-*.sh` install suites, and the `gate.sh`/`stack.sh` verb surface.

**The shipped contract.** Standard library only, Python 3.11+, `unittest`. No dependency manifest in any shipped tree; `__init__.py` is not a manifest. Battery step 1c scans every tree that reaches a consumer and enforces the stdlib-only property.

**The typed standard.** Records are frozen dataclasses. `HandoffRecord` is a union routed by `match` ending in `typing.assert_never`, so a new record type fails the type check until every arm handles it. Dicts survive only at the parse boundary and three sanctioned routing uses. One lenient lift per record type turns a dict into its dataclass, and the schema validator alone owns requiredness. Strict parsing rejects duplicate keys and pins `encoding="utf-8"`. `ruff format --check`, `ruff check`, and `mypy --strict` are battery steps 1d to 1f; the config lives in the root `pyproject.toml`. A script joins `[tool.mypy].files` when it lands strict-clean; the scope today spans the shipped packages, the producer scripts, the battery, the eval bench, `tools/agent-dev`, and `tools/deck`. Producer code meets the grading-tier bar: complete annotations, `Any` only at the `tomllib` and subprocess boundaries, named types for stable tables (`TOOLS` is a `TypedDict`).

**The shipped layout.** `scripts/` is a composition root. Root files are applications or single-file modules (`handoff.py`, `grading.py`, `changeset.py`, `doctor.py`, `accounting.py`, `backlog.py`); directories are domain packages (`handoff/`, `grading/`, `changeset/`); `tests/` mirrors the source. Root files import modules; no module imports a root file; `schema` and `records` are leaves; cross-context traffic reaches the log only through the validator API. Battery step 1g verifies every static import from the `ast`. Entries import submodule form only, because mypy refuses a same-named file and package in one build; step 1f runs the pyproject scope first, then each entry alone. Engines are invoked as `python3 scripts/<engine>.py <verb>`; no shell wrapper fronts a Python engine. A stack-agnostic suite lives once in core; a suite reading a stack's layout stays per stack. Install-time verification names the installed modules exactly, never a target-tree glob.

**The vendored pricing module.** `tools/harness-stats/accounting.py` is canonical; `harness/core/scripts/accounting.py` is its vendored copy, synced by `cp`. Step 2d byte-compares the pair, even under `--quick`. `cache-report.sh` reads the multipliers at run time and keeps rate literals only as a python3-less fallback; those literals can drift only on a host without python3. `tools/harness-stats/harness-statusline.sh` carries no rate value.

**The producer tier.** `harness/*.py` stays flat with its hyphenated, path-invoked names; its suites sit under `harness/tests/`, loaded through one shared `_loader.py`, with the shell install suites beside them. `tools/agent-dev/tests/` imports by name. The battery is the tier's one package: `verify-harness.py` is a thin launcher whose docstring is the authoritative step list, over `verify_harness/` (`text.py`, `battery.py`, `checks/{lint,sync,suites,confinement,confinement_ast}.py`). The hyphen keeps the launcher from clashing with the package. Names encode scope. `-harness` marks a tool acting on the whole reference; a tool building one derived tree names the tree; `refresh-<slice>` marks an in-place consumer update; `registry` holds the shared facts.

**Vendored suites assert harness-owned facts.** A stack slice's suites exercise the engine's module strategies on synthetic layouts and read the stack's `layout-defaults.toml` directly. The consumer's `scripts/layout.toml` is asserted only through the loader: it loads, its tables validate, its roster meets the four-reviewer floor. `harness/tests/test_stack_layouts.py` classifies a representative tree against each init skeleton, and the faithfulness step holds each sample's `layout.toml` byte-identical to its skeleton.

**Parked, with triggers.** The grading model is typed when isolation tests warrant it. The view's primitives/composition seam splits when the typed-view work reaches it; the doctor splits on a second concern, such as auto-repair. A second vendored module makes a render step the cheaper mechanism, and the vendored-copy rule is revisited at that point.

## Consequences

### Positive

- The hooks gain unit tests and handle JSON with `json`, dropping jq; routing exhaustiveness and the import graph are checker-held, not review-held.
- The tree is the layer map; package names replace prefix-compressed filenames; three opaque names (`score-change`, `brief_doctor`, `cc_accounting`) retired.
- A pricing change is one file plus a gated copy; a consumer may reshape its layout and the install stays green.
- `ls harness/` shows source only; a new producer script has a naming rule.

### Negative

- Every PreToolUse call pays Python startup, about 30 ms where bash paid about 5 ms.
- The maintainer toolchain needs ruff and mypy. The shipped `scripts/` grew from 8 to 40 Python files (11,182 to 17,108 lines per copy) at the package cut, most of it suites.
- The copy channel ships trees, so materialize, packaging, and every path list track the layout.
- Before the suite narrowing, a Java consumer with a multi-module layout failed every materialize: its two suites ran 14 tests and failed 21 times.

## Implementation

`docs/harness-code-standards.md` realizes the standard; `docs/harness-system-design.md` records the package contracts; `docs/harness-testing-principles.md` the suite layout rows. `harness/README.md` documents the toolbox.

## References

- [The Maintainer Workflow Is Tiered](2026-07-02-tiered-maintainer-workflow.md) — the battery that holds every gate named here, and the push gates that make them non-skippable.
- [The Handoff Ledger](2026-05-08-the-handoff-ledger.md) — `handoff.py`, the first logic-in-Python script and the owner of the typed record model.
- [Deterministic Routing Engines](2026-07-02-deterministic-routing-engines.md) — the fail-closed routing the union type and `assert_never` now guard.
- [The Change Grader](2026-06-05-the-change-grader.md) — the `grading/` and `changeset/` packages and the per-stack layout suites.
- [Materialize](2026-06-11-materialize.md) — install-time verification by exact module name, and the orphan pruning that bars project-owned tests under the harness tree.
- [Layout Declares the Project](2026-06-14-layout-declares-the-project.md) — the project-owned `layout.toml` a vendored suite reads only through the loader.
- [Distribution Channels](2026-06-14-distribution-channels.md) — the copy channel whose file-copy simplicity the stdlib-only contract preserves.
- [Confined Agent Tools](2026-07-16-confined-agent-tools.md) — the `tools/agent-dev` tier held to the same typed bar.
- [Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — a deterministic gate outranks a documented convention, the rule behind every gate above.
- `docs/harness-code-standards.md`, `docs/harness-system-design.md`, `docs/harness-testing-principles.md` — the standard, the design, and the suites this decision governs.
