#!/usr/bin/env python3
"""Tests for agent_dev_profiles: the per-tool facts, their serialization, and the contracts with each command."""

import dataclasses
import json
import pathlib
import re
import typing
import unittest

import agent_dev_config as c
import agent_dev_profiles as p

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
ENGINE = TOOLS_DIR / "agent-dev"
DOCKERFILE = TOOLS_DIR / "Dockerfile"
INSTALLER = TOOLS_DIR / "install.sh"
HARNESS = TOOLS_DIR.parent.parent / "harness"

SOME_RW = "/a"
SOME_RO = "/b"
SOME_DOMAIN = "api.anthropic.com"
SOME_OPUS_PIN = "claude-opus-5-5"
SOME_SONNET_PIN = "claude-sonnet-5-5"
SOME_HAIKU_PIN = "claude-haiku-4-5"
SOME_HAIKU_TAG = "qwen3:4b"
SOME_OPUS_TAG = "glm-5.3:cloud"
SOME_SONNET_TAG = "glm-5.3-flash:cloud"
SOME_FABLE_PIN = "claude-fable-5-1[1m]"
PIN_OUTSIDE_THE_FAMILY = "some-other-pin"
UNKNOWN_TOOL = "nonesuch"

# What each client sends, and what a session might try instead. squid matches
# the regex against path plus query, so both lists carry the query.
CLAUDE_ADMITTED_PATHS = (
    "/v1/messages",
    "/v1/messages?beta=true",
    "/v1/messages/count_tokens",
    "/v1/messages/count_tokens?beta=true",
)
CLAUDE_REFUSED_PATHS = (
    "/v1/messagesX",
    "/v1/messages/x",
    "/v1/messages/../api/pull",
    "/v1/messages?/../../api/pull",
    "/v1/messages%3F/../../api/pull",
    "/api/pull",
    "/api/tags",
    "/v1/models",
    "/v1/chat/completions",
    "v1/messages",
    "/",
)
OPENCODE_ADMITTED_PATHS = ("/v1/chat/completions", "/v1/chat/completions?x=1")
OPENCODE_REFUSED_PATHS = (
    "/v1/chat/completionsX",
    "/v1/chat/completions/x",
    "/v1/chat/completions?/../../api/pull",
    "/v1/chat/completions%3F/../../api/pull",
    "/api/pull",
    "/v1/models",
    "/v1/messages",
    "/",
)
# The comment that opens the registry block of every shipped allow-list.
TOOLCHAIN_HEADER = "# the image's toolchains"

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
    "--open-weight",
)


def a_config(**overrides) -> c.Config:
    base = c.Config(rw=(SOME_RW,), ro=(SOME_RO,), allow=(SOME_DOMAIN,))
    return dataclasses.replace(base, **overrides)


def an_ow_config(*models: tuple[str, str]) -> c.OpenWeightConfig:
    """Map the given names, or an opus and a sonnet pin; the first is the session's."""
    mapped = models or (
        (SOME_OPUS_PIN, SOME_OPUS_TAG),
        (SOME_SONNET_PIN, SOME_SONNET_TAG),
    )
    return c.OpenWeightConfig(models=mapped, model=mapped[0][0])


def toolchain_hosts(command: str) -> set[str]:
    """Collect the hosts a shipped policy lists from its toolchain header to the end of the allow-list."""
    text = (TOOLS_DIR / f"{command}.toml").read_text()
    block = text.partition(TOOLCHAIN_HEADER)[2].partition("\n]")[0]
    return set(re.findall(r'(?m)^\s*"([^"]+)"', block))


def loader_keys() -> set[str]:
    """Collect the profile field names the engine's profile loop has a case arm for."""
    text = ENGINE.read_text().split('PROFILE_TEXT="$(config_py profile)"', 1)[1]
    body = text.split("done <<EOF", 1)[0].split("while IFS= read -r line", 1)[1]
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


