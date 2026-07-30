# Egress Is Enforced by an External Proxy, Not by the Workload

**Status:** Accepted

## Context

[ADR 2026-07-17](2026-07-17-default-deny-pod-host-egress.md) closed the host-loopback exposure with nftables rules installed into the container's own network namespace, and closed its own Consequences with the open item: "domain-level egress control needs a filtering proxy and is out of scope."

Bringing that item in scope showed the in-namespace design does not extend cheaply. A domain allow-list on a packet filter must be resolved to addresses at launch, so it needs a resolver whose answers the filter has already allowed, a pin so the agent's later lookups agree with it, and a fail-closed rule for every state where resolution or installation fails. A spike carrying that through reached roughly 4,400 lines across a typed policy engine, a resolver sidecar, two manager verbs, and a launch-ordering contract with an 889-line test — against a reference whose stated bar is a tool a reader can audit in one sitting. Anthropic's own devcontainer answers the same problem in about 150 lines of shell, and their networking documentation explicitly permits organizations to substitute their own controls for it.

The premise worth re-examining was not the policy but its *location*: enforcement lived inside the workload's namespace, so every added control added privileged machinery there.

## Options Considered

1. **Keep the in-namespace packet filter, add the resolver machinery** — rejected: the spike's cost, and each new control lands as more privileged code in the agent's own namespace.
2. **Adopt the devcontainer's iptables script as-is** — rejected: it grants the agent's container `NET_ADMIN` + `NET_RAW` and sudo to the firewall script, resolves the allow-list to addresses once (so a CDN rotation silently breaks it), and leaves the policy inside the workload.
3. **Filter at the engine VM** — rejected as in 2026-07-17: not per-session, engine-specific, and it constrains every workload on the VM.
4. **A dual-homed forward proxy on a per-session internal network** (chosen). Envoy and NGINX Plus were weighed as the proxy: Envoy's dynamic forward proxy is materially more configuration for no gain here, and NGINX Plus is commercial. Squid is packaged in Debian, configured in ~25 generated lines, and is the shape enterprise reviewers already recognize.

## Decision

**The session container is attached to one per-run `--internal` Docker network and reaches the internet only through a squid proxy it cannot reconfigure.** An internal network carries no default route and no NAT, so the internet, the LAN, and the host are not routable from it — enforced by the engine, not by a rule inside the container. The proxy is dual-homed onto a *second* per-run network, so it is never on a shared bridge where another container could use it as an open relay.

Enforcement moves entirely outside the session: Docker networking decides where packets may go, and the proxy's generated config decides which destinations are allowed. **No container in the design holds `NET_ADMIN`, `NET_RAW`, or root in the session's namespace** — the privileged init container, the `route_localnet` sysctls, and the kernel NAT rules of 2026-07-17 are all retired. Three consequences follow that the packet filter could not reach: the allow-list is expressed as hostnames the proxy resolves per request (no launch-time pin, no rotation failure), a `dst` deny above the allow rules refuses any name resolving into loopback, RFC1918, carrier-NAT or link-local space (closing the DNS-rebind, LAN and cloud-metadata gaps 2026-07-17 disclosed as open), and the access log records attempts *with verdicts* outside the container rather than resolutions inside it.

The ordering requirement disappears with the privilege. Under the old design the agent had to not execute before the rules landed; here there is no route to race, so proxy readiness is a functional check whose failure means the session has no network — denied, never exposed. The `--ide` bridge becomes one proxy rule above the private-range deny plus an unprivileged `socat` inside the session that tunnels the IDE's own `127.0.0.1:<port>` entry through CONNECT; it holds no privilege and enforces nothing, so the session gains nothing by killing it. The residual VM-local endpoint that the old /24 drop happened to cover is closed by creating the internal network with `inhibit_ipv4`, which leaves its engine-side bridge interface with no address at all; an engine that rejects the option warns and names what stays reachable rather than falling through silently.

**Claude Code's in-process sandbox stays off, now on evidence rather than on the absence of a package.** The prior reasoning was that the image shipped no `bubblewrap`. That was the wrong premise: the image now ships it, and it still cannot run. Measured on Rancher Desktop, docker 29.5.2, `bwrap --unshare-all` fails under `cap-drop=ALL` + `no-new-privileges` + default seccomp, fails with default capabilities, fails at `pivot_root` even with `--cap-add=SYS_ADMIN`, and succeeds only with `--security-opt seccomp=unconfined`. The blocker is the syscall filter, not capabilities. Enabling the sandbox therefore costs seccomp for every process in the container to buy a per-command boundary the container already provides — egress is proxy-controlled either way, and the filesystem is the project plus the named crossings. So the launcher keeps injecting the sandbox-off `--settings`, which no longer needs a managed-settings escape hatch because managed policy does not cross at all (below). `bubblewrap` ships anyway, ungated: it costs ~50KB and keeps the other posture reachable without a rebuild.

