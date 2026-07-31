#!/usr/bin/env python3
"""Tests for the confinement gate — verify_harness/checks/confinement.py
(stdlib only).

Run: python3 harness/tests/test_confinement.py

Three levels, matching the gate's own layers. Unit: the detectors on synthetic
sources — argv rules, alias/from-import resolution, write-mode parsing, the
bash line scan. Policy: the manifest loads into an immutable record, malformed
fails loud, stale sanctions fail. Integration: both steps pass on today's live
tree — the premise the ADR 2026-07-19 gate rests on. The runtime half of the
pairing (write_guard) is pinned by test_write_guard.py.
"""

import ast
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

sys.path.insert(0, str(ROOT))

from verify_harness import battery  # noqa: E402
from verify_harness.checks import confinement, confinement_ast  # noqa: E402


class NoNetworkGate(unittest.TestCase):
    """1h's argv rules (ADR 2026-07-19 network-write-confinement-gate): a
    subprocess call must present a list-literal argv whose argv0 is in the
    file's [[sanctioned_spawner]] spawns allowlist; both tiers ban network
    CLIs; the producer tier sanctions exactly the egress pairs passed in
    (here deps-report's `git ls-remote https://github.com/…`)."""

    F = Path("harness/x.py")
    GIT = frozenset({"git"})
    EGRESS = frozenset({("ls-remote", "https://github.com/")})

    def _hits(self, code, tier, allowed=GIT):
        node = ast.parse(code).body[0].value
        return confinement_ast._check_subprocess(
            self.F, node, tier, allowed, self.EGRESS
        )

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
        # -m runs a module by name; only unittest (materialize's suite
        # discovery) is sanctioned — pip above all must fire.
        sysexec = frozenset({"sys.executable"})
        self.assertFalse(
            self._hits(
                'subprocess.run([sys.executable, "-m", "unittest", "discover"])',
                "producer",
                sysexec,
            )
        )
        hits = self._hits(
            'subprocess.run([sys.executable, "-m", "pip", "install", "x"])',
            "producer",
            sysexec,
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
                'subprocess.run(["git", "ls-remote", "https://evil.com/x"])',
                "producer",
            )
        )

    def test_sanctioned_sys_executable_allowed(self):
        self.assertFalse(
            self._hits(
                'subprocess.run([sys.executable, "y"])',
                "producer",
                frozenset({"sys.executable"}),
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
        # The sanctioned pair a call exercises lands in used_egress — the
        # staleness check's evidence.
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
                self.F, node, "producer", self.GIT, self.EGRESS, used
            )
        )
        self.assertEqual(used, {("ls-remote", "https://github.com/")})


