#!/usr/bin/env python3
"""Tests for claude_dev_config: the first-match-wins squid policy order and the fail-closed reader."""

import dataclasses
import ipaddress
import pathlib
import tempfile
import unittest

import claude_dev_config as c

LAUNCHER = pathlib.Path(__file__).resolve().parent.parent / "claude-dev"

SOME_SUBNET = "172.30.0.0/16"
SOME_DOMAIN = "api.anthropic.com"
SOME_HOME = "/home/u"
SOME_RW = "/a"
SOME_RO = "/b"
SOME_SOURCE = "somefile.toml"
ANY_WHAT = "t"

# The values the launcher passes for the IDE bridge and the session label.
IDE_GATEWAY_NAME = "host.docker.internal"
SOME_IDE_GATEWAY_ADDRESS = "172.17.0.1"
SOME_IDE_PORT = 64342
PORT_ABOVE_MAX = c.MAX_PORT + 1
LAUNCHER_LABEL = "claude-dev-123-4567"

CLIENT_RESTRICTION = "http_access deny !session"
PLAINTEXT_DENY = "http_access deny !CONNECT"
IDE_PINHOLE = "http_access allow session ide_host ide_port"
PRIVATE_DENY = "http_access deny to_private"
PORT_RESTRICTION = "http_access deny CONNECT !SSL_ports"
ALLOW_LIST_RULE = "http_access allow session allowed"
OPEN_MODE_RULE = "http_access allow session"
DENY_ALL = "http_access deny all"

# Every destination class the private deny covers: host, LAN, metadata, carrier NAT.
LOOPBACK_V4 = "127.0.0.0/8"
LOOPBACK_V6 = "::1/128"
RFC1918_RANGES = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
LINK_LOCAL_METADATA = "169.254.0.0/16"
CARRIER_NAT = "100.64.0.0/10"
# Squid holds every IPv4 destination in this mapped form, so a deny on it
# refuses all IPv4 egress.
V4_MAPPED_RANGE = ipaddress.ip_network("::ffff:0:0/96")
# Rejected by name into the egress log on every launch.
SQUID_6_REJECTED_DIRECTIVES = ("dns_v4_first",)

VALID_DOMAINS = ("api.anthropic.com", ".github.com", "a-b.example.co.uk")
REFUSED_DOMAIN_SHAPES = (
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
)
REFUSED_TOKEN_SHAPES = ("", "a b", "a\tb", "a#b", 'a"b')


def a_policy() -> c.ProxyPolicy:
    return c.ProxyPolicy(subnet=SOME_SUBNET, mode="allow-list", allow=(SOME_DOMAIN,))


def a_config() -> c.Config:
    return c.Config(rw=(SOME_RW,), ro=(SOME_RO,), allow=(SOME_DOMAIN,))


def squid_conf(**overrides):
    return c.emit_squid_conf(dataclasses.replace(a_policy(), **overrides))


def rules(text):
    return [line for line in text.splitlines() if line.startswith("http_access")]


def launcher_read_keys() -> set[str]:
    """Collect the setting names the launcher's read loop has a case arm for."""
    text = LAUNCHER.read_text()
    body = text.split("done <<EOF", 1)[0].rsplit("while IFS='='", 1)[1]
    return {
        line.split(")", 1)[0].strip()
        for line in body.splitlines()
        if ")" in line and line.strip() and not line.strip().startswith("#")
    }


