#!/usr/bin/env python3
"""egress_rules — emit the pod's default-deny nftables ruleset (ADR 2026-07-17).

A pure emitter: validated inputs in, ruleset text on stdout, nothing else. The
one-shot init container pipes the output into `nft -f -` inside the pod's
network namespace. The logic lives here so the tools unit suite can pin the
ruleset byte-for-byte; applying it stays in the orchestration wrapper
(egress_init.sh), per the logic-in-python ADR (2026-07-06).

The policy it emits:
  - drop all IPv4 traffic to the gateway's /24 (the Docker VM subnet — the
    path to every host loopback service);
  - drop every IPv6 address the gateway name resolves to (--gateway-ip6,
    repeatable) — engines that publish an AAAA would otherwise bypass the
    IPv4 deny silently; no v6 subnet is knowable, so the drop is per-address;
  - except port 53 — toward the v4 subnet and toward each dropped v6 address
    alike — because on Rancher the pod's DNS resolver IS the gateway address,
    and severing it would cut API access;
  - except each --port toward the gateway (the preflighted IDE MCP port), with
    a DNAT+masquerade pair so the pod's own 127.0.0.1:<port> config entry
    resolves through the kernel — route_localnet is set at pod creation.
Every other destination — the internet, other local networks — is deliberately
untouched: the Claude API must stay reachable, and only the gateway subnet is
the boundary this filter owns.

Usage:
    egress_rules.py --gateway-ip 192.168.5.2 [--port 64342 ...]
"""

from __future__ import annotations

import argparse
import ipaddress
import sys


def build_ruleset(
    gateway_ip: str, ports: list[int], gateway_ip6: list[str] | None = None
) -> str:
    """The full nft ruleset for one pod: filter always, NAT only with ports."""
    gw = ipaddress.IPv4Address(gateway_ip)  # raises ValueError on junk
    subnet = ipaddress.ip_network(f"{gw}/24", strict=False)
    gw6 = [ipaddress.IPv6Address(a) for a in (gateway_ip6 or [])]
    for p in ports:
        if not 0 < p < 65536:
            raise ValueError(f"port out of range: {p}")

    out = [
        "table inet pod {",
        "  chain out {",
        "    type filter hook output priority 0; policy accept;",
    ]
    out += [f"    ip daddr {gw} tcp dport {p} accept" for p in ports]
    out += [
        f"    ip daddr {subnet} udp dport 53 accept",
        f"    ip daddr {subnet} tcp dport 53 accept",
        f"    ip daddr {subnet} drop",
    ]
    out += [f"    ip6 daddr {a} udp dport 53 accept" for a in gw6]
    out += [f"    ip6 daddr {a} tcp dport 53 accept" for a in gw6]
    out += [f"    ip6 daddr {a} drop" for a in gw6]
    out += [
        "  }",
        "}",
    ]
    if ports:
        out += [
            "table ip podnat {",
            "  chain out {",
            "    type nat hook output priority -100;",
        ]
        out += [f"    ip daddr 127.0.0.1 tcp dport {p} dnat to {gw}:{p}" for p in ports]
        out += [
            "  }",
            "  chain post {",
            "    type nat hook postrouting priority 100;",
        ]
        out += [f"    ip daddr {gw} tcp dport {p} masquerade" for p in ports]
        out += [
            "  }",
            "}",
        ]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--gateway-ip", required=True, help="resolved gateway address (IPv4)"
    )
    ap.add_argument(
        "--gateway-ip6",
        action="append",
        default=[],
        help="IPv6 address of the gateway name to drop (repeatable)",
    )
    ap.add_argument(
        "--port",
        type=int,
        action="append",
        default=[],
        help="IDE port to bridge (repeatable)",
    )
    args = ap.parse_args(argv)
    try:
        sys.stdout.write(build_ruleset(args.gateway_ip, args.port, args.gateway_ip6))
    except ValueError as exc:
        print(f"egress_rules: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
