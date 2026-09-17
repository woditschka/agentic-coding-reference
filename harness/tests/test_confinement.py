#!/usr/bin/env python3
"""Pin the confinement gate's detectors, policy manifest, and live-tree premise."""

import ast
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import ROOT

sys.path.insert(0, str(ROOT))

from verify_harness import battery
from verify_harness.checks import confinement, confinement_ast

SOME_FILE = Path("harness/x.py")
SOME_SCRIPT = Path("harness/x.sh")
SOME_LINE_NO = 1
GIT_ONLY = frozenset({"git"})
SYS_EXECUTABLE_ONLY = frozenset({"sys.executable"})
GITHUB_LS_REMOTE = frozenset({("ls-remote", "https://github.com/")})
SPAWNER_FLAGS: dict[str, object] = {"is_spawner": True, "allowed": GIT_ONLY}


def quiet_battery(check, policy=None) -> tuple[bool, str]:
    b = battery.Battery(quick=True, strict=False)
    err = io.StringIO()
    patch = (
        mock.patch.object(confinement, "_policy", policy)
        if policy is not None
        else contextlib.nullcontext()
    )
    with (
        patch,
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(err),
    ):
        check(b)
    return b.failed, err.getvalue()


class NoNetworkGate(unittest.TestCase):
    """The subprocess argv rules on synthetic calls, per tier."""

    def _hits(self, code, tier, allowed=GIT_ONLY):
        node = ast.parse(code).body[0].value
        rules = confinement_ast.EgressRules(
            tier, allowed=allowed, egress=GITHUB_LS_REMOTE
        )
        return confinement_ast._check_subprocess(SOME_FILE, node, rules)

    def test_shipped_network_tool_fires_and_names_it(self):
        hits = self._hits('subprocess.run(["curl", "x"])', "shipped")
        self.assertEqual(len(hits), 1)
        self.assertIn("network tool", hits[0])

    def test_shipped_git_network_subcommand_fires(self):
        self.assertTrue(self._hits('subprocess.run(["git", "fetch"])', "shipped"))

    def test_shipped_git_local_subcommand_allowed(self):
        self.assertFalse(self._hits('subprocess.run(["git", "diff"])', "shipped"))

    def test_shipped_git_gateway_dynamic_subcommand_allowed(self):
        # The two shipped git gateways pass *args; the literal-only rule
        # deliberately trusts them (the import-boundary gate funnels git there).
        self.assertFalse(self._hits('subprocess.run(["git", *a])', "shipped"))

    def test_shipped_non_literal_argv0_fires(self):
        self.assertTrue(self._hits('subprocess.run([x, "y"])', "shipped"))

    def test_producer_git_push_fires(self):
        self.assertTrue(self._hits('subprocess.run(["git", "push"])', "producer"))

    def test_git_subcommand_behind_options_fires(self):
        # The subcommand is scanned anywhere in argv — `-C <path>` (already
        # idiomatic in init.py's local ls-files call) cannot hide a push.
        for tier in ("shipped", "producer"):
            self.assertTrue(
                self._hits('subprocess.run(["git", "-C", ".", "push", "origin"])', tier)
            )

    def test_egress_url_found_past_a_flag(self):
        # The URL hunt skips option-like literals: --heads must not be
        # mistaken for the destination and false-fail the sanctioned pair.
        self.assertFalse(
            self._hits(
                'subprocess.run(["git", "ls-remote", "--heads", '
                '"https://github.com/x/y.git"])',
                "producer",
            )
        )

    def test_python_m_is_allowlisted(self):
        # -m runs a module by name; only unittest is sanctioned, so pip fires.
        self.assertFalse(
            self._hits(
                'subprocess.run([sys.executable, "-m", "unittest", "discover"])',
                "producer",
                SYS_EXECUTABLE_ONLY,
            )
        )
        hits = self._hits(
            'subprocess.run([sys.executable, "-m", "pip", "install", "x"])',
            "producer",
            SYS_EXECUTABLE_ONLY,
        )
        self.assertTrue(any("pip" in h for h in hits))

    def test_ls_remote_behind_options_matches_egress(self):
        # Position-relative, not index-fixed: the sanctioned pair still matches
        # when options precede the subcommand.
        self.assertFalse(
            self._hits(
                'subprocess.run(["git", "-C", ".", "ls-remote", '
                '"https://github.com/x/y.git"])',
                "producer",
            )
        )

    def test_producer_ls_remote_github_fstring_allowed(self):
        self.assertFalse(
            self._hits(
                'subprocess.run(["git", "ls-remote", f"https://github.com/{r}.git"])',
                "producer",
            )
        )

    def test_producer_ls_remote_other_host_fires(self):
        self.assertTrue(
            self._hits(
                'subprocess.run(["git", "ls-remote", "https://other.example/x"])',
                "producer",
            )
        )

    def test_sanctioned_sys_executable_allowed(self):
        self.assertFalse(
            self._hits(
                'subprocess.run([sys.executable, "y"])',
                "producer",
                SYS_EXECUTABLE_ONLY,
            )
        )

    def test_unsanctioned_sys_executable_fires(self):
        # The allowlist is per file: a spawner sanctioned for git only cannot
        # spawn the interpreter.
        self.assertTrue(self._hits('subprocess.run([sys.executable, "y"])', "producer"))

    def test_unsanctioned_argv0_fires(self):
        # An allowlist, not a network-CLI denylist: pip is unlisted, so it
        # fires without being a known network tool.
        self.assertTrue(
            self._hits('subprocess.run(["pip", "install", "x"])', "producer")
        )

    def test_non_spawner_empty_allowlist_fires(self):
        self.assertTrue(
            self._hits('subprocess.run(["git", "diff"])', "producer", frozenset())
        )

    def test_producer_network_tool_fires(self):
        self.assertTrue(self._hits('subprocess.run(["wget", "x"])', "producer"))

    def test_producer_shell_string_network_tool_fires(self):
        # A literal shell command naming a network CLI is called out by name.
        self.assertTrue(
            self._hits('subprocess.run("curl http://x", shell=True)', "producer")
        )

    def test_any_shell_string_fires(self):
        # Shell strings are rejected outright in both tiers — `"git push"` as a
        # string must not slip past the list-literal git rules.
        for tier in ("shipped", "producer"):
            self.assertTrue(
                self._hits('subprocess.run("git push origin", shell=True)', tier)
            )

    def test_args_keyword_spelling_is_checked(self):
        # subprocess accepts the command as `args=` too — the keyword spelling
        # is held to the same rules as the positional one.
        hits = self._hits('subprocess.run(args=["curl", "x"])', "producer")
        self.assertEqual(len(hits), 1)
        self.assertIn("network tool", hits[0])

    def test_rsync_is_a_network_tool(self):
        self.assertTrue(self._hits('subprocess.run(["rsync", "a", "b"])', "producer"))

    def test_matched_egress_pair_is_recorded(self):
        node = (
            ast.parse(
                'subprocess.run(["git", "ls-remote", "https://github.com/x/y.git"])'
            )
            .body[0]
            .value
        )
        used = set()
        self.assertFalse(
            confinement_ast._check_subprocess(
                SOME_FILE,
                node,
                confinement_ast.EgressRules(
                    "producer", allowed=GIT_ONLY, egress=GITHUB_LS_REMOTE
                ),
                used,
            )
        )
        self.assertEqual(used, set(GITHUB_LS_REMOTE))


