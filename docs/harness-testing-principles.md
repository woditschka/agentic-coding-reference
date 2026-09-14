# Harness Testing Principles

The harness ships a testing brief to every consumer and expects its tests to read as a specification. This document applies that brief to the harness's own suites. Those are the runtime tests under `scripts/tests/`, the hook tests, the producer tests under `harness/tests/`, the eval bench and tools suites, and the three bash end-to-end suites. The language-agnostic principles live in the transported [`testing-principles.md`](../harness/core/.claude/skills/doctor/templates/testing-principles.md) template and are not restated here. This document carries the Python realization, the suite layout, and the rules on what not to test.

The suites are the harness's executable specification. The battery runs them on every edit, so a test that asserts implementation detail taxes every later refactor. A rule with no test is a rule the next refactor is free to break. The brief therefore pushes in two directions at once: every rule the code enforces has one test that names it, and nothing else is tested.

Sections follow: the pyramid and its measure, the mocking policy, the naming school, data construction, what not to test, fixtures, and the suite layout the battery runs.

## Test Pyramid

| Layer | Scope | I/O | Target share | Runner |
|---|---|---|---|---|
| Unit | one function or record over in-memory input | none | at least 70% | `unittest` |
| Integration | one script or package against a real temporary tree, real git, real subprocess | temporary directory only | at most 25% | `unittest` |
| End-to-end | one channel installed and exercised as a consumer would | throwaway clone or `HOME` | the three bash suites and the battery's render-faithfulness steps | bash under the battery |
| Contract nets | every command's printed contract, held across a refactor | a baseline checkout beside the tree | `harness/replay-ledgers.py` over the recorded eval ledgers, `harness/fuzz-handoff.py` over synthetic ones, `harness/fuzz-grading.py` over synthetic projects | the maintainer, before a refactor commit |

