---
name: install-claude-dev
description: >-
  Install or update the claude-dev tooling — the claude-dev command, the
  shared agent-dev engine and its modules, the container Dockerfile, the
  default policy file with its egress allow-list, the IDE-oracle preflight, the
  open-weight preflight, and the ~/.claude.json scrubber — from this repo's
  tools/agent-dev/ into ~/.local/bin and ~/.config/claude-dev. Thin front-end
  for tools/agent-dev/install.sh claude: run its check mode to show drift, apply only
  on the user's approval. Use when the user asks to install claude-dev, set up
  the development container, or update the launcher or image definition.
  Examples: "install claude-dev", "update the container tooling", "set up the
  claude container".
compatibility:
  - claude-code
metadata:
  version: "2.4"
---

# install-claude-dev

The mechanics live in `tools/agent-dev/install.sh` (source of truth: this repo's `tools/agent-dev/`). The skill adds the approval gate: **never apply without the user's explicit OK.** It installs the `claude-dev` command only; other agent-dev commands install separately and never touch these files.

## Process

1. **Detect drift.** Run from the repo root (the script reads sources relative to itself; if not in this repo, stop and say so):
   ```bash
   tools/agent-dev/install.sh claude check
   ```
   It prints one status per target: `identical`, `drift (N lines)`, or `missing`. The targets are the command (`~/.local/bin/claude-dev`), the managed files, and the one policy file the user owns (`claude-dev.toml`). The managed files are `agent-dev`, `agent_dev.py`, `agent_dev_config.py`, `agent_dev_profiles.py`, `Dockerfile`, `claude_dev_scrub.py`, `ide_preflight.py` and `open_weight_preflight.py`. The installer carries no migration path. It reports the one module on its retired list, `claude_dev_config.py`, as `retired` and removes it on apply.

2. **Show the table and get approval.** Present the drift; for drifted rows, offer the unified diff on request. Do NOT edit without explicit approval ("apply", "go ahead", "install"). If everything is `identical`, report that and stop.

3. **Apply:**
   ```bash
   tools/agent-dev/install.sh claude apply
   ```
   It installs the command and the managed files, keeps an existing `claude-dev.toml` untouched, and smoke-tests `claude-dev help`. The smoke test proves that the installed command runs and prints its help. It reads no policy: `help` answers before any config is read. A smoke-test failure exits non-zero: do not declare success; report the exact output.

4. **Handle policy drift.** `apply` never overwrites `claude-dev.toml`, so a drifted config stays drifted. The usual cause is a new default domain in the repo copy. Show the diff and offer to merge the additions into the installed file; edit it only with the user's approval. `install.sh claude reset-config` replaces it with the shipped version and keeps the old one as `.bak`. Offer it only when the user wants to discard their policy, never as the fix for a small merge.

   A config carrying a table or key this version does not read is refused by name at launch, not ignored. `check` reads the installed policy and reports that case as `REFUSED by this version`. Raise it BEFORE applying: a refused policy smoke-tests green, so `apply` reports success over it. After an apply, `claude-dev access` is the check that reads the policy. The fix is to delete the named line, never to widen the reader.

5. **Change the open-weight models, only when asked.** The shipped `claude-dev.toml` enables `[open-weight]` for the Ollama daemon on this machine. It maps `claude-opus-5-5` and `claude-sonnet-5-5` to GLM cloud tags, so `--ow` works once the daemon is signed in (`ollama signin`). Before the user's first `--ow` run, relay the cloud-tag limit from `tools/agent-dev/README.md` § The reverse port. `apply` keeps an installed policy that has no `[open-weight]` table, so offer to merge the table in. `[open-weight.models]` is a pinned name → the tag the peer serves. When the user asks for other models, read what the daemon has:
   ```bash
   ollama list
   ```
   Propose a map from that listing, one tag per pinned name: `claude-opus-5-5` for the judgment tier, `claude-sonnet-5-5` for the checklist tier. The shipped `claude-dev.toml` documents the table, and `docs/open-weight-models.md` the tiers. A cloud tag (`:cloud`) is served on demand and need not be listed, so take one from the user on their word. The peer need not be Ollama: any server that answers `POST /v1/messages` in plain HTTP with no real key works. The root session runs as the first mapping unless `[open-weight] model` names another key. Edit the table only on approval. Then `claude-dev access --ow` prints the plan, and the launch's own preflight re-checks the map against the peer.

6. **Report.** State what changed and the smoke-test result. Name the next steps that are NOT this skill's job: `claude-dev build` for the image build, `claude-dev update` after a Dockerfile change, and one `/login` inside on first run. An image built without squid, socat and bubblewrap must be rebuilt first: a session started on one refuses to launch rather than running unproxied.

## What this skill does NOT do

- **Build or update the image** — that is `claude-dev build` / `claude-dev update`; builds take minutes and the user runs them when ready.
- **Run the container** — the user runs `claude-dev` from a project directory.
- **Log in** — credentials are container-private; `/login` happens inside.
- **Edit the allow-list** — `[egress] allow` in `claude-dev.toml` is the user's egress policy. Suggest entries; never add one unasked, and never paste in a list of names a session was observed requesting.
- **Choose an open-weight peer** — `[open-weight] peer` in `claude-dev.toml` names the model server `claude-dev --ow` runs on; the shipped file sets it to this machine's Ollama daemon. Step 5 proposes another model map on request; changing the peer is the user's policy and is never written unasked.
- **Uninstall** — the user deletes `~/.local/bin/claude-dev` and `~/.config/claude-dev/` manually.
- **Pull from upstream** — the source of truth is this repo.
- **Survive across machines** — the install targets are per-machine; run once per machine.
