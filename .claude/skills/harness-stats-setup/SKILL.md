---
name: harness-stats-setup
description: >-
  Install or update the harness-stats tooling — statusline.sh, cache-report.sh,
  and the cache-report skill — from this repo's tools/harness-stats/ into the
  user's ~/.claude/ directory. Detects drift, shows what would change, applies
  on approval, and merges the statusLine block into ~/.claude/settings.json
  without clobbering other keys. Use when the user asks to install the cache
  tooling, set up the statusline, update the harness-stats scripts, or
  reconfigure cache reporting. Examples: "set up the statusline", "install
  harness-stats", "update the cache tooling", "configure cache report".
compatibility:
  - claude-code
metadata:
  version: "1.0"
---

## Scope

| Source (this repo, source of truth) | Target (user-level install) |
|---|---|
| `tools/harness-stats/statusline.sh` | `~/.claude/statusline.sh` |
| `tools/harness-stats/cache-report.sh` | `~/.claude/cache-report.sh` |
| `tools/harness-stats/skills/cache-report/SKILL.md` | `~/.claude/skills/cache-report/SKILL.md` |
| (synthesized) `statusLine` block | `~/.claude/settings.json` (merged) |

## Process

### 1. Detect current state

Check each target. For each, classify as:

- **missing** — target does not exist
- **identical** — `diff` against source returns empty
- **drift** — file exists but differs

For `~/.claude/settings.json`:

- If file is missing → will create with just the `statusLine` block.
- If file exists → read it, check whether `.statusLine` is present and whether `.statusLine.command` points to `~/.claude/statusline.sh` or `/home/<user>/.claude/statusline.sh`. Classify as **missing**, **identical**, or **drift**.

Use absolute paths in settings.json (`~` is unreliable depending on Claude Code version). Derive the absolute path from `$HOME`.

### 2. Show drift table

Present findings before changing anything. Format:

```
## Harness-stats install drift

| File | Status |
|---|---|
| ~/.claude/statusline.sh             | drift (5 lines changed) |
| ~/.claude/cache-report.sh           | identical |
| ~/.claude/skills/cache-report/...   | missing |
| ~/.claude/settings.json statusLine  | drift (command path differs) |
```

For drift rows, optionally show the unified diff under the table so the user can decide whether to apply.

### 3. Get approval

Do NOT edit without explicit user approval. Wait for the user to say "apply", "go ahead", "install", or similar. If only some rows should be applied, the user may specify which.

A bundled "install/update everything" response is approval for all drifted/missing rows.

### 4. Apply edits

For each approved row:

1. **Script or skill file** — copy from repo to target. Create the target directory with `mkdir -p` if needed. Preserve executable bit on `.sh` files (use `cp` then `chmod +x`).
2. **Settings merge** — use `jq` to merge the `statusLine` block without disturbing other keys. Example:
   ```bash
   ABS_PATH="$HOME/.claude/statusline.sh"
   tmp=$(mktemp)
   jq --arg cmd "$ABS_PATH" '. + {
     statusLine: {
       type: "command",
       command: $cmd,
       padding: 1
     }
   }' ~/.claude/settings.json > "$tmp" && mv "$tmp" ~/.claude/settings.json
   ```
   If `~/.claude/settings.json` does not exist, create it with just the `statusLine` block.

Use specific file copies — do not `rsync` or `cp -r` an unrelated directory; always copy individual files by name.

### 5. Verify

After applying, run two smoke tests:

1. **statusline smoke test** — invoke `~/.claude/statusline.sh` with a synthetic stdin JSON pointing at the most recent transcript in the current project. The script should exit 0 and produce a non-empty single line of output.

   ```bash
   LATEST=$(ls -t ~/.claude/projects/$(pwd | tr / -)/*.jsonl 2>/dev/null | head -1)
   SID=$(basename "$LATEST" .jsonl)
   echo "{\"workspace\":{\"current_dir\":\"$(pwd)\"},\"session_id\":\"$SID\",\"transcript_path\":\"$LATEST\",\"cwd\":\"$(pwd)\"}" \
     | ~/.claude/statusline.sh
   ```

2. **cache-report smoke test** — run `~/.claude/cache-report.sh --list` and confirm at least the header is printed without error.

If either smoke test fails, do not declare success — report the failure with the exact output. Most likely culprits: missing `jq`, `awk`, or a `stat` invocation that fell through both GNU and BSD paths.

### 6. Report

Summarize: which files changed, the smoke-test results, and a one-line reminder that Claude Code must be restarted for the new statusline and skill to load (settings.json is read at startup).

If the user already had a `statusLine` configured pointing at a different script, mention that it was replaced and the original `command` value (so they can recover it if needed).

## What this skill does NOT do

- **Uninstall** — there's no removal flow. If the user wants to uninstall, they delete the four target files manually and remove the `statusLine` key from settings.
- **Tune thresholds** — color-coding thresholds (`HIT_GREEN`, `HIT_YELLOW`, `CREATION_WARN`) live as constants at the top of `statusline.sh` and `cache-report.sh`. Adjusting them is a manual edit of the source files in `tools/harness-stats/`, then re-run this skill to install.
- **Pull from upstream** — the source of truth is *this repo*, not a remote. If a newer version exists elsewhere, the user must update the repo first.
- **Run the report** — that's the `cache-report` skill (installed by this one). After install, the user invokes `/cache-report` or asks Claude about cache stats.
- **Survive across machines automatically** — `~/.claude/` is per-machine. The user must run this skill on each machine where they want the tooling.

## Notes

- `~/.claude/` files are user-level and shared across every project on the machine. Installing once is enough.
- The skill must be invoked from inside this repo (it reads source files from `tools/harness-stats/`). If invoked from another working directory, fail with a clear message and instructions to `cd` into the repo first.
- The `cache-report` skill installed by this one will only be discoverable after Claude Code restarts (skills are scanned at session start).