class EgressFileRules(unittest.TestCase):
    """The per-file egress rules on synthetic sources, with the policy dissolved into flags."""

    def _hits(self, code, tier="producer", **flags):
        tree = ast.parse(code)
        used_egress = flags.pop("used_egress", None)
        rules = confinement_ast.EgressRules(tier, **flags)
        return confinement_ast._file_egress_hits(SOME_FILE, tree, rules, used_egress)

    def test_subprocess_import_banned_outside_spawners(self):
        hits = self._hits("import subprocess")
        self.assertEqual(len(hits), 1)
        self.assertIn("not a sanctioned spawner", hits[0])

    def test_aliased_subprocess_import_fires(self):
        self.assertTrue(self._hits("import subprocess as sp"))

    def test_from_subprocess_import_fires(self):
        self.assertTrue(self._hits("from subprocess import run"))

    def test_sanctioned_spawner_may_import_subprocess(self):
        self.assertFalse(self._hits("import subprocess", **SPAWNER_FLAGS))

    def test_aliased_call_in_spawner_is_still_argv_checked(self):
        hits = self._hits(
            'import subprocess as sp\nsp.run(["git", "push"])', **SPAWNER_FLAGS
        )
        self.assertEqual(len(hits), 1)
        self.assertIn("push", hits[0])

    def test_from_bound_call_in_spawner_is_argv_checked(self):
        hits = self._hits(
            'from subprocess import run\nrun(["git", "push"])', **SPAWNER_FLAGS
        )
        self.assertTrue(any("push" in h for h in hits))

    def test_aliased_os_system_fires(self):
        self.assertTrue(
            any("os.system" in h for h in self._hits('import os as o\no.system("x")'))
        )

    def test_from_os_import_system_fires_at_import_and_call(self):
        hits = self._hits('from os import system\nsystem("x")')
        self.assertEqual(len(hits), 2)

    def test_aliased_dynamic_network_import_fires(self):
        self.assertTrue(
            self._hits('import importlib as il\nil.import_module("socket")')
        )

    def test_network_module_import_fires(self):
        self.assertTrue(self._hits("import urllib.request"))

    def test_getoutput_is_rejected_even_in_a_spawner(self):
        # No argv to introspect, so no sanction opens the shell-string helpers.
        for code in (
            'import subprocess\nsubprocess.getoutput("x")',
            'from subprocess import getstatusoutput\ngetstatusoutput("x")',
        ):
            hits = self._hits(code, **SPAWNER_FLAGS)
            self.assertTrue(any("shell string" in h for h in hits), code)

    def test_dynamic_subprocess_import_fires_even_in_a_spawner(self):
        for code in (
            'import importlib\nimportlib.import_module("subprocess")',
            'from importlib import import_module\nimport_module("pty")',
        ):
            for flags in ({}, SPAWNER_FLAGS):
                hits = self._hits(code, **flags)
                self.assertTrue(
                    any("defeats the spawn sanction" in h for h in hits),
                    (code, flags),
                )

    def test_webbrowser_is_a_network_module(self):
        self.assertTrue(self._hits("import webbrowser"))

    def test_pty_import_is_banned_even_in_a_spawner(self):
        # pty.spawn runs a command outside argv introspection.
        for code in ("import pty", "from pty import spawn"):
            for flags in ({}, SPAWNER_FLAGS):
                self.assertTrue(self._hits(code, **flags), (code, flags))

    def test_clean_file_is_clean(self):
        self.assertFalse(self._hits("import json\nimport re\nprint(1)"))


