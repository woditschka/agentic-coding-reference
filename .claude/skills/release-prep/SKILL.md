---
name: release-prep
description: >-
  Roll the /harness source out to every instance, then prove it green — the
  propagate-and-verify step after a /harness edit. Thin front-end for
  harness/release-prep.sh, which runs bootstrap.sh (re-materialize the
  samples), package-marketplace.sh (re-render the plugins + marketplace.json),
  then check-sync.sh (the full deterministic battery). Use before audit-harness
  or a release-version. Writes the materialized tree; never commits, pushes, or
  runs the adversarial review. Root-only (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "2.0"
  author: team
---

# release-prep

The one call that makes the samples **and** the plugin marketplace reflect the
current `/harness` source, then runs the full deterministic battery. The whole
sequence is scripted:

```bash
harness/release-prep.sh
```

It runs `bootstrap.sh` (extras must be 0 per sample), `package-marketplace.sh`,
then `check-sync.sh` — the battery's step list lives in that script's header.
A non-zero exit is a hard stop.

## When to run

- After any `/harness` edit, to propagate it to the samples and the marketplace and verify.
- Before `/audit-harness` (the judgment gate) or `/release-version`.

## What it is, and is not

| | Propagates | Verifies | Judges |
|---|---|---|---|
| `check-sync.sh` | re-materializes in place for faithfulness only | full battery | no |
| **`release-prep.sh`** | **samples + marketplace (writes the tree)** | **full battery** | no |
| `/audit-harness` | (runs the battery) | full battery | **adversarial review + consistency** |

`release-prep` *applies* the source everywhere, where `check-sync` alone *fails*
if you forgot to re-materialize or re-render.

## Process

1. Run `harness/release-prep.sh`.
2. **Report one verdict.** Green: state that samples and marketplace match
   `/harness` and the battery passed. Not green: name the failing step, fix at
   the source (never a materialized sample or generated plugin), re-run.

```
## release-prep: <date>

Propagate: samples re-materialized (extras 0 each), marketplace re-rendered
Battery:    PASS | FAIL (<failing step>)

Verdict: <propagated and green, or what blocks it>
```

## What it does NOT do

- **Does not commit or push.** It leaves the propagated tree for you to review and commit (local-only — never propose server-side CI; the battery is the local gate).
- **Does not run the adversarial review or the consistency audit** — that is `/audit-harness`.
- **Does not change the version** — that is `/release-version`, whose script runs this one after the bump.
