#!/usr/bin/env python3
"""Tests for claude_dev_config — the config reader and the proxy policy emitter.

The squid policy is first-match-wins, so its ORDER is the security property.
These tests pin the order and the rules that must sit above one another; a
reordered http_access line fails here rather than silently changing what a
session can reach. The reader's tests pin the other half: a defect in the file
is refused by name, never read as an absent policy.
"""

import ipaddress
import pathlib
import tempfile
import unittest

import claude_dev_config as c

SUBNET = "172.30.0.0/16"


def conf(**kw):
    args = {"subnet": SUBNET, "mode": "allow-list", "allow": ("api.anthropic.com",)}
    args.update(kw)
    return c.emit_squid_conf(**args)


def rules(text):
    return [l for l in text.splitlines() if l.startswith("http_access")]


class PolicyOrder(unittest.TestCase):
    def test_first_rule_restricts_the_client_and_last_denies_all(self):
        r = rules(conf())
        self.assertEqual(r[0], "http_access deny !session")
        self.assertEqual(r[-1], "http_access deny all")

    def test_plaintext_is_denied_before_anything_is_allowed(self):
        r = rules(conf())
        first_allow = next(
            i for i, l in enumerate(r) if l.startswith("http_access allow")
        )
        self.assertLess(r.index("http_access deny !CONNECT"), first_allow)

    def test_private_deny_sits_above_the_allow_list(self):
        # An allow-listed name resolving into the host or LAN must not connect.
        r = rules(conf())
        self.assertLess(
            r.index("http_access deny to_private"),
            r.index("http_access allow session allowed"),
        )

    def test_ide_pinhole_sits_above_the_private_deny(self):
        # The IDE is reached at a private address by definition, so its rule
        # must precede the private deny or the bridge silently never works.
        r = rules(conf(ide_gateway="host.docker.internal", ide_port=64342))
        self.assertLess(
            r.index("http_access allow session ide_host ide_port"),
            r.index("http_access deny to_private"),
        )

    def test_port_restriction_sits_below_the_pinhole_and_above_the_allow_list(self):
        # 443-only must not close the IDE port, but must bind the allow-list.
        r = rules(conf(ide_gateway="host.docker.internal", ide_port=64342))
        restriction = r.index("http_access deny CONNECT !SSL_ports")
        self.assertLess(
            r.index("http_access allow session ide_host ide_port"), restriction
        )
        self.assertLess(restriction, r.index("http_access allow session allowed"))

    def test_open_mode_keeps_every_rule_above_the_allow_list(self):
        r = rules(conf(mode="open"))
        self.assertIn("http_access allow session", r)
        self.assertNotIn("http_access allow session allowed", r)
        for rule in (
            "http_access deny !session",
            "http_access deny !CONNECT",
            "http_access deny to_private",
            "http_access deny CONNECT !SSL_ports",
        ):
            self.assertLess(r.index(rule), r.index("http_access allow session"))


