# Confined Agent Tools

**Status:** Accepted

## Context

A coding agent in the harness runs with reduced approvals over the project, a `~/.claude` shadow, and a network path. A hostile repository can poison the agent's context, so every boundary must be sized to hold with permissions fully skipped. Four forces shaped the container that holds those boundaries.

**The host is reachable from any container.** Docker proxies `host.docker.internal` onto the host's loopback. JetBrains' MCP server binds `127.0.0.1` with no authentication; its only gate is a spoofable `Host:` header. A bare `docker run alpine` reached the IDE.

**The IDE's exposed tool set drifts.** IntelliJ IDEA 2026.1.4 exposed seven tools where the policy named six. The extra, `apply_patch`, writes files, arrived enabled, and appears in no JetBrains document. Settings Sync propagates the set across IDEs and machines. Only `tools/list` against the running IDE is authoritative. `build_project` executed `build.gradle` on the host from inside the container and performed no source refresh.

**The image's supply chain was unverified.** A 2026-07-20 review found `curl https://claude.ai/install.sh | bash` run as root at build time, unpinned toolchains, a root default user, and a mode-777 home. Anthropic now publishes GPG-signed apt repositories with a documented key fingerprint.

**Controls inside the workload's namespace do not extend.** A packet filter needs a resolver whose answers it already allowed and a pin for later lookups. A spike adding a domain allow-list to the in-namespace filter reached roughly 4,400 lines. Anthropic's devcontainer solves the same problem in about 150 lines of shell and permits substitute controls.

Three later forces widened the scope. A third-party review recommended auto permission mode; the operator confirmed full unattended runs are not a requirement. OpenCode became the second tool to run this way, and about 90 of the launcher's 853 lines named Claude Code. An open-weight model server's HTTP API carries `/api/pull`, `/api/delete`, and `/api/push` beside inference, and a CONNECT tunnel would carry all of them unobserved.

Every `build` or `update` retags the image and strands a multi-GB predecessor, and a SIGKILLed launcher leaves its session container and networks behind. On macOS the engine's disk is a fixed-size VM image; a full VM fails sessions with `ENOSPC`. Docker's `prune` family never removes a running container, so an orphaned session's placeholder outlives every prune.

On the bare host, Claude Code's own sandbox denies `bind` by default; `tools/agent-dev`'s suite failed 34 of 148 tests without `allowLocalBinding`. The key emits three Seatbelt rules as one unit, including localhost outbound.

## Options Considered

1. **Fix `apply_patch` and restate the no-write invariant** — rejected: the next IDE upgrade adds the next tool with nobody watching.
2. **Keep accept-and-warn on host reachability** — rejected: a permission-skipped session is the client a warning cannot govern.
3. **Filter from inside the container with `CAP_NET_ADMIN`, or adopt the devcontainer's iptables script** — rejected: the agent could rewrite its own rules, and the policy stays in the workload. A once-resolved allow-list also breaks on CDN rotation.
4. **Filter at the engine VM** — rejected: not per-session, engine-specific, and it constrains every workload on the VM.
5. **Default-deny nftables from a one-shot `NET_ADMIN` init container, kernel DNAT for the IDE** — adopted 2026-07-17, retired 2026-07-29: every added control landed as privileged code in the agent's namespace.
6. **Pin the base digest and toolchain checksums** — implemented and reverted the same day: recurring maintenance for tamper-evidence against a rare attack.
7. **Keep `--dangerously-skip-permissions` as the default** — rejected: it serves a zero-prompt requirement the operator does not hold. A launcher-owned `--skip-perms` flag and a `permissions` key in the policy file were rejected as second spellings of a pass-through flag.
8. **Copy the launcher per tool, sourced bash profiles, or profiles as TOML data** — rejected: duplicated security-critical rule order, untested host-run shell, or data that cannot hold the settings emitter.
9. **A CONNECT pinhole to the open-weight peer, or TLS interception** — rejected: the first admits the management API unlogged; the second breaks the proxy's where-not-what property. A router sidecar holding the credential is deferred until the eval bench measures a per-tier split.
10. **Leave `allowLocalBinding` off, or grant it per run** — rejected: every listening test fails opaquely, and a control re-enabled by hand each session is no control.
11. **Point the operator at `docker system prune`, or name the verb `prune`** — rejected: prune cannot reap a running orphaned session. The docker name promises never to touch anything running, a promise this verb breaks.
12. **One engine, an external proxy on a per-session internal network, a verified image, auto mode, typed per-tool profiles, and a reverse port for open-weight peers** (chosen).

## Decision

**Agent tools run in a container whose only route out is an external proxy.** Three properties are each enforced or verified outside the session. They are what the session reaches, what the image contains, and the tool's permission posture.