# The top-level keys OpenCode's published config schema accepts that the
# emitter may use; the schema rejects every other top-level key.
OPENCODE_TOP_LEVEL_KEYS = {
    "$schema",
    "autoupdate",
    "share",
    "provider",
    "model",
    "small_model",
}


class OpenCodeSettings(unittest.TestCase):
    def settings(self, config: c.Config, *, open_weight: bool) -> dict:
        return json.loads(p.opencode_session_settings(config, open_weight=open_weight))

    def test_without_ow_sharing_and_auto_update_are_off(self):
        settings = self.settings(a_config(), open_weight=False)
        self.assertEqual(settings["share"], "disabled")
        self.assertIs(settings["autoupdate"], False)
        self.assertNotIn("provider", settings)

    def test_every_top_level_key_is_one_the_schema_accepts(self):
        cfg = a_config(open_weight=an_ow_config())
        for open_weight in (False, True):
            with self.subTest(open_weight=open_weight):
                self.assertLessEqual(
                    set(self.settings(cfg, open_weight=open_weight)),
                    OPENCODE_TOP_LEVEL_KEYS,
                )

    def test_with_ow_the_provider_points_at_the_reverse_port(self):
        cfg = a_config(open_weight=an_ow_config())
        provider = self.settings(cfg, open_weight=True)["provider"][p.OPENCODE_PROVIDER]
        self.assertEqual(provider["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(
            provider["options"],
            {
                "baseURL": f"http://proxy:{c.OW_PROXY_PORT}/v1",
                "apiKey": p.OPENCODE_PLACEHOLDER_KEY,
                "timeout": c.OW_TIMEOUT_MS,
            },
        )

    def test_the_map_keys_the_pins_the_agents_name_and_rewrites_each_id(self):
        cfg = a_config(open_weight=an_ow_config())
        models = self.settings(cfg, open_weight=True)["provider"][p.OPENCODE_PROVIDER][
            "models"
        ]
        self.assertEqual(
            models,
            {
                f"anthropic/{SOME_OPUS_PIN}": {"id": SOME_OPUS_TAG},
                f"anthropic/{SOME_SONNET_PIN}": {"id": SOME_SONNET_TAG},
            },
        )

    def test_the_session_model_is_the_mapped_root_model(self):
        cfg = a_config(open_weight=an_ow_config())
        settings = self.settings(cfg, open_weight=True)
        self.assertEqual(
            settings["model"], f"{p.OPENCODE_PROVIDER}/anthropic/{SOME_OPUS_PIN}"
        )

    def test_the_small_model_is_the_lowest_mapped_tier(self):
        # Title generation names the small model; unpinned it reaches the peer
        # as a model the map does not cover.
        three = an_ow_config(
            (SOME_OPUS_PIN, SOME_OPUS_TAG),
            (SOME_HAIKU_PIN, SOME_HAIKU_TAG),
            (SOME_SONNET_PIN, SOME_SONNET_TAG),
        )
        settings = self.settings(a_config(open_weight=three), open_weight=True)
        self.assertEqual(
            settings["small_model"], f"{p.OPENCODE_PROVIDER}/anthropic/{SOME_HAIKU_PIN}"
        )

    def test_a_name_outside_the_claude_family_never_becomes_the_small_model(self):
        mixed = an_ow_config(
            (SOME_OPUS_PIN, SOME_OPUS_TAG), (PIN_OUTSIDE_THE_FAMILY, SOME_HAIKU_TAG)
        )
        settings = self.settings(a_config(open_weight=mixed), open_weight=True)
        self.assertEqual(settings["small_model"], settings["model"])

    def test_a_single_mapped_model_serves_both_roles(self):
        one = an_ow_config((SOME_OPUS_PIN, SOME_OPUS_TAG))
        settings = self.settings(a_config(open_weight=one), open_weight=True)
        self.assertEqual(settings["small_model"], settings["model"])

    def test_a_map_with_no_family_name_gives_the_small_role_to_the_session_model(self):
        other = an_ow_config((PIN_OUTSIDE_THE_FAMILY, SOME_HAIKU_TAG))
        settings = self.settings(a_config(open_weight=other), open_weight=True)
        self.assertEqual(
            settings["small_model"],
            f"{p.OPENCODE_PROVIDER}/anthropic/{PIN_OUTSIDE_THE_FAMILY}",
        )

    def test_ow_without_a_table_is_refused(self):
        with self.assertRaises(c.ConfigError):
            p.opencode_session_settings(a_config(), open_weight=True)


class PinnedNameRank(unittest.TestCase):
    def test_names_sort_by_family_tier_and_a_name_outside_the_family_sorts_last(self):
        unordered = [
            SOME_HAIKU_PIN,
            PIN_OUTSIDE_THE_FAMILY,
            SOME_FABLE_PIN,
            SOME_SONNET_PIN,
            SOME_OPUS_PIN,
        ]
        self.assertEqual(
            sorted(unordered, key=p.name_rank),
            [
                SOME_FABLE_PIN,
                SOME_OPUS_PIN,
                SOME_SONNET_PIN,
                SOME_HAIKU_PIN,
                PIN_OUTSIDE_THE_FAMILY,
            ],
        )


class InferencePath(unittest.TestCase):
    """Each profile's regex, matched as squid matches it: unanchored search over path plus query."""

    def test_the_claude_shape_is_the_messages_endpoint_and_its_token_count(self):
        pattern = re.compile(p.CLAUDE.inference_path_regex)
        for admitted in CLAUDE_ADMITTED_PATHS:
            with self.subTest(path=admitted):
                self.assertIsNotNone(pattern.search(admitted))
        for refused in CLAUDE_REFUSED_PATHS:
            with self.subTest(path=refused):
                self.assertIsNone(pattern.search(refused))

    def test_the_opencode_shape_is_the_chat_endpoint_only(self):
        pattern = re.compile(p.OPENCODE.inference_path_regex)
        for admitted in OPENCODE_ADMITTED_PATHS:
            with self.subTest(path=admitted):
                self.assertIsNotNone(pattern.search(admitted))
        for refused in OPENCODE_REFUSED_PATHS:
            with self.subTest(path=refused):
                self.assertIsNone(pattern.search(refused))


class StateRootShape(unittest.TestCase):
    def test_the_engine_has_an_arm_for_every_lifetime(self):
        engine = ENGINE.read_text()
        for lifetime in typing.get_args(p.Lifetime):
            with self.subTest(lifetime=lifetime):
                self.assertRegex(engine, rf"(?m)^\s+{lifetime}\)\s+SHADOW=")

    def test_no_root_sits_inside_another_root(self):
        # The engine gives each nested root's parents their own tmpfs; a root
        # that was also another root's parent would be mounted twice.
        for name, profile in p.PROFILES.items():
            paths = [root.path for root in profile.roots]
            for path in paths:
                with self.subTest(profile=name, root=path):
                    self.assertFalse(
                        [other for other in paths if other.startswith(path + "/")]
                    )

    def test_the_root_record_carries_its_lifetime(self):
        lines = p.shell_profile(p.OPENCODE).splitlines()
        self.assertIn("ROOT=.local/share/opencode|opencode-data||project", lines)
        self.assertIn("ROOT=.config/opencode|opencode-config||run", lines)


class FencesInTheShellView(unittest.TestCase):
    """Each tool's fences must know every tool's host config and every other tool's command."""

    def lines(self, profile: p.Profile, key: str) -> list[str]:
        return [
            line.split("=", 1)[1]
            for line in p.shell_profile(profile).splitlines()
            if line.startswith(key + "=")
        ]

    def test_each_profile_names_the_others_commands_and_never_its_own(self):
        for name, profile in p.PROFILES.items():
            expected = sorted(o.command for n, o in p.PROFILES.items() if n != name)
            with self.subTest(profile=name):
                self.assertEqual(sorted(self.lines(profile, "OTHER_COMMAND")), expected)

    def test_every_profile_lists_every_tools_protected_paths(self):
        everything = {
            path for profile in p.PROFILES.values() for path in profile.protected
        }
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                listed = [
                    line.split("|")[0] for line in self.lines(profile, "PROTECTED")
                ]
                self.assertEqual(sorted(listed), sorted(everything))

    def test_a_path_names_its_own_tools_binary_first_then_the_tool_that_reads_it(self):
        # ~/.claude is protected by both tools: each names its own binary for it.
        self.assertIn(".claude|claude", self.lines(p.CLAUDE, "PROTECTED"))
        self.assertIn(".claude|opencode", self.lines(p.OPENCODE, "PROTECTED"))
        self.assertIn(".config/opencode|opencode", self.lines(p.CLAUDE, "PROTECTED"))


class OpenCodeImageStage(unittest.TestCase):
    """The opencode stage runs package scripts, and the proxy starts from the same image."""

    def stage(self) -> str:
        text = DOCKERFILE.read_text().split("FROM base AS opencode\n", 1)[1]
        return re.split(r"(?m)^FROM ", text, maxsplit=1)[0]

    def instructions(self) -> list[str]:
        return [
            line for line in self.stage().splitlines() if re.match(r"[A-Z]+ ", line)
        ]

    def test_no_npm_install_runs_as_root(self):
        user = "root"
        for line in self.stage().splitlines():
            if line.startswith("USER "):
                user = line.split()[1]
            if "npm install" in line and not line.lstrip().startswith("#"):
                self.assertEqual(user, "dev", line)

    def test_the_package_directory_joins_path_last(self):
        # First on PATH, a package could shadow squid in the proxy container.
        paths = [line for line in self.instructions() if line.startswith("ENV PATH=")]
        self.assertEqual(paths, ['ENV PATH="${PATH}:/opt/opencode/node_modules/.bin"'])

    def test_the_seed_the_prepare_step_copies_is_the_one_the_stage_builds(self):
        self.assertIn("cp -R /opt/opencode-seed/.", p.OPENCODE.prepare)
        self.assertIn("npm install --prefix /opt/opencode-seed", self.stage())
        self.assertTrue(p.OPENCODE.prepare.rstrip().endswith('exec "$@"'))


def pinned_models(tool_dir: str) -> set[str]:
    """Collect the model every harness agent pins for one tool."""
    pins = set()
    for agent in HARNESS.glob(f"*/{tool_dir}/agents/*.md"):
        pins.update(re.findall(r"(?m)^model: (\S+)$", agent.read_text()))
    for agent in HARNESS.glob(f"stacks/*/{tool_dir}/agents/*.md"):
        pins.update(re.findall(r"(?m)^model: (\S+)$", agent.read_text()))
    return pins


class ShippedOpenWeightDefault(unittest.TestCase):
    """Both shipped policies enable --ow, so their maps must cover what the agents pin."""

    def table(self, command: str) -> c.OpenWeightConfig:
        table = c.load(TOOLS_DIR / f"{command}.toml", "/home/u").open_weight
        assert table is not None
        return table

    def test_the_default_peer_is_the_daemon_on_this_machine(self):
        for command in ("claude-dev", "opencode-dev"):
            with self.subTest(command=command):
                self.assertEqual(self.table(command).peer, c.OW_PEER_HOST)
                self.assertEqual(self.table(command).port, c.OW_DEFAULT_PORT)

    def test_the_claude_map_keys_are_exactly_the_pins_of_the_claude_agents(self):
        # A pin with no key reaches the peer unmapped and fails every dispatch.
        pins = pinned_models(".claude")
        self.assertTrue(pins)
        self.assertEqual({name for name, _ in self.table("claude-dev").models}, pins)

    def test_the_opencode_map_keys_are_exactly_the_pins_of_the_opencode_agents(self):
        prefix = f"{p.OPENCODE_PROVIDER}/{p.OPENCODE_MODEL_PREFIX}"
        pins = pinned_models(".opencode")
        self.assertTrue(pins)
        self.assertTrue(all(pin.startswith(prefix) for pin in pins), pins)
        self.assertEqual(
            {name for name, _ in self.table("opencode-dev").models},
            {pin.removeprefix(prefix) for pin in pins},
        )

    def test_both_tools_map_each_tier_to_the_same_tag(self):
        def by_tier(command: str) -> dict[int, str]:
            return {
                p.name_rank(name)[0]: tag for name, tag in self.table(command).models
            }

        self.assertEqual(by_tier("claude-dev"), by_tier("opencode-dev"))

    def test_the_root_session_runs_on_the_top_tier(self):
        for command in ("claude-dev", "opencode-dev"):
            with self.subTest(command=command):
                table = self.table(command)
                top = min((name for name, _ in table.models), key=p.name_rank)
                self.assertEqual(table.model, top)


class ImageAndInstaller(unittest.TestCase):
    """Each profile's image stage, labels and installer arm exist."""

    def test_every_profile_names_a_stage_the_dockerfile_defines(self):
        text = DOCKERFILE.read_text()
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertRegex(
                    text, rf"(?m)^FROM base AS {re.escape(profile.image_target)}$"
                )

    def test_every_stage_declares_its_build_args_and_its_label(self):
        text = DOCKERFILE.read_text()
        for name, profile in p.PROFILES.items():
            stage = text.split(f"FROM base AS {profile.image_target}\n", 1)[1]
            stage = re.split(r"(?m)^FROM ", stage, maxsplit=1)[0]
            with self.subTest(profile=name):
                self.assertIn(f"ARG {profile.build_arg}=", stage)
                self.assertIn(f"ARG {profile.cache_bust_arg}=", stage)
                self.assertIn(f"{profile.command}.image=1", stage)
                self.assertIn("agent-dev.image=1", stage)

    def test_the_installer_has_an_arm_for_every_profile(self):
        text = INSTALLER.read_text()
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertIn(f"CMD={profile.command}", text)
                self.assertIn(f"  {name})\n", text)

    def test_every_profile_ships_a_policy_the_reader_accepts(self):
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                config = c.load(TOOLS_DIR / f"{profile.command}.toml", "/home/u")
                self.assertTrue(config.allow)

    def test_the_toolchain_hosts_are_the_same_in_every_shipped_policy(self):
        # The toolchains belong to the shared base image, not to a tool, so a
        # registry added for one policy and not the other would drift silently.
        shared = toolchain_hosts(p.CLAUDE.command)
        self.assertTrue(shared)
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                self.assertEqual(toolchain_hosts(profile.command), shared)

    def test_the_version_variable_is_named_for_the_command_and_the_tool(self):
        for name, profile in p.PROFILES.items():
            with self.subTest(profile=name):
                expected = (
                    f"{profile.command.upper().replace('-', '_')}_"
                    f"{profile.binary.upper()}_VERSION"
                )
                self.assertEqual(profile.version_env, expected)


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
        # shares a root read-only or by enumerated list and hands the config
        # file over as a scrubbed replica, so a protected path outside both
        # would be one the session never sees.
        for name, profile in p.PROFILES.items():
            roots = [root.path for root in profile.roots]
            for protected in profile.protected:
                with self.subTest(profile=name, path=protected):
                    self.assertTrue(
                        protected == profile.replica
                        or any(
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

    def test_a_protected_path_carrying_the_separator_is_refused(self):
        # The launcher splits the record at the separator: the fence would
        # then guard a path nobody wrote.
        broken = dataclasses.replace(p.CLAUDE, protected=("a|b",))
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
        arms = set()
        for group in re.findall(
            r"^\s+(--[a-z-]+(?:\|--[a-z-]+)*)\)", ENGINE.read_text(), re.MULTILINE
        ):
            arms.update(group.split("|"))
        self.assertEqual(arms - {"--ide"}, set(ENGINE_FLAGS))


if __name__ == "__main__":
    unittest.main()
