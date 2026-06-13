# /harness — the single canonical harness source

This tree is the one place the harness is authored. The sample projects (`samples/go/`,
`samples/java-spring-boot/`) and any downstream consumer are **materialized instances**
of it, not separate sources. Edit the harness here; consumers pick up changes on
their next `materialize`. See the decision record at
[`../docs/adr/2026-06-12-docs-as-harness-project-api.md`](../docs/adr/2026-06-12-docs-as-harness-project-api.md).

## Layout

```
harness/
├── core/            Runtime files identical across every stack (the de-stackify target).
├── stacks/<stack>/  Runtime files specific to one stack (agent bodies, lint rules, schemas).
├── init/            Skeletons for the files a CONSUMER owns and commits (NOT runtime).
│   ├── core/        Project-owned files identical across stacks (settings.json, gitignore block).
│   └── stacks/<stack>/  Project-owned files per stack (CLAUDE.md, scripts/layout.toml).
├── materialize.sh   Install the runtime: overlay core then stacks/<stack> into a target.
├── init.sh          Scaffold the project-owned files into a target (never overwrites).
└── bootstrap.sh     Stack-agnostic: detect each target's stack, then materialize.
```

The split that matters: **runtime vs. project-owned.**

- `core/` and `stacks/<stack>/` hold the **runtime** — skills, agents, hooks,
  schemas, the `scripts/*.py` engines. `materialize.sh` copies them into a
  target byte-for-byte (a copy, not a render: agents are pre-expanded per tool
  surface). Under the manifest channel this runtime is **gitignored** in the
  consumer — upgrading is a re-`materialize`, never a merge.
- `init/` holds skeletons for the files the **project owns and commits** —
  `CLAUDE.md`, `.claude/settings.json`, `scripts/layout.toml` (with the channel
  declaration), and the `docs/` brief roster (sourced from the doctor templates
  under `core/.claude/skills/doctor/templates/`). `init.sh` lays these down once
  and never overwrites an existing project file.

`init/` is deliberately a sibling of `core/`/`stacks/`, not nested under them,
so `materialize.sh` (which walks `core` then `stacks/<stack>`) never copies the
init skeletons into a target's runtime.

## The two operations

| Command | Delivers | Tracked in consumer? |
|---|---|---|
| `init.sh <stack> <target> <name> <description> <harness-version>` | project-owned files | yes (committed) |
| `materialize.sh <stack> <target>` | the runtime | no (gitignored) |

A greenfield setup runs both. The `/init` and `/seed` skills are the
interactive front-ends; `/seed` is a compatibility wrapper that runs both in
order. To pull a downstream improvement back into this tree, use `/harvest`.

## The stack-agnostic invariant

`core/` carries no stack-specific fact. Anything that varies by language lives in
`stacks/<stack>/`, in a brief, or in `scripts/layout.toml` (engine-read) — never
branched in core runtime code. The same rule applies to `init/`: `init/core/`
holds only files byte-identical across stacks. Keeping this line is what lets the
core converge toward one universal runtime (phase 3 in the ADR).
