#!/usr/bin/env python3
"""Tests for agent_dev_profiles: the per-tool facts, their serialization, and the contracts with each command."""

import dataclasses
import json
import pathlib
import re
import unittest

import agent_dev_config as c
import agent_dev_profiles as p

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
ENGINE = TOOLS_DIR / "agent-dev"

SOME_RW = "/a"
SOME_RO = "/b"
SOME_DOMAIN = "api.anthropic.com"
SOME_OPUS_PIN = "claude-opus-5-5"
SOME_SONNET_PIN = "claude-sonnet-5-5"
SOME_OPUS_TAG = "glm-5.3:cloud"
SOME_SONNET_TAG = "glm-5.3-flash:cloud"
UNKNOWN_TOOL = "nonesuch"

# The operations every command's help must document: the verbs and the
# engine's own flags. --ide is documented only where the profile offers it.
VERBS = ("build", "update", "access", "cleanup", "help")
ENGINE_FLAGS = (
    "--rw",
    "--ro",
    "--allow",
    "--open-egress",
    "--allowlist-egress",
    "--ow",
)


def a_config(**overrides) -> c.Config:
    base = c.Config(rw=(SOME_RW,), ro=(SOME_RO,), allow=(SOME_DOMAIN,))
    return dataclasses.replace(base, **overrides)


def an_ow_config() -> c.OpenWeightConfig:
    return c.OpenWeightConfig(
        models=((SOME_OPUS_PIN, SOME_OPUS_TAG), (SOME_SONNET_PIN, SOME_SONNET_TAG))
    )


def loader_keys() -> set[str]:
    """Collect the profile field names the engine's profile loop has a case arm for."""
    text = ENGINE.read_text().split('PROFILE_TEXT="$(config_py profile)"', 1)[1]
    body = text.split("done <<EOF", 1)[0].split("while IFS='='", 1)[1]
    keys = set()
    for line in body.splitlines():
        match = re.match(r"\s+([A-Z_]+)\)", line)
        if match:
            keys.add(match.group(1))
    return keys


def emitted_keys(profile: p.Profile) -> set[str]:
    return {line.split("=", 1)[0] for line in p.shell_profile(profile).splitlines()}


class ClaudeSettings(unittest.TestCase):
    def test_without_ow_only_the_sandbox_is_declared(self):
        settings = json.loads(p.claude_session_settings(a_config(), open_weight=False))
        self.assertEqual(settings, p.SANDBOX_OFF)

    def test_with_ow_the_endpoint_the_token_and_the_map_ride_in_settings(self):
        # The env block, not the container environment: a settings-file env
        # overrides the process environment, and --settings outranks every
        # project file, so a project cannot point the session elsewhere.
        cfg = a_config(open_weight=an_ow_config())
        settings = json.loads(p.claude_session_settings(cfg, open_weight=True))
        self.assertEqual(settings["sandbox"], p.SANDBOX_OFF["sandbox"])
        self.assertEqual(
            settings["env"],
            {
                "ANTHROPIC_BASE_URL": f"http://proxy:{c.OW_PROXY_PORT}",
                "ANTHROPIC_AUTH_TOKEN": p.CLAUDE_PLACEHOLDER_TOKEN,
                "API_TIMEOUT_MS": str(c.OW_TIMEOUT_MS),
            },
        )
        self.assertEqual(
            settings["modelOverrides"],
            {SOME_OPUS_PIN: SOME_OPUS_TAG, SOME_SONNET_PIN: SOME_SONNET_TAG},
        )
        # The root session names a mapped model, or its own name reaches
        # the peer unmapped.
        self.assertEqual(settings["model"], SOME_OPUS_PIN)

    def test_ow_without_a_table_is_refused(self):
        with self.assertRaises(c.ConfigError):
            p.claude_session_settings(a_config(), open_weight=True)


class ProfileLookup(unittest.TestCase):
    def test_every_profile_is_found_by_its_name(self):
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertIs(p.profile_for(name), profile)
                self.assertEqual(profile.name, name)

    def test_an_unknown_tool_is_refused_naming_the_known_ones(self):
        with self.assertRaises(c.ConfigError) as caught:
            p.profile_for(UNKNOWN_TOOL)
        for name in p.PROFILES:
            self.assertIn(name, str(caught.exception))

    def test_the_claude_profile_delivers_its_settings_by_flag(self):
        # The sandbox-off declaration reaches the session only this way, and
        # the battery pins the same two facts.
        self.assertEqual(p.CLAUDE.settings_flag, "--settings")
        self.assertEqual(p.CLAUDE.settings_env, "")


