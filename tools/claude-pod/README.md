# Claude Pod

User-level tooling for running Claude Code unattended. The harness's loops want `--dangerously-skip-permissions`; claude-pod confines the session in a disposable Linux container so the agent reaches far less of your host. The agent sees the project directory and your shared `~/.claude`, but not the rest of your host — read the [Security Model](#security-model) for the exact boundary before running an untrusted repo.

| Artifact | Purpose | Where it lives once installed |
|---|---|---|
| `claude-pod` | The command: builds the image on first run, then starts Claude Code in the pod from any project directory. | `~/.local/bin/claude-pod` |
| `Dockerfile` | The image: Ubuntu 26.04, JDK 25 (Corretto), Node 24, current Go, Claude Code as the last (cheap-to-rebuild) layer. | `~/.config/claude-pod/Dockerfile` |
| `claude-pod.cfg` | Your default policy: docker context (defaults to `auto`, which reaches Rancher Desktop on every platform; a hard `rancher-desktop` pin and ambient are documented options), extra writable/read-only mounts, network on/off. | `~/.config/claude-pod/claude-pod.cfg` |
| `ide_preflight.py` | Enumerates a running JetBrains IDE's MCP tools and checks them against the harness's read-only policy. Runs on every pod launch and warns on drift. With `--ide` it also verifies which IDE has the pod's project open. | `~/.config/claude-pod/ide_preflight.py` |
| `ide_relay.py` | Optional (`--ide`): runs inside the pod so the IDE's own `~/.claude.json` entry resolves there. Plumbing, not a boundary. Bridged only when exactly one IDE has the project open. | `~/.config/claude-pod/ide_relay.py` |

## Security Model

What the pod can touch:

- The current working directory (always writable; refuses to run from `$HOME`).
- `~/.claude` and `~/.claude.json`, bind-mounted at their real paths so shared config resolves identically in and out of the pod. `~/.claude/settings.json` and `settings.local.json` are overlaid **read-only** (see below).
- `~/.gitconfig` and `~/.config/git`, read-only.
- Directories you opt in via `--rw` / `--ro` or the config file.

Everything else of your home is hidden behind an empty tmpfs. Credentials are pod-private: `/login` once inside, and the OAuth token persists in `~/.config/claude-pod/auth`, never in the shared `~/.claude`. No `ANTHROPIC_API_KEY` is forwarded, so a subscription login stays subscription-billed. The container runs as your uid, non-root, which is also what lets Claude Code accept `--dangerously-skip-permissions`. It also runs hardened: every Linux capability dropped, `no-new-privileges` set so no setuid binary can escalate, Docker's default seccomp profile kept. These are runtime flags; they add no binaries to the image.