class PolicyContent(unittest.TestCase):
    def test_client_acl_is_the_given_subnet(self):
        self.assertIn(f"acl session src {SUBNET}", conf())

    def test_private_ranges_cover_host_lan_and_metadata(self):
        text = conf()
        for cidr in (
            "127.0.0.0/8",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "169.254.0.0/16",
            "100.64.0.0/10",
        ):
            self.assertIn(cidr, text)
        self.assertIn("::1/128", text)

    def test_the_v6_deny_never_carries_the_v4_mapped_range(self):
        # Squid holds every destination as an IPv6 address, and an IPv4 one in
        # the ::ffff: form — so ::ffff:0:0/96 in this list matches EVERY IPv4
        # destination and denies all egress (measured 2026-07-29: every CONNECT
        # TCP_DENIED/403, `/login` failing with "Socket is closed"). The literal
        # it was meant to catch is normalized to v4 before the ACL runs, so the
        # v4 list already covers it.
        mapped = ipaddress.ip_network("::ffff:0:0/96")
        for entry in c.PRIVATE_V6:
            net = ipaddress.ip_network(entry)
            self.assertFalse(
                net.subnet_of(mapped) or mapped.subnet_of(net),
                f"{entry} overlaps the v4-mapped range: it denies all IPv4 egress",
            )

    def test_no_obsolete_directives(self):
        # squid 6 rejects these by name into the egress log on every launch.
        for directive in ("dns_v4_first",):
            self.assertNotIn(directive, conf())

    def test_visible_hostname_is_set(self):
        # Without it squid can abort at startup on an unresolvable hostname.
        self.assertIn("visible_hostname claude-dev-proxy", conf())

    def test_caching_is_off(self):
        self.assertIn("cache deny all", conf())

    def test_pinger_is_off(self):
        # It needs raw ICMP sockets, which cap-drop=ALL denies; leaving it on
        # writes a FATAL into the egress log on every launch.
        self.assertIn("pinger_enable off", conf())

    def test_named_gateway_uses_dstdomain_and_an_address_uses_dst(self):
        self.assertIn(
            "acl ide_host dstdomain host.docker.internal",
            conf(ide_gateway="host.docker.internal", ide_port=1),
        )
        self.assertIn(
            "acl ide_host dst 172.17.0.1", conf(ide_gateway="172.17.0.1", ide_port=1)
        )

    def test_no_ide_means_no_pinhole(self):
        self.assertNotIn("ide_host", conf())


class PolicyRefusals(unittest.TestCase):
    def test_empty_allow_list_is_refused(self):
        with self.assertRaises(c.ConfigError):
            conf(allow=())

    def test_open_mode_needs_no_allow_list(self):
        self.assertIn("http_access allow session", conf(mode="open", allow=()))

    def test_bad_subnet_and_mode_and_port_are_refused(self):
        with self.assertRaises(ValueError):
            conf(subnet="not-a-subnet")
        with self.assertRaises(c.ConfigError):
            conf(mode="whatever")
        with self.assertRaises(c.ConfigError):
            conf(ide_gateway="h", ide_port=70000)

    def test_half_an_ide_bridge_is_refused(self):
        with self.assertRaises(c.ConfigError):
            conf(ide_gateway="host.docker.internal")


class InterpolatedValueValidation(unittest.TestCase):
    """label and ide_gateway go into squid.conf raw, ABOVE every deny.

    A newline in either forges a directive line that outranks the private-range
    deny, the port restriction and deny-all — one injected `http_access allow
    all` defeats the whole policy. The launcher passes constants, so these are
    the tests that keep that from being the only thing holding it.
    """

    def test_a_newline_in_the_label_cannot_forge_a_directive(self):
        with self.assertRaises(c.ConfigError):
            conf(label="x\nhttp_access allow all\n# ")

    def test_a_newline_in_the_ide_gateway_cannot_forge_a_directive(self):
        with self.assertRaises(c.ConfigError):
            conf(ide_gateway="h\nhttp_access allow all", ide_port=1234)

    def test_the_values_the_launcher_actually_passes_are_accepted(self):
        text = conf(
            label="claude-dev-123-4567",
            ide_gateway="host.docker.internal",
            ide_port=64342,
        )
        self.assertIn("acl ide_host dstdomain host.docker.internal", text)
        self.assertIn("# generated by claude-dev for claude-dev-123-4567", text)

    def test_spaces_and_empty_values_are_refused(self):
        for bad in ("", "a b", "a\tb", "a#b", 'a"b'):
            with self.subTest(bad=bad), self.assertRaises(c.ConfigError):
                c.validate_token(bad, "t")


class DomainValidation(unittest.TestCase):
    def test_hosts_and_subdomain_wildcards_pass(self):
        for entry in ("api.anthropic.com", ".github.com", "a-b.example.co.uk"):
            self.assertEqual(c.validate_domain(entry, "t"), entry)

    def test_urls_ports_cidrs_and_addresses_are_refused(self):
        for entry in (
            "https://x.com",
            "x.com:443",
            "10.0.0.0/8",
            "x.com/path",
            "1.2.3.4",
            "::1",
            "x com",
            "",
            ".",
            "..x.com",
            "-x.com",
            "x.com.",
            "x.com-",
        ):
            with self.subTest(entry=entry), self.assertRaises(c.ConfigError):
                c.validate_domain(entry, "somefile.toml")

    def test_the_refusal_quotes_the_entry_and_names_the_source(self):
        with self.assertRaises(c.ConfigError) as cm:
            c.validate_domain("https://x.com", "somefile.toml")
        self.assertIn("'https://x.com'", str(cm.exception))
        self.assertIn("somefile.toml", str(cm.exception))


