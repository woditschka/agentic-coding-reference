# Local Binding Is Granted, and Its Localhost Egress Accepted

**Status:** Accepted

## Context

[`docs/native-sandbox.md`](../native-sandbox.md) publishes a strict user-scope configuration for Claude Code's OS-level sandbox. Its central property is that `strictAllowlist` plus the out-of-sandbox proxy govern egress from sandboxed commands: an unlisted host is refused, never prompted.

Serving a local port is ordinary work. The default Seatbelt profile denies `bind` with `EPERM`, so every dev server and every test that listens fails. Measured on this repository, `tools/claude-dev`'s suite fails 34 of 148 tests without the grant, each at `bind(("127.0.0.1", 0))`.

`sandbox.network.allowLocalBinding` lifts that denial. The key is absent from the Claude Code sandboxing and settings pages. It is described in the [`@anthropic-ai/sandbox-runtime`](https://github.com/anthropic-experimental/sandbox-runtime) package the sandbox derives from. Within Claude Code's own schema it carries no description string, which is why no generated page names it.

Reading the Seatbelt profile generator shows the grant is not what the name suggests. The emission is identical in builds 2.1.218 through 2.1.220. The key emits three rules as a unit:

```
(allow network-bind (local ip "*:*"))
(allow network-inbound (local ip "*:*"))
(allow network-outbound (remote ip "localhost:*"))
```

Two facts follow. The bind is not loopback-scoped — `*:*` is any local address, with inbound accepted from any source. And with the key off, the only permitted localhost outbound is the proxy's own ports, which is precisely the mechanism that keeps remote traffic on the allowlist's path. Turning the key on removes that funnel for local destinations.

## Options Considered

1. **Leave the key off** — rejected: it bricks a normal workload. Any dev server, integration test, or local tool that listens fails at `bind`, and the failure is opaque at the call site.
2. **Grant it at user scope and accept the residual** (chosen).
3. **Grant it per run via `--settings`, or at project scope** — rejected. The key carries no settings-source restriction, unlike `strictAllowlist`, so both would work. But serving a port is not a per-project exception, and the friction would land on every session that runs a test suite. A control that is routinely re-enabled by hand is a control in name only.
4. **Grant bind without the localhost-egress rule** — unavailable. The three rules are emitted from a single branch on the key; the profile generator offers no narrower form.

## Decision

**`allowLocalBinding: true` is part of the published configuration, and its localhost-egress residual is accepted and named.** The enforcement table in [`docs/native-sandbox.md`](../native-sandbox.md) carries a row for the grant, and the network-allowlist row is qualified to remote destinations.

**The allowlist covers the remote hosts a sandboxed command addresses directly, and nothing else.** A host listener that forwards — an `ssh -L` tunnel, a local proxy, an MCP server — is an egress path the proxy never sees. That residual is one more reason the posture stays scoped to trusted repositories.

**Claude-dev is unaffected, structurally.** Its loopback sits entirely inside the container boundary, with no unsandboxed peer to reach, so the residual has nowhere to land. Its launcher also injects the sandbox off ([ADR 2026-07-29](2026-07-29-proxy-enforced-egress.md)), leaving no profile to carry the key. A user-passed `--settings` can displace that injection, so the container boundary is the load-bearing fact.

## Consequences

Positive:

- Ordinary work runs: dev servers, listening tests, and local tooling bind as they do outside the sandbox.
- The residual is written down where the configuration is read, rather than discovered when someone trusts the allowlist too far.
- The two postures separate cleanly. Untrusted repositories belong in claude-dev, which does not carry this residual.

Negative:

- Localhost egress bypasses the proxy and the allowlist, and leaves no entry in any log the session cannot reach.
- The bind grant covers routable interfaces, so a sandboxed command can serve to other machines on the network.
- A sandboxed command can claim a port an unsandboxed local client expects, and answer in that service's place.
- The published configuration is no longer defensible for untrusted code on the bare host. It was already scoped to trusted repositories; this narrows the margin that scoping carried.

Re-measure trigger:

- A Claude Code release that changes the key's emission. A build splitting bind from localhost outbound removes the trade entirely, and the grant narrows to bind alone.

## References

- [`docs/native-sandbox.md`](../native-sandbox.md) — the configuration this decision is part of, and the enforcement table that carries the grant.
- [Egress Is Enforced by an External Proxy, Not by the Workload](2026-07-29-proxy-enforced-egress.md) — the sandbox-off decision that makes claude-dev structurally immune.
- [The Default Permission Posture Is Auto Mode, Not Skip](2026-07-31-auto-permission-mode-default.md) — the same-day posture decision this one sits beside.
