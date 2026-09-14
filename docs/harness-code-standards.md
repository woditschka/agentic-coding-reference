# Harness Code Standards

The harness ships a code bar to every consumer: the conjunctive bar in the `tdd-workflow` skill's [`tdd-principles.md`](../harness/core/.claude/skills/tdd-workflow/tdd-principles.md) and the stack `code-quality-review` checklists. This document is that bar realized for the harness's own code: the shipped Python runtime, the producer tooling, the battery, the eval bench, and the user-level tools. The same reviewer that grades a consumer's Java or Go grades this Python. A rule here is either enforced by the battery or checked in review; the table in [The Gate](#the-gate) says which.

The standard has one organizing idea: code reads cold. A competent engineer opening a module in two years, without the commit history, understands what it does from its names and its shape. The why comes from the design document and the decision log. Names carry the what. [`harness-system-design.md`](harness-system-design.md) and [`docs/adr/`](adr/README.md) carry the why. A comment carries only the residue neither of those can hold.

Sections follow: the baseline the code targets, then names, function shape, types, comments, error handling, modern idiom, and shell. The gate that enforces the mechanical subset and the review checklist that covers the rest close the document.

## Baseline

| Aspect | Rule | Source of the rule |
|---|---|---|
| Language level | Python 3.11 | [ADR: logic in Python, orchestration in bash](adr/2026-07-06-logic-in-python-orchestration-in-bash.md) |
| Dependencies | Standard library only in every tree; the shipped trees are gated, the producer trees follow by convention | [`harness/README.md` § The stdlib-only invariant](../harness/README.md#the-stdlib-only-invariant) |
| Test framework | `unittest`, discovered by the battery; no third-party runner | same ADR |
| Type checking | `mypy --strict` over the typed scope in `pyproject.toml` | [ADR: typed Python core](adr/2026-07-17-typed-python-core.md) |
| Formatting | `ruff format`, defaults | same ADR |
| Shell | bash 3.2 compatible, orchestration only | same ADR; the macOS floor is stated in [`tools/harness-stats/README.md`](../tools/harness-stats/README.md) |

## Names

Names are accurate, and their length is proportional to their scope. A single letter is correct inside a three-line comprehension and wrong as a parameter of a function that spans a screen. The vocabulary is the harness's own, as [`glossary.md`](glossary.md) defines it: a ledger entry is a `record`, never a `rec`; the layout table is a `layout`, never a `cfg`.

- A module is named by what it holds, a function by what it does or returns. Actions read verb-first (`render_view`, `resolve_roster`); queries read as nouns or predicates (`latest_build_pass`, `is_stale`).
- No `util`, `common`, or `misc` module. A function without a domain home has not found its abstraction yet. A module of pure functions over one type the project does not own is the Python form of the utility class and is named for that type (`paths`, never `helpers`).
- No abbreviation outside a scope of a few lines. Three short forms count as words in this code base: `args` for a parsed argument namespace, `exc` inside an `except` clause, `md` as a Markdown format tag.
- No type name repeated in a member name: `roster.resolve()`, not `roster.resolve_roster()`.
- A boolean parameter is keyword-only, so a call site names it: `render(entries, color=False)`.
- A constant with cross-module meaning has one defining module and is imported from there. A literal that carries meaning is named at its first use; a bare `3` in a comparison is a defect.

## Single Level of Abstraction

A function body reads at one level of abstraction. It calls functions one level down, or composes siblings at its own level, and never reaches up; a module lists its functions in that descending order (the Stepdown Rule). A body that scans the ledger, decides policy, and formats prompt text in one pass is three functions. The mechanical limits are the ones the battery enforces; the design rule is the reason they exist. The test pyramid follows the same levels, as [`harness-testing-principles.md`](harness-testing-principles.md#test-pyramid) states.

| Limit | Value | Enforced by |
|---|---|---|
| Cyclomatic complexity | 10 | ruff `C901` |
| Parameters | 4; a frozen record carries more | ruff `PLR0913` |
| Branches, returns, statements | ruff defaults | ruff `PLR0912`, `PLR0911`, `PLR0915` |
| Nesting | guard clauses first; a body never needs a fifth indent | review |

- Boundaries validate, internal code trusts its contracts. A private function receives typed records and never re-checks them.
- A repeated computation or condition at sibling sites is written once. The text and Markdown renderers of one view share their grouping and differ only in their span formatting.
- No speculative generality: an abstraction earns its place at the second real call site, not before.

## Records and Types

The typed standard is [ADR: typed Python core](adr/2026-07-17-typed-python-core.md) with its producer-side amendment; this section states the shape it produces.

- Data crossing a function boundary is a frozen dataclass with `slots=True`, or a `NamedTuple` when it is two or three fields with no behavior. A dataclass earns its class with a method, a default, or an invariant its docstring states. A raw `dict` survives only at the parse boundary (JSON, TOML, subprocess output) and at the routing core's sanctioned raw sites the ADR names.
- Every `match` over a record union ends in `typing.assert_never`.
- `Any` appears only at a parse boundary, and each site carries `# noqa: ANN401`. The marker is the boundary's declaration; a module whose `Any` count grows has moved its boundary inward.
- A closed vocabulary is a `Literal` or an `Enum`, never a documented set of strings.
- A seam another module implements is a `Protocol`. A tuple with meaning is a `NamedTuple` or a `TypeAlias` named for the meaning.
- Construction is one entry point per type. A record is built through its constructor with every mandatory field; a test builds it the same way.

## Comments and Doc Comments

Comments explain why. A comment that restates what the code does is deleted; a comment a better name would make redundant is a rename. The remaining comments are short: one to three lines naming a constraint the code cannot express, such as a platform quirk or a fail-closed choice.

- No decision history in code. "Since the July decomposition" and "moved here from check-sync" are ADR content. Prose describes the current state as if it always held.
- No citations in code. An ADR reference, a battery step number, or a requirement id belongs in [`harness-system-design.md`](harness-system-design.md), in the ADR index, or in the covering test. Code cites nothing.
- No comment addressed to an agent or to a reader in the second person.
- A public function, class, and module carries a docstring of one sentence in the imperative mood stating its purpose. It never restates the signature, never lists parameters, and never enumerates the cases the tests already name.
- A module docstring is one purpose sentence, plus at most one sentence naming its layer when the design document's package map needs the anchor.
- A test module docstring, when present, is one sentence. The guards a suite pins are its test names, not a numbered list above them.

## Errors, Exit, and Reporting

- An error carries the context a person needs at the point of failure: the path, the record line, the expected shape. `raise ValueError("bad input")` is a defect.
- No blind `except Exception`. The one sanctioned shape is a read-only overlay that must never take its host down, such as the board's cost overlay; that site carries `# noqa: BLE001` and a one-line why.
- A library function raises; a composition root decides the exit code. `sys.exit` appears only in a `main` or in the `if __name__ == "__main__": raise SystemExit(main())` idiom.
- Each application reports through one function that writes to stderr, so the report shape is uniform and testable. Scattered `print(..., file=sys.stderr)` calls are consolidated as a module is passed.
- `subprocess.run` states `check=` explicitly and passes `text=True`. A command's failure is either raised or read from `returncode` in the next statement.
- Paths are `pathlib.Path` end to end. `os.path` does not appear.
- A timestamp is timezone-aware.

## Modern Idiom

The code targets Python 3.11 and uses its idiom where the idiom is clearer than the alternative, not for its own sake.

- `match` for dispatch over a record union; `if`/`elif` for two or three arms.
- `tomllib` for TOML, `json` for JSON, both at the boundary module only.
- `dataclasses.replace` for a modified copy; no hand-written `with_` methods on records.
- f-strings for all formatting. `str.join` over a comprehension for lists.
- `functools.cache` for a pure, repeatedly called reader; no module-level mutable caches.
- Comprehensions and generator expressions over accumulator loops when the result is one expression.
- `from __future__ import annotations` is absent; the target version needs no deferral.

## Shell

Shell scripts orchestrate; they hold no roster and no logic that Python can hold ([ADR: logic in Python, orchestration in bash](adr/2026-07-06-logic-in-python-orchestration-in-bash.md)). Every script is shellcheck-clean at the warning level and runs on bash 3.2: no associative arrays, no `mapfile`, no `${var,,}`. A shell script that needs a roster asks Python for it.

## The Gate

The mechanical half of this standard lives in `pyproject.toml` and in the battery; the judgment half lives in review. The per-file-ignores table in `pyproject.toml` is the debt list: one entry per file still under the previous bar, naming the rules it fails. An entry only shrinks. A module pass deletes it. A new file never joins it.

| Rule | Mechanical enforcement | Review clause |
|---|---|---|
| Names | ruff `N`, `A`, `PLR2004` | `legible-cold`, `consistent-with-codebase` |
| Function shape | ruff `C901`, `PLR09xx`, `FBT`, `RET`, `SIM` | `legible-cold`, `fit-for-purpose` |
| Types | `mypy --strict`, ruff `ANN` | `correct` |
| Comments and docstrings | ruff `D` (pep257), `ERA` | `legible-cold`, `human-maintainable` |
| Errors and exit | ruff `BLE`, `TRY`, `PLW1510`, `RSE` | `operationally-honest` |
| Paths and time | ruff `PTH`, `DTZ` | `correct` |
| Idiom | ruff `UP`, `C4`, `PERF`, `FURB`, `PIE`, `RUF`, `FLY` | `consistent-with-codebase` |
| Security | bandit (battery 1b), confinement gates (1h, 1i), stdlib-only (1c) | `secure-by-design` |
| Import graph | battery 1g | — |
| Shell | shellcheck (battery 1) | `consistent-with-codebase` |

Tests carry a permanent exemption from the docstring, annotation, and magic-value rules; the reasons are in [`harness-testing-principles.md`](harness-testing-principles.md).

## The Floor

The bar is a floor for what ships, never a ceiling to climb. A change is done when it ships green against the gate and the review. A finding that adds work without naming the defect it prevents is itself the defect. A behavior-preserving change that rewrites more test lines than source lines has found tests coupled to structure, and the tests are what the finding names.

## Review Checklist

The `/audit-harness` adversarial review walks a Python diff against this list, the way a consumer's `code-quality-reviewer` walks its stack checklist.

- [ ] Every new or renamed identifier is a glossary term or a plain word; no new abbreviation.
- [ ] Every function reads at one level of abstraction; extracted names describe the extracted step.
- [ ] Data crossing a boundary is a frozen record or a named tuple; no new `dict[str, Any]` past the parse boundary.
- [ ] Nothing added exists for ceremony: no record that wraps a pair, no seam nothing drives, no test no change would fail.
- [ ] A behavior-preserving change rewrote fewer test lines than source lines; more means the tests are coupled to structure, and the tests are the finding.
- [ ] Every comment states a why the code cannot; no history, no citation, no narration.
- [ ] Every public name has a one-sentence imperative docstring; no signature restated.
- [ ] Errors carry context; exits live in composition roots; subprocess failures are handled in the next statement.
- [ ] The touched module's debt-list entry shrank or vanished; no new entry.
- [ ] The design document still describes the module after the change.