class PolicyOrder(unittest.TestCase):
    def test_the_first_rule_restricts_the_client_and_the_last_denies_all(self):
        r = rules(squid_conf())
        self.assertEqual(r[0], CLIENT_RESTRICTION)
        self.assertEqual(r[-1], DENY_ALL)

    def test_plaintext_is_denied_before_anything_is_allowed(self):
        r = rules(squid_conf())
        first_allow = next(
            i for i, line in enumerate(r) if line.startswith("http_access allow")
        )
        self.assertLess(r.index(PLAINTEXT_DENY), first_allow)

    def test_the_private_deny_sits_above_the_allow_list(self):
        # An allow-listed name resolving into the host or LAN must not connect.
        r = rules(squid_conf())
        self.assertLess(r.index(PRIVATE_DENY), r.index(ALLOW_LIST_RULE))

    def test_the_ide_pinhole_sits_above_the_private_deny(self):
        # The IDE is reached at a private address, so a pinhole below the
        # private deny would never match.
        r = rules(squid_conf(ide_gateway=IDE_GATEWAY_NAME, ide_port=SOME_IDE_PORT))
        self.assertLess(r.index(IDE_PINHOLE), r.index(PRIVATE_DENY))

    def test_the_port_restriction_sits_below_the_pinhole_and_above_the_allow_list(
        self,
    ):
        r = rules(squid_conf(ide_gateway=IDE_GATEWAY_NAME, ide_port=SOME_IDE_PORT))
        restriction = r.index(PORT_RESTRICTION)
        self.assertLess(r.index(IDE_PINHOLE), restriction)
        self.assertLess(restriction, r.index(ALLOW_LIST_RULE))

    def test_open_mode_keeps_every_deny_above_its_allow_rule(self):
        r = rules(squid_conf(mode="open"))
        self.assertIn(OPEN_MODE_RULE, r)
        self.assertNotIn(ALLOW_LIST_RULE, r)
        for rule in (
            CLIENT_RESTRICTION,
            PLAINTEXT_DENY,
            PRIVATE_DENY,
            PORT_RESTRICTION,
        ):
            self.assertLess(r.index(rule), r.index(OPEN_MODE_RULE))


class PolicyContent(unittest.TestCase):
    def test_the_client_acl_is_the_given_subnet(self):
        self.assertIn(f"acl session src {SOME_SUBNET}", squid_conf())

    def test_the_private_ranges_cover_host_lan_and_metadata(self):
        text = squid_conf()
        for cidr in (
            LOOPBACK_V4,
            LOOPBACK_V6,
            *RFC1918_RANGES,
            LINK_LOCAL_METADATA,
            CARRIER_NAT,
        ):
            self.assertIn(cidr, text)

    def test_the_v6_deny_never_carries_the_v4_mapped_range(self):
        for entry in c.PRIVATE_V6:
            net = ipaddress.ip_network(entry)
            self.assertFalse(
                net.subnet_of(V4_MAPPED_RANGE) or V4_MAPPED_RANGE.subnet_of(net)
            )

    def test_directives_squid_6_rejects_are_absent(self):
        for directive in SQUID_6_REJECTED_DIRECTIVES:
            self.assertNotIn(directive, squid_conf())

    def test_a_visible_hostname_is_set(self):
        # Without one squid can abort at startup on an unresolvable hostname.
        self.assertIn("visible_hostname claude-dev-proxy", squid_conf())

    def test_caching_is_off(self):
        self.assertIn("cache deny all", squid_conf())

    def test_the_pinger_is_off(self):
        # It needs raw ICMP sockets, which cap-drop=ALL denies; left on, it
        # writes a FATAL into the egress log on every launch.
        self.assertIn("pinger_enable off", squid_conf())

    def test_a_named_gateway_uses_dstdomain_and_an_address_uses_dst(self):
        self.assertIn(
            f"acl ide_host dstdomain {IDE_GATEWAY_NAME}",
            squid_conf(ide_gateway=IDE_GATEWAY_NAME, ide_port=SOME_IDE_PORT),
        )
        self.assertIn(
            f"acl ide_host dst {SOME_IDE_GATEWAY_ADDRESS}",
            squid_conf(ide_gateway=SOME_IDE_GATEWAY_ADDRESS, ide_port=SOME_IDE_PORT),
        )

    def test_no_ide_means_no_pinhole(self):
        self.assertNotIn("ide_host", squid_conf())


class PolicyRefusals(unittest.TestCase):
    def test_an_empty_allow_list_is_refused(self):
        with self.assertRaises(c.ConfigError):
            squid_conf(allow=())

    def test_open_mode_needs_no_allow_list(self):
        self.assertIn(OPEN_MODE_RULE, squid_conf(mode="open", allow=()))

    def test_a_bad_subnet_mode_or_port_is_refused(self):
        with self.assertRaises(ValueError):
            squid_conf(subnet="not-a-subnet")
        with self.assertRaises(c.ConfigError):
            squid_conf(mode="whatever")
        with self.assertRaises(c.ConfigError):
            squid_conf(ide_gateway=IDE_GATEWAY_NAME, ide_port=PORT_ABOVE_MAX)

    def test_half_an_ide_bridge_is_refused(self):
        with self.assertRaises(c.ConfigError):
            squid_conf(ide_gateway=IDE_GATEWAY_NAME)