**The shared `~/.claude` is a trust boundary.** It is mounted read-write so Claude can persist session state. A hostile repo run permission-skipped could otherwise plant a hook or `statusLine` command that runs on the host at your next `claude` launch. The pod seeds an inert `settings.json` and `settings.local.json` when absent, then mounts both read-only, so it blocks that no-prompt path whether or not you already had those files. This is a partial barrier, not a wall: `mcpServers` in the read-write `~/.claude.json`, hook scripts your settings already reference by path, the user-level `~/.claude/CLAUDE.md`, and anything under `~/.claude/plugins/` remain writable. For full isolation from host config, run the pod against a throwaway `HOME`, pinning the pod data dir to its real place: `CLAUDE_POD_HOME="$HOME/.config/claude-pod" HOME="$(mktemp -d)" claude-pod`. The pin matters — `CLAUDE_POD_HOME` defaults under `$HOME`, so unpinned it follows the throwaway and costs a `/login` per run. (A throwaway `CLAUDE_POD_HOME` alone buys no isolation: it relocates the pod's own config and credentials, not the `$HOME`-driven `~/.claude` mount.) Or treat untrusted repos as untrusted regardless.

**A running JetBrains IDE is reachable from the pod, and the pod's boundary does not stop it.** This is not something `claude-pod` enables — it is true of every container on your Docker VM, with or without `--ide`, and it was true before this tooling existed. Three facts compose into it:

- JetBrains binds the IDE's MCP server to `127.0.0.1` deliberately, for security ([IJPL-200926](https://youtrack.jetbrains.com/issue/IJPL-200926); staff confirm the intent). On macOS that bind does **not** confine it: Docker Desktop and Rancher proxy `host.docker.internal` to the host's loopback, so a bare `docker run alpine` reaches it.
- The server has **no authentication**. Its only gate is a `Host: localhost` check — DNS-rebinding protection, satisfied by any client that sets the header.
- The pod is running permission-skipped, and `~/.claude.json` — where the IDE writes its endpoint — is mounted read-write.

So the only thing deciding what a pod can do to your IDE is the IDE's own **Settings → Tools → MCP Server → Exposed Tools**. The harness's policy keeps that set read-only (no tool writes a file or executes code), which is what makes the exposure tolerable. And the set is a checkbox that drifts: IDEA 2026.1 shipped an undocumented file-writing `apply_patch` enabled, and Settings Sync moves the set between IDEs and machines.

When python3 is on the host, every pod launch runs `ide_preflight.py` against whatever port the IDE assigned and warns if the exposed set leaves policy. **The warning is not a control.** It does not block the pod, and skipping the relay does not deny the agent anything it could not reach on its own. It tells you to go fix the setting, which is the only thing that actually restricts access.

With `--ide`, the preflight also enforces the oracle contract: exactly one policy-conforming IDE must have the pod's project open. It checks this by probing each conforming IDE with a read-only policy tool, so a subdirectory of an open project counts. An unverifiable answer counts as not open — the bridge carries only what the probe confirmed. Zero matches or several skip the bridge with a warning naming the observed state. Several means the same project in two IDEs: answers would depend on which server the agent queries. The pod still runs. Three limits worth knowing:

- Preflight is a snapshot: opening the IDE mid-session re-opens the path with no warning.
- With `--ide` the relay is TOCTOU: widening `Exposed Tools` mid-session is forwarded.
- Whether the IDE's file watcher sees writes the pod makes through the bind mount is unverified. `get_file_problems` refreshes only what the watcher noticed, so a miss degrades to a stale answer with no error.

**Why not Claude Code's in-process sandbox?** Its Linux backend is `bubblewrap` + `socat`, and `socat` is a dual-use binary that security scanners routinely flag, so the pod deliberately avoids it. Confinement is layered from tools already trusted here: the Rancher Desktop VM and container as the outer boundary; dropped capabilities, `no-new-privileges`, and the default seccomp profile as the inner one. The trade is coarseness — these act on the whole container, not per-command — accepted because the VM boundary is the load-bearing one.

With the target engine, Rancher Desktop, the Docker daemon runs in a VM on every platform, so the pod sits behind a VM boundary (see [Platform Support](#platform-support)).

## Installation

### Recommended: via the setup skill

If you're working inside this repo, run the project skill:

```
/claude-pod-setup
```

The skill runs the installer's check mode, shows what would change, and applies on approval. An existing `claude-pod.cfg` is never overwritten; the skill offers a merge when the shipped config gains new options.

### Manual

```bash
tools/claude-pod/install.sh   # command -> ~/.local/bin, data -> ~/.config/claude-pod
claude-pod build              # one-time image build (pulls toolchains, a few minutes)
```

Then, from any project directory:

```bash
claude-pod                    # Claude Code, permissions skipped, confined
claude-pod update             # rebuild only the Claude layer (seconds)
```

`claude-pod help` prints the full flag and env reference.

## Platform Support

The target engine is [Rancher Desktop](https://rancherdesktop.io/), which runs the Docker daemon in a VM on every platform — the pod always sits behind a VM boundary:

| Platform | How the default `auto` context reaches Rancher |
|---|---|
| macOS | `auto` pins the `rancher-desktop` context when present, else the ambient socket. Developed and used here |
| Linux | Same `auto` resolution — reaches Rancher whether it created the named context (admin access off) or owns the default socket. Not yet smoke-tested |
| Windows | Run from a WSL2 distro with Rancher's integration enabled; `auto` uses the ambient `/var/run/docker.sock` (Rancher creates no named context inside WSL). Not yet smoke-tested |

Windows Git Bash and native cmd/PowerShell are not supported: it is a bash script, and MSYS path mangling breaks the `-v` mounts.

Other engines work through the same ambient fallback but are not the target. Plain Docker Engine on native Linux confines by kernel namespace only — the container shares the host kernel. Rootless Docker and Podman are untested; the `--user $(id -u)` mapping behaves differently there.

## Related

- [`docs/adoption-guide.md` § Claude Pod](../../docs/adoption-guide.md#claude-pod) — when to reach for it.
- [`tools/harness-stats/`](../harness-stats/) — the other user-level tool; same install pattern.
