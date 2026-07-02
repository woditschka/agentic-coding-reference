---
name: harness-stats-setup
description: >-
  Install or update the harness-stats tooling — statusline.sh, cache-report.sh,
  and the cache-report skill — from this repo's tools/harness-stats/ into the
  user's ~/.claude/ directory. Thin front-end for tools/harness-stats/install.sh:
  run its check mode to show drift, apply only on the user's approval. Use when
  the user asks to install the cache tooling, set up the statusline, update the
  harness-stats scripts, or reconfigure cache reporting. Examples: "set up the
  statusline", "install harness-stats", "update the cache tooling".
compatibility:
  - claude-code
metadata:
  version: "2.0"
---

# harness-stats-setup

The mechanics live in `tools/harness-stats/install.sh` (source of truth: this
repo's `tools/harness-stats/`). The skill adds the approval gate: **never apply
without the user's explicit OK.**

## Process

1. **Detect drift.** Run from the repo root (the script reads sources relative
   to itself; if not in this repo, stop and say so):
   ```bash
   tools/harness-stats/install.sh check
   ```
   It prints one status per target — `identical`, `drift (N lines)`, or
   `missing` — for the three files and the `statusLine` block in
   `~/.claude/settings.json`.

2. **Show the table and get approval.** Present the drift; for drifted rows,
   offer the unified diff on request. Do NOT edit without explicit approval
   ("apply", "go ahead", "install"). If everything is `identical`, report that
   and stop — nothing to do.

3. **Apply:**
   ```bash
   tools/harness-stats/install.sh apply
   ```
   It copies the three files, preserving the executable bit. It merges the
   `statusLine` block into `~/.claude/settings.json` with `jq` — other keys
   untouched, a replaced `statusLine.command` echoed for recovery. It then runs
   two smoke tests: statusline against the latest transcript, and
   `cache-report.sh --list`. A smoke-test failure exits non-zero: do not
   declare success; report the exact output. Likely culprits: missing `jq` or
   `awk`, or a `stat` call that fell through both GNU and BSD paths.

4. **Report.** What changed, the smoke-test results, and the reminder that
   Claude Code must restart for the statusline and skill to load.

## What this skill does NOT do

- **Uninstall** — the user deletes the targets and the `statusLine` key manually.
- **Tune thresholds** — the color-coding constants live at the top of `statusline.sh` and `cache-report.sh`; edit the sources in `tools/harness-stats/`, then re-run.
- **Pull from upstream** — the source of truth is this repo.
- **Survive across machines** — `~/.claude/` is per-machine and shared by every project on it; run once per machine.
- **Run the report** — that is the installed `cache-report` skill.
- **Partial installs** — `apply` refreshes all targets; per-file selection is a manual copy.
