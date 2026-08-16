# The Shipped Runtime Becomes Domain Packages Under a Composition Root

**Status:** Accepted (install-verification contract change reversed by [2026-08-16 exact-module-install-verification](2026-08-16-exact-module-install-verification.md))

> Reversed 2026-08-16, one aspect: the layout, the composition root, and the boundary gates all stand; only the install-verification contract change in Consequences is reversed. Verification names the installed modules exactly, restoring the 2026-07-13 never-a-target-glob guarantee.

## Context

After the typed migration, `scripts/` holds 17 flat files: five `handoff_*` siblings, three engines, one vendored module, seven test suites, one fixture. The layer map — schema is the ACL, records the model, route the policy, view the presentation — is reconstructable only from imports. Prefix names compress a missing folder into filenames; `brief_doctor` and `cc_accounting` do not say what they do. The test pyramid is real but unselectable. The typed-core ADR's own clause reopens the question when the core "still resists audit"; the maintainer reports it does. Spring Modulith supplies the missing pattern: modules as packages, launchers in a composition root, boundaries verified by a test.

## Options Considered

1. **Keep flat; add a README layer map and an import gate** — rejected: documents the structure without creating it; the folder still interleaves runtime, engines, tests, and fixtures.
2. **Author structured, materialize flattened** — rejected: breaks source-equals-shipped; a consumer stack trace would no longer match the maintained source.
3. **Thin entry shims delegating into per-package `cli.py` modules** — rejected: places the application layer inside a module and leaves a stub at the root; Modulith puts launchers in the composition root, above the modules.
4. **Domain packages under a composition root** (chosen) — entries stay applications; directories become modules; a gate enforces the graph.

## Decision

**`scripts/` becomes a composition root: root files are applications or single-file modules, directories are domain packages, and a battery gate enforces the one-way import graph.**

```
scripts/
├── handoff.py                # application: argparse + cmd_* composing handoff/
├── grading.py                # application: cmd_extract/review_plan over grading/ (renamed from score-change.py)
├── changeset.py              # application: the emit verb over changeset/ (entry ↔ package)
├── doctor.py                 # application + single-file module (renamed from brief_doctor.py)
├── doctor-expectations.toml  # its manifest (renamed from brief-expectations.toml)
├── accounting.py             # vendored single-file module (renamed from cc_accounting.py)
├── handoff/                  # schema.py, records.py, routing.py, view.py
├── changeset/                # config.py (exclude filter), git_facts.py, emit.py (the verb)
├── grading/                  # config.py, features.py, handoff_facts.py, planner.py (composes changeset/)
└── tests/                    # mirrors source: tests/handoff/test_records.py, tests/changeset/test_git_facts.py, …
```

Load-bearing details:

