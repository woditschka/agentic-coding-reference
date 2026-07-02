---
name: release-prep
description: >-
  Roll the /harness source out to every instance, then prove it green. Runs
  bootstrap.sh (re-materialize the samples) and package-marketplace.sh
  (re-render the plugins + marketplace.json), then check-sync.sh (the full
  deterministic battery: lint, syntax, sample suites, materialization and
  marketplace faithfulness, doctors, marketplace acceptance, the real plugin
  install). Use after editing /harness to make the samples and the marketplace
  reflect the source and confirm nothing regressed — before audit-harness or a
  release-version. Writes the materialized tree; never commits, pushes, or runs
  the adversarial review. Root-only (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# release-prep

The one call that makes the samples **and** the plugin marketplace reflect the
current `/harness` source, then runs the full deterministic battery. It is the
inner-loop "I edited `/harness` — apply it everywhere and confirm green" action.

## When to run

- After any `/harness` edit (`core/`, `stacks/<stack>/`, `init/`, scripts), to propagate it to the samples and the marketplace and verify.
- Before `/audit-harness` (the heavier pre-commit gate) or `/release-version`.
- Any time you want to confirm the tree is fully propagated and the battery is green.

## What it is, and is not

| | Propagates | Verifies | Judges |
|---|---|---|---|
| `check-sync.sh` (script) | re-materializes in place for faithfulness only | full battery | no |
| **`release-prep`** | **samples + marketplace (writes the tree)** | **full battery** | no |
| `/audit-harness` | (runs the battery) | full battery | **adversarial review + consistency** |

`release-prep` *applies* the source everywhere, where `check-sync` alone *fails*
if you forgot to re-materialize or re-render. It stops at "propagated and green";
the judgment pass is `/audit-harness`.

## Process

1. **Re-materialize the samples** (go, java-spring-boot, generic) from `/harness`:
   ```bash
   harness/bootstrap.sh
   ```
   It prints an `extras: N` line per sample — `N` must be `0` (a non-zero count is a committed orphan `/harness` no longer produces; `git rm` it).

2. **Re-render the marketplace** (one plugin per stack × tool + root `marketplace.json`):
   ```bash
   harness/package-marketplace.sh
   ```

3. **Run the full battery:**
   ```bash
   harness/check-sync.sh
   ```
   It re-runs the materialize and the render in place to confirm faithfulness, then the sample suites, the doctors, the marketplace acceptance test, and the real `claude plugin` install. A non-zero exit is a hard stop.

4. **Report one verdict.** If green, state that the samples and marketplace match `/harness` and the battery passed. If not, name the failing step; fix at the source (never a materialized sample or generated plugin) and re-run from step 1.

## Verdict format

```
## release-prep: <date>

Propagate: samples re-materialized (extras 0 each), marketplace re-rendered (<N> plugins)
Battery:    PASS | FAIL (<failing step>)

Verdict: <propagated and green, or what blocks it>
```

## What it does NOT do

- **Does not commit or push.** It leaves the propagated tree for you to review and commit (local-only — never propose server-side CI; the battery is the local gate).
- **Does not run the adversarial review or the consistency audit** — that is `/audit-harness`.
- **Does not change the version** — that is `/release-version`, which runs this skill after the bump.
- **Does not edit a materialized sample or a generated plugin by hand** — every fix goes to `/harness` (or root) and is re-propagated.