**Network.** The session container sits on one per-run `--internal` Docker network, which carries no default route and no NAT. A squid proxy, dual-homed onto a second per-run network, is the only exit. The allow-list is hostnames the proxy resolves per request; a `dst` deny above the allow rules refuses any name resolving into loopback, RFC1918, carrier-NAT, or link-local space. No container holds `NET_ADMIN`, `NET_RAW`, or root in the session's namespace. The internal network is created with `inhibit_ipv4` (Moby 26+); an older engine warns and names what stays reachable. The access log records attempts with verdicts. Policy is data: `claude-dev.toml` and `opencode-dev.toml`, parsed with `tomllib`, never executed, unknown keys refused by name. The settable surface is `[mounts]`, `[egress]`, `[telemetry]`, and `[open-weight]`; the OpenCode profile refuses `[telemetry]`. An empty allow-list refuses to launch; `python3` is a hard requirement.

**IDE oracle.** The exposed tool set is configuration to verify. A tool qualifies only if it carries information plain text cannot reconstruct and neither writes files nor executes code. The set is five: `get_file_problems`, `search_symbol`, `get_symbol_info`, `get_project_modules`, `get_project_dependencies`. `get_file_problems` refreshes the index and runs first; the project build stays canonical. With `--ide`, `ide_preflight.py` enumerates the live set over MCP and fails on any tool outside policy, a strict subset test. An exactly-one-IDE verdict opens one proxy rule above the private-range deny plus an unprivileged `socat` tunnel inside the session. Without `--ide` no path to the host exists; the standing drift check is `ide_preflight.py --discover`. The IDE's Exposed Tools setting remains the only control binding every client.

**Image.** The base is `debian:13-slim`, upgraded with `apt-get upgrade` in the first layer. Claude Code installs from Anthropic's signed apt repository; the layer asserts the keyring holds exactly one primary key whose fingerprint equals the pin. Node and Go float at latest over TLS. The default user is `dev`, uid 1000, and every run passes an explicit `--user`. One Dockerfile builds a shared `base` stage and one stage per tool, each carrying a shared label that `cleanup --all` spares. The battery's `pod-toolchain-pins` tripwire fails any pipe-into-shell idiom.

**Permission posture.** `claude-dev` injects `--permission-mode auto`; a passed-through `--permission-mode` or `--dangerously-skip-permissions` suppresses the injection. The launcher owns no permission flag. Auto mode is a behavioral layer, never a boundary: the classifier reads the same context a hostile repository poisons. Claude Code's in-process sandbox stays off on measurement: `bwrap` fails under `cap-drop=ALL` plus default seccomp and succeeds only with seccomp unconfined. Host managed policy does not cross into the session; a `/login` inside is not bound by `forceLoginOrgUUID`.

**One engine.** The confinement is the `agent-dev` engine under `tools/agent-dev/`. A command script such as `claude-dev` or `opencode-dev` names its tool and execs the engine beside it. Each tool is a frozen typed dataclass in `agent_dev_profiles.py`: image stage, state roots with lifetimes, protected host paths, credential mechanism, proxy variables, admitted inference path, and settings renderer. `agent_dev_config.py` reads policy and emits squid rules and knows no tool. Names follow the command: data directory, image tag, container, network, and cleanup labels. `install.sh <tool>` installs one command with its own engine copy. Fences judge the resolved path: no session mounts any tool's data directory, `~/.claude.json` is refused as writable, and a project containing a protected path is refused. A root a tool loads code from is never shared across projects; `claude-dev`'s `~/.claude` shadow is per-project, keyed by a hash of the project path, with a separate `.ow` shadow. OpenCode's config and cache shadows are per-run, its data shadow per-project; its settings travel as `OPENCODE_CONFIG_CONTENT` with sharing and auto-update disabled; it receives `HTTPS_PROXY` only; `opencode.ai` stays off the allow-list.

**Open-weight peer.** `--ow` (`--open-weight`) opens a reverse port on the same proxy with the `[open-weight]` peer as its only origin. The port admits `POST /v1/messages` and its `count_tokens` sibling for `claude-dev`, `POST /v1/chat/completions` for `opencode-dev`, and nothing else; a percent-encoded path is refused. The session receives no stored credential: the credential directory is unmounted and the `~/.claude.json` replica drops `primaryApiKey` and every token-capable `mcpServers` entry. The settings document carries `http://proxy:3129`, a placeholder `ANTHROPIC_AUTH_TOKEN`, a 30-minute `API_TIMEOUT_MS`, and `[open-weight.models]` as `modelOverrides`; a test holds the map's keys equal to the agent frontmatter pins. `open_weight_preflight.py` compares the map to the peer's listing before anything is created. The shipped policies map the pins to GLM cloud tags, so a default `--ow` session sends prompts to the tag's vendor through the daemon; `access --ow` names that leg.