- **The trust-class cut: handoff.py splits by trust class into `handoff/`.** The file had reached about 4,600 annotated lines mixing three trust classes: the log's byte contract, the routing decisions, the board renderer. An audit or a change to one class had to hold the whole file in view. It splits along those seams — `schema.py` (strict parse, the draft-07 subset validator, canonical serialization), `records.py` (the typed model), `routing.py` (the decision tables), `view.py` (the board, kept whole). `handoff/__init__.py` declares the public API, replacing the entry's re-export block; `import handoff` resolves to the package. Imports are one-directional (entry → routing/view → records/schema). The entry contract `python3 scripts/handoff.py <cmd>` keeps identical flags, output bytes, and exit codes.
- **`grading/` is carved from score-change.py by role:** grading layout-config ACL, feature model, handoff-log gateway, and the pure risk-ladder planner. The entry keeps the CLI contract and its `cmd_*` handlers.
- **`changeset/` is carved from grading by neutrality.** The change set — what a reviewer and the grader both judge — is not grading; it was only ever grading's caller. So its git gateway (`git_facts`), its exclude-filter config slice, and the emit verb (`base_arg`, `_resolve_changeset`, `cmd_changeset`, now the `changeset.emit` module) move to a neutral `changeset/` package. `grading/` composes it. A dedicated `changeset.py` launcher replaces `grading.py changeset` behind the `changeset.sh` wrapper, so the reviewer roster no longer reaches through the grader for its own review scope. The entry is same-named as its package, like handoff and grading. `layout.toml` is read by two ACLs — `changeset.config` validates `exclude_globs`, `grading.config` the rest — each blind to the other's sections.
- **Entries are launchers, Modulith-style.** Root files may import modules; no module imports a root file. Module-internal graphs are declared: `schema` and `records` are leaves; `planner` imports no gateway. Cross-context traffic reaches the handoff log only through the validator API. A check-sync step verifies every static import from the `ast`; the one deliberate dynamic edge (the grading engine's lazy validator-API load) is named in the gate's table — [mechanical promises move into engines](2026-07-14-mechanical-promises-into-engines.md).
- **Renames replace opaque names.** `doctor.py`: the installation doctor outgrew "brief"; the repo already calls it the doctor. `accounting.py`: renamed at its producer (`tools/harness-stats`, outside the copy channel); the vendored copy, callers, and the byte-identity gate follow. `grading.py`: "score-change" matched no artifact-family name — the skill is change-grading, the agent change-grader, the records grader-*. The rename retires the one hyphenated, unimportable module name. It did not fully settle the `changeset.sh` dissonance, though: the wrapper still execed a *grading* engine to emit a neutral change set — the `changeset/` carve (above) closes that by giving the verb its own launcher. Every CLI rename updates every caller in the same slice it lands.
- **Tests mirror the source, Modulith-style.** One top-level `tests/` tree, one test module per source module, `__init__.py` files for `unittest` discovery. Shared scaffolding moves to its own module instead of living inside `test_handoff.py`. A suite lives once in core only if it is fully stack-agnostic — the handoff and changeset suites, and grading's engine pins. A suite entangled with a stack's real `layout.toml` stays per-stack. grading's suites were mixed on that line, so they split by it. The synthetic-layout engine pins single-source into core (`tests/grading/test_config.py`, `test_features.py`, and the whole `test_handoff_facts.py`/`test_planner.py`); the real-layout classification cases stay per-stack in `test_config_layout.py`/`test_features_layout.py` siblings. Single-sourcing the last triplicated classes retires the `SHARED_TEST_PINS` byte-identity gate (3j) that stood in for it — a hand-owned parallel is deleted, not guarded.
- **Execution is behavior-frozen, three slices:** first the `handoff/` move (file moves plus import edits), then the `grading/` carve, then the `changeset/` carve that lifts the neutral change-set layer out of grading. The golden-byte suites, the three stack suites, and a differential oracle (old vs new CLI, byte-identical transcripts) freeze behavior; docs and CLAUDE.md update as each slice lands.
- **Parked, with triggers:** typing the grading model (when isolation tests warrant it); splitting the view's primitives/composition seam (the typed-view decision); splitting the doctor (a second concern, such as auto-repair); decomposing maintainer-side check-sync.py, 2,166 lines, already authorized by [logic-in-python](2026-07-06-logic-in-python-orchestration-in-bash.md).

## Consequences

- Positive: the tree is the layer map; boundaries are checker-enforced, not conventional; the pyramid is selectable per module; package names decompress the prefixes (`handoff.records`); the two opaque names now self-describe; consumers browsing `scripts/` see the same structure the maintainer audits.
- Negative: the copy channel ships trees, not flat files — materialize, marketplace packaging, and every path list in check-sync update; `__init__.py` files join the shipped runtime; two CLI renames fan out to callers across samples and plugins; the interim flat-sibling layout is superseded by the package in the same migration. The shipped `scripts/` grows from 8 to 40 Python files, 11,182 to 17,108 lines per copy — the suites account for most of it and earn their place at install-time verification.
- Contract change: install-time verification (`setup.sh`, materialize) now runs `unittest` discovery over the target's `scripts/tests/`, so a target-authored test file executes at install time. The prior layout's "a project-authored `scripts/test_*.py` is never run as a suite" guarantee is retired; point installers only at trees you trust. (Reversed by [2026-08-16 exact-module-install-verification](2026-08-16-exact-module-install-verification.md).)

## Implementation

Two constraints, both prototype-verified, keep a same-named entry and package strict-checkable. mypy refuses `handoff.py` and `handoff/` in one build ("Duplicate module"), so the battery's mypy step runs the pyproject scope (packages plus root modules) first, then each same-named entry alone. All three launchers pair with a package of the same name (`handoff.py`↔`handoff/`, `grading.py`↔`grading/`, `changeset.py`↔`changeset/`), so all three run solo. A solo entry run resolves a bare `import handoff` to the entry itself, so the entries import submodule-form only (`from handoff.schema import …`, `from changeset.emit import …`) — the boundary gate enforces this mechanically.

## References

- [Handoff Log Access: Single Deterministic Tool](2026-06-11-handoff-log-access-tool.md) — the tool the `handoff/` carve refactors; its CLI contract is unchanged.
- [A Typed, Checker-Enforced Standard for the Harness Python Core](2026-07-17-typed-python-core.md) — its audit-resistance clause is the trigger; its script-shape bullet is amended here.
- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — stdlib-only and no-manifest hold (`__init__.py` is not a manifest); its script-shape clause is amended again.
- [Single Pricing Source via Vendored Copy](2026-07-13-single-pricing-source-vendored-copy.md) — the vendoring contract that keeps `accounting.py` a single file and carries its rename.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — the import gate outranks a documented convention.