class EgressFileRules(unittest.TestCase):
    """1h's per-file rules on synthetic sources (_file_egress_hits): the
    subprocess import is a sanctioned capability — banned outside
    [[sanctioned_spawner]] files, alias-proof because import statements name
    the real module — and call receivers resolve through the file's import
    bindings, so aliased and from-imported forms fire like the spelled-out
    ones. The caller's policy arrives dissolved into flags, so these tests
    need no manifest at all."""

    SPAWNER = {"is_spawner": True, "allowed": frozenset({"git"})}

    def _hits(self, code, tier="producer", **flags):
        tree = ast.parse(code)
        return confinement_ast._file_egress_hits(
            Path("harness/x.py"), tree, tier, **flags
        )

    def test_subprocess_import_banned_outside_spawners(self):
        hits = self._hits("import subprocess")
        self.assertEqual(len(hits), 1)
        self.assertIn("not a sanctioned spawner", hits[0])

    def test_aliased_subprocess_import_fires(self):
        self.assertTrue(self._hits("import subprocess as sp"))

    def test_from_subprocess_import_fires(self):
        self.assertTrue(self._hits("from subprocess import run"))

    def test_sanctioned_spawner_may_import_subprocess(self):
        self.assertFalse(self._hits("import subprocess", **self.SPAWNER))

    def test_aliased_call_in_spawner_is_still_argv_checked(self):
        # Inside a sanctioned file the argv rules see through the alias.
        hits = self._hits(
            'import subprocess as sp\nsp.run(["git", "push"])', **self.SPAWNER
        )
        self.assertEqual(len(hits), 1)
        self.assertIn("push", hits[0])

    def test_from_bound_call_in_spawner_is_argv_checked(self):
        hits = self._hits(
            'from subprocess import run\nrun(["git", "push"])', **self.SPAWNER
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
        # No argv to introspect: the shell-string helpers are banned outright,
        # sanction or not, in both their spellings.
        for code in (
            'import subprocess\nsubprocess.getoutput("x")',
            'from subprocess import getstatusoutput\ngetstatusoutput("x")',
        ):
            hits = self._hits(code, **self.SPAWNER)
            self.assertTrue(any("shell string" in h for h in hits), code)

    def test_dynamic_subprocess_import_fires_even_in_a_spawner(self):
        # importlib.import_module("subprocess") would bypass the argv rules —
        # banned regardless of sanction, in both spellings.
        for code in (
            'import importlib\nimportlib.import_module("subprocess")',
            'from importlib import import_module\nimport_module("pty")',
        ):
            for flags in ({}, self.SPAWNER):
                hits = self._hits(code, **flags)
                self.assertTrue(
                    any("defeats the spawn sanction" in h for h in hits),
                    (code, flags),
                )

    def test_webbrowser_is_a_network_module(self):
        self.assertTrue(self._hits("import webbrowser"))

    def test_pty_import_is_banned_even_in_a_spawner(self):
        # pty.spawn runs a command through a pseudo-terminal — outside argv
        # introspection, so no sanction opens it.
        for code in ("import pty", "from pty import spawn"):
            for flags in ({}, self.SPAWNER):
                self.assertTrue(self._hits(code, **flags), (code, flags))

    def test_clean_file_is_clean(self):
        self.assertFalse(self._hits("import json\nimport re\nprint(1)"))


class WriteGate(unittest.TestCase):
    """1i's write detector (ADR 2026-07-19): a capability checker, not a
    name-matcher — it resolves module aliases and from-imports, so a write fires
    however it is spelled. str/datetime .replace and the real write_guard module
    stay out; a name-shadowed write_guard local does not."""

    def _fires(self, code):
        tree = ast.parse(code)
        module_of, from_bind = confinement_ast._import_bindings(tree)
        return any(
            confinement_ast._write_primitive(n, module_of, from_bind)
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
        # tar modes carry a compression suffix — "r:xz" is a read despite the
        # 'x'; only the direction before the separator counts.
        self.assertFalse(self._fires('import tarfile\ntarfile.open(p, "r:xz")'))
        self.assertTrue(self._fires('import tarfile\ntarfile.open(p, "w:gz")'))

    def test_metadata_writes_fire(self):
        # chmod/chown/utime alter filesystem entries (executability is
        # security-relevant), in both the os and Path spellings.
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
        # `open(p, MODE)` cannot de-gate a write — mirrors the dynamic-argv
        # subprocess rule. The generic `.open(` receiver stays lenient for a
        # non-mode positional (urllib's opener.open(request)), strict for a
        # non-literal mode= keyword.
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
        # The target= keyword spelling must not defeat the arity match.
        self.assertTrue(self._fires("Path(t).replace(target=dst)"))

    def test_dynamic_import_of_a_write_module_fires(self):
        self.assertTrue(
            self._fires('import importlib\nimportlib.import_module("sqlite3")')
        )

    def test_write_capability_module_imports_are_flagged(self):
        # sqlite3/dbm/shelve create their backing file with no labelable call —
        # the import is the capability 1i bans outside sanctioned writers.
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
    """1h's bash scan on synthetic lines (_bash_line_hits): a network CLI or a
    git network subcommand as an executed word fires; a comment or a quoted
    string is data — but a $(…) substitution executes even inside double
    quotes, so it is scanned before the quotes are stripped."""

    SH = Path("harness/x.sh")

    def _hits(self, line):
        return confinement._bash_line_hits(self.SH, 1, line)

    def test_network_cli_fires(self):
        self.assertTrue(self._hits("curl http://example.com"))

    def test_comment_is_skipped(self):
        self.assertFalse(self._hits("# curl is mentioned here"))

    def test_git_network_subcommand_fires(self):
        self.assertTrue(self._hits("git push origin main"))

    def test_git_option_argument_cannot_hide_the_subcommand(self):
        self.assertTrue(self._hits('git -C "$target" push'))

    def test_quoted_text_is_data(self):
        # release-version.sh prints the push commands for the maintainer to
        # run — a quoted hint, not an executed command.
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
        # Only a word-opening # starts a comment — the # in ${#arr[@]} must
        # not hide the rest of the line.
        self.assertTrue(self._hits("n=${#arr[@]} && curl http://x"))

    def test_escaped_quote_stays_data(self):
        # An escaped \" inside a double-quoted string must not end the mask
        # and expose the string's tail as executed words.
        self.assertFalse(self._hits('echo "say \\"curl\\" now"'))

    def test_quote_adjacent_hash_is_not_a_comment(self):
        # Masking turns quotes into spaces; the comment cut judges the
        # ORIGINAL line, so `""#` cannot hide the rest of the line.
        self.assertTrue(self._hits('echo ""# && curl http://evil.com'))

    def test_backtick_substitution_is_scanned(self):
        # Backticks execute inside double quotes, like $(…).
        self.assertTrue(self._hits('msg="hello `curl http://evil`"'))
        self.assertTrue(self._hits("x=`git push`"))

    def test_continuation_folds_into_one_logical_line(self):
        # A wrapped command scans as the one command it is — the subcommand
        # cannot hide behind a backslash-newline.
        folded = confinement._folded_lines('git -C "$d" \\\n  push origin\necho ok\n')
        self.assertEqual(folded, [(1, 'git -C "$d"    push origin'), (3, "echo ok")])
        self.assertTrue(
            any("push" in h for h in confinement._bash_line_hits(self.SH, *folded[0]))
        )


class StaleSanctions(unittest.TestCase):
    """The gates fail a sanction no code exercises (ADR 2026-07-19): a writer
    with no raw write, a spawner with no subprocess import, a network file with
    no network-module import, an egress pair no call matches. The manifest
    stays the exact sanctioned surface, never an accumulating one."""

    # registry.py is real, scanned, and clean — sanctioning it must read stale.
    CLEAN = "harness/registry.py"

    def _run(self, check, **overrides):
        import contextlib
        import io
        from unittest import mock

        base = confinement._load_confinement_policy()
        fake = confinement.ConfinementPolicy(
            writers=dict(base.writers) | overrides.get("writers", {}),
            egress=base.egress | overrides.get("egress", set()),
            network=dict(base.network) | overrides.get("network", {}),
            spawners=dict(base.spawners) | overrides.get("spawners", {}),
        )
        b = battery.Battery(quick=True, strict=False)
        err = io.StringIO()
        with (
            mock.patch.object(confinement, "_policy", lambda: fake),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(err),
        ):
            check(b)
        return b.failed, err.getvalue()

    def test_stale_writer_fails(self):
        failed, err = self._run(
            confinement.check_confined_writes, writers={self.CLEAN: "stale"}
        )
        self.assertTrue(failed)
        self.assertIn("stale sanctioned_writer", err)

    def test_stale_spawner_fails(self):
        failed, err = self._run(
            confinement.check_no_network, spawners={self.CLEAN: frozenset({"git"})}
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

    # A real file the gate deliberately never scans (test scaffolding) — a
    # sanction on it would be dead: never enforced, never probed stale.
    UNSCANNED = "harness/tests/test_write_guard.py"

    def test_writer_sanction_on_unscanned_file_fails(self):
        failed, err = self._run(
            confinement.check_confined_writes, writers={self.UNSCANNED: "dead"}
        )
        self.assertTrue(failed)
        self.assertIn("outside the gate's scan targets", err)

    def test_spawner_sanction_on_unscanned_file_fails(self):
        failed, err = self._run(
            confinement.check_no_network,
            spawners={self.UNSCANNED: frozenset({"git"})},
        )
        self.assertTrue(failed)
        self.assertIn("outside the gate's scan targets", err)


class ConfinementGateLiveTree(unittest.TestCase):
    """The two confinement checks (1h, 1i) pass on today's tree — the premise
    the ADR 2026-07-19 gate rests on. A new egress or raw write anywhere in
    the scanned tiers fails here before it fails the battery."""

    def _run(self, check):
        import contextlib
        import io

        b = battery.Battery(quick=True, strict=False)
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            check(b)
        return b.failed

    def test_live_tree_has_no_network_egress(self):
        self.assertFalse(self._run(confinement.check_no_network))

    def test_live_tree_writes_are_confined(self):
        self.assertFalse(self._run(confinement.check_confined_writes))


class ConfinementGateScope(unittest.TestCase):
    """1h/1i scope (ADR 2026-07-19): both user-level tools under tools/ are
    scanned on the producer tier, and claude-dev's network-facing preflight is
    a recorded SANCTIONED_NETWORK exception, not a blanket carve-out."""

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
        # accounting.py is scanned like any producer file — no network pass.
        self.assertNotIn(
            "tools/harness-stats/accounting.py", confinement._policy().network
        )


class ConfinementPolicyManifest(unittest.TestCase):
    """The policy is loaded from one explicit manifest (ADR 2026-07-19): a frozen
    record whose every path resolves, and a malformed manifest fails loud rather
    than silently disarming the gate."""

    def test_policy_is_a_frozen_record(self):
        self.assertTrue(confinement.ConfinementPolicy.__dataclass_params__.frozen)

    def test_policy_mappings_are_read_only(self):
        # Frozen all the way down: the mapping fields are proxies, so an
        # entry cannot be slipped in after the parse boundary.
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
        # An entry with spawns = [] would sanction the import while banning
        # every call — a contradiction that means the entry is stale.
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
        # lookalike domains (github.com.evil.com). Both fail at the parse
        # boundary, before the gate trusts them.
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
        # The two gate steps convert a loader error into an aggregated FAIL,
        # honoring the battery contract (aggregate; the sole sanctioned abort
        # stays the materialize-samples crash in step 3).
        import contextlib
        import io
        from unittest import mock

        def boom():
            raise RuntimeError("confinement policy unreadable (test)")

        for check in (confinement.check_no_network, confinement.check_confined_writes):
            with self.subTest(check=check.__name__):
                b = battery.Battery(quick=True, strict=False)
                with (
                    mock.patch.object(confinement, "_policy", boom),
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    check(b)
                self.assertTrue(b.failed)


if __name__ == "__main__":
    unittest.main()
