#!/usr/bin/env python3
"""Tests for agent_dev_config: the first-match-wins squid policy order and the fail-closed reader."""

import dataclasses
import ipaddress
import json
import pathlib
import re
import tempfile
import unittest

import agent_dev_config as c

LAUNCHER = pathlib.Path(__file__).resolve().parent.parent / "agent-dev"

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
SOME_TOOL = "claude-dev"
SOME_PATH_REGEX = r"^/v1/messages(/count_tokens)?(\?.*)?$"

CLIENT_RESTRICTION = "http_access deny !session"
PLAINTEXT_DENY = "http_access deny !CONNECT"
IDE_PINHOLE = "http_access allow session ide_host ide_port"
OW_ESCAPE_DENY = "http_access deny ow_port ow_escaped"
OW_ALLOW = "http_access allow session ow_port POST ow_paths"
OW_PORT_DENY = "http_access deny ow_port"
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

# The [open-weight] table: a peer on the host or on the LAN, and the model map.
SOME_LAN_PEER = "192.168.1.123"
SOME_OW_PORT = 11434
MESSAGES_PATH = "/v1/messages"
# What Claude Code sends, what the Messages API also carries, and what a
# session might try instead.
ADMITTED_PATHS = (
    "/v1/messages",
    "/v1/messages?beta=true",
    "/v1/messages/count_tokens",
    "/v1/messages/count_tokens?beta=true",
)
REFUSED_PATHS = (
    "/v1/messagesX",
    "/v1/messages/x",
    "/v1/messages/../api/pull",
    "/api/pull",
    "/api/tags",
    "/v1/chat/completions",
    "v1/messages",
)
SOME_OPUS_PIN = "claude-opus-5-5"
SOME_SONNET_PIN = "claude-sonnet-5-5"
SOME_OPUS_TAG = "glm-5.3:cloud"
SOME_SONNET_TAG = "hf.co/org/model:q8"
REFUSED_PEER_SHAPES = (
    "http://x",
    "x:11434",
    "h\nhttp_access allow all",
    "a b",
    "",
    "-x",
    "--help",
    "::1",
)
REFUSED_MODEL_TOKENS = ("a b", "", "-x", "--tag", "a\x1bb", "a\nb", "\u00e9")
OW_MODELS_TOML = (
    f'[open-weight.models]\n"{SOME_OPUS_PIN}" = "{SOME_OPUS_TAG}"\n'
    f'"{SOME_SONNET_PIN}" = "{SOME_SONNET_TAG}"\n'
)


def a_policy() -> c.ProxyPolicy:
    return c.ProxyPolicy(
        subnet=SOME_SUBNET,
        mode="allow-list",
        allow=(SOME_DOMAIN,),
        tool=SOME_TOOL,
        label=SOME_TOOL,
        mandatory_host=SOME_DOMAIN,
    )


def an_ow_policy(**overrides) -> c.OpenWeightPolicy:
    base = c.OpenWeightPolicy(
        gateway=IDE_GATEWAY_NAME, port=SOME_OW_PORT, path_regex=SOME_PATH_REGEX
    )
    return dataclasses.replace(base, **overrides)


def an_ow_config(**overrides) -> c.OpenWeightConfig:
    base = c.OpenWeightConfig(
        models=((SOME_OPUS_PIN, SOME_OPUS_TAG), (SOME_SONNET_PIN, SOME_SONNET_TAG))
    )
    return dataclasses.replace(base, **overrides)


def a_config() -> c.Config:
    return c.Config(rw=(SOME_RW,), ro=(SOME_RO,), allow=(SOME_DOMAIN,))


def squid_conf(**overrides):
    return c.emit_squid_conf(dataclasses.replace(a_policy(), **overrides))


def rules(text):
    return [line for line in text.splitlines() if line.startswith("http_access")]


def launcher_read_keys() -> set[str]:
    """Collect the setting names the launcher's read loop has a case arm for."""
    # The launcher reads two documents with this loop shape; the settings one
    # follows the config module's `settings` verb.
    text = LAUNCHER.read_text().split('config_py settings "$CONFIG"', 1)[1]
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