class InterpolatedValueValidation(unittest.TestCase):
    """The label and the gateway land in squid.conf raw, above every deny, so a newline in either would forge a directive."""

    def test_a_newline_in_the_label_cannot_forge_a_directive(self):
        with self.assertRaises(c.ConfigError):
            squid_conf(label="x\nhttp_access allow all\n# ")

    def test_a_newline_in_the_ide_gateway_cannot_forge_a_directive(self):
        with self.assertRaises(c.ConfigError):
            squid_conf(ide_gateway="h\nhttp_access allow all", ide_port=SOME_IDE_PORT)

    def test_the_values_the_launcher_passes_are_accepted(self):
        text = squid_conf(
            label=LAUNCHER_LABEL, ide_gateway=IDE_GATEWAY_NAME, ide_port=SOME_IDE_PORT
        )
        self.assertIn(f"acl ide_host dstdomain {IDE_GATEWAY_NAME}", text)
        self.assertIn(f"# generated by claude-dev for {LAUNCHER_LABEL}", text)

    def test_a_token_with_spaces_or_quotes_or_no_characters_is_refused(self):
        for bad in REFUSED_TOKEN_SHAPES:
            with self.subTest(bad=bad), self.assertRaises(c.ConfigError):
                c.validate_token(bad, ANY_WHAT)


class DomainValidation(unittest.TestCase):
    def test_hosts_and_subdomain_wildcards_pass(self):
        for entry in VALID_DOMAINS:
            self.assertEqual(c.validate_domain(entry, ANY_WHAT), entry)

    def test_urls_ports_cidrs_and_addresses_are_refused(self):
        for entry in REFUSED_DOMAIN_SHAPES:
            with self.subTest(entry=entry), self.assertRaises(c.ConfigError):
                c.validate_domain(entry, SOME_SOURCE)

    def test_the_refusal_quotes_the_entry_and_names_the_source(self):
        entry = REFUSED_DOMAIN_SHAPES[0]
        with self.assertRaises(c.ConfigError) as cm:
            c.validate_domain(entry, SOME_SOURCE)
        self.assertIn(f"'{entry}'", str(cm.exception))
        self.assertIn(SOME_SOURCE, str(cm.exception))


