# The Pod Denies Host Egress by Default; the Preflight Opens One Port

**Status:** Superseded by [2026-07-29 proxy-enforced-egress](2026-07-29-proxy-enforced-egress.md)

> The goal holds and widens: the session still denies host egress by default, and `--ide` still opens exactly one preflighted port. The mechanism is retired. Enforcement moved out of the container's network namespace onto a per-session internal Docker network plus an external proxy, so the one-shot `NET_ADMIN` init container, the nftables ruleset, the `route_localnet` sysctls, and the kernel-NAT bridge are all gone — as is the install-before-workload ordering they required. This ADR's own closing item, "domain-level egress control needs a filtering proxy and is out of scope", is what the successor delivers.

## Context

The Security Model discloses: Docker and Rancher proxy `host.docker.internal` onto the host's loopback, so any container reaches every service bound `127.0.0.1`. The IDE MCP server has no authentication. The pod runs permission-skipped. [The exposed-set ADR](2026-07-16-exposed-tool-set-is-a-setting.md) put the only enforcement in the IDE's Exposed Tools setting and treated the launch preflight as a warning rather than a control.

A relay-versus-DNAT review (2026-07-17, after fixing the relay's stream-killing socket timeout) asked whether netfilter should replace the relay. The analysis found netfilter's value elsewhere: closing the gateway exposure the README documents as accepted.

## Options Considered

1. **Keep accept-and-warn** (status quo) — rejected: the permission-skipped pod is exactly the client a warning cannot govern.
2. **Grant the pod `CAP_NET_ADMIN` and filter from inside** — rejected: the agent could rewrite its own rules, and the pod loses its cap-drop-ALL posture.
3. **Filter at the VM** — rejected: not per-container, engine-specific, and it constrains every workload on the VM.
4. **Keep the in-pod relay beside the filter** — rejected after the spike. The relay is a hand-maintained proxy: 202 committed lines plus a 17-test suite, one real bug found 2026-07-17. Its remaining advantage was owned TCP keepalive on the forwarder leg. The maintainer chose less owned transport code over that liveness control; the trade is recorded under Consequences.
5. **Install from the pod's own entrypoint, then drop privileges** — root entrypoint applies the rules, clears the capability bounding set, execs the agent. One `docker run`, old TTY and signal semantics kept. Rejected: the policy would ship inside the image, not the versioned scripts — a stale installed image silently runs an old policy. The pod would start as root with `CAP_NET_ADMIN` in its bounding set, and the `setpriv` hand-off is owned security-critical code.
6. **Host-driven one-shot init container installs default-deny rules in the pod's netns; a DNAT pair replaces the relay** (chosen).

## Decision

**The pod's network namespace denies all IPv4 traffic to the gateway's /24 by default, plus every IPv6 address the gateway name resolves to.** The rules land before the agent starts and are immutable from inside. The launch sequence becomes create → configure → exec: the pod starts on an inert placeholder. A `--network container:` init container with `CAP_NET_ADMIN` installs the nftables rules and exits; only then does the agent start. The pod keeps `--cap-drop ALL`, so changing the rules requires a capability no pod process holds.

With `--ide` and the preflight's exactly-one-IDE verdict, one accept rule opens the discovered port. A DNAT+masquerade pair bridges the pod's own `127.0.0.1:<port>` to the gateway — kernel NAT replaces the in-pod relay process. `route_localnet` is set at pod creation. Zero or ambiguous matches, or no `--ide`, leave the host fully dark: fail-closed — an absent oracle, never a widened hole. Two requirements are load-bearing: a DNS carve-out (on Rancher the pod's resolver *is* the gateway address, so port 53 is excepted inside the deny target — v4 subnet and v6 addresses alike), and the install-before-workload ordering.

## Consequences

Positive:

- The preflight verdict upgrades from warning to kernel-enforced reachability for pod sessions.
- Other host loopback services (a second IDE, local dev servers) become unreachable from the pod instead of reachable-but-disclosed.
- The preflight's failure paths — zero matches, ambiguity, no `--ide` — degrade to a missing oracle, never to widened reach.

Negative:

- The closure covers only pod-launched containers; the disclosed wall stays open for any other container on the VM. Exposed Tools remains the only control binding every client.
- The launch path grows from one `docker run` to create/configure/exec with a cleanup trap — new bash surface, testable only in integration, per platform. The image gains `nftables`. The trap covers TERM and HUP; a SIGKILLed launcher skips it and the placeholder never exits, so each launch reaps pods whose recorded launcher PID is dead. The reap label scopes that PID to a per-install id: one engine can serve several PID namespaces (WSL distros, remote contexts), and a foreign PID must never be judged dead here.
- `docker exec` proxies no signals: a TERM to the launcher runs the cleanup trap, which force-removes the pod — SIGKILL to the agent. The old `exec docker run` forwarded the signal for a graceful stop; scripted (non-TTY) runs lose that.
- Every networked launch pays the restructure: create, init container, exec, remove — 0.4s measured on Rancher Desktop (2026-07-17, warm image). Engines where the gateway never resolves (native Linux) pay the init attempt on every launch just to fail open.
- Services the host binds on real interfaces stay reachable while general egress is open; domain-level egress control needs a filtering proxy and is out of scope.
- Mid-session TOCTOU is unchanged: the port stays open for the session, so Exposed Tools widened mid-session still flow.
- Retiring the relay surrenders the bridge's liveness control: kernel NAT owns no socket, so a gateway connection dropped without a FIN hangs an MCP call until the client reconnects. A same-day relay fix covered that with TCP keepalive (60s idle, three probes 10s apart) but was never committed — discarded with the relay to stop owning transport code.
- The relay also normalized `Host:` to `localhost`; the bridge forwards the client's literal `Host: 127.0.0.1`, which IDEA 2026.1.4 accepts. An IDE build enforcing exactly `localhost` degrades to a failed MCP connection — fail-closed, but undiagnosed until read here.
- The filter itself fails open: no nftables in the image or an unresolvable gateway prints a WARNING and the pod runs with the pre-filter exposure. Blocking the launch instead would break engines the pod explicitly tolerates. With a qualified bridge port, `route_localnet` stays set on that pod with no DNAT installed — a marginal, warned relaxation.
- The deny owns only the gateway name's addresses. The container bridge subnet, engines where the name never resolves (native Linux), and link-local IPv6 paths stay open; overriding `--ide-gateway` moves the deny target with the bridge.

## Implementation

`tools/claude-dev/`: `egress_rules.py` is the unit-tested ruleset emitter — the single source of the policy. `egress_init.sh` resolves the gateway, applies the ruleset, and asserts the deny landed. `claude-pod` restructures its launch to create → configure → exec; the `Dockerfile` gains `nftables`. `ide_relay.py` and its suite are deleted; the preflight's `--relay-ports` interface is renamed `--bridge-ports`. The README's Security Model carries the disclosure.

A pre-implementation spike on Rancher Desktop (2026-07-17) validated the mechanics: init-container rule installation, persistence after installer exit, and allow/deny/DNS/egress reachability. It also proved kernel-enforced immutability (`EPERM` even for cap-dropped root) and the loopback DNAT (HTTP 200 from the IDE, which accepts `Host: 127.0.0.1`). It produced two corrections. The DNS carve-out is port 53 across the deny subnet: the resolver is a VM address — the gateway itself on Rancher — whose identity varies by engine. `route_localnet` is set at pod creation via `--sysctl`; `/proc/sys` is read-only for the init container.

## References

- [The Exposed Tool Set Is a Setting, Not an Invariant](2026-07-16-exposed-tool-set-is-a-setting.md) — disclosed the open wall; its rejection of a filtering proxy ("a proxy filters nothing") loses that premise for pod sessions once this lands. Its enforcement point still binds every client.
- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — the boundary this obeys: rule installation is orchestration; the port decision stays in the tested preflight.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — closing a disclosed exposure outranks feature work.
- [`tools/claude-dev/README.md` § Security Model](../../tools/claude-dev/README.md) — the disclosure this converts into a control.
