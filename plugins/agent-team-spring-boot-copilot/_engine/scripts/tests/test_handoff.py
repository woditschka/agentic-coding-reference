#!/usr/bin/env python3
"""The handoff command line: wiring, exit codes, output channels, and the rules the root still holds."""

import concurrent.futures
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import accounting

from tests.support import (
    _HERE,
    _REPO_SCHEMAS,
    GOLDEN_RECORDS,
    SOME_REQ_ID,
    SOME_TS,
    HandoffCase,
    RouteCase,
    a_record,
    a_slice_record,
    entry,
)


class TestAppendCanonicalForm(HandoffCase):
    def test_reports_appended_line_number(self):
        _, out, _ = self.append(a_record())
        self.assertEqual(out, "appended test-rec at line 1\n")
        _, out, _ = self.append(a_record())
        self.assertEqual(out, "appended test-rec at line 2\n")

    def test_overwrites_supplied_ts(self):
        code, _, err = self.append(a_record(ts="2020-01-01T00:00:00Z"))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.log_lines()[0])["ts"], SOME_TS)

    def test_a_supplied_bad_timestamp_is_overwritten_before_validation(self):
        code, _, err = self.append(a_record(ts="yesterday"))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.log_lines()[0])["ts"], SOME_TS)

    def test_fills_missing_ts(self):
        record = a_record()
        del record["ts"]
        code, _, err = self.append(record)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.log_lines()[0])["ts"], SOME_TS)

    def test_append_onto_truncated_tail_warns_and_lands_glued(self):
        # No pre-write repair: a reader cannot tell crash damage from a
        # concurrent write still landing (ADR 2026-08-16
        # lock-free-ledger-appends). The append lands on the damaged line,
        # warns, and validate blocks the log until it is repaired.
        self.log.write_text(json.dumps(a_record()))  # no trailing newline
        code, out, err = self.append(a_record(note="second"))
        self.assertEqual(code, 0)
        self.assertIn("truncated", err)
        self.assertIn("at line 1", out)  # the glued line is line 1
        self.assertEqual(len(self.log_lines()), 1)
        code, _, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)


class TestReviewFeedbackAnchor(HandoffCase):
    """The review-anchor gate reaches append: the refusal names the fix and lands nothing."""

    def _feedback(self):
        return {
            "type": "review-feedback",
            "req_id": SOME_REQ_ID,
            "author": "test-reviewer",
            "verdict": "approved",
            "findings": [],
        }

    def _build_pass(self):
        return a_record(
            "build-pass", author="feature-implementer", gate_checks_run=["build"]
        )

    def _start(self):
        return a_record("dispatch-start", author="test-reviewer", responding_to=[1])

    def test_a_re_review_without_its_dispatch_start_is_refused(self):
        self.write_log(self._build_pass(), self._start(), self._build_pass())
        code, _, err = self.append(self._feedback(), schemas=_REPO_SCHEMAS)
        self.assertEqual(code, 1)
        self.assertIn("no dispatch-start since the build-pass at line 3", err)
        self.assertEqual(len(self.log_lines()), 3)


class TestDesignSyncGate(HandoffCase):
    """The design-sync gate reaches append: a malformed line in the log is skipped on the way."""

    def _build_pass(self):
        return {
            "type": "build-pass",
            "req_id": SOME_REQ_ID,
            "author": "feature-implementer",
            "gate_checks_run": ["build"],
        }

    def _prd_response(self):
        return a_record(
            "consultation-response",
            author="product-requirements-expert",
            in_response_to=1,
            answer="answered",
            memory_updates=[{"path": "docs/prd.md", "summary": "edge case 5 added"}],
        )

    def test_a_prd_change_with_no_design_answer_is_refused(self):
        self.write_log(self._prd_response())
        with open(self.log, "a", encoding="utf-8") as handle:
            handle.write("not json\n")
        code, _, err = self.append(self._build_pass(), schemas=_REPO_SCHEMAS)
        self.assertEqual(code, 1)
        self.assertIn("consultation-response at line 1, which changed docs/prd.md", err)
        self.assertEqual(len(self.log_lines()), 2)


class TestAppendValidation(HandoffCase):
    def test_rejects_type_argument_mismatch(self):
        code, _, err = self.append(a_record(), rtype="strict-rec")
        self.assertEqual(code, 1)
        self.assertIn("does not match", err)

    def test_rejects_unknown_record_type(self):
        code, _, err = self.append({"type": "nope"}, rtype="nope")
        self.assertEqual(code, 1)
        self.assertIn("known types", err)
        self.assertIn("test-rec", err)

    def test_rejects_non_object_record(self):
        code, _, err = self.run_cli(
            "append",
            "test-rec",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            stdin="[1, 2]",
        )
        self.assertEqual(code, 1)
        self.assertIn("JSON object", err)


class TestHardening(HandoffCase):
    def test_nan_rejected_on_stdin(self):
        code, _, err = self.run_cli(
            "append",
            "test-rec",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            stdin='{"type": "test-rec", "extra": NaN}',
        )
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", err)
        self.assertFalse(self.log.exists())

    def test_next_retry_warns_above_schema_maximum(self):
        retry_schema = {
            "type": "object",
            "properties": {"retry": {"type": "integer", "minimum": 1, "maximum": 3}},
        }
        (self.schemas / "build-failure.schema.json").write_text(
            json.dumps(retry_schema)
        )
        self.write_log(
            {"type": "design-block", "req_id": "REQ-A-001"},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 1},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 2},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 3},
        )
        code, out, err = self.run_cli(
            "next-retry",
            "--req-id",
            "REQ-A-001",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "4\n")
        self.assertIn("exceeds the schema maximum", err)