class OpenWeightReversePort(unittest.TestCase):
    """The --ow listener: one fixed origin, one request shape, nothing else on that port."""

    def test_the_reverse_port_block_sits_right_after_the_client_restriction(self):
        # It must precede the plaintext and private denies: the request is
        # plain HTTP and the peer sits at a private address.
        r = rules(squid_conf(open_weight=an_ow_policy()))
        self.assertEqual(r[0], CLIENT_RESTRICTION)
        self.assertEqual(r[2], OW_ALLOW)
        self.assertLess(r.index(OW_ALLOW), r.index(PLAINTEXT_DENY))
        self.assertLess(r.index(OW_ALLOW), r.index(PRIVATE_DENY))

    def test_everything_else_on_the_reverse_port_is_refused_before_any_other_rule(
        self,
    ):
        # A model pull, delete or push, a listing, any other method: refused
        # on the port itself, so no later allow can reach them.
        r = rules(squid_conf(open_weight=an_ow_policy()))
        self.assertEqual(r[3], OW_PORT_DENY)

    def test_the_forward_port_rules_are_unchanged(self):
        # The reverse port's rules are scoped to its own listener and inserted
        # as one block; every rule the forward port had stays, in its order.
        with_ow = rules(squid_conf(open_weight=an_ow_policy()))
        block = [OW_ESCAPE_DENY, OW_ALLOW, OW_PORT_DENY]
        self.assertEqual(with_ow[1:4], block)
        self.assertEqual(with_ow[:1] + with_ow[4:], rules(squid_conf()))

    def test_an_escaped_path_is_refused_before_the_allow(self):
        # squid matches the decoded path, so %00 would end the match early
        # while the raw bytes reach the peer.
        r = rules(squid_conf(open_weight=an_ow_policy()))
        self.assertLess(r.index(OW_ESCAPE_DENY), r.index(OW_ALLOW))
        self.assertIn(
            "acl ow_escaped urlpath_regex %", squid_conf(open_weight=an_ow_policy())
        )

    def test_the_listener_is_an_accelerator_with_the_peer_as_its_only_origin(self):
        text = squid_conf(open_weight=an_ow_policy())
        self.assertIn(
            f"http_port {c.OW_PROXY_PORT} accel defaultsite={IDE_GATEWAY_NAME} "
            "no-vhost name=ow",
            text,
        )
        self.assertIn(
            f"cache_peer {IDE_GATEWAY_NAME} parent {SOME_OW_PORT} 0 no-query "
            "originserver no-digest name=ow",
            text,
        )
        self.assertIn("never_direct allow ow_port", text)
        self.assertIn("cache_peer_access ow deny all", text)

    def test_the_acls_are_defined_before_the_lines_that_name_them(self):
        # squid resolves an ACL where it is named; a use above its definition
        # aborts the proxy at startup.
        lines = squid_conf(open_weight=an_ow_policy()).splitlines()
        definition = lines.index("acl ow_port myportname ow")
        for user in (
            "never_direct allow ow_port",
            "cache_peer_access ow allow ow_port",
        ):
            self.assertLess(definition, lines.index(user))

    def test_the_path_regex_admits_what_claude_code_sends_and_nothing_wider(self):
        # squid's urlpath_regex sees the query string, and the client posts
        # to /v1/messages?beta=true; the regex is matched here as squid
        # would, path plus query, against both lists.
        text = squid_conf(open_weight=an_ow_policy())
        line = next(ln for ln in text.splitlines() if "acl ow_paths" in ln)
        pattern = re.compile(line.split("urlpath_regex ", 1)[1])
        for path in ADMITTED_PATHS:
            with self.subTest(path=path):
                self.assertIsNotNone(pattern.search(path))
        for path in REFUSED_PATHS:
            with self.subTest(path=path):
                self.assertIsNone(pattern.search(path))

    def test_a_lan_peer_is_the_origin_as_given(self):
        text = squid_conf(open_weight=an_ow_policy(gateway=SOME_LAN_PEER))
        self.assertIn(f"cache_peer {SOME_LAN_PEER} parent", text)

    def test_no_ow_means_no_listener_and_no_peer(self):
        text = squid_conf()
        self.assertNotIn(str(c.OW_PROXY_PORT), text)
        self.assertNotIn("cache_peer", text)
        self.assertNotIn("ow_port", text)

    def test_an_unresolved_host_peer_and_a_bad_port_are_refused(self):
        with self.assertRaises(c.ConfigError):
            squid_conf(open_weight=an_ow_policy(gateway=c.OW_PEER_HOST))
        with self.assertRaises(c.ConfigError):
            squid_conf(open_weight=an_ow_policy(port=PORT_ABOVE_MAX))

    def test_a_newline_in_the_peer_cannot_forge_a_directive(self):
        with self.assertRaises(c.ConfigError):
            squid_conf(open_weight=an_ow_policy(gateway="h\nhttp_access allow all"))