class Loading(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)

    def _write(self, text):
        path = self.dir / "claude-dev.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def _load(self, text):
        return c.load(self._write(text), SOME_HOME)

    def test_defaults_apply_to_an_empty_file(self):
        cfg = self._load("")
        self.assertEqual(cfg.mode, "allow-list")
        self.assertEqual(cfg.allow, ())
        self.assertEqual(cfg.rw, ())
        self.assertEqual(cfg.ro, ())

    def test_a_full_file_round_trips(self):
        cfg = self._load(
            f'[mounts]\nrw = ["$HOME{SOME_RW}"]\nro = ["{SOME_RO}"]\n'
            f'[egress]\nmode = "open"\nallow = ["{SOME_DOMAIN}"]\n'
        )
        self.assertEqual(cfg.rw, (SOME_HOME + SOME_RW,))
        self.assertEqual(cfg.ro, (SOME_RO,))
        self.assertEqual(cfg.mode, "open")
        self.assertEqual(cfg.allow, (SOME_DOMAIN,))

    def test_home_expands_only_as_a_leading_segment(self):
        self.assertEqual(c.expand_home("$HOME", SOME_HOME), SOME_HOME)
        self.assertEqual(c.expand_home("$HOME/x", SOME_HOME), SOME_HOME + "/x")
        self.assertEqual(c.expand_home("/a/$HOME/x", SOME_HOME), "/a/$HOME/x")
        self.assertEqual(c.expand_home("$HOMEWORK", SOME_HOME), "$HOMEWORK")

    def test_an_unparseable_file_is_refused_by_name(self):
        with self.assertRaises(c.ConfigError) as cm:
            self._load("[egress\nmode = broken")
        self.assertIn("not valid TOML", str(cm.exception))

    def test_a_missing_file_is_refused_by_name(self):
        missing = self.dir / "absent.toml"
        with self.assertRaises(c.ConfigError) as cm:
            c.load(missing, SOME_HOME)
        self.assertIn(missing.name, str(cm.exception))

    def test_wrong_types_and_values_are_refused(self):
        for text in (
            '[egress]\nmode = "sometimes"\n',
            '[mounts]\nro = "not-a-list"\n',
            "[egress]\nallow = [1, 2]\n",
            'egress = "not-a-table"\n',
        ):
            with self.subTest(text=text), self.assertRaises(c.ConfigError):
                self._load(text)

    def test_a_retired_or_mistyped_key_is_refused_rather_than_ignored(self):
        # A key this version does not read must not sit in the file looking
        # like policy.
        for text, named in (
            ('[session]\ncontext = "rancher-desktop"\n', "[session]"),
            ('[egress]\nmode = "open"\nmodes = ["open"]\n', "egress.modes"),
            ('[mounts]\nrx = ["/opt"]\n', "mounts.rx"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(c.ConfigError) as cm:
                    self._load(text)
                self.assertIn(named, str(cm.exception))

    def test_a_bad_allow_entry_names_the_file(self):
        path = self._write(f'[egress]\nallow = ["{REFUSED_DOMAIN_SHAPES[0]}"]\n')
        with self.assertRaises(c.ConfigError) as cm:
            c.load(path, SOME_HOME)
        self.assertIn(str(path), str(cm.exception))

    def test_telemetry_defaults_off_when_the_table_is_absent(self):
        # A config written before the key existed keeps the posture it had.
        self.assertFalse(self._load("[egress]\n").telemetry)

    def test_an_enabled_telemetry_table_reads_true(self):
        self.assertTrue(self._load("[telemetry]\nenabled = true\n").telemetry)

    def test_a_quoted_boolean_is_refused_rather_than_read_as_truthy(self):
        for text in ('[telemetry]\nenabled = "true"\n', "[telemetry]\nenabled = 1\n"):
            with self.subTest(text=text):
                with self.assertRaises(c.ConfigError) as cm:
                    self._load(text)
                self.assertIn("telemetry.enabled", str(cm.exception))

    def test_enabling_telemetry_allow_lists_nothing(self):
        # The allow-list alone says what the network permits; an implied
        # intake host would make the policy unreadable off the file.
        cfg = self._load(
            f'[telemetry]\nenabled = true\n[egress]\nallow = ["{SOME_DOMAIN}"]\n'
        )
        self.assertEqual(cfg.allow, (SOME_DOMAIN,))


class ShellSettings(unittest.TestCase):
    def test_scalars_emit_once_and_lists_emit_one_line_per_entry(self):
        another_rw = SOME_RW + "2"
        cfg = dataclasses.replace(a_config(), rw=(SOME_RW, another_rw))
        lines = c.shell_settings(cfg).splitlines()
        self.assertIn("EGRESS=allow-list", lines)
        self.assertIn(f"PROXY_PORT={c.PROXY_PORT}", lines)
        self.assertEqual(
            [line for line in lines if line.startswith("RW=")],
            [f"RW={SOME_RW}", f"RW={another_rw}"],
        )
        self.assertEqual(
            [line for line in lines if line.startswith("RO=")], [f"RO={SOME_RO}"]
        )
        self.assertIn("TELEMETRY=0", lines)

    def test_telemetry_reaches_the_launcher_as_one_or_zero(self):
        # The launcher's case arm accepts 0|1 and dies on anything else.
        on = dataclasses.replace(a_config(), telemetry=True)
        off = dataclasses.replace(a_config(), telemetry=False)
        self.assertIn("TELEMETRY=1", c.shell_settings(on))
        self.assertIn("TELEMETRY=0", c.shell_settings(off))

    def test_every_emitted_key_is_one_the_launcher_reads(self):
        # The launcher dies on a key it does not know; reading its case arms
        # rather than restating them keeps the two sides from drifting apart.
        emitted = {
            line.split("=", 1)[0] for line in c.shell_settings(a_config()).splitlines()
        }
        read = launcher_read_keys()
        self.assertTrue(
            emitted <= read, f"launcher does not read: {sorted(emitted - read)}"
        )
        self.assertIn("RW", emitted)
        self.assertIn("RO", emitted)

    def test_shell_metacharacters_stay_inert_text(self):
        # The launcher reads these lines and never evals them.
        path = "/srv/$(touch pwned);`id`;x"
        cfg = dataclasses.replace(a_config(), ro=(path,))
        self.assertIn(f"RO={path}", c.shell_settings(cfg).splitlines())

    def test_a_newline_in_a_value_is_refused(self):
        cfg = dataclasses.replace(a_config(), ro=("/a\nRW=/etc",))
        with self.assertRaises(c.ConfigError):
            c.shell_settings(cfg)


if __name__ == "__main__":
    unittest.main()