class TestValidate(HandoffCase):
    def validate(self):
        return self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )

    def test_clean_log(self):
        self.append(a_record())
        self.append({"type": "ref-rec", "facet": "skim"})
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "2 records valid\n")

    def test_detects_unknown_type(self):
        self.write_log({"type": "mystery"})
        code, _, err = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("no schema for record type 'mystery'", err)

    def test_missing_file_fails(self):
        code, _, err = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("no handoff log", err)


class TestQueries(HandoffCase):
    def test_latest_returns_last_match(self):
        self.write_log(
            {
                "type": "design-block",
                "req_id": "REQ-A-001",
                "verdict": "covered",
            },
            {"type": "design-block", "req_id": "REQ-A-001", "verdict": "minor"},
            {"type": "design-block", "req_id": "REQ-B-001", "verdict": "new"},
        )
        code, out, err = self.run_cli(
            "latest",
            "--type",
            "design-block",
            "--req-id",
            "REQ-A-001",
            "--file",
            str(self.log),
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["verdict"], "minor")

    def test_latest_with_line_prefix(self):
        self.write_log({"type": "design-block", "req_id": "REQ-A-001"})
        code, out, _ = self.run_cli(
            "latest", "--type", "design-block", "--with-line", "--file", str(self.log)
        )
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("1\t"))

    def test_latest_no_match_exits_3(self):
        self.write_log({"type": "design-block", "req_id": "REQ-A-001"})
        code, _, err = self.run_cli(
            "latest", "--type", "build-pass", "--file", str(self.log)
        )
        self.assertEqual(code, 3)
        self.assertIn("no build-pass record", err)

    def test_latest_refuses_corrupt_log(self):
        self.log.write_text("not json\n")
        code, _, err = self.run_cli(
            "latest", "--type", "design-block", "--file", str(self.log)
        )
        self.assertEqual(code, 1)
        self.assertIn("run validate", err)

    def test_next_retry_counts_after_latest_design_block(self):
        self.write_log(
            {"type": "design-block", "req_id": "REQ-A-001"},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 1},
            {"type": "build-failure", "req_id": "REQ-B-001", "retry": 1},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 2},
            {
                "type": "design-block",
                "req_id": "REQ-A-001",
                "supersedes_record_at": 1,
            },
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 1},
        )
        code, out, err = self.run_cli(
            "next-retry", "--req-id", "REQ-A-001", "--file", str(self.log)
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "2\n")

    def test_next_retry_without_design_block_exits_3(self):
        self.write_log({"type": "build-failure", "req_id": "REQ-A-001", "retry": 1})
        code, _, err = self.run_cli(
            "next-retry", "--req-id", "REQ-A-001", "--file", str(self.log)
        )
        self.assertEqual(code, 3)
        self.assertIn("no design-block", err)


class TestShow(HandoffCase):
    def test_show_marks_unparseable_lines(self):
        self.log.write_text(json.dumps(a_record()) + "\nnot json\n")
        code, out, _ = self.run_cli("show", "--file", str(self.log))
        self.assertEqual(code, 0)
        self.assertIn("UNPARSEABLE", out)
        self.assertIn("test-rec · REQ-DEMO-001", out)

    def test_show_empty_filter(self):
        self.write_log({"type": "design-block", "req_id": "REQ-A-001"})
        code, out, _ = self.run_cli(
            "show", "--type", "build-pass", "--file", str(self.log)
        )
        self.assertEqual(code, 0)
        self.assertIn("no matching records", out)

    def test_show_directory_at_log_path_fails_clean(self):
        # Every other reader degrades to the clean error form on a directory
        # at the log path (parse_log's broad OSError); show must too, not
        # traceback with IsADirectoryError.
        self.log.unlink(missing_ok=True)
        self.log.mkdir()
        code, _, err = self.run_cli("show", "--file", str(self.log))
        self.assertNotEqual(code, 0)
        self.assertIn("cannot read", err)
        self.assertNotIn("Traceback", err)

    def test_show_plain_text_cannot_inject_terminal_escapes(self):
        # show prints an unparseable line raw and builds a header from record
        # fields; neither may carry an escape byte to the reader's terminal.
        # (The JSON body escapes C0 controls via json.dumps.)
        self.log.write_text(
            json.dumps(a_record(type="test-rec")) + "\n"
            "raw \x1b]0;pwned\x07\x1b[2J line\n"
        )
        code, out, _ = self.run_cli("show", "--file", str(self.log))
        self.assertEqual(code, 0)
        self.assertNotIn("\x1b", out)
        self.assertIn("UNPARSEABLE", out)


