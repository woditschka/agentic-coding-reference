# The Pod Image Verifies Claude's Channel, Floats the Toolchains, Runs Non-Root

**Status:** Accepted

## Context

An external review of the pod's Dockerfile (2026-07-20) flagged its supply chain: `curl https://claude.ai/install.sh | bash` executed a mutable remote script as root at build time, the base image and toolchains were unpinned, and the image defaulted to root with a mode-777 home. The image's contents run permission-skipped with the project, the shared `~/.claude`, and an open internet path — a compromised build-time artifact could exfiltrate all three, so build integrity is load-bearing, not hygiene.

Anthropic now publishes signed apt/dnf/apk repositories with a documented signing-key fingerprint, which did not exist when the Dockerfile was written.

## Options Considered

1. **Keep `curl | bash`** — rejected: TLS-only trust, root execution of an unpinned script, and the installer's bootstrap fetches the latest binary even when a version is pinned.
2. **Pin everything** (base digest, Node/Go SHA256s, maintained by deps-upgrade) — implemented, then reverted the same day. The pins added recurring maintenance and new machinery (deps-report rows, battery format gates) for tamper-evidence against a rare attack. The maintainer chose zero recurring cost over pin-grade integrity for the toolchains.
3. **Signed apt for Claude, floating toolchains, non-root default** (chosen).

## Decision

**Claude Code installs from Anthropic's GPG-signed apt repository (`latest` channel), with the signing key's fingerprint pinned in the Dockerfile.** The layer downloads the key, asserts the keyring holds exactly one primary key whose fingerprint equals the pin, and only then lets apt trust it — a served key that mismatches fails the build. A battery tripwire (`pod-toolchain-pins`) fails any pipe-into-shell idiom returning; it guards that idiom, not every execution path.

**The base is `debian:13-slim`.** Debian's security team patches the packages this image draws from its archive without a paid tier; the equivalents live in Ubuntu's universe pocket, where guaranteed fixes need a Pro subscription. Debian and Corretto packages are apt-signature-verified; Node and Go tarballs ride TLS alone, resolved to latest at build time.

**The image defaults to a non-root user** (`dev`, uid 1000 — Debian ships no default account). The wrapper still passes an explicit `--user` on every run: the caller's uid for the pod, root for the one-shot egress init.

## Consequences

Positive:

- A CDN or origin compromise of Claude's channel after the pin fails the build loudly instead of executing attacker code as root.
- Version pinning works through apt (`x.y.z` maps to deb revision `x.y.z-1`); `claude-pod update` semantics are unchanged, and the deb's `/usr/bin/claude` needs no permission fixup for arbitrary-uid runs.
- A direct `docker run` of the image no longer lands on root, and the home directory drops from mode 777 to 755.
- Zero recurring maintenance: no pin to bump, no new deps-upgrade surface.

Negative:

- A signing-key rotation by Anthropic fails builds until the fingerprint pin is re-verified against the docs — a rare, loud maintenance event the old installer did not have.
- Pinned versions reach only the apt repo's rolling window (~80 releases at decision time); older versions the old installer could fetch are unreachable.
- Node, Go, and the Corretto signing key keep TLS-only trust — the weakest links, accepted for currency. Revisit if a pinning cadence ever becomes free (e.g. automated upstream checksum sync).
- The Claude layer's `apt-get update` now touches all configured repos, so a Debian or Corretto mirror outage can block the seconds-fast Claude-only rebuild.

## Amendment (2026-07-21): base packages upgrade at build time

The original decision chose Debian for its no-cost security archive but wired no mechanism to receive those fixes — no `apt-get upgrade`, and only `claude-pod update --all` re-pulls the base. The first apt layer now runs `apt-get upgrade -y`, so base-image packages carry Debian's security state as of the last uncached build. Rebuild cadence still rides `update --all`; nothing schedules it.
