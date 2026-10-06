---
name: install-claude-dev
description: >-
  Install or update the claude-dev tooling — the claude-dev command, the
  container Dockerfile, the default config, the egress allow-list, the
  IDE-oracle preflight, and the ~/.claude.json scrubber — from this repo's
  tools/claude-dev/ into ~/.local/bin and ~/.config/claude-dev. Thin front-end
  for tools/claude-dev/install.sh: run its check mode to show drift, apply only
  on the user's approval. Use when the user asks to install claude-dev, set up
  the development container, or update the launcher or image definition.
  Examples: "install claude-dev", "update the container tooling", "set up the
  claude container".
compatibility:
  - claude-code
metadata:
  version: "2.2"
---

# install-claude-dev

The mechanics live in `tools/claude-dev/install.sh` (source of truth: this
repo's `tools/claude-dev/`). The skill adds the approval gate: **never apply
without the user's explicit OK.**

## Process

1. **Detect drift.** Run from the repo root (the script reads sources relative
   to itself; if not in this repo, stop and say so):
   ```bash
   tools/claude-dev/install.sh check
   ```
   It prints one status per target — `identical`, `drift (N lines)`, or
   `missing` — for the command (`~/.local/bin/claude-dev`), the managed files
   (`Dockerfile`, `claude_dev_config.py`, `claude_dev_scrub.py`,
   `ide_preflight.py`, `open_weight_preflight.py`), and the one policy file the
   user owns (`claude-dev.toml`). The installer carries no migration path and
   reports no retired files: it installs the current tool and nothing else.

2. **Show the table and get approval.** Present the drift; for drifted rows,
   offer the unified diff on request. Do NOT edit without explicit approval
   ("apply", "go ahead", "install"). If everything is `identical`, report that
   and stop.

3. **Apply:**
   ```bash
   tools/claude-dev/install.sh apply
   ```
   It installs the command and the managed files, keeps an existing
   `claude-dev.toml` untouched, and smoke-tests `claude-dev help`. A smoke-test
   failure exits non-zero: do not declare success; report the exact output.

4. **Handle policy drift.** `apply` never overwrites `claude-dev.toml`, so a
   drifted config stays drifted — most often the repo copy gained a new default
   domain. Show the diff and offer to merge the additions into the installed
   file; edit it only with the user's approval. `install.sh reset-config`
   replaces it with the shipped version and keeps the old one as `.bak` — offer
   it only when the user wants to discard their policy, and never as the fix
   for a small merge.

   A config carrying a table or key this version does not read is refused by
   name at launch, not ignored. `check` reports that case as `REFUSED by this
   version` — raise it BEFORE applying, because `apply` overwrites the managed
   files first and its smoke test would then fail on the stale policy. The fix
   is to delete the named line, never to widen the reader.

5. **Map the open-weight models, only when asked.** `claude-dev --ow` needs
   `[open-weight.models]` in `claude-dev.toml`: pinned name → the tag the peer serves.
   When the user asks to set up `--ow` or a local model, read what the daemon
   has:
   ```bash
   ollama list
   ```
   Propose a map from that listing, one tag per pinned name (`claude-opus-5-5`
   for the judgment tier, `claude-sonnet-5-5` for the checklist tier; the
   shipped `claude-dev.toml` documents the table, `docs/open-weight-models.md`
   the tiers). A cloud tag (`:cloud`) is served on demand and need not be
   listed, so take one from the user on their word. The root session runs as
   the first mapping unless `[open-weight] model` names another key. Write the table
   only on approval, and never fill it unasked. Then `claude-dev access --ow` prints
   the plan, and the launch's own preflight re-checks the map against the peer.

6. **Report.** What changed, the smoke-test result, and the next steps that are
   NOT this skill's job: `claude-dev build` for the image build (this build adds
   squid, socat and bubblewrap, so an existing image must be rebuilt — a session
   started on a stale image refuses to launch rather than running unproxied),
   `claude-dev update` after a Dockerfile change, and one `/login` inside on
   first run.

## What this skill does NOT do

- **Build or update the image** — that is `claude-dev build` / `claude-dev update`; builds take minutes and the user runs them when ready.
- **Run the container** — the user runs `claude-dev` from a project directory.
- **Log in** — credentials are container-private; `/login` happens inside.
- **Edit the allow-list** — `[egress] allow` in `claude-dev.toml` is the user's egress policy. Suggest entries; never add one unasked, and never paste in a list of names a session was observed requesting.
- **Choose an open-weight peer** — `[open-weight] peer` in `claude-dev.toml` names the model server `claude-dev --ow` runs on; the shipped file documents it commented out. Step 5 proposes the model map on request; the peer itself is the user's policy and is never written unasked.
- **Uninstall** — the user deletes `~/.local/bin/claude-dev` and `~/.config/claude-dev/` manually.
- **Pull from upstream** — the source of truth is this repo.
- **Survive across machines** — the install targets are per-machine; run once per machine.