class TestGoldenCanonicalBytes(unittest.TestCase):
    """The append path writes each golden record's exact bytes."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        stamp = unittest.mock.patch.object(entry, "ts_now", return_value=SOME_TS)
        stamp.start()
        self.addCleanup(stamp.stop)

    def _append(self, rtype, record):
        log = self.root / f"{rtype}.jsonl"
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(record))
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = entry.main(
                    [
                        "append",
                        rtype,
                        "--file",
                        str(log),
                        "--schemas",
                        str(_REPO_SCHEMAS),
                    ]
                )
        finally:
            sys.stdin = old_stdin
        self.assertEqual(code, 0, err.getvalue())
        return log.read_bytes()

    def test_every_golden_type_resolves_to_a_schema(self):
        # Every pinned record maps to a real schema in whatever tree this runs
        # (core carries the nine below; a materialized sample adds stack types,
        # so this is a subset check, not equality). A golden entry naming a
        # deleted schema fails here.
        covered = {rtype for rtype, _, _ in GOLDEN_RECORDS}
        on_disk = {
            p.name[: -len(".schema.json")] for p in _REPO_SCHEMAS.glob("*.schema.json")
        }
        self.assertTrue(covered <= on_disk, covered - on_disk)

    def test_canonical_bytes_are_frozen(self):
        for rtype, record, expected in GOLDEN_RECORDS:
            with self.subTest(schema=rtype):
                self.assertEqual(self._append(rtype, record), expected)


class TestAuditAutofix(HandoffCase):
    """audit-autofix and the design-block gate reach the command line over a real repository."""

    COMMIT_DATE = "2026-01-01T00:00:00Z"

    def setUp(self):
        super().setUp()
        self.repo = self.fresh_directory()
        os.chdir(self.repo)
        (self.repo / "docs" / "adr").mkdir(parents=True)
        (self.repo / "docs" / "system-design.md").write_text(
            "design\n", encoding="utf-8"
        )
        self.git("init", "-q")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "init")

    def fresh_directory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(os.chdir, Path.cwd())
        return Path(tmp.name)

    def git(self, *argv):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv],
            check=True,
            env={
                **os.environ,
                "GIT_COMMITTER_DATE": self.COMMIT_DATE,
                "GIT_AUTHOR_DATE": self.COMMIT_DATE,
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
            },
            capture_output=True,
            text=True,
        )

    def audit(self):
        return self.run_cli("audit-autofix", "--file", str(self.log))

    def autofix_record(self, **over):
        base = {
            "type": "design-doc-autofix",
            "req_id": "REQ-A-001",
            "ts": SOME_TS,
            "author": "root",
            "file": "docs/system-design.md",
            "category": "writing-standards",
            "source_finding": {
                "review_feedback_author": "doc-reviewer",
                "review_feedback_ts": SOME_TS,
                "tag": "autofix",
                "location": "docs/system-design.md:1",
                "description": "d",
                "fix": "new text",
            },
            "old_content": "old text",
            "new_content": "new text",
            "lines_changed": 1,
            "chars_changed": 8,
        }
        base.update(over)
        return base

    def edit_design_doc(self):
        (self.repo / "docs" / "system-design.md").write_text(
            "edited\n", encoding="utf-8"
        )

    def test_a_clean_log_and_clean_tree_pass(self):
        self.write_log(self.autofix_record())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)
        self.assertEqual(
            out,
            "autofix audit clean: 1 record(s) validated, 0 dirty design-doc path(s) covered\n",
        )

    def test_a_missing_log_and_clean_tree_pass(self):
        code, _, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_a_static_failure_reaches_stderr_with_its_line(self):
        self.write_log(self.autofix_record(lines_changed=6))
        code, _, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("line 1: lines_changed outside the 1-5 autofix cap", err)

    def test_an_uncovered_path_reaches_stderr(self):
        self.edit_design_doc()
        self.write_log(a_slice_record("build-pass"))
        code, _, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("docs/system-design.md: uncommitted change with no covering", err)

    def test_a_dirty_log_fails_before_the_audit(self):
        self.log.write_text("not json\n", encoding="utf-8")
        code, _, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("log is not clean", err)

    def test_the_unborn_note_reaches_stdout(self):
        fresh = self.fresh_directory()
        os.chdir(fresh)
        self.git("init", "-q")
        (fresh / "docs").mkdir()
        (fresh / "docs" / "system-design.md").write_text("new\n", encoding="utf-8")
        self.write_log(self.autofix_record())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)
        self.assertIn("no commit yet", out)

    def test_no_repository_fails_closed(self):
        os.chdir(self.fresh_directory())
        self.write_log(self.autofix_record())
        code, _, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("cannot read the git worktree state; the audit fails closed", err)

    def append_design_block(self, **paths):
        record = {
            "type": "design-block",
            "req_id": "REQ-A-001",
            "author": "system-design-expert",
            "verdict": "covered",
            "architectural_fit": "Fits.",
            "primary_paths": ["src/x.py"],
            **paths,
        }
        return self.append(record, schemas=_REPO_SCHEMAS)

    def test_a_design_block_append_refuses_an_unlisted_dirty_design_doc_path(self):
        self.edit_design_doc()
        code, _, err = self.append_design_block()
        self.assertEqual(code, 1)
        self.assertIn("docs/system-design.md", err)
        self.assertFalse(self.log.exists())

    def test_a_design_block_append_accepts_the_listed_path(self):
        self.edit_design_doc()
        code, _, err = self.append_design_block(
            supporting_paths=["docs/system-design.md"]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.log_lines()), 1)

    def test_a_design_block_append_on_a_dirty_log_is_refused(self):
        self.log.write_text("not json\n", encoding="utf-8")
        code, _, err = self.append_design_block()
        self.assertEqual(code, 1)
        self.assertIn("log is not clean — run validate", err)
        self.assertEqual(self.log.read_text(encoding="utf-8"), "not json\n")


class TestAccountingDegradation(unittest.TestCase):
    def test_broken_accounting_module_never_gates_the_writer(self):
        # A present-but-broken vendored accounting.py (an interrupted copy)
        # must not take handoff.py down: the overlay's import guard catches
        # any import-time error, not just a missing module — SyntaxError is
        # not an ImportError subclass.
        with tempfile.TemporaryDirectory() as td:
            scripts = Path(td)
            # handoff.py composes the handoff package (ADR 2026-07-17
            # runtime-package-layout); ship the entry and the whole package so
            # startup runs, then break the vendored accounting module beside them.
            shutil.copy(_HERE / "handoff.py", scripts / "handoff.py")
            shutil.copytree(_HERE / "handoff", scripts / "handoff")
            (scripts / "accounting.py").write_text("def broken(:\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(scripts / "handoff.py"), "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)


class TestConcurrentAppends(HandoffCase):
    """Lock-free append under real multi-process concurrency (ADR 2026-08-16
    in the reference): parallel writers through the CLI must land every
    record exactly once, keep the log validate-clean, and report receipts
    naming each record's true line. This also proves the host filesystem
    honors O_APPEND write atomicity — the property the parallel reviewer
    fan-out rests on. A failure here means parallel appends are unsafe on
    this filesystem (network mounts are the known offender)."""

    WORKERS = 4
    APPENDS = 6

    def test_interleaved_descriptors_yield_exact_offsets(self):
        # The receipt mechanism, deterministically: two O_APPEND descriptors
        # interleave; each lseek(SEEK_CUR) bounds its own write, so each
        # prefix count names that writer's true line — the property the
        # probabilistic test below can only sample.
        fd_a = os.open(self.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        fd_b = os.open(self.log, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(fd_a, b'{"one":1}\n')
            os.write(fd_b, b'{"two":2}\n')
            end_a = os.lseek(fd_a, 0, os.SEEK_CUR)
            end_b = os.lseek(fd_b, 0, os.SEEK_CUR)
        finally:
            os.close(fd_a)
            os.close(fd_b)
        raw = self.log.read_bytes()
        self.assertEqual(raw[:end_a].count(b"\n"), 1)
        self.assertEqual(raw[:end_b].count(b"\n"), 2)

    def test_parallel_appends_land_exactly_with_exact_receipts(self):
        """Needs O_APPEND write atomicity — a failure here means this
        filesystem (network mounts are the known offender) cannot run the
        parallel reviewer fan-out safely."""
        (self.schemas / "stress-rec.schema.json").write_text(
            json.dumps({"type": "object", "required": ["type"]})
        )

        def worker(w):
            # Odd workers append multi-page records: real review-feedback
            # runs to tens of KB, and page-crossing writes are the size
            # class where atomicity is not free.
            pad = "x" * 6000 if w % 2 else ""
            receipts = []
            for seq in range(self.APPENDS):
                record = {
                    "type": "stress-rec",
                    "worker": w,
                    "seq": seq,
                    "pad": pad,
                }
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(_HERE / "handoff.py"),
                        "append",
                        "stress-rec",
                        "--file",
                        str(self.log),
                        "--schemas",
                        str(self.schemas),
                        "--layout",
                        str(self.layout),
                    ],
                    input=json.dumps(record),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                match = re.search(r"at line (\d+)", proc.stdout)
                self.assertIsNotNone(match, proc.stdout)
                receipts.append((w, seq, int(match.group(1))))
            return receipts

        with concurrent.futures.ThreadPoolExecutor(self.WORKERS) as pool:
            receipts = [
                r for chunk in pool.map(worker, range(self.WORKERS)) for r in chunk
            ]

        total = self.WORKERS * self.APPENDS
        lines = self.log_lines()
        self.assertEqual(len(lines), total, "every append lands exactly once")
        code, _, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(
            sorted(line_no for _, _, line_no in receipts),
            list(range(1, total + 1)),
            "receipts are a permutation of the physical lines",
        )
        for w, seq, line_no in receipts:
            record = json.loads(lines[line_no - 1])
            self.assertEqual(
                (record["worker"], record["seq"]),
                (w, seq),
                f"receipt line {line_no} names another writer's record",
            )


class TestBuildPassRunsPlanEngine(HandoffCase):
    """A build-pass append on the default ledger composes the review-plan
    engine (route-spec § Gate 5): the plan exists by construction, at the
    append's own tree state. Pins: the spawn and its argv, the fail-open
    contract (a failed engine warns, the append stays green), and the two
    non-trigger paths — a --file-redirected append (harness-internal by
    design; the skip announces itself on stderr) and every other record
    type. The trigger compares resolved paths, never spellings."""

    def setUp(self):
        super().setUp()
        (self.schemas / "build-pass.schema.json").write_text(
            json.dumps({"type": "object", "required": ["type", "req_id"]})
        )
        (self.schemas / "prd-entry.schema.json").write_text(
            json.dumps({"type": "object", "required": ["type", "req_id"]})
        )
        # Point the CLI's default ledger into the fixture, so an append
        # without --file (the runtime shape) lands here, not in the repo.
        pin = unittest.mock.patch.object(entry, "DEFAULT_LOG", str(self.log))
        pin.start()
        self.addCleanup(pin.stop)

    def _append_default_file(self, rtype, spawn):
        with unittest.mock.patch.object(
            entry.subprocess, "run", side_effect=spawn
        ) as spawned:
            code, out, err = self.run_cli(
                "append",
                rtype,
                "--schemas",
                str(self.schemas),
                stdin=json.dumps({"type": rtype, "req_id": "REQ-XX-001"}),
            )
        return code, out, err, spawned

    def test_build_pass_on_the_default_ledger_spawns_the_engine(self):
        ok = subprocess.CompletedProcess(
            [],
            0,
            stdout="review-plan: appended low plan for REQ-XX-001\n",
            stderr="",
        )
        code, out, err, spawned = self._append_default_file(
            "build-pass", lambda *a, **k: ok
        )
        self.assertEqual(0, code, err)
        spawned.assert_called_once()
        argv = spawned.call_args.args[0]
        self.assertEqual(sys.executable, argv[0])
        # -E -B: PYTHON* env never shapes the child's imports; no bytecode.
        self.assertEqual(["-E", "-B"], argv[1:3])
        self.assertTrue(argv[3].endswith("grading.py"))
        self.assertEqual(["review-plan", "--feature", "REQ-XX-001"], argv[4:])
        self.assertIn("review-plan: appended low plan", out)

    def test_a_failed_engine_leaves_the_append_green_and_warns(self):
        bad = subprocess.CompletedProcess([], 1, stdout="", stderr="boom\n")
        code, out, err, _ = self._append_default_file("build-pass", lambda *a, **k: bad)
        self.assertEqual(0, code)
        self.assertIn("appended build-pass", out)
        self.assertIn("falls back to the full battery", err)

    def test_an_engine_that_cannot_start_leaves_the_append_green(self):
        def raise_oserror(*a, **k):
            raise OSError("no interpreter")

        code, out, err, _ = self._append_default_file("build-pass", raise_oserror)
        self.assertEqual(0, code)
        self.assertIn("appended build-pass", out)
        self.assertIn("falls back to the full battery", err)

    def test_a_file_redirected_append_never_spawns(self):
        other = self.log.parent / "redirected.jsonl"
        with unittest.mock.patch.object(entry.subprocess, "run") as spawned:
            code, _, err = self.run_cli(
                "append",
                "build-pass",
                "--file",
                str(other),
                "--schemas",
                str(self.schemas),
                stdin=json.dumps({"type": "build-pass", "req_id": "REQ-XX-001"}),
            )
        self.assertEqual(0, code, err)
        spawned.assert_not_called()
        self.assertIn("redirected ledger", err)
        self.assertIn("falls back to the full battery", err)

    def test_an_equivalent_spelling_of_the_default_still_spawns(self):
        # `--file` naming the default ledger by another spelling is not a
        # redirect: string equality alone would silently skip the engine
        # on every such gate-pass — the exact skip class the composed
        # trigger exists to close.
        spelled = self.log.parent / "." / self.log.name
        ok = subprocess.CompletedProcess(
            [],
            0,
            stdout="review-plan: appended low plan for REQ-XX-001\n",
            stderr="",
        )
        with unittest.mock.patch.object(
            entry.subprocess, "run", side_effect=lambda *a, **k: ok
        ) as spawned:
            code, _, err = self.run_cli(
                "append",
                "build-pass",
                "--file",
                str(spelled),
                "--schemas",
                str(self.schemas),
                stdin=json.dumps({"type": "build-pass", "req_id": "REQ-XX-001"}),
            )
        self.assertEqual(0, code, err)
        spawned.assert_called_once()

    def test_other_record_types_never_spawn(self):
        code, _, err, spawned = self._append_default_file(
            "prd-entry", unittest.mock.MagicMock()
        )
        self.assertEqual(0, code, err)
        spawned.assert_not_called()

    def test_an_unclean_req_id_never_reaches_argv(self):
        # The permissive fixture schema admits shapes the shipped pattern
        # rejects; the spawn's own fullmatch re-check must refuse them —
        # including the trailing newline a `$` pattern tolerates.
        for req in ("REQ-XX-001\n", "--evil", "REQ-XX-001 extra", 7):
            with self.subTest(req=req):
                with unittest.mock.patch.object(entry.subprocess, "run") as spawned:
                    code, out, err = self.run_cli(
                        "append",
                        "build-pass",
                        "--schemas",
                        str(self.schemas),
                        stdin=json.dumps({"type": "build-pass", "req_id": req}),
                    )
                self.assertEqual(0, code, err)
                self.assertIn("appended build-pass", out)
                spawned.assert_not_called()
                self.assertIn("falls back to the full battery", err)

    def test_engine_output_is_sanitized_before_echo(self):
        evil = subprocess.CompletedProcess(
            [], 0, stdout="review-plan: appended \x1b[31mlow\x1b[0m plan\n", stderr=""
        )
        code, out, _, _ = self._append_default_file("build-pass", lambda *a, **k: evil)
        self.assertEqual(0, code)
        self.assertNotIn("\x1b", out)
        bad = subprocess.CompletedProcess([], 1, stdout="", stderr="x\x1b]0;t\x07y\n")
        code, _, err, _ = self._append_default_file("build-pass", lambda *a, **k: bad)
        self.assertEqual(0, code)
        self.assertNotIn("\x1b", err)


class ViewCommand(HandoffCase):
    """The view subcommand's wiring: flags, environment, layout, and the transcript overlay."""

    def setUp(self):
        super().setUp()
        # An empty projects tree keeps the cost overlay independent of the host.
        patcher = unittest.mock.patch.dict(
            os.environ, {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "no-projects")}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def view(self, *extra):
        return self.run_cli(
            "view", "--file", str(self.log), "--layout", str(self.layout), *extra
        )

    def a_routine_slice(self):
        return (
            a_slice_record(
                "design-block", verdict="covered", implementation_effort="routine"
            ),
            a_slice_record(
                "dispatch-start", author="feature-implementer", responding_to=[1]
            ),
            a_slice_record("build-pass"),
            a_slice_record(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[
                    {
                        "tag": "autofix",
                        "location": "src/widget:1",
                        "description": "d",
                        "severity": "minor",
                        "fix": "x",
                    }
                ],
            ),
            a_slice_record(
                "dispatch-start", author="feature-implementer", responding_to=[4]
            ),
            a_slice_record("build-pass"),
        )

    def test_a_missing_log_renders_a_message(self):
        code, out, err = self.view("--no-color")
        self.assertEqual(code, 0, err)
        self.assertIn("no handoff log", out)

    def test_the_color_flag_forces_ansi_through_a_pipe(self):
        self.write_log(a_slice_record("prd-entry", title="t"))
        with unittest.mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            code, out, err = self.view("--color")
        self.assertEqual(code, 0, err)
        self.assertIn("\x1b[", out)

    def test_color_follows_the_tty_unless_no_color_is_set(self):
        self.write_log(a_slice_record("prd-entry", title="T"))

        class Tty(io.StringIO):
            def isatty(self):
                return True

        argv = ["view", "--file", str(self.log), "--layout", str(self.layout)]
        with unittest.mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            os.environ.pop("NO_COLOR")
            out = Tty()
            with contextlib.redirect_stdout(out):
                entry.main(argv)
            self.assertIn("\x1b[", out.getvalue())
            os.environ["NO_COLOR"] = "1"
            out = Tty()
            with contextlib.redirect_stdout(out):
                entry.main(argv)
            self.assertNotIn("\x1b[", out.getvalue())

    def test_color_and_no_color_are_mutually_exclusive(self):
        self.write_log(a_slice_record("prd-entry", title="t"))
        code, _, err = self.view("--color", "--no-color")
        self.assertEqual(code, 2)
        self.assertIn("not allowed with", err)

    def test_markdown_and_a_color_flag_are_mutually_exclusive(self):
        self.write_log(a_slice_record("prd-entry", title="t"))
        for flag in ("--color", "--no-color"):
            code, _, err = self.view("--markdown", flag)
            self.assertEqual(code, 2)
            self.assertIn("not allowed with", err)

    def test_the_layout_turns_grading_off(self):
        self.layout.write_text("[harness]\nauto_grade = false\n")
        self.write_log(
            a_slice_record("prd-entry", title="t"), a_slice_record("build-pass")
        )
        _, out, _ = self.view("--no-color")
        self.assertIn("grading disabled", out)

    def test_an_extra_reviewer_from_the_layout_gets_a_lane(self):
        self.layout.write_text('[harness]\nextra_reviewers = ["perf-reviewer"]\n')
        self.write_log(
            a_slice_record(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            )
        )
        _, out, _ = self.view("--no-color")
        self.assertEqual(
            len([line for line in out.splitlines() if line.startswith("perf")]), 1
        )

    def test_a_malformed_layout_roster_falls_back_to_the_floor(self):
        self.layout.write_text('[harness]\nextra_reviewers = "oops"\n')
        self.write_log(
            a_slice_record("review-feedback", verdict="approved", findings=[])
        )
        code, out, _ = self.view("--no-color")
        self.assertEqual(code, 0)
        self.assertIn("code-quality", out)

    def test_an_unparseable_layout_fails_closed(self):
        self.layout.write_text("[harness\n")
        self.write_log(a_slice_record("prd-entry", title="t"))
        code, _, err = self.view("--no-color")
        self.assertEqual(code, 1)
        self.assertIn("cannot be parsed", err)

    def test_the_routine_window_of_a_rated_slice_is_annotated(self):
        self.write_log(*self.a_routine_slice())
        code, out, err = self.view("--no-color")
        self.assertEqual(code, 0, err)
        self.assertIn("(implementer · routine)", out)
        self.assertIn("(implementer)  ", out)

    def test_an_unrated_slice_never_annotates_fix_rounds(self):
        design, dispatch, build, review, fix_dispatch, fix_build = (
            self.a_routine_slice()
        )
        del design["implementation_effort"]
        self.write_log(design, dispatch, build, review, fix_dispatch, fix_build)
        _, out, _ = self.view("--no-color")
        self.assertNotIn("· routine", out)

    def test_an_unknown_req_id_exits_three_through_main(self):
        self.write_log(a_slice_record("prd-entry", title="T"))
        code, out, _ = self.view("--no-color", "--req-id", "REQ-NOPE-999")
        self.assertEqual(code, 3)
        self.assertIn("no records for REQ-NOPE-999", out)

    def test_markdown_renders_the_selected_slice(self):
        self.write_log(a_slice_record("prd-entry", title="T"))
        code, out, err = self.view("--markdown", "--req-id", "REQ-A-001")
        self.assertEqual(code, 0, err)
        self.assertIn("### REQ-A-001 — T", out)

    def test_a_dirty_log_renders_with_the_parse_errors_as_a_footer(self):
        self.log.write_text(
            json.dumps(a_slice_record("prd-entry", title="T")) + "\nnot json\n"
        )
        code, out, _ = self.view("--no-color")
        self.assertEqual(code, 0)
        self.assertIn("prd-entry", out)
        self.assertIn("line 2: invalid JSON", out)

    def test_a_forged_tier_key_is_scrubbed(self):
        design, dispatch, build = self.a_routine_slice()[:3]
        dispatch["_tier"] = "routine"
        self.write_log(design, dispatch, build)
        _, out, _ = self.view("--no-color")
        self.assertNotIn("· routine", out)

    def _synthetic_project(self, usage):
        slug = accounting.slug_for(os.getcwd())
        subagents = self.log.parent / "projects" / slug / "sess1" / "subagents"
        subagents.mkdir(parents=True)
        message = {
            "type": "assistant",
            "timestamp": "2026-07-06T10:10:00Z",
            "message": {"model": "claude-opus-4-8", "usage": usage},
        }
        (subagents / "agent-x.jsonl").write_text(json.dumps(message) + "\n")
        (subagents / "agent-x.meta.json").write_text(
            json.dumps({"agentType": "feature-implementer"})
        )

    def _view_with_projects(self):
        with unittest.mock.patch.dict(
            os.environ, {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "projects")}
        ):
            self.write_log(
                a_slice_record(
                    "dispatch-start",
                    author="feature-implementer",
                    ts="2026-07-06T10:05:00Z",
                    responding_to=[0],
                ),
                a_slice_record(
                    "build-pass",
                    author="feature-implementer",
                    ts="2026-07-06T10:20:00Z",
                    gate_checks_run=["test"],
                ),
            )
            return self.view("--no-color")

    def test_the_cost_overlay_reads_the_transcripts_end_to_end(self):
        self._synthetic_project(
            {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 0}
        )
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        # opus prices 1000 input and 500 output tokens at 0.0175 dollars,
        # shown as $0.02; the 1000 input tokens read as 1k.
        self.assertIn("◷ 15m │ Σ ▲1k ▼500 $0.02 │ ⛁ 0%", out)

    def test_the_header_roll_up_ignores_foreign_agents_in_the_window(self):
        self._synthetic_project(
            {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 0}
        )
        subagents = (
            self.log.parent
            / "projects"
            / accounting.slug_for(os.getcwd())
            / "sess1"
            / "subagents"
        )
        foreign = {
            "type": "assistant",
            "timestamp": "2026-07-06T10:11:00Z",
            "message": {"model": "claude-opus-4-8", "usage": {"input_tokens": 77000}},
        }
        (subagents / "agent-y.jsonl").write_text(json.dumps(foreign) + "\n")
        (subagents / "agent-y.meta.json").write_text(
            json.dumps({"agentType": "Explore"})
        )
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        self.assertIn("│ ◷ 15m │ Σ ▲1k ▼500 $0.02 │ ⛁ 0%", out)

    def test_a_malformed_transcript_degrades_to_no_figures(self):
        self._synthetic_project({"input_tokens": "1200", "output_tokens": 500})
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        self.assertNotIn("Traceback", err)
        self.assertIn("◷ 15m", out)


