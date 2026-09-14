# Harness System Design

This document describes the harness's Python as software. It covers the runtime a consumer receives, the producer tooling that renders and installs it, the battery that gates both, the eval bench, and the user-level tools. It names each module once, states the contract it holds, and points at the source. The loop model lives in [`agentic-harness.md`](agentic-harness.md), the consumer-facing contract in [`harness-project-api.md`](harness-project-api.md), and every rationale in [`docs/adr/`](adr/README.md); this document links to them and restates none of them.

Every imperative line below carries the decision it comes from. A rule without a back-link is a description of current state, not a guardrail. The code standard the modules are held to is [`harness-code-standards.md`](harness-code-standards.md); the suites that pin these contracts are described in [`harness-testing-principles.md`](harness-testing-principles.md).

Sections follow the transported system-design shape: package structure, contracts, constants, dependency policy, security context and threat model, and the routing state machine.

## Package Structure

The Python lives in four trees with one direction of flow. The shipped runtime under `harness/core/scripts/` is what a consumer runs. The producer tooling under `harness/` renders that runtime into the samples and the marketplace and never ships. The battery under `harness/verify_harness/` reads both. The eval bench under `evals/` and the tools under `tools/` sit beside them, and one tools module is vendored into the runtime.

### Shipped Runtime

| Module | Kind | Purpose |
|---|---|---|
| `handoff.py` | composition root | Deterministic access to the ledger: append, validate, route, show, view, tier, audit, latest, next-retry |
| `handoff/__init__.py` | surface | The declared package surface: every seam a suite or the root reaches, so a module split or merge changes one re-export and no test |
| `handoff/schema.py` | leaf | Byte contract of the ledger: strict JSON, the schema-subset validator, canonical serialization, sanitization, the log parser |
| `handoff/records.py` | leaf | One frozen record type per ledger record, the record union, the never-raising lift, the pipeline vocabulary constants |
| `handoff/ledger.py` | leaf | The typed ledger line, the latest-of query, and the review-cycle arithmetic the router and the board share |
| `handoff/findings.py` | leaf | Review findings: artifact owners, the gate's shape errors, the dissent they carry |
| `handoff/tiers.py` | leaf | The effort ladder: the implementer tier the next dispatch runs, the tier each window ran |
| `handoff/roster.py` | leaf | The reviewer roster from the layout and the pass roster from the active review plan |
| `handoff/ladder.py` | leaf | The reviewer ladder, the dissent ceilings, and outstanding dissent of one review pass |
| `handoff/scope_lock.py` | leaf | Gate 1's scope lock over the Non-Goals delta and the overrides' cited sources |
| `handoff/repository.py` | gateway | The repository reads the gates and the audit make, behind one protocol: HEAD state, the PRD at HEAD and in the tree, the dirty design docs, the docs baseline |
| `handoff/non_goals.py` | leaf | The PRD's Non-Goals table and the rows changed against HEAD |
| `handoff/autofix.py` | leaf | The autofix audit: the allowlist bounds, the content checks, supersession, and the design-doc coverage over an injected repository |
| `handoff/gates.py` | leaf | The append-time gates: the review anchor, the design sync, the responding-to pointers, the design-block coverage |
| `handoff/routing.py` | middle | The routing core: the decision record and its constructors, the rows, the gates, and the phases composed from the routing leaves |
| `handoff/text.py` | leaf | Display text over `str`: gists, plurals, clipped locations |
| `handoff/timestamps.py` | leaf | Ledger timestamps: ISO-8601 to seconds, elapsed time, the clock face |
| `handoff/cost.py` | middle | The cost overlay: the one seam over the vendored `accounting` module, degrading to no figures |
| `handoff/board.py` | middle | The board model: one typed slice with its rounds, sessions, and timeline, built once for both views, free of presentation |
| `handoff/view.py` | middle | The two views over the board model, terminal and Markdown; every color and glyph lives here |
| `grading.py` | composition root | Feature extraction and review planning: extract, contracts sync, coverage map, conventions map, review plan |
| `grading/config.py` | anti-corruption layer | The grading sections of `scripts/layout.toml` plus the stack defaults, validated once |
| `grading/features.py` | model | Structural feature rows over a diff through the git gateway; no verdict logic |
| `grading/handoff_facts.py` | gateway | The grading context's read of the ledger; degrades to null facts |
| `grading/planner.py` | pure policy | The risk ladder: plan context, surface roster, first-pass and fix-cycle derivation, git reads injected |
| `grading/contracts.py` | leaf | The design-doc sync check for one requirement id |
| `grading/conventions.py`, `grading/coverage.py` | leaf | Write-time maps over the diff and the test tree; maps, never gates |
| `changeset.py` | composition root | The change set under review, one definition shared by reviewers and grader |
| `changeset/config.py` | anti-corruption layer | The exclude-glob section of the layout, only |
| `changeset/git_facts.py` | gateway | Every git invocation, under one canonical environment, with untrusted-ref hardening |
| `changeset/emit.py` | verb | Base and head resolution and the emit verb |
| `backlog.py` | application | The outer loop's candidate set through the project-owned connector |
| `doctor.py` | application | The blocking validator of a project's briefs against the expectations manifest |
| `accounting.py` | vendored module | Transcript usage to tokens and list-price cost; the byte-identical copy of the tools module |
| `.claude/hooks/*.py` | hooks | Four Claude Code backstops: the sanctioned append form, the ledger write guard, the intake stop guard, the continue-only resume |

