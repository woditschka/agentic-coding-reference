# An Open-Weight Peer Is Reached Through a Reverse Port the Proxy Can Read

**Status:** Accepted

## Context

[ADR 2026-07-29](2026-07-29-proxy-enforced-egress.md) routes every path out of the claude-dev session through a squid forward proxy. The proxy tunnels CONNECT to port 443 and refuses the host, the LAN and the metadata ranges. The one exception is the `--ide` pinhole: one preflighted port toward the host machine, carried as a CONNECT tunnel through an unprivileged `socat` in the session.

[`docs/open-weight-models.md`](../open-weight-models.md) maps the harness's two pinned model names onto an Ollama daemon. The mapping lives in a project's `settings.local.json`: `ANTHROPIC_BASE_URL`, a token and `modelOverrides`. The daemon was unreachable from inside claude-dev, so open-weight runs executed on the host only.

Bringing the daemon inside the boundary raises a question the IDE pinhole never had. A model server's HTTP API has no authentication and carries model management beside inference: `/api/pull`, `/api/delete`, `/api/create`, and `/api/push`, which uploads to a registry. A CONNECT tunnel carries bytes the proxy never reads. A tunnel to the daemon would therefore carry all of those unobserved. The proxy's log, the review tool the 2026-07-29 design rests on, would show one tunnel line per connection and nothing about what crossed it.

Three Claude Code documentation pages, read 2026-10-06, settle the shape. A settings-file `env` block overrides the process environment, and `--settings` sits above every project file. `ANTHROPIC_AUTH_TOKEN` counts as a credential, so a session with it set asks for no login. `NO_PROXY` is honoured.

## Options Considered

1. **A CONNECT pinhole like `--ide`.** One more rule and one more `socat`. Rejected: the proxy would admit the daemon's whole API by port, model management included, and log none of it.
2. **TLS interception on the forward port**, to redirect or inspect the Anthropic traffic itself. Rejected: the proxy's design property is that it decides where traffic goes and never what is in it. The log is trustworthy because it never reads content. 2026-07-29 declined this on the same ground.
3. **A router sidecar**: a third container speaking the Messages API, holding the real credential, reading each request's model name and forwarding per tier. Deferred. It is the only shape that can filter on the request body, and the only one that keeps the Anthropic credential out of the session while still using it. It is also a second image to build and pin and a server to maintain, bought for a per-tier split the eval bench has not yet measured.
4. **A second listener on the same proxy, in reverse-proxy mode** (chosen). Squid's accelerator mode gives the port one fixed origin, the `[open-weight]` peer. The session sends ordinary HTTP requests, and the proxy parses method and path. One rule admits `POST /v1/messages`; the next refuses everything else on that port. The forward port's rules do not change.

## Decision

**`claude-dev --ow` opens a reverse port on the existing proxy with the `[open-weight]` peer as its only origin.** The port admits `POST /v1/messages` and nothing else, and logs each request by path. The flag takes no argument. The peer is policy and lives in `claude-dev.toml`, so no session can be pointed at a machine nobody wrote down. `peer = "host"` is this machine, reached as the engine's host gateway. An address is a LAN machine; `access --ow` says that prompts and code then leave the machine in plain HTTP.

The admitted shape is a constant, not a setting. The client chooses the path, no peer needs another, and a wider shape would be the management API the port exists to refuse. The constant admits the Messages endpoint and its `count_tokens` sibling. A query string is admitted when it holds only letters, digits and `_ = & -`, because squid's `urlpath_regex` sees the query and Claude Code posts to `/v1/messages?beta=true`. A percent-encoded path is refused outright: squid matches the decoded path while the raw bytes reach the peer.

The allow rule and the port-wide deny sit directly after the client restriction, above the plaintext and private-range denies. The request is plain HTTP, and the peer sits at a private address. The forward port is untouched: a plain request there still meets the plaintext deny, and a CONNECT to a private peer meets the private-range deny. The config refuses port 443 for the peer, so a public peer cannot be reached as a tunnel either. Squid resolves an ACL where a line names it, so the peer routing follows the ACL definitions rather than the listener. The suite pins both orders.

**The launcher hands the session no stored credential.** The credential directory is not mounted. Claude Code's credential store points at an unmounted path under the tmpfs home, so a `/login` typed inside persists nowhere. The per-launch `~/.claude.json` replica drops `primaryApiKey` and every `mcpServers` entry that can hold a token, top-level and per-project. A bare loopback endpoint, the entry an IDE writes for its own server, stays, so `--ide` works on a peer. The session's `~/.claude` shadow is separate from the one a credentialed session uses; the [one-engine ADR](2026-10-06-one-engine-for-agent-dev-tools.md) records that lifetime. A key written in the clear in a shared file stays readable.

**The settings document carries the peer and the map.** The launcher's single `--settings` document carries the base URL `http://proxy:3129`, a placeholder `ANTHROPIC_AUTH_TOKEN`, a fixed 30-minute `API_TIMEOUT_MS`, and the `[open-weight.models]` map as `modelOverrides`. It also sets `model` to a mapped name, since the root session's own model is whatever `/model` says and would reach the peer unmapped. The endpoint rides in the settings `env` block rather than the container environment. A settings-file `env` block overrides the process environment, and `--settings` outranks every project file, so a project's own `ANTHROPIC_BASE_URL` cannot point the session past the proxy.