class RouteCommand(RouteCase):
    """The route subcommand's wiring: the log file's damage modes, the layout file,
    and the slice flag. The decisions themselves are the routing suite's."""

    def test_a_missing_log_escalates_with_no_active_slice(self):
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "no-active-slice")

    def test_an_empty_log_escalates_with_no_active_slice(self):
        self.log.write_text("")
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "no-active-slice")

    def test_a_dirty_log_blocks_with_the_parse_errors(self):
        self.log.write_text(json.dumps(a_slice_record("prd-entry")) + "\ngarbage\n")
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("line 2: invalid JSON (Expecting value)", decision["errors"][0])

    def test_a_truncated_final_line_blocks(self):
        # An agent dying mid-append leaves no trailing newline; route refuses
        # to guess over it.
        self.log.write_text(
            json.dumps(a_slice_record("prd-entry")) + "\n" + '{"type": "desi'
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")

    def test_a_directory_at_the_log_path_blocks_with_exit_zero(self):
        self.log.mkdir()
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("cannot read", decision["errors"][0])

    def test_an_unparseable_layout_blocks(self):
        self.layout.write_text("[harness\nbroken = ")
        self.write_log(a_slice_record("build-pass"))
        decision = self.route("--layout", str(self.layout))
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "layout-unreadable")

    def test_the_layout_file_reaches_the_router(self):
        self.layout.write_text('[harness]\nextra_reviewers = ["perf-reviewer"]\n')
        self.write_log(a_slice_record("build-pass"))
        decision = self.route("--layout", str(self.layout))
        self.assertEqual(decision["next"][-1], "perf-reviewer")

    def test_the_req_id_flag_selects_the_slice(self):
        self.write_log(
            a_slice_record("prd-entry"), a_slice_record("prd-entry", req_id="REQ-B-001")
        )
        decision = self.route("--req-id", "REQ-A-001")
        self.assertEqual(decision["req_id"], "REQ-A-001")
        self.assertEqual(decision["next"], ["system-design-expert"])

    def test_a_schema_gate_reads_the_schemas_directory(self):
        strict = {"type": "object", "required": ["type", "title"]}
        (self.schemas / "prd-entry.schema.json").write_text(json.dumps(strict))
        self.write_log(a_slice_record("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("title", " ".join(decision["context"]["errors"]))


class TierCommand(RouteCase):
    def test_the_tier_command_prints_the_derivation(self):
        self.write_log(
            a_slice_record(
                "design-block", verdict="covered", implementation_effort="routine"
            )
        )
        code, out, err = self.run_cli("tier", "--file", str(self.log))
        self.assertEqual(code, 0, err)
        derived = json.loads(out)
        self.assertEqual(derived["req_id"], "REQ-A-001")
        self.assertEqual(derived["agent"], "feature-implementer")
        self.assertEqual(derived["reason"], "initial")

    def test_a_missing_log_reads_the_base_tier(self):
        code, out, err = self.run_cli("tier", "--file", str(self.log))
        self.assertEqual(code, 0, err)
        derived = json.loads(out)
        self.assertEqual(derived["agent"], "feature-implementer")
        self.assertEqual(derived["reason"], "no-records")


class ValidateDispatchDiscipline(RouteCase):
    def validate(self):
        return self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )

    def test_a_substantive_record_without_a_dispatch_start_warns(self):
        self.write_log(a_slice_record("build-pass", author="feature-implementer"))
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertIn("no prior dispatch-start", err)

    def test_the_warning_sanitizes_agent_authored_fields(self):
        control_bytes = "\x1b]0;title\x07\x1b[31mtext\x1b[0m"
        self.write_log(a_slice_record("build-pass", author=control_bytes))
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertIn("no prior dispatch-start", err)
        self.assertNotIn("\x1b", err)
        self.assertNotIn("\x07", err)


class AppendRespondingTo(RouteCase):
    def test_a_dangling_pointer_is_rejected(self):
        # Append is the one moment the referent set is known.
        code, out, err = self.append(
            a_slice_record("dispatch-start", responding_to=[5]), rtype="dispatch-start"
        )
        self.assertEqual(code, 1)
        self.assertIn("non-existent log line", err)

    def test_an_unterminated_last_line_still_counts_as_a_referent(self):
        self.log.write_text('{"a":1}\n{"b":2}\n{"c":3}', encoding="utf-8")
        code, out, err = self.append(
            a_slice_record("dispatch-start", responding_to=[3]), rtype="dispatch-start"
        )
        self.assertEqual(code, 0, err)


class DuplicateKeyFailClosed(RouteCase):
    """A log line with duplicate keys fails at parse, before any schema check,
    so validate errors and route blocks; neither crashes."""

    DUP_LINE = '{"type": "prd-entry", "req_id": "REQ-A-001", "req_id": "REQ-A-002"}\n'

    def test_validate_reports_a_duplicate_key_as_a_parse_error(self):
        self.log.write_text(self.DUP_LINE, encoding="utf-8")
        code, out, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)
        self.assertIn("invalid JSON", err)
        self.assertIn('duplicate key: "req_id"', err)
        self.assertNotIn("Traceback", err)

    def test_route_blocks_on_a_duplicate_key_line(self):
        self.log.write_text(self.DUP_LINE, encoding="utf-8")
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn('duplicate key: "req_id"', decision["errors"][0])