class WriteGate(unittest.TestCase):
    """The write detector resolves aliases and from-imports, so a write fires however it is spelled."""

    def _fires(self, code):
        tree = ast.parse(code)
        module_of, from_bind = confinement_ast._import_bindings(tree)
        return any(
            confinement_ast._write_primitive(n, (module_of, from_bind))
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
        )

    def test_builtin_open_append_is_a_write(self):
        self.assertTrue(self._fires('open(p, "ab")'))

    def test_builtin_open_read_is_not(self):
        self.assertFalse(self._fires('open(p, "rb")'))

    def test_builtin_open_default_is_not(self):
        self.assertFalse(self._fires("open(p)"))

    def test_path_open_write_is_a_write(self):
        self.assertTrue(self._fires('p.open("w")'))

    def test_mode_keyword_is_a_write(self):
        self.assertTrue(self._fires('open(p, mode="w")'))

    def test_io_open_write_is_a_write(self):
        self.assertTrue(self._fires('import io\nio.open(p, "w")'))

    def test_from_import_writer_fires(self):
        self.assertTrue(self._fires("from shutil import copytree\ncopytree(a, b)"))

    def test_module_alias_writer_fires(self):
        self.assertTrue(self._fires("import shutil as sh\nsh.copy(a, b)"))

    def test_from_os_rename_fires(self):
        self.assertTrue(self._fires("from os import rename\nrename(a, b)"))

    def test_path_rename_fires(self):
        self.assertTrue(self._fires("Path(t).rename(dst)"))

    def test_path_replace_single_arg_fires(self):
        self.assertTrue(self._fires("Path(t).replace(dst)"))

    def test_os_symlink_fires(self):
        self.assertTrue(self._fires("import os\nos.symlink(a, b)"))

    def test_tempfile_mkstemp_fires(self):
        self.assertTrue(self._fires("import tempfile\ntempfile.mkstemp()"))

    def test_str_replace_two_args_is_not(self):
        self.assertFalse(self._fires("s.replace(a, b)"))

    def test_datetime_replace_kwarg_is_not(self):
        self.assertFalse(self._fires("dt.replace(tzinfo=z)"))

    def test_real_write_guard_module_is_skipped(self):
        self.assertFalse(self._fires("import write_guard\nwrite_guard.mkdir(p)"))

    def test_shadowed_write_guard_local_still_fires(self):
        self.assertTrue(self._fires("write_guard = Obj()\nwrite_guard.mkdir(p)"))

    def test_path_touch_and_rmdir_fire(self):
        self.assertTrue(self._fires("Path(p).touch()"))
        self.assertTrue(self._fires("Path(p).rmdir()"))

    def test_path_link_methods_fire(self):
        self.assertTrue(self._fires("Path(p).symlink_to(t)"))
        self.assertTrue(self._fires("Path(p).hardlink_to(t)"))

    def test_shutil_copyfile_fires(self):
        self.assertTrue(self._fires("import shutil\nshutil.copyfile(a, b)"))
        self.assertTrue(
            self._fires("from shutil import copyfileobj\ncopyfileobj(a, b)")
        )

    def test_compression_open_write_fires_read_does_not(self):
        self.assertTrue(self._fires('import gzip\ngzip.open(p, "wb")'))
        self.assertFalse(self._fires("import gzip\ngzip.open(p)"))

    def test_zipfile_write_fires_default_read_does_not(self):
        self.assertTrue(
            self._fires('from zipfile import ZipFile\nZipFile(p, mode="w")')
        )
        self.assertFalse(self._fires("import zipfile\nzipfile.ZipFile(p)"))

    def test_tarfile_mode_suffix_is_not_a_write(self):
        # "r:xz" is a read despite the 'x': only the part before ':' counts.
        self.assertFalse(self._fires('import tarfile\ntarfile.open(p, "r:xz")'))
        self.assertTrue(self._fires('import tarfile\ntarfile.open(p, "w:gz")'))

    def test_metadata_writes_fire(self):
        self.assertTrue(self._fires("import os\nos.chmod(p, 0o755)"))
        self.assertTrue(self._fires("from os import utime\nutime(p)"))
        self.assertTrue(self._fires("Path(p).chmod(0o755)"))

    def test_logging_file_handler_fires(self):
        self.assertTrue(self._fires("import logging\nlogging.FileHandler(p)"))
        self.assertTrue(
            self._fires(
                "from logging.handlers import RotatingFileHandler\n"
                "RotatingFileHandler(p)"
            )
        )

    def test_non_literal_open_mode_fails_closed(self):
        # The generic `.open(` receiver stays lenient for a non-mode positional
        # (urllib's opener.open(request)), strict for a non-literal mode=.
        self.assertTrue(self._fires("open(p, MODE)"))
        self.assertTrue(self._fires("import io\nio.open(p, m)"))
        self.assertTrue(self._fires("p.open(mode=m)"))
        self.assertFalse(self._fires("_OPENER.open(req, timeout=t)"))

    def test_codecs_open_write_fires(self):
        self.assertTrue(self._fires('import codecs\ncodecs.open(p, "w")'))
        self.assertFalse(self._fires("import codecs\ncodecs.open(p)"))

    def test_shutil_archive_and_chown_fire(self):
        self.assertTrue(self._fires('import shutil\nshutil.make_archive(b, "zip", r)'))
        self.assertTrue(self._fires("import shutil\nshutil.unpack_archive(a, d)"))
        self.assertTrue(self._fires("import shutil\nshutil.chown(p, user=u)"))

    def test_os_node_writers_fire(self):
        self.assertTrue(self._fires("import os\nos.mkfifo(p)"))
        self.assertTrue(self._fires("import os\nos.pwrite(fd, b, 0)"))

    def test_path_replace_target_keyword_fires(self):
        self.assertTrue(self._fires("Path(t).replace(target=dst)"))

    def test_dynamic_import_of_a_write_module_fires(self):
        self.assertTrue(
            self._fires('import importlib\nimportlib.import_module("sqlite3")')
        )

    def test_write_capability_module_imports_are_flagged(self):
        # sqlite3/dbm/shelve create their backing file with no labelable call,
        # so the import itself is the write capability.
        for code in ("import sqlite3", "from dbm import open", "import shelve"):
            self.assertTrue(
                confinement_ast._imports_module(
                    ast.parse(code), confinement_ast.WRITE_MODULES
                ),
                code,
            )
        self.assertFalse(
            confinement_ast._imports_module(
                ast.parse("import json"), confinement_ast.WRITE_MODULES
            )
        )