The stack slices under `harness/stacks/<stack>/scripts/` ship no Python: each carries a `layout-defaults.toml` and the layout-bound tests; the generic stack adds the verb dispatcher `gate.sh`.

Execution model, as it exists:

- A script runs from the consumer's project root; the ledger, schema, and layout paths default relative to it.
- The three entries `handoff.py`, `grading.py`, `changeset.py` share their name with a package. An entry imports its package in submodule form, never as a bare module ([ADR: runtime package layout](adr/2026-07-17-runtime-package-layout.md)).
- Each entry places its own directory on `sys.path`, so a load by path from another working directory resolves the packages.
- The Python floor is enforced at import: a missing `tomllib` exits with the usage code.

### Layers

| Layer | Modules | May import |
|---|---|---|
| Leaves | `handoff/schema.py`, `handoff/records.py`, `handoff/text.py`, `handoff/timestamps.py`, `changeset/config.py`, `grading/config.py`, `grading/contracts.py`, `grading/conventions.py`, `grading/coverage.py` | standard library only |
| Ledger | `handoff/ledger.py` | the schema and records leaves |
| Routing leaves | `handoff/findings.py`, `handoff/tiers.py`, `handoff/roster.py`, `handoff/ladder.py`, `handoff/scope_lock.py` | the ledger and the leaves; the ladder adds findings and the roster, the tiers add findings |
| Repository gateway | `handoff/repository.py`, `handoff/non_goals.py` | the timestamps leaf; the Non-Goals delta reads through the gateway's protocol |
| Append gates and the audit | `handoff/autofix.py`, `handoff/gates.py` | the ledger, the leaves, and the repository gateway; the gates add the audit |
| Middle | `handoff/routing.py`, `handoff/cost.py`, `handoff/board.py`, `handoff/view.py` | the ledger and the leaves; the routing core adds the routing leaves, the cost overlay adds the vendored `accounting`, the board adds the overlay, the view adds the board and the overlay's figures record |
| Gateways and models | `changeset/git_facts.py`, `changeset/emit.py`, `grading/features.py`, `grading/handoff_facts.py`, `grading/planner.py` | their own package's leaves and the change-set gateway |
| Composition roots | `handoff.py`, `grading.py`, `changeset.py`, `doctor.py` | the packages they compose |

Every import edge under `core/scripts` is declared in the battery's allow table ([ADR: runtime package layout](adr/2026-07-17-runtime-package-layout.md)). An undeclared edge, a declared edge with no file, or a bare entry import fails step 1g. One dynamic edge exists outside the static gate: the grading gateway imports `handoff` through `importlib` when it appends a plan record. Sanitization lives in the lowest layer, `handoff/schema.py`, so agent bytes never reach a terminal from any layer above it.

### Producer Tooling