class DuplicateKeyControlBytesSanitized(RouteCase):
    """The duplicated key is agent content; a control byte in it never reaches
    the terminal raw. The parse error sanitizes at message construction, so
    validate, append, and route's errors all inherit it."""

    # A key carrying ESC/BEL/CR, duplicated. The controls are escaped so the
    # line is valid JSON; json decodes them to raw bytes before the hook runs.
    DUP = (
        '{"type": "prd-entry", "k\\u001b\\u0007\\u000dx": 1, '
        '"k\\u001b\\u0007\\u000dx": 2}\n'
    )

    def _assert_no_control_bytes(self, text):
        self.assertIn("duplicate key", text)
        for ch in ("\x1b", "\x07", "\r"):
            self.assertNotIn(ch, text)

    def test_validate_stderr_is_sanitized(self):
        self.log.write_text(self.DUP, encoding="utf-8")
        code, out, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)
        self._assert_no_control_bytes(err)

    def test_append_stderr_is_sanitized(self):
        code, out, err = self.run_cli(
            "append",
            "prd-entry",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            stdin=self.DUP.strip(),
        )
        self.assertEqual(code, 1)
        self._assert_no_control_bytes(err)

    def test_the_route_errors_entry_is_sanitized(self):
        self.log.write_text(self.DUP, encoding="utf-8")
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self._assert_no_control_bytes(" ".join(decision.get("errors", [])))