class BashLineRules(unittest.TestCase):
    """The bash line scan on synthetic lines."""

    def _hits(self, line):
        return confinement._bash_line_hits(SOME_SCRIPT, SOME_LINE_NO, line)

    def test_network_cli_fires(self):
        self.assertTrue(self._hits("curl http://example.com"))

    def test_comment_is_skipped(self):
        self.assertFalse(self._hits("# curl is mentioned here"))

    def test_git_network_subcommand_fires(self):
        self.assertTrue(self._hits("git push origin main"))

    def test_git_option_argument_cannot_hide_the_subcommand(self):
        self.assertTrue(self._hits('git -C "$target" push'))

    def test_quoted_text_is_data(self):
        self.assertFalse(
            self._hits('echo "Next (run manually): git push origin $b && git push v$n"')
        )
        self.assertFalse(self._hits('echo "install curl first"'))

    def test_substitution_inside_quotes_still_executes(self):
        self.assertTrue(self._hits('x="$(git push)"'))

    def test_local_git_is_clean(self):
        self.assertFalse(
            self._hits('BRANCH=$(git -C "$CWD" branch --show-current || true)')
        )

    def test_length_expansion_hash_does_not_cut_the_scan(self):
        self.assertTrue(self._hits("n=${#arr[@]} && curl http://x"))

    def test_escaped_quote_stays_data(self):
        self.assertFalse(self._hits('echo "say \\"curl\\" now"'))

    def test_quote_adjacent_hash_is_not_a_comment(self):
        # Masking turns quotes into spaces; the comment cut judges the
        # original line.
        self.assertTrue(self._hits('echo ""# && curl http://other.example'))

    def test_backtick_substitution_is_scanned(self):
        self.assertTrue(self._hits('msg="hello `curl http://other.example`"'))
        self.assertTrue(self._hits("x=`git push`"))

    def test_continuation_folds_into_one_logical_line(self):
        folded = confinement._folded_lines('git -C "$d" \\\n  push origin\necho ok\n')
        self.assertEqual(folded, [(1, 'git -C "$d"    push origin'), (3, "echo ok")])
        self.assertTrue(
            any(
                "push" in h
                for h in confinement._bash_line_hits(SOME_SCRIPT, *folded[0])
            )
        )


