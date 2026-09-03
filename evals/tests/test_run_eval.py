"""Unit suite for the runner's pure measurement helpers: the blind judge's
patch sanitization, the post-hoc judge sweep, the ledger-windowed stage
slices with their caps, the hardened JUnit report parse, and the facet
lockstep with the pinned rubric."""

from __future__ import annotations

import datetime
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest import mock

import run_eval
from run_eval import (
    AGENT_BASH_ENV,
    EVALS,
    JUDGE_FACETS,
    LIVE_MAX_LINES_PER_POLL,
    LOGIN_NAME,
    MAX_LEDGER_BYTES,
    MAX_STAGE_MARKS,
    SCRUB_PREFIXES,
    LedgerTail,
    OracleSpec,
    VersionRef,
    agent_claude_args,
    attempt_name,
    commit_baseline,
    consultation_requests,
    dev_source_kept,
    do_judge_runs,
    enabled_plugin_ids,
    era_project_contract,
    era_root_model,
    format_ledger_record,
    installed_plugin_ids,
    judge_argv,
    leak_scan,
    listing_digest,
    load_accounting,
    load_config,
    load_tasks,
    next_rep,
    no_pipeline_run,
    oracle_test_results,
    parse_json_object,
    parse_numstat,
    pipeline_incomplete,
    plugin_enabled,
    quoted_sut_stamps,
    raise_bash_ceiling,
    recorded_sut_stamps,
    rescue_utc,
    resolve_plugin,
    rewrite_project_settings,
    sanitize_patch,
    scrub,
    slice_abandoned,
    stage_slices,
    sut_commit_stamps,
    sweep_order,
    unpinned_enabled,
    utc_stamp,
    write_session_pins,
)


class RouteDecisionTest(unittest.TestCase):
    """The post-session routing read: real subprocess against a stub
    engine, fail-open to None on every degraded shape."""

    def a_workspace(self, script_body: str | None) -> Path:
        workdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, workdir, ignore_errors=True)
        if script_body is not None:
            (workdir / "scripts").mkdir()
            (workdir / "scripts" / "handoff.py").write_text(
                script_body, encoding="utf-8"
            )
        return workdir

    def test_a_dispatch_decision_is_read_from_the_engine(self) -> None:
        workdir = self.a_workspace(
            'import json; print(json.dumps({"decision": "dispatch", "rule": "x"}))'
        )
        self.assertEqual(run_eval.route_decision(workdir), "dispatch")

    def test_a_workspace_without_an_engine_reads_none(self) -> None:
        self.assertIsNone(run_eval.route_decision(self.a_workspace(None)))

    def test_a_refusing_engine_reads_none(self) -> None:
        workdir = self.a_workspace("import sys; sys.exit(2)")
        self.assertIsNone(run_eval.route_decision(workdir))

    def test_non_json_output_reads_none(self) -> None:
        workdir = self.a_workspace('print("not json")')
        self.assertIsNone(run_eval.route_decision(workdir))


class SanitizePatchTest(unittest.TestCase):
    PATCH = (
        "diff --git a/src/main/java/A.java b/src/main/java/A.java\n"
        "+public class A {}\n"
        "diff --git a/docs/testing-principles.md b/docs/testing-principles.md\n"
        "+Visits are editable.\n"
        "+<!-- harness provenance: workflow=tdd-slice v0.2.0 -->\n"
        "+> Provenance: derived — from the visit controller.\n"
        "+Reviewed statement (confirmed 2026-08-01).\n"
        "+No mock frameworks.\n"
        "diff --git a/.claude/agents/coder.md b/.claude/agents/coder.md\n"
        "+identifying runtime file\n"
    )

    def test_source_and_doc_hunks_reach_the_judge(self) -> None:
        clean, _dropped = sanitize_patch(self.PATCH)
        self.assertIn("public class A", clean)
        self.assertIn("No mock frameworks", clean)

    def test_provenance_marked_lines_are_stripped(self) -> None:
        clean, _dropped = sanitize_patch(self.PATCH)
        self.assertNotIn("provenance", clean)
        self.assertNotIn("Provenance:", clean)
        self.assertNotIn("confirmed 2026-08-01", clean)

    def test_the_inline_confirmed_mark_strips_as_a_token_not_a_line(self) -> None:
        # A narrative brief carries a full paragraph on one line; dropping
        # the line would hand the judge a fabricated deletion.
        clean, _dropped = sanitize_patch(self.PATCH)
        self.assertIn("+Reviewed statement.", clean)

    def test_files_outside_src_and_docs_are_dropped_and_counted(self) -> None:
        clean, dropped = sanitize_patch(self.PATCH)
        self.assertNotIn("identifying runtime file", clean)
        self.assertEqual(dropped, 1)

    def test_an_empty_patch_sanitizes_to_empty(self) -> None:
        self.assertEqual(sanitize_patch(""), ("", 0))


class StageSlicesTest(unittest.TestCase):
    acc: ModuleType

    @classmethod
    def setUpClass(cls) -> None:
        cls.acc = load_accounting()

    def a_workdir(self) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        return Path(holder.name)

    def workdir_with_ledger(self, records: list[dict[str, Any]]) -> Path:
        """Returns the ledger path itself — stage_slices reads a ledger file."""
        workdir = self.a_workdir()
        (workdir / ".scratch").mkdir()
        text = "\n".join(json.dumps(r) for r in records)
        ledger = workdir / ".scratch" / "handoff.jsonl"
        ledger.write_text(text, encoding="utf-8")
        return ledger

    def row(self, minute: int, output_tokens: int) -> tuple[float, Any, dict[str, Any]]:
        secs = self.acc.parse_ts(f"2026-08-02T10:{minute:02d}:00Z")
        assert secs is not None
        usage = {"input_tokens": 100, "output_tokens": output_tokens}
        return (float(secs), "claude-opus-5", usage)

    def test_ledger_records_partition_usage_rows_without_double_count(self) -> None:
        workdir = self.workdir_with_ledger(
            [
                {"type": "spec-ready", "ts": "2026-08-02T10:10:00Z", "author": "spec"},
                {"type": "tests-ready", "ts": "2026-08-02T10:20:00Z", "author": "td"},
            ]
        )
        # The 10:10 row sits exactly on a boundary: it lands once, in the
        # stage that record closes.
        rows = [self.row(2, 10), self.row(10, 20), self.row(15, 40), self.row(25, 80)]
        slices = stage_slices(self.acc, workdir, rows)
        self.assertEqual(
            [s["closes"] for s in slices], ["spec-ready", "tests-ready", None]
        )
        self.assertEqual([s["totals"]["output"] for s in slices], [30, 40, 80])
        self.assertEqual(slices[0]["wall_seconds"], 480.0)

    def test_a_non_string_author_is_dropped_not_embedded(self) -> None:
        workdir = self.workdir_with_ledger(
            [
                {
                    "type": "spec-ready",
                    "ts": "2026-08-02T10:10:00Z",
                    "author": {"nested": "object"},
                }
            ]
        )
        slices = stage_slices(self.acc, workdir, [self.row(2, 10)])
        self.assertIsNone(slices[0]["author"])

    def test_a_ledger_over_the_mark_cap_is_refused_whole(self) -> None:
        records = [
            {"type": "noise", "ts": "2026-08-02T10:10:00Z"}
            for _ in range(MAX_STAGE_MARKS + 1)
        ]
        workdir = self.workdir_with_ledger(records)
        self.assertEqual(stage_slices(self.acc, workdir, [self.row(1, 1)]), [])

    def test_no_ledger_yields_no_slices(self) -> None:
        self.assertEqual(
            stage_slices(
                self.acc, self.a_workdir() / "handoff.jsonl", [self.row(1, 1)]
            ),
            [],
        )

    def test_records_without_timestamps_yield_no_slices(self) -> None:
        workdir = self.workdir_with_ledger([{"type": "spec-ready", "author": "spec"}])
        self.assertEqual(stage_slices(self.acc, workdir, [self.row(1, 1)]), [])