class NonUtf8Log(RouteCase):
    """A non-UTF-8 byte in the log is a dirty-log parse error, never a decode
    traceback: route blocks with exit 0, validate exits 1, view footers it,
    show degrades cleanly."""

    BAD = b'{"type": "prd-entry", "req_id": "REQ-A-001"}\n\xff\xfe\n'

    def test_route_blocks_with_exit_zero(self):
        self.log.write_bytes(self.BAD)
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("not valid UTF-8", " ".join(decision.get("errors", [])))

    def test_validate_exits_one_cleanly(self):
        self.log.write_bytes(self.BAD)
        code, out, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)
        self.assertIn("not valid UTF-8", err)
        self.assertNotIn("Traceback", err)

    def test_view_renders_the_problem_footer_with_exit_zero(self):
        self.log.write_bytes(self.BAD)
        code, out, err = self.run_cli("view", "--file", str(self.log))
        self.assertEqual(code, 0, err)
        self.assertIn("not valid UTF-8", out)

    def test_show_degrades_without_a_traceback(self):
        self.log.write_bytes(self.BAD)
        code, out, err = self.run_cli("show", "--file", str(self.log))
        self.assertNotEqual(code, 0)
        self.assertIn("not valid UTF-8", err)
        self.assertNotIn("Traceback", err)