| Module | Kind | Purpose |
|---|---|---|
| `registry.py` | library | The rosters: stacks, tools and their agent surfaces, channels, the engine sliver, the stack markers, the one layout reader |
| `write_guard.py` | library | The confined-write choke point: every tree-rewriting write passes through a declared scope |
| `retired_paths.py` | library and CLI | The retired-paths manifest: parse, coverage, and the release-time update |
| `materialize.py` | application | Copy core then the stack slice into a target, channel- and tool-aware; report extras, never delete |
| `init.py` | application | Scaffold the project-owned files; never overwrite |
| `refresh-settings.py`, `refresh-gitignore.py`, `claude-md/refresh-chapters.py` | applications | Ensure-present refreshers of the three project-owned files the harness co-owns |
| `render-agent-mirrors.py` | application | Render the per-tool agent bodies from each `.claude` base; prune orphans |
| `render-route-rules.py`, `render-adr-index.py` | applications | Generate the route-rule inventory and the ADR index from their sources; `--check` detects drift |
| `package-marketplace.py` | application | Render the per-(stack, tool) plugins and the marketplace manifest, deterministic and self-cleaning |
| `deps-report.py` | application | Collect every pinned version the upgrade skill tracks; fail on intra-item drift |
| `marketplace/prune-retired.py` | consumer-shipped application | Remove retired engine files from a marketplace consumer, bounded to the engine sliver |
| `verify-harness.py` and `verify_harness/` | launcher and package | The battery; see [The Battery](#the-battery) |
| `*.sh` | orchestrators | `propagate-harness.sh` sequences render, materialize, package, battery; `materialize-samples.sh`, `release-version.sh`, `marketplace/setup.sh` sequence their one operation each |

Guardrails:

- Python holds the logic; bash sequences Python and holds no roster ([ADR: logic in Python, orchestration in bash](adr/2026-07-06-logic-in-python-orchestration-in-bash.md)).
- A tree-rewriting script writes only through `write_guard` inside a declared scope, and the battery bans raw write primitives elsewhere ([ADR: network and write confinement gate](adr/2026-07-19-network-write-confinement-gate.md)).
- The stack layer copies after core and wins on overlap; a materialization replaces the harness-owned runtime whole ([ADR: materialize is a complete replacement](adr/2026-06-13-materialize-complete-replacement.md)).
- One layout reader serves init and materialize; a malformed layout raises, never defaults ([ADR: one layout reader](adr/2026-07-18-materialize-previewable-plan.md)).
- Generated surfaces are rendered from source and gated for drift, never hand-edited: the agent mirrors ([ADR](adr/2026-07-03-rendered-agent-mirror-bodies.md)), the route-rule inventory ([ADR](adr/2026-08-16-generated-route-rule-inventory.md)), the ADR index, the plugins, the retired-paths manifest ([ADR](adr/2026-08-20-retired-paths-manifest.md)).

### The Battery

`verify-harness.py` is a launcher whose header carries the authoritative step list and whose body dispatches in order. The steps live in `verify_harness/`: `text.py` holds pure helpers, `battery.py` the aggregator, and `checks/` the step functions grouped by the evidence they read ([ADR: check-sync decomposition](adr/2026-07-18-check-sync-decomposition.md)). The groups are `lint` for the static tools, `sync` for rendered-tree parity and content invariants, `suites` for subprocess suites, and `confinement` with `confinement_ast` for the egress and write gates.

The aggregator's contract: a step notes its title, fails with a message, or skips with a reason; the run aggregates and exits once. `--quick` refuses while any derived tree is dirty and otherwise skips the re-render and sub-suite steps whose inputs the guard proves untouched. `--strict` turns a missing external tool from a skip into a failure; both push gates run strict ([ADR: the battery gates every push](adr/2026-07-13-server-side-battery-enforcement.md)). The same import-boundary check that gates the runtime gates the battery's own package: launcher, checks, aggregator, helpers, one direction.

### Eval Bench and Tools

| Module | Purpose |
|---|---|
| `evals/run_eval.py` | Run version × task × repetition cells against the fixed system under test; persist one run folder per cell |
| `evals/summarize.py` | Regenerate every derived view from the run folders and the operator notes; `--check` fails on drift |
| `evals/render_figure.py`, `evals/refresh_trend.py` | Redraw the dated trend figure from the trend data; the two-step refresh |
| `tools/harness-stats/accounting.py` | The canonical usage-accounting module and pricing table |
| `tools/claude-dev/claude_dev_config.py`, `claude_dev_scrub.py`, `ide_preflight.py` | Proxy policy from configuration, the container-private settings replica, the IDE tool-set check; the launcher itself is bash |

Run folders are ground truth and every view is derived; a development version's folders and trend page are never committed ([ADR: cost per pass against a fixed SUT](adr/2026-08-02-eval-bench-cost-per-pass.md)). The accounting module has one canonical home in `tools/` and one vendored copy in the runtime ([ADR: single pricing source as a gated vendored copy](adr/2026-07-13-single-pricing-source-vendored-copy.md)). Battery step 2d compares the two byte for byte. Methodology, tiers, and the run-folder layout are in [`evals/README.md`](../evals/README.md).

## Contracts

| Contract | Purpose | Source | Decision |
|---|---|---|---|
| The ledger | Append-only JSONL, one canonical record per newline-terminated line; ordering is file position, timestamps are stamped at append and never a routing input | `handoff.py`, `handoff/schema.py` | [ADR](adr/2026-05-08-append-only-jsonl-handoffs.md), [ADR](adr/2026-07-13-append-stamped-record-timestamps.md) |
| Lock-free append | One positional `os.write` on an append-only descriptor; the receipt line number is exact; a glued tail warns on append and blocks on validate and route | `handoff.py` | [ADR](adr/2026-08-16-lock-free-ledger-appends.md) |
| Record union | One frozen dataclass per record type; the lift is total and never raises; the schema alone owns requiredness; field parity between schema and dataclass is a tested gate | `handoff/records.py` | [ADR](adr/2026-07-17-typed-python-core.md) |
| Schema subset | A closed keyword vocabulary; an unknown keyword is an error; patterns and enums may resolve from the layout | `handoff/schema.py`, `schemas/scratch/` | [ADR](adr/2026-06-14-layout-sourced-schema-patterns.md), [ADR](adr/2026-08-02-gate-facts-in-layout-schemas-defer.md) |
| Decision payload | Four kinds, dispatch, bounce, blocked, escalate, each naming its rule and reason; route exits zero with any decision and never repairs the log | `handoff/routing.py`, `handoff.py` | [ADR](adr/2026-07-06-deterministic-mid-slice-routing.md) |
| Route-rule inventory | Generated from the four decision constructors; drift fails battery step 3j; two rules raised by the CLI before routing, the dirty-log and unreadable-layout blocks, live outside the inventory | `render-route-rules.py`, `route-rules.md` | [ADR](adr/2026-08-16-generated-route-rule-inventory.md) |
| Layout table | Each package reads only its own sections through its own reader; the schema resolves named keys; the routing core reads the extra reviewers and the grading switch | `scripts/layout.toml`, the three config modules | [ADR](adr/2026-06-13-extensions-and-tool-surfaces.md), [ADR](adr/2026-07-17-module-derivation-named-layouts.md) |
| Stack defaults | Two tables only, merged key by key under the project's layout; a foreign key fails the load | `scripts/layout-defaults.toml`, `grading/config.py` | [ADR](adr/2026-09-07-security-review-follows-the-surface.md) |
| Review plan | An engine-authored record per build pass naming risk, scope, basis, and roster; a gray plan defers to the planner; absent or invalid plans fail closed to the full roster | `grading.py`, `grading/planner.py` | [ADR](adr/2026-07-09-risk-proportional-review.md), [ADR](adr/2026-09-01-evidence-gated-dynamic-tiering.md) |
| Change set | One definition of the diff under review, shared by every reviewer and the grader; the snapshot never touches the real index | `changeset/emit.py`, `changeset/git_facts.py` | [ADR](adr/2026-06-21-fresh-eyes-review-changeset.md) |
| Grading facts | Six facts read from the ledger, every one null on an absent or unreadable log | `grading/handoff_facts.py` | [ADR](adr/2026-06-05-change-grader.md) |
| Conventions and coverage maps | Lists for the implementer's walk and the reviewers' checklists; no exit code carries a verdict | `grading/conventions.py`, `grading/coverage.py` | [ADR](adr/2026-09-03-coverage-map-joins-the-walk.md) |
| Contracts sync | A requirement id present in the PRD and the design doc, or a named failure | `grading/contracts.py` | [ADR](adr/2026-08-15-contracts-sync-joins-the-gate.md) |
| Backlog connector | Candidates are PRD ids minus delivered, non-goal, and superseded; the team's board enters through a project-owned shell connector with a fixed row format | `backlog.py`, `scripts/backlog.sh` | [ADR](adr/2026-09-12-backlog-connector.md) |
| Doctor manifest | The blocking checks of a project's briefs, driven by one expectations file | `doctor.py`, `doctor-expectations.toml` | [ADR](adr/2026-06-12-docs-as-harness-project-api.md), [ADR](adr/2026-06-14-doctor-engine-in-scripts.md) |
| Hooks | Four backstops with declared fail directions; the deterministic control is `handoff.py validate` in the quality gate | `.claude/hooks/` | [ADR](adr/2026-06-20-handoff-append-pre-approval.md), [ADR](adr/2026-06-10-continue-only-resume.md), [ADR](adr/2026-08-08-unattended-refusals-are-resumable-pauses.md) |
| Registry rosters | One definition of stacks, tools, channels, and the engine sliver, imported by every producer script and bundled into every plugin | `registry.py` | [ADR](adr/2026-06-14-marketplace-plugin-channel.md), [ADR](adr/2026-08-02-plugin-shipped-init.md) |
| Write guard | A context-scoped allowlist of roots; a write outside it fails closed; delete verbs never follow symlinks | `write_guard.py` | [ADR](adr/2026-07-19-network-write-confinement-gate.md) |
| Confinement policy | One manifest of sanctioned writers, spawners, egress, and network; a stale sanction fails | `confinement-policy.toml`, `verify_harness/checks/confinement.py` | same ADR |
| Retired-paths manifest | Cumulative and append-only; the release script appends the set difference between the last tag and the working tree | `retired-paths.txt`, `retired_paths.py` | [ADR](adr/2026-08-20-retired-paths-manifest.md) |
| Managed chapters | The harness-owned chapters of a consumer's rules file, replaced heading to heading; the stamp line is the reserved token | `claude-md/refresh-chapters.py` | [ADR](adr/2026-06-24-claude-md-managed-chapters.md), [ADR](adr/2026-06-27-harness-version-stamp.md) |
| Handbook delta | The pinned line-set difference between the root handbook and the shipped copy | `handbook-delta.expected` | [ADR](adr/2026-07-12-parity-gates-for-hand-owned-parallels.md) |
| Install verification | The exact installed module list is run, never discovery; the battery's own steps use discovery | `materialize.py`, `marketplace/setup.sh` | [ADR](adr/2026-08-16-exact-module-install-verification.md) |
| Run folder | One folder per cell with manifest, result, ledger, costs, patch, egress log; derived pages regenerate from it | `evals/run_eval.py`, `evals/summarize.py` | [ADR](adr/2026-08-02-eval-bench-cost-per-pass.md) |
| Pricing table | One family table, dated overrides, cache multipliers; the single edit point for cost | `tools/harness-stats/accounting.py` | [ADR](adr/2026-07-13-single-pricing-source-vendored-copy.md), [ADR](adr/2026-07-15-transcript-file-cost-attribution.md) |

## Constants

Values live in source; this table names the constants with cross-module meaning and where each is defined.

| Constant | Meaning | Source |
|---|---|---|
| `ROSTER_FLOOR` | The four mandatory reviewers; extras extend, nothing removes | `handoff/records.py`; restated as `REVIEWERS` in `grading/config.py` and pinned by the doctor manifest |
| `SUBSTANTIVE` | The record types that close a dispatch | `handoff/records.py` |
| `RETRY_CAP` | Build retries and truncation continuations before re-triage | `handoff/records.py`; the build-failure schema pins the same bound |
| `REVIEW_ROUND_CAP` | Fix rounds a review cycle buys; from the cap on, the bar is critical-only | `handoff/records.py` |
| Role names | `IMPLEMENTER`, `ROUTINE_IMPLEMENTER`, `DESIGNER`, `PRODUCT`, `PLANNER`, `PLAN_ENGINE`, `GRADER`, `HUMAN` | `handoff/records.py` |
| `SURFACE_REVIEWERS`, `STACK_DEFAULT_KEYS`, the size threshold | The surface-to-reviewer map, the two defaultable layout tables, the oversize trigger | `grading/config.py` |
| `_GIT_ENV`, the tree-sha pattern | Deterministic git environment; the only accepted tree name shape | `changeset/git_facts.py` |
| Engine timeout, route re-read delay, route hook timeout | Child-process bounds around the plan engine and the stop hook | `handoff.py`, `intake-stop-guard.py` |
| `STACKS`, `TOOLS`, `CHANNELS`, `ENGINE_SLIVER`, `PLUGIN_NAMESPACE` | The producer rosters | `registry.py` |
| `RUFF_TARGETS`, `ENTRY_MODULES`, the suite floors | The lint scope, the solo mypy entries, the minimum suite counts | `verify_harness/checks/lint.py`, `suites.py`, `sync.py` |
| `PRICE`, `PRICE_OVERRIDE`, cache multipliers | List pricing | `tools/harness-stats/accounting.py` |

Exit codes are an interface:

| Application | Exit codes |
|---|---|
| `handoff.py` | 0 success; 1 validation, parse, or I/O failure; 2 usage; 3 no matching record. `route` exits 0 with its decision |
| `grading.py`, `changeset.py` | 0 success; 1 unresolved base, git failure, or append failure |
| `backlog.py` | 0 success; 2 connector or id failure; the connector's own 3 and 4 are probe sentinels |
| `doctor.py` | 0 no failing check; 1 any failing check; 2 manifest error |
| Hooks | allow and log-guard always 0 with a decision or nothing; stop-guard and continue-only 0 allow, 2 block |
| `verify-harness.py` | 0 pass; 1 any failure or a refused `--quick`; 2 usage |
| `materialize.py`, `init.py` | 0 success; 1 target, layout, or verification failure; 2 usage |

## Dependency Policy

- The shipped runtime imports the standard library or a sibling module in its own scripts tree, ships no dependency manifest, and targets Python 3.11 ([ADR: logic in Python, orchestration in bash](adr/2026-07-06-logic-in-python-orchestration-in-bash.md)). Battery step 1c enforces this across every tree that reaches a consumer. The invariant is stated once in [`harness/README.md`](../harness/README.md#the-stdlib-only-invariant).
- The producer tooling, the battery, the eval bench, and the tools follow the same rule by convention. The one manifest in the repository is the root `pyproject.toml`, which configures ruff and mypy and ships nowhere.
- External developer tools, ruff, mypy, bandit, shellcheck, are optional on a maintainer host and required under `--strict` ([ADR: typed Python core](adr/2026-07-17-typed-python-core.md)). A missing tool is a loud skip, never a silent pass. Their versions are pinned in three places, the root `pyproject.toml`, the container image, and the CI workflow, and battery step 6bb holds the three equal.
- A new runtime dependency is not added. A new producer-side tool joins only through the skip-if-missing contract with its pin in all three places.

## Security Context

| Code | Runs where | Data leaving the machine | Inputs it does not trust |
|---|---|---|---|
| Shipped runtime | The consumer's project root, under whichever agent tool dispatched it | None | The ledger, the layout, the diff, the PRD, the test tree, transcripts, the connector's output, the project's docs |
| Producer tooling and battery | The maintainer's host | One sanctioned `git ls-remote` in the deps report | The working tree it renders from; nothing it writes lands outside a declared scope |
| Eval bench | The agent turn inside the claude-dev container by default, measurement on the host | Proxy-allowed HTTPS to the model API and the build dependency chain, every request logged per run | Everything the agent leaves behind: ledger, patch, build scripts; the patch text shown to the judge |
| claude-dev | Host launcher, container workload, proxy container | Proxy allow-list only; telemetry off by default | The project directory, the settings replica, the IDE's exposed tool set |
| harness-stats | The host, reading `~/.claude` | None | Transcript JSON; a malformed line is skipped |

## Threat Model

Boundaries validate; internal code trusts its contracts. Every input in the table above is agent-written or operator-edited, and each has one reader that owns its defense.

| Input | Boundary reader | Defense |
|---|---|---|
| Ledger | `handoff/schema.py`, `handoff/records.py` | Strict JSON rejects duplicate keys and non-finite numbers; the lift never raises; schema gates run per record before any typed read; raw reads are sanctioned at three sites only |
| Ledger, grading side | `grading/handoff_facts.py` | A malformed line is skipped; an unreadable log nulls every fact |
| Layout | the three config readers, `handoff/roster.py` | Malformed reviewer extras block the route; a bad layout-sourced pattern is reported, not raised; the grading and change-set readers raise on a broken install |
| Diff, PRD, test tree | `grading/conventions.py`, `grading/coverage.py` | Control bytes are stripped before rendering; read problems land in notes, never in an exit code |
| Repository reads | `handoff/repository.py` | Every read answers None on failure; the scope lock and the autofix audit fail closed on it; the PRD read is size-capped |
| Tree names and refs | `changeset/git_facts.py` | Bare hexadecimal tree names only; a dash-prefixed or symbolic reference is refused; the planner receives only these hardening readers |
| Requirement ids and scope-override sources | `handoff.py`, `handoff/scope_lock.py` | Full-match patterns before a child argv or an integer parse |
| Transcripts | `accounting.py`, `handoff/cost.py` | Any failure drops the cost overlay; the board never gates |
| Connector output and arguments | `backlog.py` | The id is pattern-checked before any shell; path and id pass as positional arguments, never interpolated; stderr is scrubbed |
| Hook stdin | the four hooks | The allow and log-guard hooks defer on malformed input; the stop guard fails open; the continue-only guard fails closed |
| Terminal output | `handoff/schema.py` | One sanitizer drops control and direction characters from every string the runtime prints; route output is ASCII-escaped JSON |
| Child processes | `handoff.py` | The engine child is a constant sibling path with list argv, an isolated interpreter, and a timeout; the battery's confinement steps gate every spawn and every write in the glue |

Guardrails with their decisions:

- The route never repairs, guesses, or writes; a dirty log blocks and an ambiguous state escalates ([ADR: single deterministic tool](adr/2026-06-11-handoff-log-access-tool.md)).
- The hooks are backstops per tool; `handoff.py validate` in the quality gate is the deterministic control on every tool ([ADR: pre-approved append via hook](adr/2026-06-20-handoff-append-pre-approval.md)).
- The board reads and never gates; a bad roster, a dirty log, or a missing overlay degrade the view and never block the pipeline ([ADR: deterministic mid-slice routing](adr/2026-07-06-deterministic-mid-slice-routing.md)).
- The producer glue makes no network call and writes only to declared roots, both proven by AST scan ([ADR: network and write confinement gate](adr/2026-07-19-network-write-confinement-gate.md)).
- Appends are atomic in placement on a local POSIX filesystem; materialization refuses a filesystem that fails the shipped stress test ([ADR: lock-free ledger appends](adr/2026-08-16-lock-free-ledger-appends.md)).

## State Machine

The routing core is a state machine over the ledger, deterministic from file position alone. The generated [`route-rules.md`](../harness/core/.claude/skills/handoff-routing/route-rules.md) is the complete rule inventory; this table names the phases and the transitions between them. A row's event names the rule the decision carries.

| # | From | Event | To |
|---|---|---|---|
| 1 | (start) | Empty log: `no-active-slice` | escalated |
| 2 | Any | Unanswered human consultation anywhere on the log: `human-consultation` | blocked until the human responds |
| 3 | Any | Latest record is a consultation request: `consultation-dispatch` | Consultation |
| 4 | Consultation | Response recorded: `consultation-return` with resume | the requester's prior phase |
| 5 | Intake | Intake decision passes its gate: `intake-ready` | PRD gate |
| 6 | PRD gate | Entry passes schema and scope lock: `prd-approved` | Design gate |
| 7 | PRD gate | Gate failure: `prd-gate-failed` | PRD gate, bounced to the product expert |
| 8 | Design gate | Block passes with an implementable verdict: `design-approved` | Implement |
| 9 | Design gate | Gate failure: `design-gate-failed` | Design gate, bounced to the designer |
| 10 | Design gate | Conflicting verdict: `design-conflict`; refactor-first verdict: `refactor-first` | blocked; escalated |
| 11 | Implement | Silent dispatch-start below the cap: `truncation-continue` | Implement |
| 12 | Implement | Cap reached: `truncation-non-convergence`; failures at the cap: `build-non-convergence` | Design gate |
| 13 | Implement | Build failure below the cap: `build-retry` | Implement |
| 14 | Implement | Abort reasons: `abort-wrong-shape`, `abort-prd-mismatch`, `abort-design-mismatch`, `abort-prerequisite` | PRD gate, PRD gate, Design gate, blocked |
| 15 | Implement | Build pass recorded | Review |
| 16 | Review | Engine plan is gray: `plan-gray`; planner silent once: `planner-stall-retry`; twice: `planner-stalled` | Review; Review; blocked |
| 17 | Review | Roster resolved, reviewers undispatched: `reviews-needed`; one silent start: `reviewer-stall-retry`; two: `reviewer-stalled` | Review; Review; blocked |
| 18 | Review | Feedback fails its gate: `review-record-invalid`; dissent without findings: `reviewer-empty-findings` | Review, bounced to that reviewer |
| 19 | Review | Dissent with owners: `process-findings` | Fix round in Implement, PRD gate, or Design gate by finding owner |
| 20 | Review | Escalate finding: `escalate-finding-halt`, `escalate-on-approved`; autofix-only round: `autofix-only-round` | blocked; blocked; escalated |
| 21 | Review | A non-convergence ceiling: `review-non-convergence` with its cause | blocked |
| 22 | Review | Dissent outside the pass roster: `outstanding-dissent` | Review |
| 23 | Review | All approved, grading on: `grade`; grading off or already graded: `feature-complete` | Grade; terminal |
| 24 | Grade | Features without verdict: `grade-continue`; verdict: `feature-complete` or `refactor-resume` | Grade; terminal or Design gate |
| 25 | Any | No substantive record, unknown state, or truncation of an unlisted author: `no-substantive-record`, `unroutable-state`, `truncation-undefined` | escalated |

Invariants the machine holds:

- Feedback older than its reviewer's latest dispatch-start is stale; one silent dispatch-start earns the single retry, a second blocks ([ADR: deterministic truncation detection](adr/2026-06-04-deterministic-truncation-detection.md)).
- The round counts passes with substantive dissent; from the cap on the bar is critical-only, past it dissent blocks; truncation-only dissent never advances the round ([ADR: bounded review convergence](adr/2026-08-11-bounded-review-convergence.md)).
- The review cycle starts at the latest superseding design block whose pointer resolves; a forged pointer is ignored ([ADR: the review cycle survives mid-slice design records](adr/2026-08-07-review-cycle-survives-mid-slice-design-records.md)).
- An approved verdict carries no fix-routable finding ([ADR](adr/2026-08-02-approved-carries-no-fix-routable-finding.md)).
- A changed non-goal needs a scope override quoting a human line; the request itself is never the override ([ADR: scope-lock](adr/2026-08-08-scope-lock-the-request-is-never-the-override.md)).
- Only an all-autofix fix round on a rated slice runs the routine implementer; one miss retires it for the slice; recovery paths run the base pin ([ADR: evidence-gated dynamic tiering](adr/2026-09-01-evidence-gated-dynamic-tiering.md)).
- A build pass is refused while a PRD-changing consultation has no design response ([ADR: design-sync gate](adr/2026-09-12-design-sync-gate.md)).
- Route totality over every record type is checker-enforced through `assert_never` ([ADR: typed Python core](adr/2026-07-17-typed-python-core.md)).