class StaleSanctions(unittest.TestCase):
    """The gates fail a sanction no scanned code exercises."""

    # A real, scanned, clean file: sanctioning it must read stale.
    CLEAN = "harness/registry.py"
    # A real file the gate never scans: a sanction on it would be dead.
    UNSCANNED = "harness/tests/test_write_guard.py"

    def _run(self, check, **overrides):
        base = confinement._load_confinement_policy()
        fake = confinement.ConfinementPolicy(
            writers=dict(base.writers) | overrides.get("writers", {}),
            egress=base.egress | overrides.get("egress", set()),
            network=dict(base.network) | overrides.get("network", {}),
            spawners=dict(base.spawners) | overrides.get("spawners", {}),
        )
        return quiet_battery(check, lambda: fake)

    def test_stale_writer_fails(self):
        failed, err = self._run(
            confinement.check_confined_writes, writers={self.CLEAN: "stale"}
        )
        self.assertTrue(failed)
        self.assertIn("stale sanctioned_writer", err)

    def test_stale_spawner_fails(self):
        failed, err = self._run(
            confinement.check_no_network, spawners={self.CLEAN: GIT_ONLY}
        )
        self.assertTrue(failed)
        self.assertIn("stale sanctioned_spawner", err)

    def test_stale_network_entry_fails(self):
        failed, err = self._run(
            confinement.check_no_network, network={self.CLEAN: "stale"}
        )
        self.assertTrue(failed)
        self.assertIn("stale sanctioned_network", err)

    def test_stale_egress_pair_fails(self):
        failed, err = self._run(
            confinement.check_no_network, egress={("fetch", "https://example.com/")}
        )
        self.assertTrue(failed)
        self.assertIn("stale sanctioned_egress", err)

    def test_writer_sanction_on_unscanned_file_fails(self):
        failed, err = self._run(
            confinement.check_confined_writes, writers={self.UNSCANNED: "dead"}
        )
        self.assertTrue(failed)
        self.assertIn("outside the gate's scan targets", err)

    def test_spawner_sanction_on_unscanned_file_fails(self):
        failed, err = self._run(
            confinement.check_no_network,
            spawners={self.UNSCANNED: GIT_ONLY},
        )
        self.assertTrue(failed)
        self.assertIn("outside the gate's scan targets", err)


