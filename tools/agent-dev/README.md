# Agent Dev

User-level tooling for running coding agents with approvals heavily reduced. `claude-dev` runs Claude Code and `opencode-dev` runs OpenCode. Unless a heading names `opencode-dev`, the sections below describe Claude Code's session.

A claude-dev session defaults to `--permission-mode auto`: a classifier approves routine actions and prompts only on the ones it flags. `--dangerously-skip-permissions` passes through for fully unattended runs. Either posture is confined in a disposable Linux container whose only path to the internet is a proxy it cannot reconfigure. The agent sees the project directory and a named slice of the host `~/.claude`, and reaches only the allow-listed domains. The [Security Model](#security-model) states the exact boundary; read it before running an untrusted repo.

## Structure

Every command runs one engine, `agent-dev`, which holds the confinement. A further tool adds a profile, a command script, a policy file, an installer arm and an image stage.

A command script names its tool, carries its usage text as its header, and execs the engine. The engine prints that header as `help` and checks where the script may run from. The tool's profile supplies every fact that differs between tools. These are the image stage, the shadowed directories, the credential store, the permission posture and the one inference path the reverse port admits. A command's data directory, image tag and labels carry its name, so two installed tools share no state, and neither session can mount the other's ([Fences Between Tools](#fences-between-tools)). Every code file sits beside the engine, so an engine never runs another version's modules. `install.sh <tool>` installs one command and leaves the others untouched.

| Artifact | Purpose | Where it lives once installed |
|---|---|---|
| `claude-dev` | The command: names its tool, holds its usage text, and execs the shared `agent-dev` engine. A first run builds the image. | `~/.local/bin/claude-dev` |
| `Dockerfile` | The image, one `base` stage for the toolchains and one stage per tool, built with `--target`: Debian 13 slim, JDK 25 (Corretto), Node 24, current Go. The `claude` stage adds Claude Code from Anthropic's signed apt repo as the last (cheap-to-rebuild) layer, and the `opencode` stage adds `opencode-ai` and a plugin seed. The base carries squid and socat, which carry the egress boundary and the IDE tunnel, and bubblewrap, which ships unused (see the sandbox note). | `~/.config/<command>/Dockerfile` |
| `claude-dev.toml` | The whole confinement policy, as data. Extra mounts sit under `[mounts]`, the mode and egress allow-list under `[egress]`, the open-weight peer and model map under `[open-weight]`, and Claude Code's telemetry declaration under `[telemetry]`. That is every key. The engine, the network and the bridge hardening have one sensible value each, so none of them is settable at all. Parsed with `tomllib` and never executed; unknown tables and keys are refused by name, so a typo cannot read as policy. Edited by hand, and the tool only ever reads it. | `~/.config/claude-dev/claude-dev.toml` |
| `opencode-dev` | The same shape for OpenCode. | `~/.local/bin/opencode-dev` |
| `opencode-dev.toml` | OpenCode's confinement policy: the tables `[mounts]`, `[egress]` and `[open-weight]`, with no `[telemetry]`, which the reader refuses for this tool. It names no model provider: the operator adds the hosts the chosen provider needs. | `~/.config/opencode-dev/opencode-dev.toml` |
| `agent-dev` | The engine every command runs. It owns the confinement: networks, proxy, mounts, fences, hardening, `access`, `cleanup` and `help`. It runs only through a command and reads the tool's facts from the profile as data. | `~/.config/<command>/agent-dev` |
| `agent_dev.py` | Runs one verb for one tool: reads the policy and the profile, writes one document to stdout. Emits the proxy's rules, the settings the launcher reads, and the session's settings document. | `~/.config/<command>/agent_dev.py` |
| `agent_dev_config.py` | The engine library: the policy file's reader and validators and the proxy's rules. The rule order is the security property, so it lives here where the suite pins it. It knows no agent tool. | `~/.config/<command>/agent_dev_config.py` |
| `agent_dev_profiles.py` | One typed `Profile` per tool. It names the command and image stage, the directories the session sees as a private shadow, and the credential store. It also names the permission posture, the one inference path the reverse port admits, and the session's settings. | `~/.config/<command>/agent_dev_profiles.py` |
| `ide_preflight.py` | Enumerates a running JetBrains IDE's MCP tools and checks them against the harness's read-only policy. Runs on `--ide` launches: warns on drift and verifies which IDE has the project open. | `~/.config/claude-dev/ide_preflight.py` |
| `claude_dev_scrub.py` | Builds the container-private `~/.claude.json` replica: the host file scrubbed to this project. | `~/.config/claude-dev/claude_dev_scrub.py` |
| `open_weight_preflight.py` | Asks the `[open-weight]` peer which models it serves and names every mapped tag it does not list. Runs on `--ow` launches, before anything is created. | `~/.config/<command>/open_weight_preflight.py` |

## Security Model

Three boundaries, each enforced by something the session cannot reach: **Docker networking** decides where packets may go, **the proxy's config** decides which destinations are allowed, and **the mount set** decides which host files exist inside. Nothing inside the container enforces its own confinement, and no container in this design holds `NET_ADMIN`, `NET_RAW`, or root in the session's namespace.

The default auto permission mode adds a behavioral layer above those boundaries, and is deliberately not counted as one. The classifier runs in the session's own process and reads the same context a hostile repo poisons. Every boundary below is sized to hold with it absent. That is exactly what a passed-through `--dangerously-skip-permissions` runs. The launcher owns no permission flag: it injects the auto default and steps aside when the pass-through args carry `--permission-mode` or `--dangerously-skip-permissions`.

### Egress: the session has no route out

<p align="center">
  <img src="../../docs/images/claude-dev-egress.drawio.png" width="720" alt="The session container sits on a per-run internal Docker network with no route out. A squid proxy straddles that network and its own egress network as the only exit, allowing CONNECT to port 443 for allow-listed domains and refusing host, LAN and metadata addresses. Every verdict is saved to last-egress.log on the host, and with --ide one preflighted port bridges back to a JetBrains IDE on the host machine. (The figure shows a claude-dev session without --ow; the reverse port to an open-weight peer is described below, and opencode-dev has the same topology.)">
</p>

The session container is attached to **one per-run internal Docker network**. An internal network carries no default route and no NAT, so the internet, the LAN, and the host are not *routable* from it. That is the engine's doing, not a rule inside the container that something could remove. The only other member of that network is a squid proxy, which is separately attached to a second per-run network for its own way out. Every packet the session sends leaves through the proxy or not at all. The tool's proxy variables are set so proxy-aware tools use it: `HTTP_PROXY` and `HTTPS_PROXY` for claude-dev, `HTTPS_PROXY` alone for opencode-dev. Anything that ignores them finds no route, so the failure direction is denied, never bypassed. JVMs ignore those variables, so `JAVA_TOOL_OPTIONS` carries the same route as Java proxy system properties.

The proxy's policy is generated per launch and is first-match-wins, top to bottom:

1. **Only the session may ask** — the client ACL is the internal network's subnet, read back after creation rather than assumed.
2. **The open-weight reverse port**, `--ow` only: the tool's one inference path on the proxy's second listener is admitted (`POST /v1/messages` for claude-dev, `POST /v1/chat/completions` for opencode-dev). Everything else on that listener is refused before any other rule can see it. The section below has the whole mechanism.
3. **CONNECT only** — HTTPS tunnels; no plaintext HTTP and nothing to cache (`cache deny all`).
4. **The IDE pinhole**, `--ide` only: exactly one preflighted port toward the host machine, placed *above* the private-range deny because the host is at a private address by definition.
5. **Every other private destination is refused** — loopback, RFC1918, carrier NAT, link-local (which covers cloud instance metadata at `169.254.169.254`), and the v6 equivalents. This matches the *resolved* address, so an allow-listed name that points or rebinds into the host or LAN does not connect.
6. **Port 443 only** — an allowed name buys HTTPS and nothing else: git over SSH, plain HTTP, and alternate ports stay denied, so a git remote must be an `https://` URL.
7. **The allow-list** — `[egress] allow` plus per-run `--allow` entries. `--open-egress` replaces this one line with "anything left"; every rule above it still applies.
8. **Deny all.**

Every request the proxy sees is logged with its verdict, outside the session container. Each session names the objects it owns after itself, so a running session `claude-dev-<id>` has its proxy at `claude-dev-<id>-proxy` and its two networks at `claude-dev-<id>-internal` and `claude-dev-<id>-egress`. `docker ps` therefore lists a session next to its own proxy rather than grouping all proxies together. Read the log live with `docker logs -t "$(docker ps -q --filter name=-proxy --filter name=claude-dev | head -1)"`, or from `~/.config/claude-dev/last-egress.log` after it exits. To see what was refused: `grep TCP_DENIED ~/.config/claude-dev/last-egress.log`, or `claude-dev access` for per-host counts. Concurrent sessions share that file and the last to exit wins, so it reads as one session, any project. Claude Code's optional Datadog telemetry is declared off by default (`DISABLE_TELEMETRY=1`) rather than allow-listed, keeping its intake hosts off the list without filling the log with denials. The broader `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is deliberately never set: it refuses every non-inference first-party API call inside the client, before the socket. That costs `/usage`, the Artifact and Design tools, memory sync and the MCP directory, all of which the allow-list already reaches. The cost of the narrower switch is a few `TCP_DENIED` lines per session for update checks, the changelog fetch and GitHub host lookups. Those denials are the policy working, and reading them beats not knowing what was asked for.

To send telemetry instead, set `telemetry.enabled = true` and uncomment both intake hosts in the config. The key and the allow-list are separate on purpose, so the network policy stays readable off the list alone. Setting the key without the hosts is a supported state: telemetry is attempted and refused at the proxy, and the log then shows what it would have sent. The two hosts are `http-intake.logs.us5.datadoghq.com` (event logs, 15s batches) and `browser-intake-us5-datadoghq.com` (error tracking, capped at 100 reports per process). Weigh them as channels, not as settings. Both accept arbitrary JSON authenticated only by a public client token compiled into the binary. Allowing them therefore opens a write path out of the session that reads as ordinary traffic in the log. Feature flags need neither: Claude Code fetches them from `api.anthropic.com` with remote evaluation.

An empty allow-list refuses to launch rather than starting a session that can reach nothing, and a launch without `api.anthropic.com` warns by name. Every entry is validated before anything is created: a URL, port, CIDR or bare address is refused by name. The refusal matters because squid silently ignores a malformed entry: it reads as allowed while behaving denied.

**The policy is data, and the order is tested.** `claude-dev.toml` is parsed with `tomllib` and never executed, so no file under `~/.config/claude-dev` can run code on the host. A file that will not parse is refused by name rather than read as an absent policy. The rule list above is generated by `agent_dev_config.py`. Its suite pins each edge that carries a security property. The open-weight block sits directly after the client restriction and leaves the forward port's rules untouched. The IDE pinhole sits above the private-range deny. The port restriction sits below it and above the allow-list. Deny-all is last. Reordering any of them fails a test instead of silently changing what a session can reach.

**The engine-side bridge carries no address.** The internal network is created with `inhibit_ipv4`, so the bridge interface Docker would otherwise give an address inside the engine VM has none. The one host-local endpoint that subnet would expose does not exist. Container-to-container traffic is plain L2 and name resolution rides each container's own `127.0.0.11` resolver, so neither depends on that address. An engine too old for the option is not silently accepted: the launch warns, names what stays reachable, and continues. There is no key to silence that warning: its only alternative is an engine that cannot do this, so the fix is the engine (Moby 26+, 2024).

**What the allow-list does not promise.** An allowed domain is an allowed *channel*: `.github.com` on the list means gists and pushes are an exfiltration path. The list's tightness *is* the policy. The shipped default carries `github.com` and `.githubusercontent.com` because the Gradle wrapper's distribution chain redirects through them; drop both when sessions never bootstrap Gradle. Pushing needs credentials too, and none are shared by default: `~/.gitconfig` rides in read-only, but host credential helpers (the macOS keychain, `gh auth`) do not work inside. Share a token store with `RO`/`RW` if the session must push, or push from the host. Domain fronting is not closed. An allowed domain on a shared CDN is reachable by any co-tenant the agent names in the inner TLS SNI, which the proxy does not see. DNS remains a low-bandwidth side channel: the session's lookups go to the engine's resolver, and the proxy logs destinations rather than blocking names. And the proxy inspects no payload: it decides *where* traffic may go, never *what* is in it. TLS interception would change that and is deliberately not done. Squid resolves a name and then connects, so a name that changes answers between those two steps is a narrow race the `dst` check cannot close. Finally, a compromise of squid itself yields code in its own container as an unprivileged user with no capabilities and no host access. The control's worst case is its own absence.

### Files: `~/.claude` is default-deny, enumerated shared paths only

Inside the container, `HOME` is the host home *path* (not its contents): an empty tmpfs owned by the operator's uid, with only named paths bind-mounted in at their real locations. Same-path mounting is what makes absolute host paths in shared config (a `statusLine` command, a hook, an MCP server) resolve identically in and out.

`~/.claude` inside is a **container-private shadow directory**, one per project, persisted at `~/.config/claude-dev/state/claude-state/<key>`. The key is a hash of the project's physical path, and a launch with `--ow` uses a separate shadow, `<key>.ow`. A root that Claude Code loads code or configuration from is therefore never shared across projects. A session on a peer never shares a shadow with a credentialed one. The launcher does not read a directory at `~/.config/claude-dev/state/claude`; the operator can delete one that exists. Nothing from the host `~/.claude` is visible there unless it is named here:

- **Session state, shared read-write** — `projects/<this-project>` (transcripts and auto-memory), `tasks/`, `plans/`, `todos/`, `paste-cache/`, `history.jsonl`. These are shared because seamless host↔container switching needs them.
- **Behavior config, shared read-only** — `settings.json`, `settings.local.json`, `CLAUDE.md`, `agents/`, `commands/`, `hooks/`, `output-styles/`, `plugins/`, `rules/`, `skills/`, `workflows/`. These are the files that make a host `claude` run code with no prompt. A read-only share exists only for a name the host has. Where the host has none, the session can create that name inside its own project's shadow, and it reaches later sessions of that project only. One writable overlay sits inside the read-only `plugins/` share: `plugins/data/`, the per-plugin runtime state Claude Code creates before executing a plugin hook. Without it that mkdir fails and every plugin hook dies unrun. The overlay is container-private shadow state. Plugin code stays host-owned and read-only.
- **`~/.claude.json` is never shared.** It is replicated per launch and scrubbed to this project. Only `projects` entries overlapping the launch cwd are kept: its ancestors (they carry the trust verdict Claude looks up) and its subtrees (worktrees, subdirectory sessions). Sibling projects' paths, MCP servers, and trust states stay on the host. The host copy always wins; `/login` and trust work normally inside, and nothing written there reaches the host file.

Everything else stays private, so a new Claude Code state directory defaults to private: the failure direction is state loss, never exposure. Even a fully permission-skipped session therefore cannot plant a user-scope `mcpServers` entry or flip project trust on the host. It cannot rewrite a hook script, `plugins/` or `CLAUDE.md` that the host has. A config name the host lacks is writable in the project's own shadow, so a plant there reaches that project's later sessions and no other project's. Assets kept in `~/.claude` beyond the shared paths (the harness-stats statusline, say) share with one `RO`/`RW` entry. `install.sh` writes that line itself when it creates the config and finds those files present.

**Host managed policy is never shared, deliberately.** This is a personal tool. Carrying an org's `managed-settings.json` inside would mean owning the `managed-settings.d/` fragment directory beside it, a launch-time refusal for managed settings that hard-require the in-process sandbox, and an override variable to escape all of it. That is enterprise MDM plumbing well past what a personal launcher should hold. The cost is disclosed rather than papered over. Inside the container an org's managed policy is absent, so a `/login` here is not bound by `forceLoginMethod`/`forceLoginOrgUUID` and managed permission rules do not apply. **Work governed by managed settings belongs on the host.**

Credentials are container-private: `/login` once inside, and the OAuth token persists in `~/.config/claude-dev/auth`, never inside `~/.claude`. No `ANTHROPIC_API_KEY` is forwarded, so a subscription login stays subscription-billed. Under `--ow` the directory is not mounted at all, and the session authenticates to the peer with a placeholder token. [The reverse port](#the-reverse-port-an-open-weight-peer-the-proxy-can-read) lists what else is withheld. Running as the operator's uid, non-root, is also what lets Claude Code accept a passed-through `--dangerously-skip-permissions`.

Three residuals, disclosed. The project directory is writable by definition: in an already-trusted repo, a hostile session can still plant project-side `.claude/settings.json` hooks. Treat untrusted repos as untrusted. The shared session-state directories are session-keyed, not project-keyed, so tainted task, plan, or paste text is a cross-project prompt-level surface. `file-history/` deliberately stays private: `/rewind` restores file content, so a tainted snapshot would become a host file write on a later host-side rewind. For total isolation from host config, the throwaway-`HOME` recipe still works: `CLAUDE_DEV_HOME="$HOME/.config/claude-dev" HOME="$(mktemp -d)" claude-dev` (the pin matters: unpinned, `CLAUDE_DEV_HOME` follows the throwaway and costs a `/login` per run).

### Process: hardening, and why the in-process sandbox stays off

The session container runs with every Linux capability dropped, `no-new-privileges` set so no setuid binary can escalate, and Docker's default seccomp and AppArmor profiles kept: `=unconfined` is never passed. All runtime flags; they add no binaries to the image. The proxy container is hardened identically and additionally runs as the image's unprivileged `proxy` account.

**Claude Code's own in-process sandbox is forced off, and that is a measurement rather than a preference.** The image ships `bubblewrap`, but under Docker's default seccomp profile it cannot create a user namespace. Measured on Rancher Desktop, docker 29.5.2, 2026-07-29:

| Container flags | `bwrap --unshare-all` |
|---|---|
| `cap-drop=ALL` + `no-new-privileges` + default seccomp | no permissions to create new namespace |
| default capabilities + default seccomp | no permissions to create new namespace |
| `cap-drop=ALL` + `cap-add=SYS_ADMIN` + default seccomp | fails at `pivot_root` |
| `cap-drop=ALL` + `no-new-privileges` + `seccomp=unconfined` | works |

The documented escape for containers, `sandbox.enableWeakerNestedSandbox`, is measured too (claude 2.1.220, 2026-07-31). Under the shipped flags, every sandboxed Bash command fails with the same namespace error: the weaker mode still creates namespaces through bubblewrap. `failIfUnavailable` does not refuse startup either: the session runs with every Bash command failing. The strict nested config therefore bricks Bash rather than confining it.

So the syscall filter is the blocker, not capabilities. Turning the sandbox on means running the whole container without seccomp, losing a broad, always-on kernel filter over every process, to gain a per-command boundary the container already provides. Egress is proxy-controlled whether or not the sandbox is on, and the filesystem is already the project directory plus the named shared paths. The launcher therefore passes one generated `--settings` document, the sandbox-off declaration included, at CLI precedence above every settings file. A host that enables the sandbox, even hard-requiring it via `failIfUnavailable`, still starts here.

Nothing inside can outrank that flag, because host managed policy is not shared into the container at all (see above). The injected override is therefore the last word on the sandbox for every launch.

`bubblewrap` stays in the image regardless. It costs about 50KB, and the battery does not gate on it. Keeping it means the other posture is reachable without a rebuild on an engine whose default seccomp profile permits unprivileged user namespaces. Opting into it needs both halves: a user-passed `--settings` (it lands after the injected one in argv and displaces it) *and* `--security-opt seccomp=unconfined` on the run.

### Why the IDE bridge exists at all

**A running JetBrains IDE is reachable from every container on the Docker VM.** That is not something claude-dev enables: it is true of a bare `docker run alpine`, and it was true before this tooling existed. The internal network closes it for this session; other containers remain in the open. Three facts compose into the exposure:

- JetBrains binds the IDE's MCP server to `127.0.0.1` deliberately, for security ([IJPL-200926](https://youtrack.jetbrains.com/issue/IJPL-200926); staff confirm the intent). On macOS that bind does **not** confine it: Docker Desktop and Rancher proxy `host.docker.internal` to the host's loopback.
- The server has **no authentication**. Its only gate is a Host check accepting localhost forms: DNS-rebinding protection, satisfied by any client that sets the header.
- The session prompts rarely (never when permission-skipped), and its `~/.claude.json` replica, which carries the IDE's endpoint entry, is writable inside.

What the session can do to the IDE over the one opened port is decided by the IDE's own **Settings → Tools → MCP Server → Exposed Tools**. The harness's policy keeps that set read-only (no tool writes a file or executes code), which is what makes the exposure tolerable. And the set is a checkbox that drifts: IDEA 2026.1 shipped an undocumented file-writing `apply_patch` enabled, and Settings Sync moves the set between IDEs and machines.

An `--ide` launch with python3 on the host runs `ide_preflight.py` against whatever port the IDE assigned and warns if the exposed set leaves policy. **The warning is not a control**: the network topology and the Exposed Tools setting are. It points at the setting to fix, which is the only thing that restricts what the IDE will do for any client. A launch without `--ide` never probes the IDE: the session has no path to the IDE's port, so drift cannot reach it. A probe against a starting IntelliJ also trips an upstream bug that spams its log. The standing drift check for other clients is `ide_preflight.py --discover`, run directly.

With `--ide`, the preflight also enforces the oracle contract: exactly one policy-conforming IDE must have this project open. The check probes each conforming IDE with a read-only policy tool, so a subdirectory of an open project counts. An unverifiable answer counts as not open. Only a verified port gets a proxy pinhole, and an unprivileged `socat` inside the session listens on the IDE's own `127.0.0.1:<port>` config entry and tunnels it through the proxy's CONNECT. That listener holds no privilege and enforces nothing, so killing or replacing it gains the session nothing. Anything but exactly one match skips the bridge with a warning naming the observed state; the session still runs. Four limits worth knowing:

- Preflight is a snapshot, but the topology holds: an IDE started or re-ported mid-session lands on the deny side until relaunch. That is a missing oracle, never a new opening.
- The opened port is TOCTOU: widening `Exposed Tools` mid-session is forwarded.
- The tunnel forwards the client's literal `Host: 127.0.0.1` inside the CONNECT, which is what the IDE's rebind check wants; IDEA 2026.1.4 accepts that form (verified live).
- Whether the IDE's file watcher sees writes made through the bind mount is unverified. `get_file_problems` refreshes only what the watcher noticed, so a miss degrades to a stale answer with no error.

### The reverse port: an open-weight peer the proxy can read

`--ow` (long form `--open-weight`) runs the session on a model server declared in `[open-weight]`, an Ollama daemon on the host by default, instead of the vendor's API. Any server that answers the tool's one inference path in plain HTTP with no real key can be the peer. [`docs/open-weight-models.md`](../../docs/open-weight-models.md) covers the mapping and the model tiers. This section covers how the session reaches the peer, and why not through a tunnel.

The IDE bridge is a CONNECT tunnel: the proxy sees a destination and bytes, never a request. A model server's API has no authentication and carries model management beside inference: `/api/pull`, `/api/delete`, `/api/create`, and `/api/push`, an upload to a registry and so an exfiltration path. A tunnel to it would carry all of that unobserved. So the peer is reached differently:

- **The proxy gains a second listener**, port 3129, in squid's accelerator mode with the peer as its one fixed `cache_peer`. The session sets `ANTHROPIC_BASE_URL=http://proxy:3129` and sends ordinary HTTP requests, so the proxy parses method and path.
- **One request shape is admitted**: `POST /v1/messages` and its `count_tokens` sibling. A query string is admitted when it holds only letters, digits and `_ = & -`, since Claude Code posts to `/v1/messages?beta=true`. The shape is a constant, not a setting: the client chooses the path, and a wider shape would be the management API the port exists to refuse. Everything else on that port is refused by the block's own deny, before any later rule could see it. A percent-encoded path is refused too, since squid matches the decoded path while the raw bytes reach the peer.
- **The forward port is untouched.** A plain request there still meets the plaintext deny. A CONNECT to a host or LAN peer meets the private-range deny, and one to any port but 443 meets the 443-only deny. The config refuses port 443 for the peer, so no public peer is reachable as a tunnel either.
- **Every request is logged with its path.** `access` shows the reverse port's traffic as `host/path` rows, so a refused `/api/pull` reads as such. The forward port's rows stay host-only, since a tunnel has no path.
- **The launcher hands the session no stored credential.** The credential directory is not mounted, and Claude Code's credential store points at an unmounted path under the tmpfs home, so a `/login` typed inside persists nowhere. The per-launch `~/.claude.json` replica drops `primaryApiKey` and every `mcpServers` entry that can hold a token, top-level and per-project. A bare loopback endpoint, the entry an IDE writes for its own server, stays, so `--ide` works on a peer. The `~/.claude` shadow is the project's `.ow` one, apart from the shadow a credentialed session uses. A key written in the clear in the shared `settings.json`, or in a path the operator mounts, stays readable.
- **The settings document carries the peer and the map.** It holds the base URL, a placeholder `ANTHROPIC_AUTH_TOKEN`, a 30-minute `API_TIMEOUT_MS` for slow local models, and the `[open-weight.models]` map as `modelOverrides`. It sets `model` to a mapped name, the first mapping unless `[open-weight] model` says otherwise. The agents name their pins, but the session itself would run whatever `/model` says, and that name would reach the peer unmapped. These ride in `--settings`, at CLI precedence above every project file, because a settings-file `env` block overrides the process environment. A project's own `ANTHROPIC_BASE_URL` therefore cannot point the session past the proxy. A user-passed `--settings` displaces the whole document, map included.

The peer is policy, so it lives in the file and the flag takes no argument. `peer = "host"` is this machine, reached as `host.docker.internal`. On Docker Desktop and Rancher Desktop that name reaches a daemon bound to `127.0.0.1` without a rebind, the same fact that makes the IDE reachable above. A LAN address is a peer like any other, with two differences: the daemon there must listen beyond loopback, and prompts and code cross the LAN in plain HTTP. `access --ow` states both. Plain Docker Engine on Linux defines no `host.docker.internal`; the launch dies naming the peer, and the host's bridge address goes in its place.

Before anything is created, `open_weight_preflight.py` asks the peer for its model listing from the host and compares it with the map. A peer that does not answer ends the launch, and so does a local tag the peer does not list, since every dispatch naming it would fail. An unlisted cloud tag only warns, because the daemon fetches one on first use. The preflight asks for Ollama's listing first and falls back to the OpenAI one (`/v1/models`), so a server that is not Ollama is checked the same way. One deadline bounds the whole listing fetch, and a deeply nested or non-JSON listing is reported as an unusable answer. Peer-sent strings are reduced to printable ASCII before they reach the terminal.

Limits, disclosed:

- **The body is opaque.** The model name travels in the JSON, so the session can name any model the peer serves. `/v1/messages` does not pull a missing local model. A daemon signed in to a cloud registry serves cloud tags on demand, and that leg never shows in the proxy's log.
- **The shipped map names cloud tags.** A default `--ow` session therefore sends prompts and code to the tag's vendor through the daemon, outside the proxy's log, and the daemon must be signed in. The launch and `access --ow` say so whenever a cloud tag is mapped. An operator who wants nothing to leave the machine maps local tags and signs the daemon out. The [reverse-port ADR](../../docs/adr/2026-10-06-open-weight-reverse-port.md) records why the default ships this way.
- **Verified by hand, not by a test.** A maintainer run on 2026-10-06 served a session from the host's Ollama daemon through the reverse port. The suite pins the rule order, the request shape and the settings document, and a stub-engine test drives the launch to the session exec. No test drives a real squid or a real peer. How squid treats a percent-encoded path on that port is unverified. A live run records a `TCP_MISS` row for `/v1/messages` in `last-egress.log`, and a refused `/api/pull` shows there as `TCP_DENIED`.

### Supply chain

**Claude Code installs from Anthropic's GPG-signed apt repository.** The Dockerfile pins the signing key's fingerprint, the value documented at [code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup), and rejects a served key that does not match. No `curl | bash` installer remains; a battery tripwire fails the build if that idiom returns (it guards the idiom, not every execution path). Debian and Corretto packages are apt-signature-verified; only the Node and Go tarballs ride TLS alone, resolved to latest at build time. That trade (toolchain currency over pins) and the `debian:13-slim` base choice are recorded in [ADR 2026-07-20](../../docs/adr/2026-07-20-pod-image-supply-chain.md). The image runs non-root by default (`USER dev`); the wrapper overrides it with the operator's uid on every run.

The topology and the reasoning behind it are recorded in [ADR 2026-07-29](../../docs/adr/2026-07-29-proxy-enforced-egress.md), which supersedes the in-container packet filter of [ADR 2026-07-17](../../docs/adr/2026-07-17-default-deny-pod-host-egress.md).

## opencode-dev

`opencode-dev` runs OpenCode in the same confinement. The proxy, the networks, the hardening, the fences, `access` and `cleanup` are the engine's. The sections above describe Claude Code's session; this section states what differs for OpenCode. The [one-engine ADR](../../docs/adr/2026-10-06-one-engine-for-agent-dev-tools.md) records the decision.

| | claude-dev | opencode-dev |
|---|---|---|
| Image stage | `claude`, Claude Code from the signed apt repo | `opencode`, `opencode-ai` from the npm registry, installed by the unprivileged account |
| Private shadows | `~/.claude`, one per project and a separate one under `--ow` | config, data, state, cache and `~/.claude`, each with a lifetime (below) |
| Shared read-only from the host | `CLAUDE.md`, `agents`, `commands`, `hooks`, `output-styles`, `plugins`, `rules`, `settings.json`, `settings.local.json`, `skills`, `workflows` | `AGENTS.md`, `agents`, `commands`, `opencode.json`, `plugins`, `skills`, `tui.json` under `~/.config/opencode`; `CLAUDE.md` and `skills` under `~/.claude` |
| Shared read-write | session state for this project | none |
| Credential | `~/.config/claude-dev/auth`, relocated by `CLAUDE_SECURESTORAGE_CONFIG_DIR` | `auth.json` in the per-project data shadow; `/connect` once in each project |
| Under `--ow` | the credential directory is not mounted, the replica drops stored keys, and the `~/.claude` shadow is a separate one | a separate data shadow, apart from the one a provider login uses |
| Settings document | `--settings`, argv | `OPENCODE_CONFIG_CONTENT`, environment |
| Proxy variables | `HTTP_PROXY`, `HTTPS_PROXY` and their lowercase forms | `HTTPS_PROXY` and `https_proxy` |
| Reverse port admits | `POST /v1/messages` and `count_tokens` | `POST /v1/chat/completions` |
| Permission posture | `--permission-mode auto` unless overridden | OpenCode's own; the launcher injects none |
| IDE bridge | `--ide` | not offered |

**State lifetimes.** OpenCode loads plugins, agents, commands and MCP servers from `~/.config/opencode`, and it runs provider packages from `~/.cache/opencode`. A directory shared across projects would carry one hostile project's plant into every later session. So the config, state, cache and `~/.claude` shadows are created for each launch and discarded on exit. The data shadow holds `auth.json`, the session database and logs. It is keyed by a hash of the project's physical path, and a launch with `--ow` uses a separate one. A plant in one project reaches that project's later sessions only. The state directory is owner-only.

The lifetimes carry costs. Each project needs its own `/connect`, and a first run in a project says so. A package OpenCode installs into its cache at runtime is fetched again on the next launch. A `/connect` typed inside an `--ow` session persists its login in the project's `.ow` data shadow, where that project's later `--ow` sessions read it.

**Parent directories.** OpenCode's roots sit below `~/.config`, `~/.local` and `~/.cache`. The engine would create those parents owned by root inside the home tmpfs, and the Go build cache beside `~/.cache/opencode` could not be written. Each parent of a nested root is therefore its own tmpfs with the home's options.

**Why `HTTPS_PROXY` alone.** The reverse port is plain HTTP. Measured on opencode-ai 1.18.34 (2026-10-06), a session with `HTTP_PROXY` set sends the model call to the forward port, which refuses plaintext, and the run ends with `Forbidden`. With `HTTPS_PROXY` alone, the catalog fetch tunnels through `CONNECT` and the model call reaches the peer directly. Other plaintext has no route, so it is refused but not logged. `NO_PROXY` still carries the proxy host under `--ow`. With no `HTTP_PROXY` set it has no effect on the model call, and OpenCode's handling of it is unmeasured.

**The inline config outranks the project's files.** The launcher's document rides in `OPENCODE_CONFIG_CONTENT`. In the same measurement a project `opencode.json` that pointed the provider at another path and model id lost on both. A project plugin runs in-process and can still alter the provider at runtime. That costs no confinement, since the proxy decides every route. The document sets `share` to `disabled`, since a shared session uploads its transcript, and `autoupdate` to `false`, since the session has no route to the release channel.

**Under `--ow`** the document overrides the `openrouter` provider, the one the harness's OpenCode agents pin, with the reverse port's address and a placeholder key. Each `[open-weight.models]` pin maps to the peer's tag. The root model and the small model both name mapped entries. Unpinned, the title request reached the peer as `google/gemini-3.8-flash`. The pins in `opencode-dev.toml` are the part after `openrouter/anthropic/`, for example `claude-opus-5.5`.

**The plugin SDK is seeded, not fetched.** At startup OpenCode runs a background `npm` install of `@opencode-ai/plugin` into `~/.config/opencode`. The image installs that package at OpenCode's own version into `/opt/opencode-seed`. A step inside the session copies it into the per-run config shadow at every start. A read-only config directory is not an option: OpenCode writes into it at startup. The shipped allow-list carries `registry.npmjs.org` for the toolchains, so the seed buys startup determinism and an allow-list that can drop the registry. It is not a requirement.

**The image stage installs unprivileged.** npm runs package lifecycle scripts, and the proxy container starts from the same image as the session. The opencode stage therefore runs `npm install` as the unprivileged `dev` account, into directories only that account owns. A compromised package cannot replace squid or any other root-owned file. The package directory joins `PATH` last, so nothing in it shadows a system command. The trust in the registry itself is TLS alone, as for Node and Go.

**The policy file.** `opencode-dev.toml` names no model provider, and it leaves `opencode.ai` off the list: that origin accepts authenticated uploads. `models.opencode.ai` is on it, and a refusal is harmless because the session falls back to its bundled catalog. The reader refuses a `[telemetry]` table for this tool, since OpenCode's telemetry is opt-in and the launcher declares nothing about it.

**What the session can read.** The session reads the host's `opencode.json`, as claude-dev's session reads `settings.json`. A provider key written there in the clear is visible to it.

**Verified by hand.** A maintainer run on 2026-10-06 built both images, started a session in each, ran `--ow` against the host's Ollama daemon and ran `cleanup --all`. That run covers the unprivileged image stage, the parent tmpfs mounts, the shared image label and the per-project shadows of both tools. No test repeats it: the suites drive a stub engine.

**Unverified.** The OpenCode measurements used a stub peer and one OpenCode version. No HTTPS inference to a real provider has crossed the proxy. The `timeout` provider option and the `share` and `autoupdate` keys are checked against OpenCode's published config schema, not against a runtime.

## Fences Between Tools

The fences hold for every command and judge the path a mount resolves to.

- **Resolution.** A symlink or a trailing `..` is resolved before any comparison, and the comparison uses the directory entry's own spelling. A path typed in another letter case on a case-insensitive filesystem therefore resolves to the same protected path and is refused. A launch from a directory reached through a link or another spelling names the physical path it mounts.
- **A symlink to a file.** A `--rw`, `--ro` or `[mounts]` entry of this kind mounts the resolved target at the path as typed: its physical parent plus its own name. A `statusLine` or hook path therefore keeps working inside the session, and the fences judge the resolved target.
- **Data directories.** No session mounts any agent-dev tool's data directory, read-write or read-only. It holds that tool's host-run engine, its login and its state. The directory is fenced where it lives by default and where its `<COMMAND>_HOME` variable points. A path that contains one is refused the same way.
- **Protected host paths.** Each tool's host configuration (`~/.claude`, `~/.claude.json`, `~/.config/opencode`, `~/.local/share/opencode`) is refused as a writable mount by every command, and so is a path that contains one. Read-only they are shareable: that is the operator's explicit choice, and it exposes whatever the path holds.
- **Host-run code.** `~/.local/bin` and a checkout the engine runs from are refused as writable mounts.
- **The project.** The project mounts read-write, so a project that is, or contains, a data directory, a protected path or `~/.local/bin` is refused. So are `$HOME` and the filesystem root.
- **The command itself.** A command or engine that sits inside the project is refused: the session could rewrite it, and it runs on the host. `help` answers first, since the usage text must work everywhere.

Residuals remain. A command run from a source checkout runs that checkout's code on the host, so a checkout a confined session has written is session-authored code. `install.sh` installs, and in check mode runs, the checkout it lives in. A session can also write the project's `.git/config`, whose hooks and `core.fsmonitor` run under the host's own `git`.

`cleanup --all` spares every tool's image through one shared label, `agent-dev.image`. Docker spares an object only when it carries every label the `label!=` filters name, so a filter per tool would spare none. The build cache is shared and goes with the rest. `cleanup --all` refuses to prune when any agent-dev tool image present on the engine lacks the shared label. The refusal names the image and the `update` that rebuilds it.

## Installation

### Recommended: via the setup skill

Inside this repo, run the project skill:

```
/install-claude-dev
/install-opencode-dev
```

Each skill runs the installer's check mode for its own command, shows what would change, and applies on approval. An existing policy file is never overwritten: that file is the operator's policy. `install.sh <tool> reset-config` restores the shipped version, keeping the old one as `.bak`.

The installer carries no migration path. It installs the current tool, and it reports and removes the one retired module on its list, `claude_dev_config.py`. It runs and installs the checkout it lives in, so install from a checkout whose `tools/agent-dev` no confined session has written. A retired flag is not refused by name either. The launcher forwards anything it does not own to `claude`, so a stale flag surfaces as an unknown-option error from inside the container.

### Manual

```bash
tools/agent-dev/install.sh claude   # command -> ~/.local/bin, data -> ~/.config/claude-dev
claude-dev build              # one-time image build (pulls toolchains, a few minutes)
```

OpenCode installs the same way:

```bash
tools/agent-dev/install.sh opencode # command -> ~/.local/bin/opencode-dev, data -> ~/.config/opencode-dev
opencode-dev build            # one-time image build
opencode-dev                  # from a project directory: OpenCode confined; /connect once per project
opencode-dev --ow             # run on the open-weight peer in [open-weight], in a separate data shadow
```

Then, from any project directory:

```bash
claude-dev                    # Claude Code confined, auto permission mode
claude-dev --dangerously-skip-permissions   # same, every prompt skipped (passes through)
claude-dev --continue         # resume the last session in this project
claude-dev --resume <id>      # resume a specific session by id
claude-dev --allow example.com   # one extra egress domain, this run only
claude-dev --ow               # run on the open-weight peer in [open-weight]; no credential mounted
claude-dev access --ow        # the plan above plus the reverse port, its shape and the model map
claude-dev access             # print what the next session can access, launch nothing
claude-dev update             # rebuild only the Claude layer (seconds)
claude-dev cleanup            # remove dead session objects and superseded images
claude-dev cleanup --all      # same, then prune everything unused engine-wide
```

`access` prints what the next session can access, filesystem and network, then exits. It assembles the real mount plan (policy file, `--rw`/`--ro` flags, the `~/.claude` shared paths) and prints one aligned row per bind mount (`rw`/`ro`, container path, origin). Below the table it prints the egress plan: one `allow` row per effective domain, with per-run `--allow` entries marked as this run only. One `deny` row names the standing refusals (other domains, non-443 ports, host, LAN and metadata ranges). It runs the same validation a launch does, so it doubles as a policy syntax check; a defective `[mounts]` entry fails here with the launch's own message. Last comes the traffic record: per-host counts from the proxy's access log, `allow` rows for requests the policy admitted and `deny` rows for refusals, each group sorted by count. A tunnel shows as its host; a request the `--ow` reverse port forwarded shows as `host/path`, so a refused model-management call reads as such. Under `--ow` the reverse port's own plan prints between the egress plan and the record. A running session's proxy is read live; otherwise the record is the log saved on the last exit.

`cleanup` removes what the tool left behind on the engine, and nothing else. Its scope is the two labels the tool writes. Containers and networks whose recorded launcher is dead (`claude-dev.launcher`) get the same reap every launch performs. A liveness probe that cannot run counts the launcher as alive, so nothing is reaped. Dangling images from its own rebuilds (`claude-dev.image`) are pruned: every `build`/`update` retags `claude-dev:latest` and strands the predecessor. Each successful build already prunes its superseded labeled images, so the scoped verb matters after crashes and interrupted builds. An image built before the label exists carries none and stays; only `cleanup --all` or a manual `docker image prune` removes it. Other images, other containers and the engine's build cache stay untouched; `docker system df` shows what remains outside its lane.

`cleanup --all` crosses that line on request: after the scoped pass it runs an engine-wide `docker system prune -a --volumes`. That removes stopped containers, unused networks, unreferenced images, anonymous unused volumes (named ones too on engines older than Docker 23) and the whole build cache. One filter, `label!=agent-dev.image`, spares every agent-dev tool's image, so the next launch never pays a rebuild. [Fences Between Tools](#fences-between-tools) states why the filter is one shared label and when `--all` refuses to prune. Containers inherit that label, so the tools' own stopped containers are spared as well. The scoped reap has already removed this install's dead ones; another install's leftovers wait for that install's reap. The build cache is not spared, so the next `update` rebuilds every layer once; launches pay nothing. A live session's objects are in use and never pruned. The verb exists because the engine's disk (on macOS, a fixed-size VM image) fills from images no scoped cleanup may touch, and a full VM fails sessions with `ENOSPC`.

Claude's own flags pass straight through, so a session started on the host resumes inside: this project's transcripts are shared from the host `~/.claude`. Resume keys off the project path, so run it from the same project. A passed-through `--permission-mode` or `--dangerously-skip-permissions` replaces the auto default. Auto mode falls back to a prompt when the classifier blocks an action. A headless `-p` run has nobody to answer, and repeated blocks abort the session, so scripted runs want `--dangerously-skip-permissions`. The classifier itself calls `api.anthropic.com`, which the allow-list already carries as mandatory. `claude-dev help` prints the full flag and env reference.

### Run on an open-weight model: `--ow`

Both shipped policy files enable an `[open-weight]` table for the Ollama daemon on this machine, with the harness's two pins mapped to GLM tags. `--ow`, or `--open-weight`, opts in per launch:

```bash
ollama signin                 # once, for the cloud tags in the default map
claude-dev --ow               # or: opencode-dev --ow
claude-dev access --ow        # the plan: reverse port, admitted path, one row per served tag
```

The default tags are cloud tags. [The reverse port's limits](#the-reverse-port-an-open-weight-peer-the-proxy-can-read) state what that sends off the machine and how to keep a session local.

The model map lives in the installed policy file, `~/.config/<command>/<command>.toml`, under `[open-weight]` and `[open-weight.models]`. Changing a tag, pointing `peer` at a LAN machine or another model server, or deleting the table to turn the flag off are edits to that file. The file documents every key. [`docs/open-weight-models.md` § Confined Runs](../../docs/open-weight-models.md#confined-runs---ow) carries the examples, what a peer must serve, the prerequisites and the context-window floor.

## Platform Support

The target engine is [Rancher Desktop](https://rancherdesktop.io/), which runs the Docker daemon in a VM on every platform, so the session always sits behind a VM boundary:

The engine is resolved by one rule, with no flag or config key to steer it: pin the `rancher-desktop` context when it exists, else use the ambient engine. In the ambient case, docker's own `DOCKER_HOST`/`DOCKER_CONTEXT` still apply. Any other engine is a different security posture, so choosing one is a considered edit to the launcher rather than a per-run option.

| Platform | How that rule reaches Rancher |
|---|---|
| macOS | Pins the `rancher-desktop` context when present, else the ambient socket. Developed and used here |
| Linux | Same resolution — reaches Rancher whether it created the named context (admin access off) or owns the default socket. Not yet smoke-tested |
| Windows | Run from a WSL2 distro with Rancher's integration enabled; the ambient `/var/run/docker.sock` is used (Rancher creates no named context inside WSL). Not yet smoke-tested |

Windows Git Bash and native cmd/PowerShell are not supported: it is a bash script, and MSYS path mangling breaks the `-v` mounts.

Other engines work through the same ambient fallback but are not the target. Plain Docker Engine on native Linux confines by kernel namespace only (the container shares the host kernel) and defines no `host.docker.internal`. The launcher checks that the proxy resolves that name before wiring the bridge, so `--ide` there warns and the session runs without the oracle. There is no flag to point it elsewhere. `--ow` with `peer = "host"` dies by name on such an engine, and `[open-weight] peer` takes the host's bridge address instead. Rootless Docker and Podman are untested; the `--user $(id -u)` mapping behaves differently there.

## Related

- [`docs/adoption-guide.md` § Claude Dev](../../docs/adoption-guide.md#claude-dev) — when to reach for it.
- [`docs/native-sandbox.md`](../../docs/native-sandbox.md) — the container-free counterpart: Claude Code's own Seatbelt sandbox, configured strictly, for trusted repos on macOS; compares the two boundaries.
- [`tools/harness-stats/`](../harness-stats/) — the other user-level tool; same install pattern.