class ProfileShape(unittest.TestCase):
    def test_a_profile_delivers_its_settings_one_way_only(self):
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertNotEqual(
                    bool(profile.settings_flag), bool(profile.settings_env)
                )

    def test_every_root_path_is_home_relative_and_inside_home(self):
        for name, profile in p.PROFILES.items():
            for root in profile.roots:
                with self.subTest(profile=name, root=root.path):
                    self.assertFalse(root.path.startswith("/"))
                    self.assertNotIn("..", root.path.split("/"))

    def test_every_protected_path_is_a_root_or_inside_one(self):
        # A protected path decides how the tool runs on the host; the engine
        # shares a root read-only or by enumerated list, so a protected path
        # outside every root would be one the session never sees.
        for name, profile in p.PROFILES.items():
            roots = [root.path for root in profile.roots]
            for protected in profile.protected:
                with self.subTest(profile=name, path=protected):
                    self.assertTrue(
                        any(
                            protected == r or protected.startswith(r + "/")
                            for r in roots
                        )
                    )

    def test_every_overlay_sits_under_a_read_only_share_of_its_root(self):
        for name, profile in p.PROFILES.items():
            for root in profile.roots:
                for overlay in root.overlays:
                    with self.subTest(profile=name, overlay=overlay.under):
                        self.assertIn(overlay.under, root.share_ro)

    def test_the_inference_path_regex_admits_only_its_own_shape(self):
        pattern = re.compile(p.CLAUDE.inference_path_regex)
        for admitted in (
            "/v1/messages",
            "/v1/messages?beta=true",
            "/v1/messages/count_tokens",
        ):
            with self.subTest(path=admitted):
                self.assertTrue(pattern.match(admitted))
        for refused in ("/api/pull", "/v1/models", "/v1/messages/../x", "/"):
            with self.subTest(path=refused):
                self.assertFalse(pattern.match(refused))


class ShellProfile(unittest.TestCase):
    def test_every_emitted_field_has_a_case_arm_in_the_launcher(self):
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertLessEqual(emitted_keys(profile), loader_keys())

    def test_every_case_arm_in_the_launcher_is_emitted(self):
        # An arm nothing feeds is a field the launcher waits on forever.
        every = set().union(*(emitted_keys(profile) for profile in p.PROFILES.values()))
        self.assertLessEqual(loader_keys(), every)

    def test_the_command_is_emitted_so_the_launcher_can_cross_check_it(self):
        lines = p.shell_profile(p.CLAUDE).splitlines()
        self.assertIn(f"COMMAND={p.CLAUDE.command}", lines)

    def test_list_fields_are_repeated_one_per_line(self):
        lines = p.shell_profile(p.CLAUDE).splitlines()
        self.assertEqual(
            [line for line in lines if line.startswith("PERM_DEFAULT=")],
            [f"PERM_DEFAULT={flag}" for flag in p.CLAUDE.permission_default],
        )

    def test_a_value_carrying_a_newline_is_refused(self):
        broken = dataclasses.replace(p.CLAUDE, login_hint="a\nb")
        with self.assertRaises(c.ConfigError):
            p.shell_profile(broken)

    def test_a_record_field_carrying_the_separator_is_refused(self):
        root = dataclasses.replace(p.CLAUDE.roots[0], share_ro=("a|b",))
        broken = dataclasses.replace(p.CLAUDE, roots=(root,))
        with self.assertRaises(c.ConfigError):
            p.shell_profile(broken)


class CommandContract(unittest.TestCase):
    """Each profile names a command script beside the engine, and the two agree."""

    def script(self, profile: p.Profile) -> str:
        return (TOOLS_DIR / profile.command).read_text()

    def test_every_profile_has_a_command_script(self):
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertTrue((TOOLS_DIR / profile.command).is_file())

    def test_the_script_names_the_same_tool_and_command_as_the_profile(self):
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertIn(
                    f"export AGENT_DEV_TOOL={profile.name} "
                    f"AGENT_DEV_CMD={profile.command} ",
                    self.script(profile),
                )

    def test_the_data_dir_variable_follows_the_installer_rule(self):
        # install.sh derives it as the upper-cased command plus _HOME.
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                variable = profile.command.upper().replace("-", "_") + "_HOME"
                self.assertIn(
                    f'AGENT_DEV_HOME="${{{variable}:-$HOME/.config/{profile.command}}}"',
                    self.script(profile),
                )

    def test_the_help_documents_every_verb_and_flag_the_engine_accepts(self):
        for name, profile in p.PROFILES.items():
            header = "\n".join(
                line
                for line in self.script(profile).splitlines()
                if line.startswith("#")
            )
            wanted = [*VERBS, *ENGINE_FLAGS, *(["--ide"] if profile.ide else [])]
            for word in wanted:
                with self.subTest(profile=name, word=word):
                    self.assertIn(word, header)

    def test_the_help_does_not_offer_ide_where_the_profile_has_none(self):
        for name, profile in p.PROFILES.items():
            if profile.ide:
                continue
            with self.subTest(profile=name):
                self.assertNotIn("--ide", self.script(profile))

    def test_the_engine_flags_the_test_expects_are_the_ones_it_accepts(self):
        # Keep ENGINE_FLAGS honest: every option arm in the engine appears.
        arms = set(re.findall(r"^\s+(--[a-z-]+)\)", ENGINE.read_text(), re.MULTILINE))
        self.assertEqual(arms - {"--ide"}, set(ENGINE_FLAGS))


if __name__ == "__main__":
    unittest.main()