**The policy becomes data, and the rules that carry it become tested.** `claude-dev.toml` replaces the sourced shell config and the plain-text allow-list: one file, parsed with `tomllib` and never executed, so nothing under `~/.config/claude-dev` can run code on the host and a file that will not parse is refused by name rather than read as an absent policy. A single module reads it and emits two things — the proxy's rules, and `KEY=VALUE` settings the launcher reads with a read loop and never evals. This is [ADR 2026-07-06](2026-07-06-logic-in-python-orchestration-in-bash.md) applied: the proxy's rule *order* is the security property (the IDE pinhole above the private-range deny, the port restriction below it and above the allow-list, deny-all last), so it belongs in tested Python, exactly as the retired `egress_rules.py` emitter did. The scope line is written into that module: **it emits documents and values, never a docker command.** Argv construction stays in bash, where arrays handle quoting correctly; moving it would rebuild the orchestrator this design deliberately does not have.

The tool is renamed `claude-dev`: it is a development container, and the "pod" name described the retired multi-container network namespace.

## Consequences

Positive:

- Enforcement is infrastructure-shaped and separated from the workload — the posture enterprise review expects, and the one Anthropic's networking documentation permits substituting.
- The allow-list is hostnames, edited by hand in one config file. There is no resolver sidecar, no answer pin, no rotation caveat, and no manager verb: `grep TCP_DENIED` on the saved log is the review tool.
- Config is data rather than executable shell, malformed entries are refused by name before anything is created, and the rule order is pinned by a suite instead of assembled inline in bash.
- Gaps 2026-07-17 disclosed as open are closed: an allow-listed name resolving to the LAN, another Docker subnet, a VM-internal service, or cloud metadata is refused at connect time.
- Roughly 4,400 lines of spiked policy engine, resolver, verbs and ordering tests are not written; the shipped surface is one launcher, a domain list, and a ~70-line scrubber with a 7-test suite.

Negative:

- Squid is a userspace process dual-homed between the session and the internet, so a compromise reachable through crafted CONNECT traffic is surface the kernel rules did not have. It runs non-root with every capability dropped in its own container; its worst case is its own absence — the same verdict the retired resolver sidecar carried.
- The proxy sees destinations, never payloads. It decides where traffic may go, not what is in it; TLS interception would change that and is deliberately not done.
- Squid resolves a name and then connects, so a name changing answers between those steps is a narrow race the `dst` check cannot close.
- `inhibit_ipv4` needs Moby 26+ (2024). Older engines get a named warning and keep the VM-local bridge address.
- Two networks and two containers per session replace one container plus a one-shot init — comparable launch cost, more objects for the reaper to own (it now reaps networks by label too).
- Host managed policy is not carried inside. Mounting it would drag in the `managed-settings.d/` fragment directory, a refusal path for managed files that hard-require the sandbox, and an override variable — MDM plumbing disproportionate to a personal launcher. The consequence is disclosed in the README: a `/login` inside is not bound by `forceLoginOrgUUID`, and managed permission rules do not apply, so work governed by managed settings belongs on the host.
- The container remains the only process boundary: there is no per-command confinement inside it, so a permission-skipped session can do anything to the project directory the container can reach. That was already true, and the measurement above says buying the inner boundary costs more than it returns here.
- python3 becomes a hard requirement: the config is TOML and the proxy's rules are generated, so there is nothing to degrade to. It was already a hard dependency of the harness ([ADR 2026-07-06](2026-07-06-logic-in-python-orchestration-in-bash.md)), and refusing to launch when the policy generator cannot run matches the rule that nothing degrades into open egress.
- Nothing migrates. The installer holds no path from the retired name or the retired shell config, and no legacy flag survives: nobody runs the tool under its current name, so compatibility machinery would be code written for one predecessor install. A `claude-pod` install is carried over by hand, once — `mv ~/.config/claude-pod ~/.config/claude-dev` keeps the saved login and the container-private `~/.claude` shadow, and `rm ~/.local/bin/claude-pod` drops the old command. Two commands typed once beat ~40 lines of one-shot machinery in a tool whose premise is that a reader can audit it in one sitting.
- The settable surface is only what has more than one sensible value: `[mounts]` and `[egress]`. The engine, the network and the bridge hardening are settable nowhere. A second way to reach one answer costs maintenance and gives a reviewer another thing to check. The reader refuses unknown tables and keys by name, so a retired key fails loudly rather than sitting in the file looking like policy. Two costs are real. A machine with a `rancher-desktop` context can no longer be pointed at another engine; that is intended, since another engine is another security posture. And there is no offline session any more: `--no-net` is gone and an empty allow-list refuses to launch, so the minimum reachable set is whatever `[egress] allow` names.

## References

- [The Pod Denies Host Egress by Default](2026-07-17-default-deny-pod-host-egress.md) — superseded: it named the filtering proxy as the missing piece, and this ADR is that piece.
- [The Exposed Tool Set Is a Setting, Not an Invariant](2026-07-16-exposed-tool-set-is-a-setting.md) — the IDE reachability premise it amends now rests on the internal network rather than on packet-filter rules.
- [The Pod Image's Supply Chain](2026-07-20-pod-image-supply-chain.md) — unchanged; the proxy binaries install from the same signed Debian repository.
- [`tools/claude-dev/README.md`](../../tools/claude-dev/README.md) — the operator-facing statement of the boundary this ADR decides.