**Cleanup.** `<command> cleanup` removes exactly what the tool's labels attribute to it. Session containers and networks carry a launcher label with the install id and PID. The reaper every launch runs force-removes objects whose launcher is dead, judged only within the issuing install. Images carry a per-tool label plus the shared `agent-dev.image` label; the verb prunes dangling images under it, and each build prunes its own superseded predecessors. `cleanup --all` crosses that lane on the operator's word: after the scoped pass it runs `docker system prune -a --volumes` with one `label!=agent-dev.image` filter. It refuses while any agent-dev tool image lacks the shared label and names the `update` that rebuilds it. Stub-docker tests pin the reap, the no-prune-outside-the-label rule, the exact `--all` argv, and the refusal.

**Declined, with re-measure triggers.** Importing Claude settings allowlists into the proxy was declined on 2026-07-31. The launcher reads no project file, and the import would break the single-file audit property of `claude-dev.toml` plus `claude-dev access`. `sandbox.enableWeakerNestedSandbox` was measured on 2026-07-31 and declined, since the measurement did not dissolve the seccomp trade; a Claude Code release that changes the key's emission re-opens it. A build splitting bind from localhost outbound narrows the local-binding grant to bind alone. Node, Go, and the Corretto signing key keep TLS-only trust, revisited if a pinning cadence becomes free.

**Bare-host sandbox.** `docs/native-sandbox.md` publishes `allowLocalBinding: true` at user scope and names its residual: localhost egress bypasses the proxy and the allowlist, which covers remote hosts only. That posture stays scoped to trusted repositories; untrusted repositories belong in `claude-dev`, whose loopback has no unsandboxed peer.

## Consequences

Positive:

- Enforcement is infrastructure-shaped: Docker decides routes, the proxy decides destinations, and `grep TCP_DENIED` on the saved log is the review tool.
- The 4,400-line resolver spike is not written; the shipped surface is one engine, two commands, two policy files, and a ~70-line scrubber.
- A CDN or origin compromise of Claude's channel fails the build instead of running attacker code as root. Zero recurring pin maintenance.
- The exposed-set invariant is machine-checked and catches the next `apply_patch` without a changelog read.
- A further tool is a profile, a seven-line command, a policy file, an installer arm, an install skill, and an image stage. The rule-order suite runs once for every tool.
- Model management on the open-weight peer is refused at the proxy and logged by path.
- A running orphaned session, invisible to every docker prune, is removed by the one party holding the liveness picture; full-disk recovery needs no rebuild.

Negative:

- Squid is userspace surface the kernel rules lacked; it runs non-root with every capability dropped, and its worst case is its own absence.
- The proxy sees destinations, never payloads; a name changing answers between resolve and connect is a narrow race.
- No offline session exists: the minimum reachable set is whatever `[egress] allow` names.
- A signing-key rotation fails builds until the fingerprint is re-verified; pinned Claude versions reach only the apt window of about 80 releases.
- Headless `-p` runs abort after repeated classifier blocks; scripted runs pass `--dangerously-skip-permissions`. Each flagged action costs a classifier call.
- Engine files install once per tool, so a fix reaches a tool only on its next install; `install.sh check` reports drift.
- Real Docker behavior rests on maintainer runs (2026-07-29, 2026-10-06), not tests; the suites drive a stub engine.
- The default `--ow` leg to the cloud vendor never shows in the proxy log; the operator-side guard is local tags and a signed-out daemon.
- `--all` does not spare the build cache, so the next `update` rebuilds every layer once; `--volumes` removes named volumes too on engines older than Docker 23.
- On the bare host the bind grant covers routable interfaces, and localhost egress leaves no log the session cannot reach.

## References

- [The Python Core](2026-07-06-the-python-core.md) — the boundary this obeys: the rule emitter, the profiles, and both preflights are tested Python; the command scripts stay bash orchestration.
- [Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — closing a disclosed exposure outranked feature work at each step.
- [Model Tiering](2026-06-11-model-tiering.md) — the agent model pins the `[open-weight.models]` keys mirror by test.
- [`tools/agent-dev/README.md`](../../tools/agent-dev/README.md) — the operator-facing security model, postures, and the OpenCode differences.
- [`docs/native-sandbox.md`](../native-sandbox.md) — the bare-host configuration that carries the bind grant and its residual.
- [`docs/open-weight-models.md`](../open-weight-models.md) — the model mapping the reverse port serves and the host-session form.
- [`docs/harness-project-api.md` § Optional Capabilities](../harness-project-api.md) — the IDE oracle is probed, never roster-required, so every preflight failure path is non-fatal.