class ConfinementGateLiveTree(unittest.TestCase):
    """Both confinement checks pass on the live tree."""

    def _run(self, check):
        failed, _err = quiet_battery(check)
        return failed

    def test_live_tree_has_no_network_egress(self):
        self.assertFalse(self._run(confinement.check_no_network))

    def test_live_tree_writes_are_confined(self):
        self.assertFalse(self._run(confinement.check_confined_writes))


class ConfinementGateScope(unittest.TestCase):
    """The user-level tools are scanned on the producer tier with one recorded network exception."""

    def test_both_tools_are_scanned(self):
        _shipped, producer = confinement._gate_targets()
        rels = {p.relative_to(confinement.ROOT).as_posix() for p in producer}
        self.assertIn("tools/harness-stats/accounting.py", rels)
        self.assertIn("tools/claude-dev/claude_dev_scrub.py", rels)
        self.assertIn("tools/claude-dev/ide_preflight.py", rels)

    def test_claude_dev_probe_is_a_recorded_exception(self):
        self.assertIn(
            "tools/claude-dev/ide_preflight.py", confinement._policy().network
        )

    def test_a_non_probe_tool_file_carries_no_exemption(self):
        self.assertNotIn(
            "tools/harness-stats/accounting.py", confinement._policy().network
        )


class ConfinementPolicyManifest(unittest.TestCase):
    """The policy loads from one manifest into a frozen record, or fails loud."""

    def test_policy_is_a_frozen_record(self):
        self.assertTrue(confinement.ConfinementPolicy.__dataclass_params__.frozen)

    def test_policy_mappings_are_read_only(self):
        with self.assertRaises(TypeError):
            confinement._policy().writers["x"] = "y"  # type: ignore[index]

    def test_every_policy_path_exists(self):
        paths = (
            list(confinement._policy().writers)
            + list(confinement._policy().network)
            + list(confinement._policy().spawners)
        )
        for relp in paths:
            self.assertTrue((confinement.ROOT / relp).is_file(), relp)

    def test_spawner_allowlists_are_nonempty(self):
        # spawns = [] would sanction the import while banning every call.
        for relp, spawns in confinement._policy().spawners.items():
            self.assertTrue(spawns, relp)

    def test_malformed_manifest_raises(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "confinement-policy.toml"
            bad.write_text('[[sanctioned_writer]]\npath = "x"\n')  # 'why' missing
            with self.assertRaises(RuntimeError):
                confinement._load_confinement_policy(bad)

    def test_unbounded_egress_prefix_raises(self):
        # An empty prefix sanctions every host; a slash-less one admits
        # lookalike domains (github.com.other.example).
        for prefix in ("", "https://github.com", "http://github.com/"):
            with tempfile.TemporaryDirectory() as td:
                bad = Path(td) / "confinement-policy.toml"
                bad.write_text(
                    "[[sanctioned_egress]]\n"
                    'subcommand = "ls-remote"\n'
                    f'url_prefix = "{prefix}"\n'
                    'why = "x"\n'
                )
                with self.assertRaises(RuntimeError, msg=prefix):
                    confinement._load_confinement_policy(bad)

    def test_unloadable_manifest_is_a_step_fail_not_a_crash(self):
        def unreadable():
            raise RuntimeError("confinement policy unreadable (test)")

        for check in (confinement.check_no_network, confinement.check_confined_writes):
            with self.subTest(check=check.__name__):
                failed, _err = quiet_battery(check, unreadable)
                self.assertTrue(failed)


if __name__ == "__main__":
    unittest.main()
