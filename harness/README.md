# /harness — the single canonical harness source

This tree is the one place the harness is authored. The sample projects (`samples/go/`, `samples/java-spring-boot/`, `samples/generic/`) and any downstream consumer are **materialized instances** of it, not separate sources. Edit the harness here; consumers pick up changes on their next `materialize`. See the decision record at [`../docs/adr/2026-06-12-docs-as-harness-project-api.md`](../docs/adr/2026-06-12-docs-as-harness-project-api.md).

## Layout

```
harness/
├── core/            Runtime files identical across every stack (the de-stackify target).
├── stacks/<stack>/  Runtime files specific to one stack (agent bodies, lint rules, schemas).
├── init/            Skeletons for the files a CONSUMER owns and commits (NOT runtime).
│   ├── core/        Project-owned files identical across stacks (settings.json, gitignore block).
│   └── stacks/<stack>/  Project-owned files per stack (CLAUDE.md, scripts/layout.toml).
├── claude-md/       Managed CLAUDE.md chapters; materialize refreshes them in place.
├── marketplace/     Producer-side marketplace assets (setup.sh, setup skill); hooks.json renders from the settings skeleton.
├── registry.py      Source of the stack rosters, the TOOLS registry (every
│                    tool→directory mapping derives from it), and shared helpers
│                    (detect_stack, read_stamp) for the Python tooling.
├── registry.sh      Shell helpers (note, read_stamp, empty_chapter) for the bash
│                    orchestrators — no roster: shell callers read registry.py, and a
│                    battery-step-6 test keeps this file roster-free. Both producer-side
│                    only, never shipped.
├── materialize.py   Install the runtime: overlay core then stacks/<stack> into a target,
│                    then run the installed test suites once (skip: --no-verify).
├── refresh-gitignore.py, refresh-settings.py   Keep a consumer's .gitignore runtime
│                    block and settings.json harness keys current (run by materialize).
├── init.py          Scaffold the project-owned files into a target (never overwrites).
├── materialize-samples.sh   Stack-agnostic: detect each target's stack, then materialize.
├── render-agent-mirrors.py  Render the per-tool agent mirror bodies from each .claude
│                    base and prune orphaned mirrors (propagate-harness step 1).
├── package-marketplace.py  Render /harness into the per-stack, per-tool plugins.
├── propagate-harness.sh  Propagate + verify: render agent mirrors, materialize the
│                    samples, package-marketplace, then the battery.
├── release-version.sh  Cut a version: guard, stamp VERSION, propagate-harness, create commit + tag.
├── deps-report.py   Collect every pinned tool/plugin version the deps-upgrade skill
│                    tracks (init skeletons included); fail on intra-item drift.
│                    The local half runs as battery step 4c; --resolve-shas
│                    (network) verifies workflow-action SHA/comment pairs.
├── review-survey.sh  The deterministic measurements the /review-harness research
│                    agents anchor on (doc sizes, churn, cross-stack overlap).
├── VERSION, VERSION-DATE   The lockstep harness version and its release date — stamped
│                    by release-version.sh, read by the materialize and packaging scripts.
├── write_guard.py   Confined-write choke-point for the producer tree-rewriters
│                    (materialize, init, package-marketplace, render-agent-mirrors):
│                    each declares its write roots via write_scope(); battery step 1i
│                    bans raw writes everywhere else (ADR 2026-07-19).
├── confinement-policy.toml  The one explicit manifest of every sanctioned exception
│                    to the confinement gates (steps 1h/1i): writers, spawners,
│                    egress, network files — each entry with its why.
├── handbook-delta.expected  The pinned, reviewed delta between docs/agentic-harness.md
│                    and the installed copy; verify-harness step 3e fails on any other delta.
├── tests/           The producer-side suites, mirroring this toolbox tree
│   │                (ADR 2026-07-18 producer-side-tests-subdir).
│   ├── _loader.py   Shared path-loader: resolves the toolbox root and loads a
│   │                source script by path (the hyphenated names stay).
│   ├── test_*.py    Unit suites for every Python tool here (materialize, init,
│   │                the refresh writers, the renderer, the battery's own
│   │                helpers) — battery steps 2c and 6.
│   ├── claude-md/test_refresh_chapters.py   The chapter writer's suite.
│   └── test-marketplace.sh, test-plugin-install.sh, test-generic-stack.sh
│                    Battery sub-suites: marketplace acceptance, real install,
│                    generic stack.
├── verify_harness/      The battery's domain package (ADR 2026-07-18 check-sync-decomposition):
│                    text.py (pure helpers), battery.py (aggregator + run harness), and
│                    checks/ (the step functions grouped by the evidence they read —
│                    lint, sync, suites). Import graph launcher → checks → battery
│                    → text, checker-enforced by battery step 1g.
└── verify-harness.py    Local deterministic gate — every mechanical check, lint to the real
                     plugin install; the step list lives in the script header. Tier 0
                     of the maintainer loop (root CLAUDE.md) and the mechanical layer
                     of /audit-harness. --quick (edits outside the derived trees) runs
                     the static checks only, refusing when those trees are dirty.
                     Enforced at push by .githooks/pre-push and the
                     .github/workflows/checks.yml CI workflow.
```

The split that matters: **runtime vs. project-owned.**

- `core/` and `stacks/<stack>/` hold the **runtime** — skills, agents, hooks, schemas, the `scripts/*.py` engines. `materialize.py` copies them into a target byte-for-byte (a copy, not a render: agents are pre-expanded per tool surface). Under the manifest channel this runtime is **gitignored** in the consumer — upgrading is a re-`materialize`, never a merge.
- `init/` holds skeletons for the files the **project owns and commits** — `CLAUDE.md`, `.claude/settings.json`, `scripts/layout.toml` (with the channel declaration), and the `docs/` brief roster (sourced from the doctor templates under `core/.claude/skills/doctor/templates/`). `init.py` lays these down once and never overwrites an existing project file.

`init/` is deliberately a sibling of `core/`/`stacks/`, not nested under them, so `materialize.py` (which walks `core` then `stacks/<stack>`) never copies the init skeletons into a target's runtime.

## The two operations

| Command | Delivers | Tracked in consumer? |
|---|---|---|
| `init.py <stack> <target> <name> <description> [harness-version] [tools-csv] [channel]` | project-owned files | yes (committed) |
| `materialize.py <stack> <target> [--no-verify] [--dry-run \| --show-plan]` | the runtime, verified by its installed suites | yes under the copy channel (default); no under manifest (gitignored) |

A greenfield setup runs both. The `/init` and `/materialize` skills are the interactive front-ends; `/materialize` runs `/init` first when the project-owned files are missing, so it covers a greenfield target in one step. To pull a downstream improvement back into this tree, use `/harvest`.

## The stack-agnostic invariant

`core/` carries no stack-specific fact. Anything that varies by language lives in `stacks/<stack>/`, in a brief, or in `scripts/layout.toml` (engine-read) — never branched in core runtime code. The same rule applies to `init/`: `init/core/` holds only files byte-identical across stacks. Keeping this line is what lets the core converge toward one universal runtime (phase 3 in the ADR).

## The stdlib-only invariant

The shipped runtime imports only the standard library, or a module in the importing file's own directory, and ships no dependency manifest. It runs on a consumer's machine, so a dependency here is one they never chose. The contract is [logic-in-python](../docs/adr/2026-07-06-logic-in-python-orchestration-in-bash.md) ("Stdlib only, Python 3.11+ for everything"). The battery's stdlib-only step enforces it across every tree that reaches a consumer on any channel; `docs/adoption-guide.md` states it to them.