**The model map lives in the launcher's policy for container runs.** `[open-weight.models]` maps each pinned name in the agents' frontmatter to the tag the peer serves. The launcher injects it. The same checkout runs on Anthropic from the host and on the peer inside claude-dev. The choice is made at launch, not in a project file someone forgets to delete. The per-project `settings.local.json` form in `docs/open-weight-models.md` stays for host sessions. An `[open-weight]` table without a map is refused at every launch, flag or not: every dispatch would name a pinned model the peer does not serve.

**A stale map fails at launch.** Before anything is created, `open_weight_preflight.py` asks the peer for its model listing from the host. A peer that does not answer ends the launch, and so does a local tag the peer does not list. An unlisted cloud tag only warns, because the daemon fetches one on first use. One deadline bounds the whole listing fetch, and a deeply nested or non-JSON listing is reported as an unusable answer. Peer-sent strings are reduced to printable ASCII before they reach the terminal.

**The shipped policy enables the peer, with cloud tags.** Each shipped policy file carries an `[open-weight]` table for the Ollama daemon on the host. The table maps the harness's two model pins to GLM cloud tags, which the daemon serves from the vendor's servers. `--ow` therefore works on the reference machine without a policy edit. The owner accepts the cost: a default `--ow` session sends prompts and code to the tag's vendor through the daemon, outside the proxy's log. The daemon must be signed in. The launch and `access --ow` name a mapped cloud tag as leaving through the peer. An operator who wants nothing to leave the machine maps local tags and signs the daemon out.

Without `--ow` nothing is generated: no listener, no peer, no settings beyond the sandbox declaration, no change to `NO_PROXY`. The launcher passes one generated `--settings` document, the sandbox-off declaration included. The battery pins the declaration, the launcher's call for it, and the pass-through.

## Consequences

Positive:

- The proxy keeps its one property: it decides where, never what. The reverse port extends that to method and path for one origin, without reading any TLS stream.
- Model management is refused at the proxy, with the refusal in the log by path. `access --ow` shows a refused `/api/pull` as such.
- The launcher hands an open-weight session no Anthropic credential: no credential directory, and a replica without `primaryApiKey` or any token-capable `mcpServers` entry. The exfiltration channel the README discloses for the allow-list, `.github.com`, carries no stored key from such a session.
- One container and one policy file. The addition is a table, a flag, a two-line listener, a ten-directive rule block, a settings document, and a preflight module with its own suite.
- A project needs no file for the container run. The map lives beside the peer it belongs to.
- `--ow` works on the reference machine as shipped. The default map needs a signed-in daemon and no policy edit.

Negative:

- The request body is opaque. The model name travels in the JSON, so the session can name any model the peer serves. `/v1/messages` does not pull a missing local model. A daemon signed in to a cloud registry serves cloud tags on demand, and that leg never shows in the log.
- The shipped default takes that leg. A default `--ow` session sends prompts and code to the tag's vendor, and the proxy's log shows the request path without the destination behind the daemon. The guard is operator-side: map local tags and sign the daemon out. Closing it in the design is option 3.
- The mechanism is verified on a live daemon by hand, not by a test. A maintainer run on 2026-10-06 served a session from the host's Ollama daemon through the reverse port. The suite pins the rule order, the request shape and the settings document, and a stub-engine test drives a launch to the session exec. How squid treats a percent-encoded path on the reverse port is unverified.
- The preflight checks the map, not a policy. The IDE pinhole is checked against a policy contract before it opens; the reverse port has no equivalent contract, only the listing comparison.
- A LAN peer crosses the LAN in plain HTTP. Acceptable on a home network, stated at launch, and not a reason to add TLS to the peer leg before anyone asks. An IPv6 peer is not accepted, since the squid directives would need bracket forms for it.
- Plain Docker Engine on Linux defines no `host.docker.internal`, so `peer = "host"` dies there by name and the operator names the bridge address instead. The IDE pinhole has the same edge.
- A user-passed `--settings` displaces the launcher's whole document, map included. The README says so.
- The egress figure shows the IDE pinhole as the only path to the host and omits the reverse port. Its alt text says so; the redraw is `update-diagrams` work.

## References

- [Egress Is Enforced by an External Proxy, Not by the Workload](2026-07-29-proxy-enforced-egress.md) — extended: the second listener is a rule block in the same generated policy, and the forward port's rules are unchanged.
- [`docs/open-weight-models.md`](../open-weight-models.md) — the mapping and the tiers; its § Limits links here.
- [`tools/agent-dev/README.md`](../../tools/agent-dev/README.md#the-reverse-port-an-open-weight-peer-the-proxy-can-read) — the operator-facing statement of the mechanism and its limits.
- Claude Code documentation, read 2026-10-06: [settings precedence](https://code.claude.com/docs/en/settings) (a settings-file `env` block overrides the process environment; `--settings` ranks above project files), [LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect) (`ANTHROPIC_AUTH_TOKEN` is a credential), [network configuration](https://code.claude.com/docs/en/network-config) (`NO_PROXY` is honoured).