class Loading(unittest.TestCase):
    def _write(self, text):
        d = tempfile.mkdtemp()
        p = pathlib.Path(d) / "claude-dev.toml"
        p.write_text(text, encoding="utf-8")
        return p

    def test_defaults_apply_to_an_empty_file(self):
        cfg = c.load(self._write(""), "/home/u")
        self.assertEqual(cfg.mode, "allow-list")
        self.assertEqual(cfg.allow, ())
        self.assertEqual(cfg.rw, ())
        self.assertEqual(cfg.ro, ())

    def test_full_file_round_trips(self):
        cfg = c.load(
            self._write(
                '[mounts]\nrw = ["$HOME/lib"]\nro = ["/opt/ref"]\n'
                '[egress]\nmode = "open"\nallow = ["api.anthropic.com"]\n'
            ),
            "/home/u",
        )
        self.assertEqual(cfg.rw, ("/home/u/lib",))
        self.assertEqual(cfg.ro, ("/opt/ref",))
        self.assertEqual(cfg.mode, "open")
        self.assertEqual(cfg.allow, ("api.anthropic.com",))

    def test_home_expands_only_as_a_leading_segment(self):
        self.assertEqual(c.expand_home("$HOME", "/home/u"), "/home/u")
        self.assertEqual(c.expand_home("$HOME/x", "/home/u"), "/home/u/x")
        self.assertEqual(c.expand_home("/a/$HOME/x", "/home/u"), "/a/$HOME/x")
        self.assertEqual(c.expand_home("$HOMEWORK", "/home/u"), "$HOMEWORK")

    def test_unparseable_file_is_refused_by_name(self):
        with self.assertRaises(c.ConfigError) as cm:
            c.load(self._write("[egress\nmode = broken"), "/home/u")
        self.assertIn("not valid TOML", str(cm.exception))

    def test_missing_file_is_refused_by_name(self):
        with self.assertRaises(c.ConfigError) as cm:
            c.load(pathlib.Path(tempfile.mkdtemp()) / "absent.toml", "/home/u")
        self.assertIn("absent.toml", str(cm.exception))

    def test_wrong_types_and_values_are_refused(self):
        for text in (
            '[egress]\nmode = "sometimes"\n',
            '[mounts]\nro = "not-a-list"\n',
            "[egress]\nallow = [1, 2]\n",
            'egress = "not-a-table"\n',
        ):
            with self.subTest(text=text), self.assertRaises(c.ConfigError):
                c.load(self._write(text), "/home/u")

    def test_a_retired_or_mistyped_key_is_refused_rather_than_ignored(self):
        # A key this version does not read must not sit in the file looking
        # like policy. [session] carried context/net/inhibit_bridge_ip before
        # they became flags and defaults; an upgraded install fails loudly.
        for text, named in (
            ('[session]\ncontext = "rancher-desktop"\n', "[session]"),
            ('[egress]\nmode = "open"\nmodes = ["open"]\n', "egress.modes"),
            ('[mounts]\nrx = ["/opt"]\n', "mounts.rx"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(c.ConfigError) as cm:
                    c.load(self._write(text), "/home/u")
                self.assertIn(named, str(cm.exception))

    def test_a_bad_allow_entry_names_the_file(self):
        p = self._write('[egress]\nallow = ["https://x.com"]\n')
        with self.assertRaises(c.ConfigError) as cm:
            c.load(p, "/home/u")
        self.assertIn(str(p), str(cm.exception))

    def test_telemetry_defaults_off_when_the_table_is_absent(self):
        # The declaration is the default, so a config written before the key
        # existed keeps the posture it had rather than silently gaining one.
        self.assertFalse(c.load(self._write("[egress]\n"), "/home/u").telemetry)

    def test_telemetry_reads_true(self):
        cfg = c.load(self._write("[telemetry]\nenabled = true\n"), "/home/u")
        self.assertTrue(cfg.telemetry)

    def test_a_quoted_boolean_is_refused_rather_than_read_as_truthy(self):
        # TOML has real booleans. enabled = "false" is a string, and a truthy
        # read of it would mean the exact opposite of what the file says.
        for text in ('[telemetry]\nenabled = "true"\n', "[telemetry]\nenabled = 1\n"):
            with self.subTest(text=text):
                with self.assertRaises(c.ConfigError) as cm:
                    c.load(self._write(text), "/home/u")
                self.assertIn("telemetry.enabled", str(cm.exception))

    def test_enabling_telemetry_allow_lists_nothing(self):
        # The key says what the session may do; the allow-list says what the
        # network permits. If this ever implied the intake hosts, the policy
        # would stop being readable off the allow-list.
        cfg = c.load(
            self._write('[telemetry]\nenabled = true\n[egress]\nallow = ["a.com"]\n'),
            "/home/u",
        )
        self.assertEqual(cfg.allow, ("a.com",))


class ShellSettings(unittest.TestCase):
    def test_scalars_once_and_lists_repeated(self):
        cfg = c.Config(rw=("/a", "/b"), ro=("/c",), allow=("x.com",))
        lines = c.shell_settings(cfg).splitlines()
        self.assertIn("EGRESS=allow-list", lines)
        self.assertIn(f"PROXY_PORT={c.PROXY_PORT}", lines)
        self.assertEqual([l for l in lines if l.startswith("RW=")], ["RW=/a", "RW=/b"])
        self.assertEqual([l for l in lines if l.startswith("RO=")], ["RO=/c"])
        self.assertIn("TELEMETRY=0", lines)

    def test_telemetry_reaches_the_launcher_as_one_or_zero(self):
        # The launcher's case arm accepts 0|1 and dies on anything else, so the
        # emitter may not grow a "true"/"yes" spelling without that arm moving.
        self.assertIn("TELEMETRY=1", c.shell_settings(c.Config(telemetry=True)))
        self.assertIn("TELEMETRY=0", c.shell_settings(c.Config(telemetry=False)))

    def test_every_emitted_key_is_one_the_launcher_reads(self):
        # The launcher dies on a key it does not know, so an emitter that grows
        # one must grow its read loop in the same commit. Read the launcher's
        # own case arms rather than restating them: a hardcoded set here would
        # pass while the two sides drifted, which is the bug it exists to catch.
        cfg = c.Config(rw=("/a",), ro=("/b",), allow=("x.com",))
        emitted = {l.split("=", 1)[0] for l in c.shell_settings(cfg).splitlines()}
        launcher = (
            pathlib.Path(__file__).resolve().parent.parent / "claude-dev"
        ).read_text()
        body = launcher.split("done <<EOF", 1)[0].rsplit("while IFS='='", 1)[1]
        read = {
            line.split(")", 1)[0].strip()
            for line in body.splitlines()
            if ")" in line and line.strip() and not line.strip().startswith("#")
        }
        self.assertTrue(
            emitted <= read, f"launcher does not read: {sorted(emitted - read)}"
        )
        self.assertIn("RW", emitted)
        self.assertIn("RO", emitted)

    def test_shell_metacharacters_stay_inert_text(self):
        # The launcher reads these lines; it never evals them. A value that
        # looks like shell must survive as a literal.
        cfg = c.Config(ro=("/srv/$(touch pwned);`id`;x",))
        self.assertIn(
            "RO=/srv/$(touch pwned);`id`;x", c.shell_settings(cfg).splitlines()
        )

    def test_a_newline_in_a_value_is_refused(self):
        with self.assertRaises(c.ConfigError):
            c.shell_settings(c.Config(ro=("/a\nRW=/etc",)))


if __name__ == "__main__":
    unittest.main()