The layers are the code's levels of abstraction, and the transported brief's Test Pyramid, Seams, Coverage, and Cost sections state the rules; this document names where each lands here. The units are the pure engines over records and text: ledger arithmetic, schema checks, the effort-tier derivation, the board's fix-source resolution, feature classification over a diff. The integration layer holds the parse boundaries and the process boundaries: reading a ledger from disk, running `git`, spawning a script. Tests at every layer are sociable, real collaborators below; the integration layer asserts the wiring, one representative decision per branch, never a collaborator's case table. The code side of the same rule is the Single Level of Abstraction Principle in [`harness-code-standards.md`](harness-code-standards.md#single-level-of-abstraction).

A suite reaches its units through the `handoff` package surface, never a submodule path, so a module split or merge changes one re-export and moves no test. The contract nets are what let the suites move under a refactor: they compare every command's output between a baseline checkout and the tree, and they never name a module. The measure of the suites is the coverage table below, never their count.

## Coverage

The shipped runtime is standard-library only, so no coverage tool runs. Coverage is logical, measured by rule and by input shape, never by line or by test count:

| Target | Measure | Current |
|---|---|---|
| 100% of reachable route rules | every rule name in the generated route-rule inventory appears in a test name or assertion | 51 of 52; `unroutable-state` is the exhaustive match's fallback and unreachable by construction |
| 100% of battery checks | every check function has a producer test that drives it on a synthetic tree | tracked per module pass |
| 100% of decoders | every reader of agent-written input has a test per input shape in [Adversarial Inputs](#adversarial-inputs) | tracked per module pass |

A rule the inventory lists and no test names is untested, whatever the line count says. The module passes close the gap one package at a time.

## Mocking Policy

Ordered preference, first applicable wins:

1. **Real records.** Construct the frozen dataclass through its constructor. A record is cheap and immutable; a dict stand-in tests the wrong type.
2. **Real files.** A temporary directory per test holds a real ledger, a real `layout.toml`, a real git repository. The script under test reads them the way it reads a consumer's.
3. **Real subprocess.** A composition root is tested by running it, through `sys.executable`, against the temporary tree, and asserting on exit code and output.
4. **Injected fake.** A boundary the code already injects as a callable, such as the planner's git readers, receives a hand-written function returning fixed facts.
5. **Patched boundary attribute.** `unittest.mock.patch` on a module's `subprocess`, `shutil.which`, `datetime`, or `os.environ`, when a real process, tool, or clock cannot be arranged.

Never patch a function of the package under test, and never assert on how a double was called when the behavior it produced is already asserted. `MagicMock` appears only as the return value of a patched boundary. No mock framework beyond the standard library enters the tree.

## Test Naming

A failure report reads as a broken specification. The class names the subject or scenario as a noun phrase; the method names the outcome as a sentence.

| Element | Convention | Example |
|---|---|---|
| Module | `test_<seam family>.py`; the suite imports the package surface, never a submodule path | `tests/handoff/test_routing.py` |
| Class | the subject or scenario, no `Test` affix | `ReviewAfterBuildPass`, `WriteGate` |
| Method | `test_` plus the outcome in plain words | `test_a_second_silent_dispatch_start_blocks_as_stalled` |
| Rule test | the method name contains the route rule or check name it pins | `test_reviewer_stalled_after_two_silent_starts` |

A two-word method name (`test_ordering`, `test_invalid`) names a topic, not an outcome, and is renamed when its module is passed. Files under the older `Test`-prefixed school are debt to leave until their module pass, never a pattern to copy.

## Test Data

The three-tier convention applies with Python spelling:

| Tier | Form | Example |
|---|---|---|
| Meaningful | an uppercase module constant named for its role | `ROUND_CAP_REACHED = REVIEW_ROUND_CAP` |
| Irrelevant | a `SOME_` or `ANY_` constant, or a named default function | `SOME_REQ_ID`, `a_build_pass()` |
| Mystery | a bare literal in a test body | eliminated |

A named default is a zero-argument function that calls the type's constructor with irrelevant values; a test that cares about one field starts from the default and applies `dataclasses.replace`. A ledger fixture is built from records and written through the same serializer production uses, so a schema change moves one named default, not fifty JSON strings. The exception is a parse-boundary test, where the malformed bytes are the point and are written raw.

An expected value is derived from the inputs in the test body. A literal expected value that a reader cannot trace to an input is a mystery value.

## What Not to Test

The battery runs every suite on every edit, so an unnecessary test is a recurring cost. These shapes are removed when found and never added:

- **A test per private function.** Private helpers are covered through the public behavior that calls them. A private function that needs its own test is asking to become a module with a public contract. A rule reachable only by routing a whole ledger is the design smell: the unit that owns it gets a public seam and its own suite.
- **Interaction assertions.** Asserting that a double was called, in what order, or with which arguments, when the resulting behavior is already asserted.
- **A collaborator's case through its client.** A routing test does not re-assert schema validation or which round a cycle is in; a view test does not re-assert routing. Each case is tested once, at the unit that owns the logic; the client's test shows the collaborator was consulted.
- **The type checker's job.** No test passes a wrong type to see it rejected; `mypy --strict` owns that.
- **Duplicate levels.** A rule proven by a unit test is not proven again through the subprocess path. The integration test for a script asserts the wiring: exit code, output channel, one representative decision.
- **Whole-render snapshots.** A renderer test asserts the lines that carry the behavior under test. Byte-exact comparison is reserved for contracts whose bytes are the interface: canonical record serialization and generated inventories.
- **Combinatorial parametrization.** Boundary shapes from [Adversarial Inputs](#adversarial-inputs) appear once each; a cross product of them proves nothing further.
- **Narration.** No numbered guard list in a suite docstring, no phase comments, no assertion messages restating the assertion. The test names are the list.

## Adversarial Inputs

Every decoder of agent-written input has one test per applicable shape, named after the shape:

| Shape | Applies to |
|---|---|
| empty input | every reader |
| single item | every reader |
| missing file or first run | ledger, layout, notes, transcripts |
| truncated last line, missing trailing newline | ledger, transcripts |
| duplicate keys, NaN, deeply nested JSON | ledger |
| control bytes, direction marks, oversized line | ledger, diff, docs, connector output |
| CRLF line endings | rules file, ledger |
| symbolic or dash-prefixed git reference | change set, planner readers |
| unresolvable path, symlink escaping the tree | write guard, materialize, prune |

## Fixtures and Cleanup

- A test owns its world: one `TemporaryDirectory` registered with `addCleanup`, built in `setUp` or in the test body, never shared across tests.
- Environment isolation goes through `unittest.mock.patch.dict(os.environ, ...)`, including `HOME` and the transcript root, so a suite never reads the operator's `~/.claude`.
- A git repository fixture is created by the test with `user.name` and `user.email` set locally; no test depends on the operator's git configuration.
- No test writes outside its temporary directory or the repository's ignored scratch paths.
- Immutable module-level fixtures are allowed; a mutable module-level fixture is a defect.

## Suite Layout

| Suite | Location | Loads the source how | Battery step |
|---|---|---|---|
| Runtime | `harness/core/scripts/tests/`, mirroring `handoff/`, `grading/`, `changeset/` | package import from the scripts root | 4, per materialized sample |
| Stack slices | `harness/stacks/<stack>/scripts/tests/grading/` | same, against the stack's real layout | 4 |
| Hooks | `harness/core/.claude/hooks/test_<hook>.py` | runs the hook as a subprocess on stdin JSON | 4 |
| Producer | `harness/tests/`, one file per script | `_loader.load` by path, since the scripts keep hyphenated names | 6 |
| Tools | `tools/<tool>/tests/` | direct import | 6b |
| Eval bench | `evals/tests/` | direct import | 6bc |
| End-to-end | `harness/tests/test-*.sh` | installs a channel into a throwaway tree | 6c, 8, 9 |

Install-time verification in a consumer runs the exact installed module list, never discovery; the battery's steps run discovery. Both are described in [`harness-system-design.md`](harness-system-design.md#the-battery).

## Checklist

Before a test lands, in this order:

1. Does the name read as an outcome, and does it contain the rule it pins?
2. Is every value named by role, declared irrelevant, or derived from an input?
3. Is the world built from real records and real files, with a double only at a process, tool, or clock boundary?
4. Does the test assert logic this unit adds, at the level that owns it, never a collaborator's case table?
5. Is the body linear: no branching, no loops, no try/except around the act?
6. Would deleting the test leave a rule in the inventory unnamed? If not, the test is redundant.