class OracleReportTest(unittest.TestCase):
    ORACLE = OracleSpec(
        source=Path("unused"),
        dest="unused",
        test_class="org.example.Oracle",
        base_green=("wiringWorks",),
        base_red=("editUpdatesInPlace",),
    )

    def workdir_with_report(self, xml: str) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        workdir = Path(holder.name)
        report_dir = workdir / "build" / "test-results" / "test"
        report_dir.mkdir(parents=True)
        (report_dir / "TEST-org.example.Oracle.xml").write_text(xml, encoding="utf-8")
        return workdir

    def test_a_gradle_report_maps_each_case_to_its_outcome(self) -> None:
        workdir = self.workdir_with_report(
            "<testsuite>"
            '<testcase name="wiringWorks()"/>'
            '<testcase name="editUpdatesInPlace()"><failure>boom</failure></testcase>'
            "</testsuite>"
        )
        results, unexpected = oracle_test_results(workdir, self.ORACLE)
        self.assertEqual(results["wiringWorks"], "passed")
        self.assertEqual(results["editUpdatesInPlace"], "failed")
        self.assertEqual(unexpected, 0)

    def test_the_first_outcome_marker_wins_the_verdict_never_softens(self) -> None:
        workdir = self.workdir_with_report(
            "<testsuite>"
            '<testcase name="editUpdatesInPlace()">'
            "<failure>boom</failure><skipped/>"
            "</testcase>"
            "</testsuite>"
        )
        results, _unexpected = oracle_test_results(workdir, self.ORACLE)
        self.assertEqual(results["editUpdatesInPlace"], "failed")

    def test_unexpected_case_names_are_counted_never_recorded(self) -> None:
        workdir = self.workdir_with_report(
            "<testsuite>"
            '<testcase name="wiringWorks()"/>'
            '<testcase name="somethingElse()"/>'
            "</testsuite>"
        )
        results, unexpected = oracle_test_results(workdir, self.ORACLE)
        self.assertNotIn("somethingElse", results)
        self.assertEqual(unexpected, 1)

    def test_a_missing_report_reads_as_missing_for_every_expected_test(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        results, _unexpected = oracle_test_results(Path(holder.name), self.ORACLE)
        self.assertEqual(set(results.values()), {"missing"})

    def test_a_report_with_a_document_type_declaration_reads_as_missing(self) -> None:
        workdir = self.workdir_with_report(
            '<!DOCTYPE testsuite [<!ENTITY a "aaaa">]>'
            '<testsuite><testcase name="wiringWorks()"/></testsuite>'
        )
        results, _unexpected = oracle_test_results(workdir, self.ORACLE)
        self.assertEqual(set(results.values()), {"missing"})

    def test_a_malformed_report_reads_as_missing(self) -> None:
        workdir = self.workdir_with_report("<testsuite><testcase")
        results, _unexpected = oracle_test_results(workdir, self.ORACLE)
        self.assertEqual(set(results.values()), {"missing"})


class DevSourceFilterTest(unittest.TestCase):
    """The leak barrier of a dev build: the eval bench never enters the
    agent-readable marketplace source."""

    def test_the_eval_bench_never_enters_the_source(self) -> None:
        self.assertFalse(dev_source_kept("evals"))
        self.assertFalse(dev_source_kept("evals/tasks/visit-edit/task.toml"))
        self.assertFalse(dev_source_kept(""))

    def test_everything_else_is_kept_and_the_prefix_never_overmatches(self) -> None:
        self.assertTrue(dev_source_kept("harness/VERSION"))
        self.assertTrue(dev_source_kept("evals-notes.md"))


class ParseNumstatTest(unittest.TestCase):
    """The `--numstat -z` parse feeding the diff figures and the refusal
    bar's src count."""

    def test_entry_counts_sum_across_files(self) -> None:
        totals = parse_numstat("3\t1\ta.java\x0010\t0\tb.java\x00")
        self.assertEqual(
            totals,
            {
                "files_changed": 2,
                "insertions": 13,
                "deletions": 1,
                "src_files_changed": 0,
            },
        )

    def test_a_binary_file_counts_as_changed_with_zero_line_movement(self) -> None:
        totals = parse_numstat("-\t-\tlogo.png\x002\t2\ta.java\x00")
        self.assertEqual(
            totals,
            {
                "files_changed": 2,
                "insertions": 2,
                "deletions": 2,
                "src_files_changed": 0,
            },
        )

    def test_malformed_tokens_are_ignored(self) -> None:
        self.assertEqual(
            parse_numstat("garbage\x00"),
            {
                "files_changed": 0,
                "insertions": 0,
                "deletions": 0,
                "src_files_changed": 0,
            },
        )

    def test_src_paths_count_separately_from_the_rest(self) -> None:
        totals = parse_numstat(
            "3\t1\tsrc/main/java/A.java\x00"
            "1\t0\tdocs/prd.md\x00"
            "2\t0\tsrc/test/java/ATest.java\x00"
        )
        self.assertEqual(totals["files_changed"], 3)
        self.assertEqual(totals["src_files_changed"], 2)

    def test_a_rename_counts_on_either_side(self) -> None:
        # -z rename form: empty path field, then the two raw paths as their
        # own NUL-separated fields. A rename into OR out of src/ is a src
        # change; a rename entirely outside src/ is not.
        totals = parse_numstat(
            "0\t0\t\x00docs/old.md\x00src/main/java/A.java\x00"
            "0\t0\t\x00src/main/java/C.java\x00docs/new.md\x00"
            "0\t0\t\x00docs/a.md\x00docs/b.md\x00"
        )
        self.assertEqual(totals["files_changed"], 3)
        self.assertEqual(totals["src_files_changed"], 2)

    def test_hostile_file_names_cannot_dodge_the_src_prefix(self) -> None:
        # -z emits raw paths: no C-quoting of non-ASCII bytes, no `=>`
        # rendering, and a tab inside a name stays inside the path field.
        totals = parse_numstat(
            "1\t0\tsrc/main/java/Cancelación.java\x00"
            "1\t0\tsrc/sneaky => x.txt\x00"
            "1\t0\tsrc/a\tb.java\x00"
        )
        self.assertEqual(totals["files_changed"], 3)
        self.assertEqual(totals["src_files_changed"], 3)


class MakePatchTest(unittest.TestCase):
    """The staging that feeds the refusal bar: an agent-edited ignore file
    cannot hide a src/ change from the diff."""

    def a_git_workspace(self) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        workdir = Path(holder.name)
        git = ["git", "-C", str(workdir)]
        subprocess.run(git + ["init", "--quiet"], check=True)
        (workdir / "src" / "main").mkdir(parents=True)
        (workdir / "src" / "main" / "Keep.java").write_text("class Keep {}\n")
        (workdir / ".gitignore").write_text("build/\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(
            git
            + [
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@localhost",
                "commit",
                "--quiet",
                "-m",
                "baseline",
            ],
            check=True,
        )
        return workdir

    def test_an_ignore_file_edit_cannot_hide_a_src_change(self) -> None:
        workdir = self.a_git_workspace()
        baseline = subprocess.run(
            ["git", "-C", str(workdir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        with (workdir / ".gitignore").open("a") as fh:
            fh.write("src/main/Evil.java\n")
        (workdir / "src" / "main" / "Evil.java").write_text("class Evil {}\n")
        out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        totals = run_eval.make_patch(workdir, baseline, out_dir)
        self.assertEqual(totals["src_files_changed"], 1)
        patch = (out_dir / "change.patch").read_text(encoding="utf-8")
        self.assertIn("Evil.java", patch)


class ConsultationRequestsTest(unittest.TestCase):
    """The refusal ladder's Tier B checkpoint: consultation-request records
    counted from the copied ledger."""

    def out_dir_with(self, lines: list[str]) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        out_dir = Path(holder.name)
        (out_dir / "handoff.jsonl").write_text("\n".join(lines), encoding="utf-8")
        return out_dir

    def test_consultation_requests_are_counted(self) -> None:
        out_dir = self.out_dir_with(
            [
                json.dumps({"type": "dispatch-start", "author": "a"}),
                json.dumps({"type": "consultation-request", "author": "a"}),
                json.dumps({"type": "consultation-request", "author": "b"}),
            ]
        )
        self.assertEqual(consultation_requests(out_dir), 2)

    def test_malformed_lines_and_other_types_count_nothing(self) -> None:
        out_dir = self.out_dir_with(
            ["not json", json.dumps({"type": "consultation-response"}), "[1]"]
        )
        self.assertEqual(consultation_requests(out_dir), 0)

    def test_a_missing_ledger_counts_zero(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.assertEqual(consultation_requests(Path(holder.name)), 0)

    def test_an_oversized_ledger_counts_zero_never_reads(self) -> None:
        out_dir = self.out_dir_with([])
        (out_dir / "handoff.jsonl").write_text("x" * (MAX_LEDGER_BYTES + 1))
        self.assertEqual(consultation_requests(out_dir), 0)

    def test_deeply_nested_json_is_skipped_not_raised(self) -> None:
        out_dir = self.out_dir_with(
            [
                "[" * 200_000,
                json.dumps({"type": "consultation-request", "author": "a"}),
            ]
        )
        self.assertEqual(consultation_requests(out_dir), 1)


class SweepOrderTest(unittest.TestCase):
    """The version-interleaved cell order of a multi-version sweep."""

    A = VersionRef(label="v0.1.0", kind="tag", expected_version="0.1.0")
    B = VersionRef(label="v0.2.0", kind="tag", expected_version="0.2.0")

    def test_versions_alternate_within_each_task(self) -> None:
        order = sweep_order(2, ["t1", "t2"], [self.A, self.B])
        self.assertEqual(
            [(task, v.label) for task, v in order[:4]],
            [
                ("t1", "v0.1.0"),
                ("t1", "v0.2.0"),
                ("t2", "v0.1.0"),
                ("t2", "v0.2.0"),
            ],
        )
        self.assertEqual(len(order), 8)

    def test_a_single_version_sweep_keeps_task_order(self) -> None:
        order = sweep_order(1, ["t1", "t2"], [self.A])
        self.assertEqual(
            [(task, v.label) for task, v in order], [("t1", "v0.1.0"), ("t2", "v0.1.0")]
        )


class LoadTasksTest(unittest.TestCase):
    """The task loader's kind/oracle lockstep (README § Refusal tasks)."""

    def tasks_dir_with(self, kind: str, with_oracle: bool) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        task_dir = Path(holder.name) / "a-task"
        task_dir.mkdir()
        manifest = (
            f'id = "a-task"\nkind = "{kind}"\ntitle = "A task"\n'
            'prompt = "Do the thing."\n'
        )
        if with_oracle:
            (task_dir / "oracle").mkdir()
            (task_dir / "oracle" / "Oracle.java").write_text("class Oracle {}\n")
            manifest += (
                '[[oracle]]\nfile = "Oracle.java"\ndest = "src/test/Oracle.java"\n'
                'test_class = "Oracle"\nbase_green = ["a"]\nbase_red = ["b"]\n'
            )
        (task_dir / "task.toml").write_text(manifest, encoding="utf-8")
        return Path(holder.name)

    def test_a_refusal_task_loads_without_an_oracle(self) -> None:
        tasks = load_tasks(self.tasks_dir_with("refusal", with_oracle=False))
        self.assertEqual(tasks["a-task"].oracles, ())
        self.assertTrue(tasks["a-task"].fingerprint())

    def test_a_refusal_task_with_an_oracle_is_refused(self) -> None:
        with self.assertRaises(RuntimeError):
            load_tasks(self.tasks_dir_with("refusal", with_oracle=True))

    def test_a_feature_task_without_an_oracle_is_refused(self) -> None:
        with self.assertRaises(RuntimeError):
            load_tasks(self.tasks_dir_with("feature", with_oracle=False))

    def test_the_committed_task_set_loads_clean(self) -> None:
        tasks = load_tasks()
        self.assertIn("visit-cancel", tasks)
        self.assertEqual(tasks["visit-cancel"].kind, "refusal")
        self.assertIn("specialty-directory", tasks)


class RewriteProjectSettingsTest(unittest.TestCase):
    """The settings scrub that pins the workspace to the eval marketplace."""

    def workdir_with(
        self, settings: dict[str, Any], local: dict[str, Any] | None = None
    ) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        workdir = Path(holder.name)
        (workdir / ".claude").mkdir(parents=True)
        (workdir / ".claude" / "settings.json").write_text(
            json.dumps(settings), encoding="utf-8"
        )
        if local is not None:
            (workdir / ".claude" / "settings.local.json").write_text(
                json.dumps(local), encoding="utf-8"
            )
        return workdir

    def settings_of(self, workdir: Path, name: str) -> dict[str, Any]:
        payload = json.loads((workdir / ".claude" / name).read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        return payload

    def test_the_eval_marketplace_replaces_the_committed_declaration(self) -> None:
        workdir = self.workdir_with(
            {
                "extraKnownMarketplaces": {"agent-team": {}},
                "enabledPlugins": {"agent-team-spring-boot@agent-team": True},
            }
        )
        rewrite_project_settings("agent-team-spring-boot", workdir)
        settings = self.settings_of(workdir, "settings.json")
        self.assertNotIn("extraKnownMarketplaces", settings)
        self.assertEqual(
            settings["enabledPlugins"],
            {"agent-team-spring-boot@agent-team-eval": True},
        )

    def test_foreign_plugins_survive_the_rewrite(self) -> None:
        workdir = self.workdir_with(
            {"enabledPlugins": {"other-plugin@somewhere": True}}
        )
        rewrite_project_settings("agent-team-spring-boot", workdir)
        enabled = self.settings_of(workdir, "settings.json")["enabledPlugins"]
        self.assertTrue(enabled["other-plugin@somewhere"])
        self.assertTrue(enabled["agent-team-spring-boot@agent-team-eval"])

    def test_operator_plugins_are_pinned_off_in_the_workspace(self) -> None:
        workdir = self.workdir_with({"enabledPlugins": {}})
        rewrite_project_settings(
            "agent-team-spring-boot",
            workdir,
            pin_off=("agent-team-spring-boot@agent-team", "other@somewhere"),
        )
        enabled = self.settings_of(workdir, "settings.json")["enabledPlugins"]
        self.assertEqual(
            enabled,
            {
                "agent-team-spring-boot@agent-team-eval": True,
                "agent-team-spring-boot@agent-team": False,
                "other@somewhere": False,
            },
        )

    def test_a_committed_local_layer_cannot_reenable_a_pinned_plugin(self) -> None:
        workdir = self.workdir_with(
            {"enabledPlugins": {}},
            local={"enabledPlugins": {"other@somewhere": True}},
        )
        rewrite_project_settings(
            "agent-team-spring-boot", workdir, pin_off=("other@somewhere",)
        )
        local = self.settings_of(workdir, "settings.local.json")["enabledPlugins"]
        self.assertEqual(local, {"other@somewhere": False})
        self.assertNotIn(
            "agent-team-spring-boot@agent-team-eval",
            local,
            "the eval enablement stays a settings.json-only pin",
        )

    def test_the_local_layer_is_scrubbed_but_never_gains_the_pin(self) -> None:
        workdir = self.workdir_with(
            {"enabledPlugins": {}},
            local={
                "extraKnownMarketplaces": {"agent-team": {}},
                "enabledPlugins": {"agent-team-spring-boot@agent-team": True},
            },
        )
        rewrite_project_settings("agent-team-spring-boot", workdir)
        local = self.settings_of(workdir, "settings.local.json")
        self.assertNotIn("extraKnownMarketplaces", local)
        self.assertEqual(local["enabledPlugins"], {})

    def test_the_bash_ceiling_lands_beside_the_committed_env(self) -> None:
        workdir = self.workdir_with({"env": {"EXISTING": "kept"}})
        note = raise_bash_ceiling(workdir)
        env = self.settings_of(workdir, "settings.json")["env"]
        self.assertEqual(env["EXISTING"], "kept")
        for key, value in AGENT_BASH_ENV.items():
            self.assertEqual(env[key], value)
            self.assertIn(key, note)

    def test_the_bash_ceiling_overrides_a_committed_value(self) -> None:
        workdir = self.workdir_with({"env": {"BASH_DEFAULT_TIMEOUT_MS": "1000"}})
        raise_bash_ceiling(workdir)
        env = self.settings_of(workdir, "settings.json")["env"]
        self.assertEqual(
            env["BASH_DEFAULT_TIMEOUT_MS"],
            AGENT_BASH_ENV["BASH_DEFAULT_TIMEOUT_MS"],
        )


class ResolvePluginTest(unittest.TestCase):
    """Per-version plugin-id resolution against the source's marketplace.json."""

    def source_with(self, *names: str) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        src = Path(holder.name)
        (src / ".claude-plugin").mkdir()
        (src / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"plugins": [{"name": n} for n in names]}), encoding="utf-8"
        )
        return src

    def test_the_configured_id_wins_when_the_source_offers_it(self) -> None:
        src = self.source_with("agent-team-spring-boot", "spring-boot-claude")
        self.assertEqual(
            resolve_plugin("agent-team-spring-boot", src), "agent-team-spring-boot"
        )

    def test_a_pre_repackage_source_falls_back_to_the_legacy_spelling(self) -> None:
        src = self.source_with("spring-boot-claude", "go-claude")
        with redirect_stdout(io.StringIO()):
            resolved = resolve_plugin("agent-team-spring-boot", src)
        self.assertEqual(resolved, "spring-boot-claude")

    def test_a_source_offering_neither_spelling_stops_loudly(self) -> None:
        src = self.source_with("something-else")
        with self.assertRaises(RuntimeError) as caught:
            resolve_plugin("agent-team-spring-boot", src)
        self.assertIn("something-else", str(caught.exception))


class JudgeArgvTest(unittest.TestCase):
    def test_the_host_executor_invokes_the_cli_directly(self) -> None:
        argv = judge_argv("grade this", "claude-opus-5", use_claude_dev=False)
        self.assertEqual(argv[0], "claude")
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_the_container_executor_wraps_the_same_claude_args(self) -> None:
        argv = judge_argv("grade this", "claude-opus-5", use_claude_dev=True)
        self.assertEqual(argv[:2], ["claude-dev", "--"])
        self.assertIn("--dangerously-skip-permissions", argv)
        self.assertIn("grade this", argv)


class JudgeRunsTest(unittest.TestCase):
    """The post-hoc judge sweep over recorded run folders."""

    EPOCH = "a" * 40

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.runs = Path(holder.name)
        self.cfg = load_config()
        self.calls: list[tuple[Any, ...]] = []

    def record(
        self,
        name: str,
        *,
        judged: bool = False,
        status: str = "complete",
        patch: bool = True,
        kind: str = "feature",
    ) -> Path:
        out = self.runs / "v0.2.0" / name
        out.mkdir(parents=True)
        result: dict[str, Any] = {"status": status}
        if judged:
            result["quality_judge"] = {"samples": [{"design_fit": 3}], "median": {}}
        (out / "result.json").write_text(json.dumps(result), encoding="utf-8")
        (out / "manifest.json").write_text(
            json.dumps(
                {
                    "prompt": "Fix it.",
                    "sut": {"sha": self.EPOCH},
                    "task": {"id": "visit-edit", "kind": kind},
                }
            ),
            encoding="utf-8",
        )
        if patch:
            (out / "change.patch").write_text("diff --git\n", encoding="utf-8")
        return out

    def invoke(
        self,
        verdict: dict[str, Any] | None,
        *,
        epoch_in_clone: bool = True,
        versions: tuple[str, ...] = (),
        tasks: tuple[str, ...] = (),
    ) -> int:
        def fake_judge(*args: Any) -> dict[str, Any] | None:
            self.calls.append(args)
            return dict(verdict) if verdict is not None else None

        def fake_sh(*args: Any, **kwargs: Any) -> Any:
            return SimpleNamespace(returncode=0 if epoch_in_clone else 1)

        real_judge, real_sh = run_eval.run_judge, run_eval.sh
        run_eval.run_judge, run_eval.sh = fake_judge, fake_sh  # type: ignore[assignment]
        self.addCleanup(setattr, run_eval, "run_judge", real_judge)
        self.addCleanup(setattr, run_eval, "sh", real_sh)
        with redirect_stdout(io.StringIO()):
            return do_judge_runs(
                self.cfg, runs_dir=self.runs, versions=versions, tasks=tasks
            )

    @staticmethod
    def verdict(**overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "median": {facet: 3 for facet in JUDGE_FACETS},
            "cost_usd": 1.0,
        }
        base.update(overrides)
        return base

    def result_of(self, out: Path) -> dict[str, Any]:
        payload = json.loads((out / "result.json").read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        return payload

    def test_only_unjudged_complete_runs_are_judged(self) -> None:
        already = self.record("r1", judged=True)
        self.record("r2", status="timeout")
        fresh = self.record("r3")
        code = self.invoke(self.verdict())
        self.assertEqual(code, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.result_of(fresh)["quality_judge"]["post_hoc"])
        self.assertNotIn("post_hoc", self.result_of(already)["quality_judge"])

    def test_the_briefs_read_from_the_sut_clone_at_the_epoch_commit(self) -> None:
        self.record("r1")
        self.invoke(self.verdict())
        _cfg, prompt, workdir, sha, _out, _log, _use_dev = self.calls[0]
        self.assertEqual(prompt, "Fix it.")
        self.assertEqual(workdir, self.cfg.clone)
        self.assertEqual(sha, self.EPOCH)

    def test_a_missing_epoch_commit_fails_and_judges_nothing(self) -> None:
        out = self.record("r1")
        code = self.invoke(self.verdict(), epoch_in_clone=False)
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [])
        self.assertNotIn("quality_judge", self.result_of(out))

    def test_an_empty_sanitized_patch_leaves_the_record_unwritten(self) -> None:
        out = self.record("r1")
        code = self.invoke(None)
        self.assertEqual(code, 0)
        self.assertNotIn("quality_judge", self.result_of(out))

    def test_version_and_task_filters_scope_the_sweep(self) -> None:
        self.record("r1")
        self.assertEqual(self.invoke(self.verdict(), versions=("v9.9.9",)), 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.invoke(self.verdict(), tasks=("owners-page-param",)), 0)
        self.assertEqual(self.calls, [])
        self.invoke(self.verdict(), versions=("v0.2.0",), tasks=("visit-edit",))
        self.assertEqual(len(self.calls), 1)

    def test_a_refusal_run_is_never_judged(self) -> None:
        out = self.record("r1", kind="refusal")
        code = self.invoke(self.verdict())
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [])
        self.assertNotIn("quality_judge", self.result_of(out))

    def test_a_recorded_sampleless_verdict_is_rejudged(self) -> None:
        out = self.record("r1")
        payload = self.result_of(out)
        payload["quality_judge"] = {"samples": [], "error": "no parsable samples"}
        (out / "result.json").write_text(json.dumps(payload), encoding="utf-8")
        code = self.invoke(self.verdict())
        self.assertEqual(code, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("error", self.result_of(out)["quality_judge"])

    def test_a_sampleless_verdict_still_lands_and_reports_failure(self) -> None:
        out = self.record("r1")
        code = self.invoke(self.verdict(error="no parsable samples", cost_usd=0.0))
        self.assertEqual(code, 1)
        self.assertTrue(self.result_of(out)["quality_judge"]["post_hoc"])


class JudgeContractTest(unittest.TestCase):
    def test_the_pinned_rubric_output_contract_carries_every_runner_facet(self) -> None:
        rubric = load_config().judge.rubric.read_text(encoding="utf-8")
        for facet in JUDGE_FACETS:
            self.assertIn(f'"{facet}"', rubric)

    def test_the_pinned_rubric_exists_inside_the_bench(self) -> None:
        rubric = load_config().judge.rubric.resolve()
        self.assertTrue(rubric.is_file())
        self.assertEqual(rubric.parent, (EVALS / "judge").resolve())


class PluginEnabledTest(unittest.TestCase):
    """The prep-time enablement gate's parser over `claude plugin list
    --json`. Every degraded input reads as not-enabled: the gate fails
    closed."""

    PLUGIN = "agent-team-spring-boot@agent-team-eval"

    @staticmethod
    def listing(**overrides: Any) -> str:
        entry: dict[str, Any] = {
            "id": PluginEnabledTest.PLUGIN,
            "version": "0.2.0",
            "enabled": True,
        }
        entry.update(overrides)
        return json.dumps([entry])

    def test_an_enabled_plugin_at_the_expected_version_passes(self) -> None:
        self.assertTrue(plugin_enabled(self.listing(), self.PLUGIN, "0.2.0"))

    def test_a_disabled_plugin_fails(self) -> None:
        self.assertFalse(
            plugin_enabled(self.listing(enabled=False), self.PLUGIN, "0.2.0")
        )

    def test_a_load_error_fails_even_when_enabled(self) -> None:
        self.assertFalse(
            plugin_enabled(
                self.listing(error="marketplace failed to load: cache-miss"),
                self.PLUGIN,
                "0.2.0",
            )
        )

    def test_a_version_mismatch_fails(self) -> None:
        self.assertFalse(plugin_enabled(self.listing(), self.PLUGIN, "0.3.0"))

    def test_an_absent_plugin_fails(self) -> None:
        self.assertFalse(plugin_enabled("[]", self.PLUGIN, "0.2.0"))

    def test_a_name_extending_the_target_never_matches(self) -> None:
        listing = json.dumps(
            [{"id": self.PLUGIN + "-x", "version": "0.2.0", "enabled": True}]
        )
        self.assertFalse(plugin_enabled(listing, self.PLUGIN, "0.2.0"))

    def test_unparseable_output_fails_closed(self) -> None:
        self.assertFalse(plugin_enabled("Installed plugins:", self.PLUGIN, "0.2.0"))

    def test_a_non_list_document_fails_closed(self) -> None:
        self.assertFalse(plugin_enabled('{"id": "x"}', self.PLUGIN, "0.2.0"))


class EnabledPluginIdsTest(unittest.TestCase):
    """The stowaway gate's enumeration over `claude plugin list --json`."""

    def test_only_enabled_entries_are_reported(self) -> None:
        listing = json.dumps(
            [
                {"id": "a@m", "enabled": True},
                {"id": "b@m", "enabled": False},
                {"id": "c@m"},
            ]
        )
        self.assertEqual(enabled_plugin_ids(listing), ("a@m",))

    def test_degraded_entries_are_skipped(self) -> None:
        listing = json.dumps([{"enabled": True}, "junk", {"id": 7, "enabled": True}])
        self.assertEqual(enabled_plugin_ids(listing), ())

    def test_unparseable_output_reads_as_empty(self) -> None:
        self.assertEqual(enabled_plugin_ids("Installed plugins:"), ())
        self.assertEqual(enabled_plugin_ids('{"id": "x"}'), ())


class InstalledPluginIdsTest(unittest.TestCase):
    """The pin pass's enumeration: every installed id, enabled or not."""

    def test_disabled_and_flagless_entries_are_reported(self) -> None:
        listing = json.dumps(
            [
                {"id": "a@m", "enabled": True},
                {"id": "b@m", "enabled": False},
                {"id": "c@m"},
            ]
        )
        self.assertEqual(installed_plugin_ids(listing), ("a@m", "b@m", "c@m"))

    def test_degraded_entries_are_skipped(self) -> None:
        listing = json.dumps([{"enabled": True}, "junk", {"id": 7}])
        self.assertEqual(installed_plugin_ids(listing), ())

    def test_unparseable_output_reads_as_empty(self) -> None:
        self.assertEqual(installed_plugin_ids("Installed plugins:"), ())
        self.assertEqual(installed_plugin_ids('{"id": "x"}'), ())


class UnpinnedEnabledTest(unittest.TestCase):
    """The leak gate's filter: enabled ids minus the version under test and
    the pinned set."""

    LISTING = json.dumps(
        [
            {"id": "sut@agent-team-eval", "enabled": True},
            {"id": "operator@agent-team", "enabled": True},
            {"id": "arrival@elsewhere", "enabled": True},
            {"id": "off@agent-team", "enabled": False},
        ]
    )

    def test_pre_install_read_yields_every_foreign_enabled_id(self) -> None:
        self.assertEqual(
            unpinned_enabled(self.LISTING, "sut@agent-team-eval", ()),
            ("operator@agent-team", "arrival@elsewhere"),
        )

    def test_post_install_read_reports_only_unpinned_arrivals(self) -> None:
        self.assertEqual(
            unpinned_enabled(
                self.LISTING, "sut@agent-team-eval", ("operator@agent-team",)
            ),
            ("arrival@elsewhere",),
        )

    def test_a_fully_pinned_listing_reports_no_leak(self) -> None:
        self.assertEqual(
            unpinned_enabled(
                self.LISTING,
                "sut@agent-team-eval",
                ("operator@agent-team", "arrival@elsewhere"),
            ),
            (),
        )


class WriteSessionPinsTest(unittest.TestCase):
    """The judge session root's plugin pins."""

    def test_every_id_lands_as_a_false_pin(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            write_session_pins(Path(root), ("a@m", "b@m"))
            settings = json.loads(
                (Path(root) / ".claude" / "settings.json").read_text(encoding="utf-8")
            )
        self.assertEqual(settings, {"enabledPlugins": {"a@m": False, "b@m": False}})

    def test_no_ids_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            write_session_pins(Path(root), ())
            self.assertFalse((Path(root) / ".claude").exists())


class FormatLedgerRecordTest(unittest.TestCase):
    """The live view's one-line rendering of an agent-authored ledger record."""

    def test_a_prd_entry_shows_author_type_and_title(self) -> None:
        line = format_ledger_record(
            {
                "type": "prd-entry",
                "author": "product-requirements-expert",
                "title": "Owner paging",
            }
        )
        self.assertEqual(line, "product-requirements-expert · prd-entry — Owner paging")

    def test_review_feedback_shows_verdict_and_finding_count(self) -> None:
        line = format_ledger_record(
            {
                "type": "review-feedback",
                "author": "test-reviewer",
                "verdict": "approve",
                "findings": [{}, {}],
            }
        )
        self.assertEqual(
            line, "test-reviewer · review-feedback — approve · 2 finding(s)"
        )

    def test_a_design_block_shows_verdict_and_effort_rating(self) -> None:
        line = format_ledger_record(
            {
                "type": "design-block",
                "author": "system-design-expert",
                "verdict": "covered",
                "implementation_effort": "routine",
            }
        )
        self.assertEqual(
            line, "system-design-expert · design-block — covered · routine"
        )

    def test_an_unrated_design_block_shows_the_verdict_alone(self) -> None:
        line = format_ledger_record(
            {
                "type": "design-block",
                "author": "system-design-expert",
                "verdict": "covered",
            }
        )
        self.assertEqual(line, "system-design-expert · design-block — covered")

    def test_escape_bytes_neutralize_and_whitespace_collapses(self) -> None:
        line = format_ledger_record(
            {
                "type": "design-block",
                "author": "a\x1b[2Jb",
                "verdict": "covered\nnew\tground",
            }
        )
        self.assertNotIn("\x1b", line)
        self.assertNotIn("\n", line)
        self.assertIn("covered new ground", line)

    def test_a_long_detail_truncates(self) -> None:
        line = format_ledger_record(
            {"type": "prd-entry", "author": "a", "title": "x" * 500}
        )
        self.assertLess(len(line), 140)
        self.assertTrue(line.endswith("…"))

    def test_an_unknown_type_still_names_author_and_type(self) -> None:
        line = format_ledger_record({"type": "novel-record", "author": "someone"})
        self.assertEqual(line, "someone · novel-record")

    def test_missing_fields_degrade_to_placeholders(self) -> None:
        self.assertEqual(format_ledger_record({}), "? · ?")

    def test_a_req_id_joins_the_line(self) -> None:
        line = format_ledger_record(
            {"type": "dispatch-start", "author": "a", "req_id": "REQ-OWN-005"}
        )
        self.assertEqual(line, "a · dispatch-start · REQ-OWN-005")

    def test_a_lone_surrogate_renders_printable_and_encodable(self) -> None:
        line = format_ledger_record(
            {"type": "prd-entry", "author": "\ud800", "title": "x"}
        )
        line.encode("utf-8")
        self.assertIn("\\ud800", line)

    def test_cursor_control_and_bidi_characters_render_escaped(self) -> None:
        line = format_ledger_record(
            {"type": "design-block", "author": "a", "verdict": "no\x08\x8d\u202eok"}
        )
        for ch in ("\x08", "\x8d", "\u202e"):
            self.assertNotIn(ch, line)
        self.assertIn("\\u0008", line)
        self.assertIn("\\u202e", line)

    def test_an_oversized_author_cannot_flood_the_line(self) -> None:
        line = format_ledger_record({"type": "prd-entry", "author": "a" * 100_000})
        self.assertLessEqual(len(line), 160)
        self.assertTrue(line.endswith("…"))

    def test_a_boolean_retry_is_not_a_retry_count(self) -> None:
        line = format_ledger_record(
            {
                "type": "build-failure",
                "author": "a",
                "failed_check": "test",
                "retry": True,
            }
        )
        self.assertEqual(line, "a · build-failure — test")


class LedgerTailTest(unittest.TestCase):
    """The live view's incremental ledger reader: each record prints once,
    partial lines wait for their newline, and the collection cap stops it."""

    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.ledger = self.dir / "handoff.jsonl"
        self.tail = LedgerTail(self.ledger)

    def append(self, text: str) -> None:
        with self.ledger.open("a", encoding="utf-8") as fh:
            fh.write(text)

    def test_a_missing_ledger_yields_nothing(self) -> None:
        self.assertEqual(self.tail.poll(), [])

    def test_each_record_prints_once_across_polls(self) -> None:
        self.append('{"type": "dispatch-start", "author": "a"}\n')
        self.assertEqual(self.tail.poll(), ["a · dispatch-start"])
        self.assertEqual(self.tail.poll(), [])

    def test_an_implementer_dispatch_carries_the_tier_note(self) -> None:
        # The note comes from the workspace's own router derivation; a stub
        # handoff.py stands in for it here.
        ws = self.dir / "ws"
        (ws / "scripts").mkdir(parents=True)
        (ws / ".scratch").mkdir()
        (ws / "scripts" / "handoff.py").write_text(
            "import json\n"
            'print(json.dumps({"agent": "feature-implementer-routine",'
            ' "reason": "fix-round:all-autofix"}))\n'
        )
        ledger = ws / ".scratch" / "handoff.jsonl"
        ledger.write_text(
            '{"type": "dispatch-start", "author": "feature-implementer",'
            ' "req_id": "REQ-A-001"}\n'
        )
        lines = LedgerTail(ledger).poll()
        self.assertEqual(
            lines,
            [
                "feature-implementer · dispatch-start · REQ-A-001"
                " — tier: routine (fix-round:all-autofix)"
            ],
        )

    def test_a_failed_tier_derivation_renders_the_plain_line(self) -> None:
        # No scripts/handoff.py behind this ledger: the note degrades to
        # nothing, the line still prints.
        self.append(
            '{"type": "dispatch-start", "author": "feature-implementer",'
            ' "req_id": "REQ-A-001"}\n'
        )
        self.assertEqual(
            self.tail.poll(), ["feature-implementer · dispatch-start · REQ-A-001"]
        )
        self.append('{"type": "build-pass", "author": "b", "gate_checks_run": ["t"]}\n')
        self.assertEqual(self.tail.poll(), ["b · build-pass — 1 check(s) green"])

    def test_a_partial_line_waits_for_its_newline(self) -> None:
        self.append('{"type": "dispatch-start", "author": "a"')
        self.assertEqual(self.tail.poll(), [])
        self.append("}\n")
        self.assertEqual(self.tail.poll(), ["a · dispatch-start"])

    def test_malformed_lines_are_skipped(self) -> None:
        self.append('not json\n{"type": "dispatch-start", "author": "a"}\n[1]\n')
        self.assertEqual(self.tail.poll(), ["a · dispatch-start"])

    def test_a_ledger_over_the_collection_cap_stops_the_view(self) -> None:
        self.append('{"type": "dispatch-start", "author": "a"}\n')
        self.assertEqual(len(self.tail.poll()), 1)
        self.append("x" * (MAX_LEDGER_BYTES + 1) + "\n")
        notice = self.tail.poll()
        self.assertEqual(len(notice), 1)
        self.assertIn("live view stopped", notice[0])
        self.append('{"type": "dispatch-start", "author": "b"}\n')
        self.assertEqual(self.tail.poll(), [])

    def test_a_truncated_ledger_restarts_the_tail(self) -> None:
        self.append('{"type": "dispatch-start", "author": "alpha"}\n')
        self.assertEqual(len(self.tail.poll()), 1)
        # A .scratch wipe recreates the ledger smaller; size below the offset
        # is the restart signal. An equal-size rewrite is undetectable.
        self.ledger.write_text('{"type": "dispatch-start", "author": "b"}\n')
        self.assertEqual(self.tail.poll(), ["b · dispatch-start"])

    def test_deeply_nested_json_is_skipped_not_raised(self) -> None:
        self.append("[" * 200_000 + "\n")
        self.append('{"type": "dispatch-start", "author": "a"}\n')
        self.assertEqual(self.tail.poll(), ["a · dispatch-start"])

    def test_a_record_flood_collapses_to_the_per_poll_cap(self) -> None:
        for index in range(LIVE_MAX_LINES_PER_POLL + 10):
            self.append(f'{{"type": "dispatch-start", "author": "a{index}"}}\n')
        lines = self.tail.poll()
        self.assertEqual(len(lines), LIVE_MAX_LINES_PER_POLL + 1)
        self.assertEqual(lines[-1], "(+10 more record(s) this poll)")


class ParseJsonObjectTest(unittest.TestCase):
    def test_a_fenced_object_parses(self) -> None:
        parsed = parse_json_object('```json\n{"design_fit": 4}\n```')
        self.assertEqual(parsed, {"design_fit": 4})

    def test_an_object_inside_noise_parses(self) -> None:
        parsed = parse_json_object('Verdict follows: {"a": 1} — done.')
        self.assertEqual(parsed, {"a": 1})

    def test_text_without_an_object_returns_none(self) -> None:
        self.assertIsNone(parse_json_object("no json here"))


class ScrubTest(unittest.TestCase):
    """Host identity never reaches a committed run folder as text."""

    def test_every_host_prefix_rewrites_to_its_label(self) -> None:
        scratch, repo, home = (prefix for prefix, _label in SCRUB_PREFIXES)
        out = scrub(
            f"src {scratch}/marketplace-src repo {repo}/evals home {home}/.claude"
        )
        self.assertIn("<scratch>/marketplace-src", out)
        self.assertIn("<repo>/evals", out)
        self.assertIn("~/.claude", out)
        for prefix, _label in SCRUB_PREFIXES:
            self.assertNotIn(prefix, out)

    def test_the_login_name_is_scrubbed_on_word_boundaries(self) -> None:
        if run_eval.LOGIN_RE is None:
            self.skipTest("no usable login name in this environment")
        self.assertEqual(
            scrub(f"started by {LOGIN_NAME} in dir"), "started by <user> in dir"
        )
        embedded = f"x{LOGIN_NAME}x"
        self.assertEqual(scrub(embedded), embedded)

    def test_neutral_text_passes_unchanged(self) -> None:
        self.assertEqual(scrub("BUILD SUCCESSFUL (61s)"), "BUILD SUCCESSFUL (61s)")


class LoginRegexTest(unittest.TestCase):
    def test_a_distinctive_login_matches_case_insensitively(self) -> None:
        pattern = run_eval.login_regex("bw")
        assert pattern is not None
        self.assertTrue(pattern.search("started by BW in"))
        self.assertIsNone(pattern.search("xbwx"))

    def test_common_word_and_short_logins_yield_no_pattern(self) -> None:
        self.assertIsNone(run_eval.login_regex("build"))
        self.assertIsNone(run_eval.login_regex("Test"))
        self.assertIsNone(run_eval.login_regex("x"))
        self.assertIsNone(run_eval.login_regex(""))


class ListingDigestTest(unittest.TestCase):
    """The run log's plugin listing carries no operator-machine facts."""

    QUALIFIED = "agent-team-spring-boot@agent-team-eval"
    LISTING = json.dumps(
        [
            {
                "id": "agent-team-spring-boot@agent-team-eval",
                "version": "0.2.0",
                "enabled": True,
                "loadError": None,
                "installPath": "/Users/someone/.claude/plugins/cache/x",
                "installedAt": "2026-08-03T14:40:12.961Z",
                "lastUpdated": "2026-08-03T14:40:12.961Z",
            },
            {
                "id": "agent-team-spring-boot@agent-team",
                "version": "0.2.0",
                "enabled": False,
                "installPath": "/Users/someone/.claude/plugins/cache/y",
            },
        ]
    )

    def test_the_version_under_test_keeps_its_verdict_facts(self) -> None:
        digest = listing_digest(self.LISTING, self.QUALIFIED)
        self.assertIn(self.QUALIFIED, digest)
        self.assertIn('"version": "0.2.0"', digest)
        self.assertIn('"loadError": null', digest)

    def test_machine_facts_and_operator_ids_never_appear(self) -> None:
        digest = listing_digest(self.LISTING, self.QUALIFIED)
        self.assertNotIn("installPath", digest)
        self.assertNotIn("installedAt", digest)
        self.assertNotIn("lastUpdated", digest)
        self.assertNotIn('agent-team-spring-boot@agent-team"', digest)
        self.assertIn("1 other installed plugin(s)", digest)

    def test_unparseable_output_reads_as_such(self) -> None:
        self.assertEqual(
            listing_digest("Installed plugins:", self.QUALIFIED),
            "(no parseable plugin entries)",
        )


class LeakScanTest(unittest.TestCase):
    """The gate behind the scrub: a surviving host token fails the folder."""

    def setUp(self) -> None:
        self.out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out_dir, ignore_errors=True)

    def test_a_clean_folder_scans_empty(self) -> None:
        (self.out_dir / "run.log").write_text(
            "=== setup.sh <scratch>/work ===\nstarted by <user> in <scratch>/work\n"
        )
        self.assertEqual(leak_scan(self.out_dir), [])

    def test_hits_report_the_label_never_the_leaking_value(self) -> None:
        repo = SCRUB_PREFIXES[1][0]
        (self.out_dir / "result.json").write_text(f'{{"error": "{repo}/evals"}}')
        hits = leak_scan(self.out_dir)
        self.assertIn("result.json: <repo>", hits)
        self.assertNotIn(repo, json.dumps(hits))

    def test_the_login_name_is_a_hit_on_its_own(self) -> None:
        if run_eval.LOGIN_RE is None:
            self.skipTest("no usable login name in this environment")
        (self.out_dir / "run.log").write_text(f"started by {LOGIN_NAME} in <scratch>\n")
        self.assertEqual(leak_scan(self.out_dir), ["run.log: login name"])

    def test_a_case_variant_host_prefix_is_still_a_hit(self) -> None:
        repo = SCRUB_PREFIXES[1][0]
        (self.out_dir / "run.log").write_text(f"path {repo.upper()}/evals\n")
        self.assertIn("run.log: <repo>", leak_scan(self.out_dir))

    def test_plugin_machine_fact_keys_are_hits(self) -> None:
        (self.out_dir / "run.log").write_text('{"installPath": "x"}\n')
        self.assertEqual(
            leak_scan(self.out_dir),
            ['run.log: plugin machine fact "installPath"'],
        )

    def test_a_non_utc_timestamp_is_a_hit_and_utc_is_not(self) -> None:
        (self.out_dir / "ok.log").write_text(
            "2026-08-03T14:40:11+00:00 and 2026-08-03T14:40:43.968Z\n"
        )
        self.assertEqual(leak_scan(self.out_dir), [])
        (self.out_dir / "run.log").write_text("2026-08-03T16:40:30.845+02:00\n")
        self.assertEqual(leak_scan(self.out_dir), ["run.log: non-UTC timestamp"])

    def test_a_time_of_day_range_is_not_a_hit(self) -> None:
        # Reviewer prose citing an mtime range: the second time reads as a
        # zone offset without the right boundary. A quarantined v0.2.1 rep
        # hit exactly this shape.
        (self.out_dir / "handoff.jsonl").write_text(
            '{"note": "all mtimes fall in the 00:47:43-00:51:08 range"}\n'
        )
        self.assertEqual(leak_scan(self.out_dir), [])

    def test_a_stamp_from_the_suts_own_history_is_not_a_hit(self) -> None:
        # Git renders the offset stored in the commit object, so an agent
        # quoting a commit date emits public repo data, not the host clock.
        (self.out_dir / "handoff.jsonl").write_text(
            '{"note": "last doc commit 2026-08-03T16:36:18+02:00"}\n'
        )
        self.assertEqual(leak_scan(self.out_dir, frozenset({"16:36:18+02:00"})), [])

    def test_an_exempt_stamp_does_not_excuse_a_different_one(self) -> None:
        (self.out_dir / "handoff.jsonl").write_text(
            "commit 2026-08-03T16:36:18+02:00 and host 2026-08-03T19:04:02+02:00\n"
        )
        self.assertEqual(
            leak_scan(self.out_dir, frozenset({"16:36:18+02:00"})),
            ["handoff.jsonl: non-UTC timestamp"],
        )


class CommitBaselineTest(unittest.TestCase):
    """The runner's own commit carries no host zone: an agent quoting its
    date must emit a UTC stamp, or the leak gate would read the host clock."""

    def test_the_baseline_commit_is_stamped_utc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            subprocess.run(["git", "init", "-q", str(workdir)], check=True)
            (workdir / "f").write_text("x")
            with mock.patch.dict(os.environ, {"TZ": "Europe/Vienna"}):
                sha = commit_baseline(workdir)
            log = subprocess.run(
                ["git", "-C", str(workdir), "log", "-1", "--format=%aI %cI", sha],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
            self.assertEqual(len(log), 2)
            for stamp in log:
                self.assertTrue(stamp.endswith(("Z", "+00:00")), stamp)


class RescueUtcTest(unittest.TestCase):
    """A leak-gated folder whose only host identity is the runner's own
    host-zoned baseline stamp comes back with the stamps in UTC."""

    def folder(self, ledger: str, **result: Any) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        folder = tmp / "2026-08-27-visit-edit-r2-T192417"
        folder.mkdir()
        (folder / "handoff.jsonl").write_text(ledger)
        (folder / "manifest.json").write_text("{}")
        payload: dict[str, Any] = {
            "status": "leak",
            "leaks": ["handoff.jsonl: non-UTC timestamp"],
            "run": "2026-08-27-visit-edit-r2",
        }
        payload.update(result)
        (folder / "result.json").write_text(json.dumps(payload))
        return folder

    def test_a_stamp_keeps_its_instant_in_utc(self) -> None:
        self.assertEqual(utc_stamp("2026-08-27T19:24:23+02:00"), "2026-08-27T17:24:23Z")

    def test_the_rescue_normalizes_and_clears_the_leak(self) -> None:
        folder = self.folder(
            '{"note": "after the last commit (2026-08-27T19:24:23+02:00)"}\n'
        )
        repairs = rescue_utc(folder)
        self.assertEqual(
            repairs, ["handoff.jsonl: 1 non-UTC stamp(s) normalized to UTC"]
        )
        self.assertIn("2026-08-27T17:24:23Z", (folder / "handoff.jsonl").read_text())
        result = json.loads((folder / "result.json").read_text())
        self.assertEqual(result["status"], "complete")
        self.assertNotIn("leaks", result)
        self.assertEqual(result["repairs"], repairs)
        self.assertEqual(leak_scan(folder), [])

    def test_another_leak_refuses(self) -> None:
        folder = self.folder("{}\n", leaks=["run.log: login name"])
        with self.assertRaises(ValueError):
            rescue_utc(folder)

    def test_a_dateless_stamp_refuses(self) -> None:
        folder = self.folder('{"note": "at 19:24:23+02:00"}\n')
        with self.assertRaises(ValueError):
            rescue_utc(folder)


class SutCommitStampsTest(unittest.TestCase):
    """The SUT's own offsets, which the timestamp gate must not read as host
    identity. `TZ=UTC` cannot normalize them: git renders the offset stored
    in the commit object."""

    def a_repo_committed_at(self, offset: str) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        workdir = Path(holder.name)
        git = ["git", "-C", str(workdir)]
        subprocess.run(git + ["init", "--quiet"], check=True)
        (workdir / "doc.md").write_text("brief\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(
            git
            + [
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@localhost",
                "commit",
                "--quiet",
                "-m",
                "baseline",
                f"--date=2026-08-03T16:36:18{offset}",
            ],
            check=True,
            env={**os.environ, "GIT_COMMITTER_DATE": f"2026-08-03T16:36:18{offset}"},
        )
        return workdir

    def test_a_stored_offset_is_collected(self) -> None:
        stamps = sut_commit_stamps(self.a_repo_committed_at("+02:00"))
        self.assertEqual(stamps, frozenset({"16:36:18+02:00"}))

    def test_tz_utc_does_not_normalize_a_stored_offset(self) -> None:
        workdir = self.a_repo_committed_at("+02:00")
        os.environ["TZ"] = "UTC"
        self.addCleanup(os.environ.pop, "TZ", None)
        self.assertEqual(sut_commit_stamps(workdir), frozenset({"16:36:18+02:00"}))

    def test_a_utc_history_collects_nothing(self) -> None:
        self.assertEqual(
            sut_commit_stamps(self.a_repo_committed_at("+00:00")), frozenset()
        )

    def test_a_missing_repo_yields_no_exemptions(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.assertEqual(sut_commit_stamps(Path(holder.name)), frozenset())


class RecordedSutStampsTest(unittest.TestCase):
    """The bridge to the offline re-scan: `--leak-scan` runs from the
    committed tree with no SUT clone, so the folder records its own
    exemptions."""

    def setUp(self) -> None:
        self.out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out_dir, ignore_errors=True)

    def test_only_stamps_the_folder_quotes_are_recorded(self) -> None:
        (self.out_dir / "handoff.jsonl").write_text(
            "last doc commit 2026-08-03T16:36:18+02:00\n"
        )
        quoted = quoted_sut_stamps(
            self.out_dir, frozenset({"16:36:18+02:00", "09:54:30-03:00"})
        )
        self.assertEqual(quoted, ["16:36:18+02:00"])

    def test_a_host_stamp_is_never_recorded_as_exempt(self) -> None:
        (self.out_dir / "run.log").write_text("2026-08-03T19:04:02+02:00\n")
        self.assertEqual(quoted_sut_stamps(self.out_dir, frozenset()), [])

    def test_the_recorded_list_round_trips_through_result_json(self) -> None:
        (self.out_dir / "result.json").write_text(
            json.dumps({"sut_quoted_stamps": ["16:36:18+02:00"]})
        )
        self.assertEqual(
            recorded_sut_stamps(self.out_dir), frozenset({"16:36:18+02:00"})
        )

    def test_a_folder_with_no_record_gates_at_full_strength(self) -> None:
        self.assertEqual(recorded_sut_stamps(self.out_dir), frozenset())
        (self.out_dir / "result.json").write_text('{"status": "complete"}')
        self.assertEqual(recorded_sut_stamps(self.out_dir), frozenset())

    def test_a_malformed_record_gates_at_full_strength(self) -> None:
        (self.out_dir / "result.json").write_text('{"sut_quoted_stamps": "not a list"}')
        self.assertEqual(recorded_sut_stamps(self.out_dir), frozenset())
        (self.out_dir / "result.json").write_text("{ broken")
        self.assertEqual(recorded_sut_stamps(self.out_dir), frozenset())


class EgressRecordFilterTest(unittest.TestCase):
    """Only the proxy's per-request access records reach the run folder."""

    def test_access_records_match_and_startup_narration_never_does(self) -> None:
        access = (
            "2026-08-03T14:40:43.968534338Z 1785768043.968    216 172.18.0.2 "
            "TCP_TUNNEL/200 4006 CONNECT api.anthropic.com:443 - HIER_DIRECT/1.2.3.4 -"
        )
        denied = (
            "2026-08-03T14:41:00.000000000Z 1785768060.000      0 172.18.0.2 "
            "TCP_DENIED/403 3928 GET http://example.com/ - HIER_NONE/- text/html"
        )
        startup = (
            "2026-08-03T14:40:43.289933546Z 2026/08/03 14:40:43| Starting Squid "
            "Cache version 6.13 for aarch64-unknown-linux-gnu..."
        )
        self.assertTrue(run_eval.EGRESS_RECORD_RE.search(access))
        self.assertTrue(run_eval.EGRESS_RECORD_RE.search(denied))
        self.assertFalse(run_eval.EGRESS_RECORD_RE.search(startup))


class SeedIntakeTest(unittest.TestCase):
    """The headless intake front door: prep seeds one intake-decision from the
    task manifest when the installed version ships the record's schema, and
    skips silently when it does not — backfill arms route exactly as before."""

    def _workspace(self, with_schema: bool = True) -> Path:
        ws = Path(tempfile.mkdtemp(prefix="seed-intake-"))
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        core = run_eval.REPO / "harness" / "core"
        shutil.copytree(core / "scripts", ws / "scripts")
        shutil.copytree(core / "schemas", ws / "schemas")
        if not with_schema:
            (ws / "schemas" / "scratch" / "intake-decision.schema.json").unlink()
        return ws

    def test_every_task_seeds_a_schema_valid_record(self) -> None:
        # Covers the req_id minting for every real task id: append validates
        # the record (pattern included), so a bad mint fails the seed.
        log = Path(tempfile.mkdtemp(prefix="seed-log-")) / "run.log"
        self.addCleanup(shutil.rmtree, log.parent, ignore_errors=True)
        for task in run_eval.load_tasks().values():
            ws = self._workspace()
            note = run_eval.seed_intake(task, ws, log)
            self.assertIsNotNone(note, task.id)
            line = (ws / ".scratch" / "handoff.jsonl").read_text().strip()
            record = json.loads(line)
            self.assertEqual(record["author"], "human")
            self.assertEqual(record["source"], "task-prompt")
            self.assertEqual(record["request"], task.prompt)
            self.assertEqual(tuple(record["decisions"]), task.decisions)

    def test_a_seeded_workspace_routes_intake_ready(self) -> None:
        ws = self._workspace()
        log = ws / "run.log"
        task = run_eval.load_tasks()["visit-edit"]
        run_eval.seed_intake(task, ws, log)
        proc = subprocess.run(
            ["python3", "scripts/handoff.py", "route"],
            cwd=ws,
            capture_output=True,
            text=True,
        )
        decision = json.loads(proc.stdout)
        self.assertEqual(decision["rule"], "intake-ready")
        self.assertEqual(decision["next"], ["product-requirements-expert"])

    def test_a_version_without_the_schema_is_not_seeded(self) -> None:
        ws = self._workspace(with_schema=False)
        log = ws / "run.log"
        task = run_eval.load_tasks()["visit-edit"]
        self.assertIsNone(run_eval.seed_intake(task, ws, log))
        self.assertFalse((ws / ".scratch" / "handoff.jsonl").exists())

    def test_decision_clauses_are_verbatim_prompt_quotes(self) -> None:
        # The loader enforces the quote contract; this pins it for the
        # committed manifests, refusal task included (it declares none).
        tasks = run_eval.load_tasks()
        for task in tasks.values():
            for clause in task.decisions:
                self.assertIn(clause, task.prompt, task.id)
        self.assertEqual(tasks["visit-cancel"].decisions, ())


class EraContractTest(unittest.TestCase):
    def _src(self, root: Path) -> Path:
        stack = root / "src" / "harness" / "init" / "stacks" / "java-spring-boot"
        (stack / "scripts").mkdir(parents=True)
        (stack / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}\n",
            encoding="utf-8",
        )
        (stack / "scripts" / "layout.toml").write_text(
            'test = ["src/test/**"]\n', encoding="utf-8"
        )
        return root / "src"

    def test_replaces_both_files_and_fills_the_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = self._src(root)
            workdir = root / "work"
            (workdir / "scripts").mkdir(parents=True)
            (workdir / "CLAUDE.md").write_text("newer-era rules", encoding="utf-8")
            (workdir / "scripts" / "layout.toml").write_text(
                'from = "gradle"\n', encoding="utf-8"
            )
            notes = era_project_contract(workdir, src, root / "run.log")
            rules = (workdir / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("spring-petclinic: the Spring PetClinic", rules)
            self.assertNotIn("{{PROJECT_NAME}}", rules)
            self.assertIn("## Harness Channel", rules)
            self.assertIn("read-only plugin cache", rules)
            self.assertIn("## Pipeline Entry", rules)
            self.assertIn("pipeline-coordinator", rules)
            self.assertEqual(
                (workdir / "scripts" / "layout.toml").read_text(encoding="utf-8"),
                'test = ["src/test/**"]\n',
            )
            self.assertEqual(len(notes), 2)
            for note in notes:
                self.assertIn("era contract", note)
            self.assertIn("channel chapter", notes[0])

    def test_a_version_source_without_skeletons_fails_loud(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "work").mkdir()
            with self.assertRaises(RuntimeError):
                era_project_contract(root / "work", root / "src", root / "run.log")


class EraRootModelTest(unittest.TestCase):
    def _src(self, root: Path, frontmatter: str) -> Path:
        agents = root / "src" / "plugins" / "spring-boot-claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "feature-implementer.md").write_text(frontmatter, encoding="utf-8")
        return root / "src"

    def test_the_root_pin_reads_from_the_implementer_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = self._src(
                Path(tmp),
                "---\nname: feature-implementer\nmodel: claude-opus-4-8\n---\nbody\n",
            )
            self.assertEqual(
                era_root_model(src, "spring-boot-claude"), "claude-opus-4-8"
            )

    def test_a_model_mention_in_the_body_never_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = self._src(
                Path(tmp), "---\nname: feature-implementer\n---\nmodel: claude-x\n"
            )
            with self.assertRaises(RuntimeError):
                era_root_model(src, "spring-boot-claude")

    def test_a_source_without_a_pin_fails_loud(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "src").mkdir()
            with self.assertRaises(RuntimeError):
                era_root_model(Path(tmp) / "src", "spring-boot-claude")


class AgentClaudeArgsTest(unittest.TestCase):
    def test_the_frozen_prompt_passes_verbatim(self) -> None:
        args = agent_claude_args("fix the bug", "opus", True, False)
        self.assertEqual(args[:2], ["-p", "fix the bug"])
        self.assertIn("--dangerously-skip-permissions", args)
        self.assertNotIn("--append-system-prompt", args)

    def test_the_era_entry_arm_appends_the_system_prompt(self) -> None:
        args = agent_claude_args("fix the bug", "opus", True, True)
        i = args.index("--append-system-prompt")
        self.assertEqual(args[i + 1], run_eval.ERA_ENTRY_PROMPT)
        self.assertIn("pipeline-coordinator", args[i + 1])
        self.assertEqual(args[:2], ["-p", "fix the bug"])


class NoPipelineRunTest(unittest.TestCase):
    def test_a_complete_run_with_an_empty_ledger_trips_the_gate(self) -> None:
        self.assertTrue(no_pipeline_run("complete", 0, False, "feature"))

    def test_a_run_with_ledger_records_never_trips(self) -> None:
        self.assertFalse(no_pipeline_run("complete", 19, False, "feature"))

    def test_a_non_complete_run_keeps_its_own_status(self) -> None:
        self.assertFalse(no_pipeline_run("timeout", 0, False, "feature"))

    def test_an_oversize_ledger_reads_as_a_pipeline_run(self) -> None:
        self.assertFalse(no_pipeline_run("complete", 0, True, "feature"))

    def test_a_correct_refusal_may_write_no_record(self) -> None:
        self.assertFalse(no_pipeline_run("complete", 0, False, "refusal"))


class AttemptNameTest(unittest.TestCase):
    def test_the_attempt_suffixes_the_run_name_with_time_of_day(self) -> None:
        now = datetime.datetime(2026, 8, 22, 14, 32, 7)
        self.assertEqual(
            attempt_name("2026-08-22-owners-page-param-r2", now),
            "2026-08-22-owners-page-param-r2-T143207",
        )

    def test_two_attempts_at_one_cell_get_distinct_names(self) -> None:
        a = datetime.datetime(2026, 8, 22, 14, 32, 7)
        b = datetime.datetime(2026, 8, 22, 15, 1, 44)
        run = "2026-08-22-visit-edit-r1"
        self.assertNotEqual(attempt_name(run, a), attempt_name(run, b))


class NextRepTest(unittest.TestCase):
    def test_existing_reps_count_toward_the_next_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vdir = Path(tmp) / "v0.1.1"
            (vdir / "2026-08-05-visit-edit-r1").mkdir(parents=True)
            (vdir / "2026-08-22-visit-edit-r2").mkdir()
            self.assertEqual(next_rep("v0.1.1", "visit-edit", Path(tmp)), 3)

    def test_other_tasks_and_stray_folders_never_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vdir = Path(tmp) / "v0.1.1"
            (vdir / "2026-08-05-owners-page-param-r4").mkdir(parents=True)
            (vdir / "notes").mkdir()
            self.assertEqual(next_rep("v0.1.1", "visit-edit", Path(tmp)), 1)

    def test_a_missing_version_dir_starts_at_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(next_rep("v9.9.9", "visit-edit", Path(tmp)), 1)


class SliceAbandonedTest(unittest.TestCase):
    def _out_dir(self, root: Path, types: list[str]) -> Path:
        out = root / "out"
        out.mkdir()
        lines = [json.dumps({"type": t}) for t in types]
        (out / "handoff.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    def test_a_ledger_ending_on_dispatch_start_is_abandoned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(
                Path(tmp), ["prd-entry", "design-block", "dispatch-start"]
            )
            self.assertTrue(slice_abandoned(out, "feature", "complete"))

    def test_a_substantive_final_record_is_never_abandonment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(Path(tmp), ["dispatch-start", "build-pass"])
            self.assertFalse(slice_abandoned(out, "feature", "complete"))

    def test_a_refusal_task_never_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(Path(tmp), ["dispatch-start"])
            self.assertFalse(slice_abandoned(out, "refusal", "complete"))

    def test_a_non_complete_run_keeps_its_own_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(Path(tmp), ["dispatch-start"])
            self.assertFalse(slice_abandoned(out, "feature", "timeout"))


class PipelineIncompleteTest(unittest.TestCase):
    def _out_dir(self, root: Path, records: list[dict[str, Any]]) -> Path:
        out = root / "out"
        out.mkdir()
        lines = [json.dumps(r) for r in records]
        (out / "handoff.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    @staticmethod
    def _review(author: str, verdict: str, req: str = "REQ-1") -> dict[str, Any]:
        return {
            "type": "review-feedback",
            "req_id": req,
            "author": author,
            "verdict": verdict,
        }

    def test_a_build_with_no_review_record_trips_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(
                Path(tmp), [{"type": "dispatch-start"}, {"type": "build-pass"}]
            )
            self.assertEqual(
                pipeline_incomplete(out, "feature", "complete"),
                "built but never reviewed",
            )

    def test_an_unresolved_final_verdict_trips_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(
                Path(tmp),
                [
                    {"type": "build-pass"},
                    self._review("security-reviewer", "approved"),
                    self._review("test-reviewer", "changes_requested"),
                ],
            )
            reason = pipeline_incomplete(out, "feature", "complete")
            self.assertEqual(reason, "review cycle unconverged: test-reviewer")

    def test_a_fix_round_that_converges_never_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(
                Path(tmp),
                [
                    {"type": "build-pass"},
                    self._review("test-reviewer", "changes_requested"),
                    {"type": "build-pass"},
                    self._review("test-reviewer", "approved"),
                ],
            )
            self.assertIsNone(pipeline_incomplete(out, "feature", "complete"))

    def test_a_run_that_never_built_is_recorded_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(
                Path(tmp),
                [
                    {"type": "dispatch-start"},
                    self._review("test-reviewer", "changes_requested"),
                ],
            )
            self.assertIsNone(pipeline_incomplete(out, "feature", "complete"))

    def test_implementation_evidence_counts_as_built(self) -> None:
        # A rep can change src and pass its oracle without appending
        # build-pass; the implemented flag closes that ledger gap.
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(Path(tmp), [{"type": "dispatch-start"}])
            self.assertEqual(
                pipeline_incomplete(out, "feature", "complete", implemented=True),
                "built but never reviewed",
            )

    def test_a_refusal_task_reviews_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(Path(tmp), [{"type": "build-pass"}])
            self.assertIsNone(pipeline_incomplete(out, "refusal", "complete"))

    def test_a_non_complete_run_keeps_its_own_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._out_dir(Path(tmp), [{"type": "build-pass"}])
            self.assertIsNone(pipeline_incomplete(out, "feature", "timeout"))


if __name__ == "__main__":
    unittest.main()