class OpenWeightPolicyResolution(unittest.TestCase):
    def test_a_host_peer_resolves_to_the_engine_gateway(self):
        cfg = dataclasses.replace(a_config(), open_weight=an_ow_config())
        policy = c.open_weight_policy(cfg, IDE_GATEWAY_NAME, SOME_PATH_REGEX)
        self.assertEqual(policy.gateway, IDE_GATEWAY_NAME)
        self.assertEqual(policy.port, c.OW_DEFAULT_PORT)

    def test_a_named_peer_passes_through_untouched(self):
        cfg = dataclasses.replace(
            a_config(), open_weight=an_ow_config(peer=SOME_LAN_PEER)
        )
        self.assertEqual(
            c.open_weight_policy(cfg, IDE_GATEWAY_NAME, SOME_PATH_REGEX).gateway,
            SOME_LAN_PEER,
        )

    def test_a_host_peer_without_a_gateway_and_a_missing_table_are_refused(self):
        with self.assertRaises(c.ConfigError):
            c.open_weight_policy(
                dataclasses.replace(a_config(), open_weight=an_ow_config()),
                None,
                SOME_PATH_REGEX,
            )
        with self.assertRaises(c.ConfigError):
            c.open_weight_policy(a_config(), IDE_GATEWAY_NAME, SOME_PATH_REGEX)


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

    def test_no_ow_table_means_no_reverse_port(self):
        self.assertIsNone(self._load("[egress]\n").open_weight)

    def test_an_ow_table_defaults_to_the_host_daemon(self):
        open_weight = self._load(OW_MODELS_TOML).open_weight
        self.assertEqual(open_weight.peer, c.OW_PEER_HOST)
        self.assertEqual(open_weight.port, c.OW_DEFAULT_PORT)
        self.assertEqual(
            open_weight.models,
            ((SOME_OPUS_PIN, SOME_OPUS_TAG), (SOME_SONNET_PIN, SOME_SONNET_TAG)),
        )

    def test_the_root_model_defaults_to_the_first_mapping_in_file_order(self):
        text = (
            f'[open-weight]\n[open-weight.models]\n"{SOME_SONNET_PIN}" = "{SOME_SONNET_TAG}"\n'
            f'"{SOME_OPUS_PIN}" = "{SOME_OPUS_TAG}"\n'
        )
        self.assertEqual(self._load(text).open_weight.model, SOME_SONNET_PIN)

    def test_an_explicit_root_model_must_be_a_mapped_name(self):
        self.assertEqual(
            self._load(
                f'[open-weight]\nmodel = "{SOME_SONNET_PIN}"\n{OW_MODELS_TOML}'
            ).open_weight.model,
            SOME_SONNET_PIN,
        )
        with self.assertRaises(c.ConfigError) as cm:
            self._load(f'[open-weight]\nmodel = "claude-fable-5-1"\n{OW_MODELS_TOML}')
        self.assertIn("open-weight.model", str(cm.exception))

    def test_a_full_ow_table_round_trips(self):
        open_weight = self._load(
            f'[open-weight]\npeer = "{SOME_LAN_PEER}"\nport = {SOME_OW_PORT + 1}\n'
            f"{OW_MODELS_TOML}"
        ).open_weight
        self.assertEqual(open_weight.peer, SOME_LAN_PEER)
        self.assertEqual(open_weight.port, SOME_OW_PORT + 1)

    def test_an_ow_table_without_a_model_map_is_refused(self):
        # Every dispatch would name a pinned model the peer does not serve.
        for text in (
            "[open-weight]\n",
            "[open-weight]\n[open-weight.models]\n",
            '[open-weight]\nmodels = "x"\n',
        ):
            with self.subTest(text=text), self.assertRaises(c.ConfigError) as cm:
                self._load(text)
            self.assertIn("models", str(cm.exception))

    def test_a_peer_that_is_not_a_host_or_address_is_refused(self):
        for peer in REFUSED_PEER_SHAPES:
            text = f'[open-weight]\npeer = "{peer}"\n{OW_MODELS_TOML}'
            with self.subTest(peer=peer), self.assertRaises(c.ConfigError):
                self._load(text)

    def test_an_ow_key_the_table_does_not_read_is_refused_by_name(self):
        for text, named in (
            (f'[open-weight]\npaths = ["{MESSAGES_PATH}"]\n', "open-weight.paths"),
            ("[open-weight]\ntimeout_ms = 1\n", "open-weight.timeout_ms"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(c.ConfigError) as cm:
                    self._load(text + OW_MODELS_TOML)
                self.assertIn(named, str(cm.exception))

    def test_ow_port_must_be_a_plain_integer_in_range_and_not_443(self):
        # 443 is the forward port's tunnel port: a peer there would be
        # reachable with its whole API as a CONNECT tunnel.
        for text in (
            "[open-weight]\nport = 0\n",
            f"[open-weight]\nport = {PORT_ABOVE_MAX}\n",
            "[open-weight]\nport = true\n",
            '[open-weight]\nport = "11434"\n',
            f"[open-weight]\nport = {c.SSL_PORT}\n",
        ):
            with self.subTest(text=text), self.assertRaises(c.ConfigError):
                self._load(text + OW_MODELS_TOML)

    def test_a_model_name_or_tag_that_is_not_one_printable_token_is_refused(self):
        # The values reach a terminal and a command line: no control byte, no
        # whitespace, no leading dash.
        for token in REFUSED_MODEL_TOKENS:
            literal = json.dumps(token)
            for text in (
                f'[open-weight]\n[open-weight.models]\n"{SOME_OPUS_PIN}" = {literal}\n',
                f'[open-weight]\n[open-weight.models]\n{literal} = "{SOME_OPUS_TAG}"\n',
            ):
                with self.subTest(text=text), self.assertRaises(c.ConfigError):
                    self._load(text)

    def test_an_unknown_ow_key_is_refused_by_name(self):
        with self.assertRaises(c.ConfigError) as cm:
            self._load(f'[open-weight]\nhost = "x"\n{OW_MODELS_TOML}')
        self.assertIn("open-weight.host", str(cm.exception))

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
        cfg = dataclasses.replace(a_config(), open_weight=an_ow_config())
        emitted = {line.split("=", 1)[0] for line in c.shell_settings(cfg).splitlines()}
        read = launcher_read_keys()
        self.assertTrue(
            emitted <= read, f"launcher does not read: {sorted(emitted - read)}"
        )
        self.assertIn("RW", emitted)
        self.assertIn("RO", emitted)
        self.assertIn("OW_TARGET", emitted)

    def test_the_ow_lines_carry_the_peer_and_the_map(self):
        cfg = dataclasses.replace(a_config(), open_weight=an_ow_config())
        lines = c.shell_settings(cfg).splitlines()
        self.assertIn(f"OW_PEER={c.OW_PEER_HOST}", lines)
        self.assertIn(f"OW_PORT={c.OW_DEFAULT_PORT}", lines)
        self.assertIn(f"OW_PROXY_PORT={c.OW_PROXY_PORT}", lines)
        self.assertIn(f"OW_TAG={SOME_OPUS_TAG}", lines)
        self.assertIn(f"OW_TARGET={SOME_OPUS_TAG} <- {SOME_OPUS_PIN} (session)", lines)

    def test_target_lines_group_by_served_model_and_rank_the_names(self):
        # Names sharing a target list on one line, capability tier first;
        # each distinct target is a tag line once, for the preflight.
        open_weight = c.OpenWeightConfig(
            models=(
                (SOME_OPUS_PIN, SOME_OPUS_TAG),
                (SOME_SONNET_PIN, SOME_SONNET_TAG),
                ("claude-haiku-4-5", SOME_OPUS_TAG),
                ("claude-fable-5-1[1m]", SOME_OPUS_TAG),
                ("other-model", SOME_OPUS_TAG),
            )
        )
        self.assertEqual(c.served_tags(open_weight), [SOME_OPUS_TAG, SOME_SONNET_TAG])
        self.assertEqual(
            c.target_lines(open_weight),
            [
                f"{SOME_OPUS_TAG} <- claude-fable-5-1[1m], {SOME_OPUS_PIN} (session), "
                "claude-haiku-4-5, other-model",
                f"{SOME_SONNET_TAG} <- {SOME_SONNET_PIN}",
            ],
        )

    def test_no_ow_table_emits_no_ow_line(self):
        self.assertNotIn("OW_", c.shell_settings(a_config()))

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
