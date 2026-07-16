---
name: claude-pod-setup
description: >-
  Install or update the claude-pod tooling — the claude-pod command, the pod
  Dockerfile, the default config, and the IDE-oracle preflight and relay
  scripts — from this repo's tools/claude-pod/ into ~/.local/bin and
  ~/.config/claude-pod. Thin front-end for
  tools/claude-pod/install.sh: run its check mode to show drift, apply only on
  the user's approval. Use when the user asks to install claude-pod, set up the
  container pod, or update the pod script or image definition. Examples:
  "install claude-pod", "update the pod tooling", "set up the claude container".
compatibility:
  - claude-code
metadata:
  version: "1.0"
---

# claude-pod-setup

The mechanics live in `tools/claude-pod/install.sh` (source of truth: this
repo's `tools/claude-pod/`). The skill adds the approval gate: **never apply
without the user's explicit OK.**

## Process

1. **Detect drift.** Run from the repo root (the script reads sources relative
   to itself; if not in this repo, stop and say so):
   ```bash
   tools/claude-pod/install.sh check
   ```
   It prints one status per target — `identical`, `drift (N lines)`, or
   `missing` — for the command (`~/.local/bin/claude-pod`), the Dockerfile,
   the config (`~/.config/claude-pod/claude-pod.cfg`), and the two IDE-oracle
   scripts (`ide_preflight.py`, `ide_relay.py`).

2. **Show the table and get approval.** Present the drift; for drifted rows,
   offer the unified diff on request. Do NOT edit without explicit approval
   ("apply", "go ahead", "install"). If everything is `identical`, report that
   and stop — nothing to do.

3. **Apply:**
   ```bash
   tools/claude-pod/install.sh apply
   ```
   It installs the command, the Dockerfile, and the two IDE-oracle scripts,
   keeps an existing `claude-pod.cfg` untouched, and smoke-tests
   `claude-pod help`. A smoke-test failure exits non-zero: do not declare
   success; report the exact output.

4. **Handle config drift.** `apply` never overwrites the config, so a drifted
   `claude-pod.cfg` stays drifted — usually the repo copy gained a new option
   (e.g. `CONTEXT`). Show the diff and offer to merge the new option into the
   installed file; edit it only with the user's approval.

5. **Report.** What changed, the smoke-test result, and the next steps that
   are NOT this skill's job: `claude-pod build` for the one-time image build
   (pulls toolchains, a few minutes), `claude-pod update` after a Dockerfile
   change, one `/login` inside the pod on first run.

## What this skill does NOT do

- **Build or update the image** — that is `claude-pod build` / `claude-pod update`; builds take minutes and the user runs them when ready.
- **Run the pod** — the user runs `claude-pod` from a project directory.
- **Log in** — credentials are pod-private; `/login` happens inside the pod.
- **Uninstall** — the user deletes `~/.local/bin/claude-pod` and `~/.config/claude-pod/` manually.
- **Overwrite the config** — `apply` keeps an existing `claude-pod.cfg`; merges go through step 4's approval.
- **Pull from upstream** — the source of truth is this repo.
- **Survive across machines** — the install targets are per-machine; run once per machine.