class ScopeLockDelta(RouteCase):
    """The Non-Goals delta reaches Gate 1 through the command line: the root computes it
    from git in a throwaway repository; what the delta contains is the non-goals suite's."""

    PRD = (
        "# PRD\n\n## Non-Goals\n\n"
        "| ID | Non-Goal | Rationale |\n"
        "|----|----------|-----------|\n"
        "| NG-5 | Changing a record | Stated reason |\n"
    )

    def setUp(self):
        super().setUp()
        self.root = self.log.parent
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(self.root)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "prd.md").write_text(self.PRD, encoding="utf-8")
        for argv in (
            ("init", "-q"),
            ("add", "docs/prd.md"),
            ("commit", "-q", "-m", "seed"),
        ):
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv],
                cwd=self.root,
                check=True,
                env={
                    **os.environ,
                    "GIT_CONFIG_GLOBAL": "/dev/null",
                    "GIT_CONFIG_SYSTEM": "/dev/null",
                },
                capture_output=True,
                text=True,
            )
        (self.root / "docs" / "prd.md").write_text(
            self.PRD.replace("Changing a record", "Cancelling only"), encoding="utf-8"
        )
        self.write_log(a_slice_record("prd-entry"))

    def test_a_changed_row_reaches_gate_one(self):
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("NG-5", " ".join(decision["context"]["errors"]))

    def test_an_unavailable_git_fails_closed(self):
        with unittest.mock.patch.object(
            entry.subprocess, "run", side_effect=OSError("no git")
        ):
            decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "cannot read the docs/prd.md scope-lock baseline",
            " ".join(decision["context"]["errors"]),
        )
