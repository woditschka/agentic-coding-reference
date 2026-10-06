---
name: install-opencode-dev
description: >-
  Install or update the opencode-dev tooling — the opencode-dev command, the
  shared agent-dev engine and its modules, the container Dockerfile, the
  open-weight preflight, and the default policy file with its egress allow-list — from this
  repo's tools/agent-dev/ into ~/.local/bin and
  ~/.config/opencode-dev. Thin front-end for tools/agent-dev/install.sh
  opencode: run its check mode to show drift, apply only on the user's
  approval. Use when the user asks to install opencode-dev or to set up a
  confined OpenCode. Examples: "install opencode-dev", "set up the opencode
  container", "update the opencode launcher".
compatibility:
  - claude-code
metadata:
  version: "1.1"
---

# install-opencode-dev

The mechanics live in `tools/agent-dev/install.sh` (source of truth: this repo's `tools/agent-dev/`). The skill adds the approval gate: **never apply without the user's explicit OK.** It installs the `opencode-dev` command only. `/install-claude-dev` installs `claude-dev`, and neither touches the other's files, data directory or image.

## Process

1. **Detect drift.** Run from the repo root (the script reads sources relative to itself; if not in this repo, stop and say so):
   ```bash
   tools/agent-dev/install.sh opencode check
   ```
   It prints one status per target: `identical`, `drift (N lines)`, or `missing`. The targets are the command (`~/.local/bin/opencode-dev`), the managed files, and the one policy file the user owns (`opencode-dev.toml`). The managed files are `agent-dev`, `agent_dev.py`, `agent_dev_config.py`, `agent_dev_profiles.py`, `Dockerfile` and `open_weight_preflight.py`. The installer carries no migration path: it installs the current tool and nothing else.

2. **Show the table and get approval.** Present the drift; for drifted rows, offer the unified diff on request. Do NOT edit without explicit approval ("apply", "go ahead", "install"). If everything is `identical`, report that and stop.

3. **Apply:**
   ```bash
   tools/agent-dev/install.sh opencode apply
   ```
   It installs the command and the managed files, keeps an existing `opencode-dev.toml` untouched, and smoke-tests `opencode-dev help`. The smoke test proves that the installed command runs and prints its help. It reads no policy: `help` answers before any config is read. A smoke-test failure exits non-zero: do not declare success; report the exact output.

4. **Handle policy drift.** `apply` never overwrites `opencode-dev.toml`, so a drifted config stays drifted. Show the diff and offer to merge the additions into the installed file; edit it only with the user's approval. `install.sh opencode reset-config` replaces it with the shipped version and keeps the old one as `.bak`. Offer it only when the user wants to discard their policy, never as the fix for a small merge.

   A config carrying a table or key this version does not read is refused by name at launch, not ignored. That includes a `[telemetry]` table, which this tool has no setting for. `check` reads the installed policy and reports that case as `REFUSED by this version`. Raise it BEFORE applying: a refused policy smoke-tests green, so `apply` reports success over it. After an apply, `opencode-dev access` is the check that reads the policy. The fix is to delete the named line, never to widen the reader.

5. **Name the model provider, only when asked.** The shipped allow-list names no model provider: a session cannot work until the hosts of the chosen provider are on it. When the user names a provider, propose the exact hosts it needs and add them only on approval. `opencode.ai` is deliberately absent: it accepts authenticated uploads, so add it only for a session that uses that provider. Never add a host unasked, and never paste in a list of names a session was observed requesting.

6. **Change the open-weight models, only when asked.** The shipped `opencode-dev.toml` enables `[open-weight]` for the Ollama daemon on this machine. It maps `claude-opus-5.5` and `claude-sonnet-5.5` to GLM cloud tags, so `--ow` works once the daemon is signed in (`ollama signin`). Before the user's first `--ow` run, relay the cloud-tag limit from `tools/agent-dev/README.md` § The reverse port. `apply` keeps an installed policy that has no `[open-weight]` table, so offer to merge the table in. `[open-weight.models]` is a pin → the tag the peer serves. A pin is the part of an agent's model after `openrouter/anthropic/`. The shipped `opencode-dev.toml` documents the table, and `docs/open-weight-models.md` the tiers. When the user asks for other models, read what the daemon has:
   ```bash
   ollama list
   ```
   Propose a map from that listing, one tag per pin. A cloud tag (`:cloud`) is served on demand and need not be listed, so take one from the user on their word. The peer need not be Ollama: any server that answers `POST /v1/chat/completions` in plain HTTP with no real key works. The root session runs as the first mapping unless `[open-weight] model` names another key. Edit the table only on approval. Then `opencode-dev access --ow` prints the plan, and the launch's own preflight re-checks the map against the peer.

7. **Report.** State what changed and the smoke-test result. Name the next steps that are NOT this skill's job: `opencode-dev build` for the image build, `opencode-dev update` after a Dockerfile change, and one `/connect` per project. The first run in a project says so. The credential and session history live in that project's private data directory, and a `--ow` launch uses a separate one. The image stage installs `opencode-ai` from the npm registry as the unprivileged account. Report a build failure verbatim.

## What this skill does NOT do

- **Build or update the image** — that is `opencode-dev build` / `opencode-dev update`; builds take minutes and the user runs them when ready.
- **Run the container** — the user runs `opencode-dev` from a project directory.
- **Log in** — credentials are container-private; `/connect` happens inside.
- **Edit the allow-list unasked** — `[egress] allow` in `opencode-dev.toml` is the user's egress policy.
- **Choose an open-weight peer** — `[open-weight] peer` in `opencode-dev.toml` names the model server `opencode-dev --ow` runs on; the shipped file sets it to this machine's Ollama daemon. Step 6 proposes another model map on request; changing the peer is the user's policy and is never written unasked.
- **Touch claude-dev** — that is `/install-claude-dev`.
- **Uninstall** — the user deletes `~/.local/bin/opencode-dev` and `~/.config/opencode-dev/` manually.
- **Pull from upstream** — the source of truth is this repo.
- **Survive across machines** — the install targets are per-machine; run once per machine.
