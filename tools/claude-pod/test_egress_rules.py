#!/usr/bin/env python3
"""Unit tests for egress_rules — the ruleset is pinned byte-for-byte.

The emitter is the single source of the pod's egress policy (ADR 2026-07-17),
so these tests state the policy: default-deny to the VM subnet (IPv4, plus a
drop per gateway AAAA), port 53 excepted, one accept+DNAT pair per bridged IDE
port, and everything beyond the subnet untouched.
"""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

import egress_rules as e

FILTER_ONLY = """\
table inet pod {
  chain out {
    type filter hook output priority 0; policy accept;
    ip daddr 192.168.5.0/24 udp dport 53 accept
    ip daddr 192.168.5.0/24 tcp dport 53 accept
    ip daddr 192.168.5.0/24 drop
  }
}
"""


class TestBuildRuleset(unittest.TestCase):
    def test_no_ports_emits_filter_only(self):
        self.assertEqual(e.build_ruleset("192.168.5.2", []), FILTER_ONLY)

    def test_bridged_port_emits_accept_and_nat_pair(self):
        out = e.build_ruleset("192.168.5.2", [64342])
        self.assertIn("ip daddr 192.168.5.2 tcp dport 64342 accept\n", out)
        self.assertIn(
            "ip daddr 127.0.0.1 tcp dport 64342 dnat to 192.168.5.2:64342\n", out
        )
        self.assertIn("ip daddr 192.168.5.2 tcp dport 64342 masquerade\n", out)
        # The deny still closes everything else on the subnet.
        self.assertIn("ip daddr 192.168.5.0/24 drop\n", out)

    def test_accepts_precede_the_drop(self):
        out = e.build_ruleset("192.168.5.2", [64342])
        self.assertLess(out.index("dport 64342 accept"), out.index("drop"))
        self.assertLess(out.index("dport 53 accept"), out.index("drop"))

    def test_subnet_derives_from_gateway(self):
        self.assertIn(
            "ip daddr 192.168.65.0/24 drop\n", e.build_ruleset("192.168.65.254", [])
        )

    def test_multiple_ports(self):
        out = e.build_ruleset("192.168.5.2", [64342, 64343])
        for p in (64342, 64343):
            self.assertIn(f"dport {p} accept", out)
            self.assertIn(f"dport {p} dnat", out)
            self.assertIn(f"dport {p} masquerade", out)

    def test_no_rule_ever_reaches_beyond_the_subnet(self):
        # Everything beyond the subnet stays untouched: every daddr the
        # ruleset names is inside the gateway's /24, a declared gateway AAAA,
        # or the pod's own loopback.
        out = e.build_ruleset("192.168.5.2", [64342], ["fd07::1"])
        for line in out.splitlines():
            if "daddr" in line:
                self.assertRegex(line, r"daddr (192\.168\.5\.|127\.0\.0\.1|fd07::1)")

    def test_gateway_aaaa_becomes_a_v6_drop(self):
        # An engine that publishes an AAAA for the gateway would bypass the
        # IPv4 deny silently; every declared v6 address must be dropped.
        # (v4-mapped ::ffff: forms never reach the emitter — egress_init.sh
        # filters them out, since their traffic is IPv4 and already denied.)
        out = e.build_ruleset("192.168.5.2", [], ["fd07::1", "fe80::1"])
        self.assertIn("ip6 daddr fd07::1 drop\n", out)
        self.assertIn("ip6 daddr fe80::1 drop\n", out)

    def test_v6_carveout_matches_v4_dns_policy(self):
        # The v6 drops carry the same port-53 exception as the v4 subnet: an
        # engine whose in-pod resolver is the gateway's AAAA must not lose DNS
        # silently while the install reports success — that would be a mute
        # fail-closed on the one path the design promises fails open loudly.
        out = e.build_ruleset("192.168.5.2", [], ["fd07::1"])
        self.assertIn("ip6 daddr fd07::1 udp dport 53 accept\n", out)
        self.assertIn("ip6 daddr fd07::1 tcp dport 53 accept\n", out)
        self.assertLess(
            out.index("fd07::1 udp dport 53 accept"), out.index("fd07::1 drop")
        )

    def test_no_v6_addresses_means_no_v6_rules(self):
        self.assertNotIn("ip6", e.build_ruleset("192.168.5.2", []))

    def test_rejects_junk_v6(self):
        for bad in ("192.168.5.2", "fd07::/64", "nope"):
            with self.assertRaises(ValueError):
                e.build_ruleset("192.168.5.2", [], [bad])

    def test_rejects_junk_gateway(self):
        for bad in ("host.docker.internal", "192.168.5", "192.168.5.2; drop", ""):
            with self.assertRaises(ValueError):
                e.build_ruleset(bad, [])

    def test_rejects_out_of_range_port(self):
        for bad in (0, -1, 65536):
            with self.assertRaises(ValueError):
                e.build_ruleset("192.168.5.2", [bad])


class TestMain(unittest.TestCase):
    def test_prints_ruleset_and_exits_zero(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = e.main(["--gateway-ip", "192.168.5.2"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), FILTER_ONLY)

    def test_bad_gateway_is_a_clean_error(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = e.main(["--gateway-ip", "not-an-ip"])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")  # nothing half-emitted for nft to apply
        self.assertIn("egress_rules:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
