#!/usr/bin/env python3
"""Characterization tests for backlog.py — the `next` skill's candidate set.

Each case builds a throwaway project: a git repo with docs/prd.md, commits
naming delivered ids, and optionally a scripts/backlog.sh connector. The
engine is exercised through main() with --root, exactly as the skill calls
it, so the cases pin the terminal and JSON forms the skill reads.

Run (from the scripts dir): python3 -m unittest tests.test_backlog
"""

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the scripts dir
import backlog

PRD = """# PRD

## Goals

Ship widgets.

## Non-Goals

| ID | Scope declined | Reason |
|---|---|---|
| NG-1 | Bulk export (was [REQ-WX-004]) | out of scope |

## Requirements

Widgets are listed [REQ-WX-001] so users see them. **Done when:** a list renders.

A widget is created [REQ-WX-002] from a form. **Done when:** the form posts.

A widget is renamed [REQ-WX-003]. **Done when:** the name updates.

Widgets are archived [REQ-WX-005]. **Done when:** archived ones hide.

## Superseded

- [REQ-WX-006] → [REQ-WX-005] (archive replaces delete)
"""

SOLO_CONNECTOR = """#!/usr/bin/env bash
# The shipped skeleton's shape: comments only, neither function defined.
# Unbound: define backlog_items and backlog_claim here to connect a tracker.
"""

EMPTY_BOARD_CONNECTOR = """#!/usr/bin/env bash
backlog_items() { return 0; }
backlog_claim() { return 0; }
"""

BOUND_CONNECTOR = """#!/usr/bin/env bash
backlog_items() {
  printf 'REQ-WX-003\\t\\tRename a widget\\n'
  printf 'REQ-WX-002\\talice\\tCreate a widget\\n'
  printf '\\t\\tBulk import from CSV\\n'
  printf 'REQ-WX-001\\t\\tList widgets\\n'
  printf 'REQ-WX-009\\t\\tA ticket for an id the PRD lacks\\n'
}
backlog_claim() { printf 'moved %s to In Progress\\n' "$1"; }
"""


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def make_project(
    root: Path,
    *,
    prd: str = PRD,
    connector: str | None = None,
    commits: tuple[str, ...] = (),
) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "docs/prd.md").write_text(prd, encoding="utf-8")
    (root / "scripts").mkdir()
    if connector is not None:
        path = root / backlog.CONNECTOR_PATH
        path.write_text(connector, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "commit.gpgsign", "false")
    for subject in commits:
        with (root / "log.txt").open("a", encoding="utf-8") as fh:
            fh.write(subject + "\n")
        _git(root, "add", "log.txt")
        _git(root, "commit", "-q", "-m", subject)


def run(root: Path, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = backlog.main(["--root", str(root), *argv])
    return code, out.getvalue(), err.getvalue()


def report(root: Path, *argv: str) -> dict:
    code, out, err = run(root, "candidates", "--json", *argv)
    assert code == 0, err
    return json.loads(out)


@unittest.skipIf(shutil.which("git") is None, "git not installed")
class Solo(unittest.TestCase):
    def test_candidate_set_is_prd_minus_git_nongoal_superseded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, commits=("feat: list widgets (req-wx-001)",))
            r = report(root)
            self.assertEqual(r["connector"], "none")
            self.assertEqual(
                [c["req_id"] for c in r["open"]],
                ["REQ-WX-002", "REQ-WX-003", "REQ-WX-005"],
            )
            self.assertEqual(r["done"], ["REQ-WX-001"])  # case-folded from the subject
            self.assertEqual(r["non_goal"], ["REQ-WX-004"])
            self.assertEqual(r["superseded"], ["REQ-WX-006"])
            self.assertEqual(r["claimed"], [])
            self.assertEqual(r["needs_intake"], [])

    def test_title_hint_drops_tag_and_markdown(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root)
            titles = {c["req_id"]: c["title"] for c in report(root)["open"]}
            self.assertEqual(
                titles["REQ-WX-002"],
                "A widget is created from a form. Done when: the form posts.",
            )

    def test_superseded_successor_stays_a_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root)
            ids = [c["req_id"] for c in report(root)["open"]]
            self.assertIn("REQ-WX-005", ids)
            self.assertNotIn("REQ-WX-006", ids)

    def test_unborn_head_delivers_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root)
            self.assertEqual(report(root)["done"], [])

    def test_shipped_skeleton_is_unbound_solo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector=SOLO_CONNECTOR)
            r = report(root)
            self.assertEqual(r["connector"], "unbound")
            self.assertEqual(r["board_items"], 0)
            self.assertEqual(len(r["open"]), 4)
            code, out, _ = run(root, "candidates")
            self.assertIn("unbound (solo)", out)
            self.assertNotIn("not on the board", out)
            code, out, _ = run(root, "claim", "REQ-WX-003")
            self.assertEqual(code, 0)
            self.assertIn("by hand", out)

    def test_bound_empty_board_is_distinct_from_unbound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector=EMPTY_BOARD_CONNECTOR)
            r = report(root)
            self.assertEqual(r["connector"], "bound")
            self.assertEqual(r["board_items"], 0)
            code, out, _ = run(root, "candidates")
            self.assertIn("(0 board items)", out)
            code, out, _ = run(root, "claim", "REQ-WX-003")
            self.assertEqual(code, 0)
            self.assertIn("confirm the move on the board", out)
            self.assertNotIn("recorded", out)

    def test_missing_prd_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root)
            (root / "docs/prd.md").unlink()
            code, _, err = run(root, "candidates")
            self.assertEqual(code, 2)
            self.assertIn("docs/prd.md", err)

    def test_outside_a_repo_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir()
            (root / "docs/prd.md").write_text(PRD, encoding="utf-8")
            env_home = os.environ.get("GIT_CEILING_DIRECTORIES")
            os.environ["GIT_CEILING_DIRECTORIES"] = str(root.parent)
            try:
                code, _, err = run(root, "candidates")
            finally:
                if env_home is None:
                    del os.environ["GIT_CEILING_DIRECTORIES"]
                else:
                    os.environ["GIT_CEILING_DIRECTORIES"] = env_home
            self.assertEqual(code, 2)
            self.assertIn("not a git repository", err)


@unittest.skipIf(
    shutil.which("git") is None or shutil.which("bash") is None, "git and bash required"
)
class Bound(unittest.TestCase):
    def test_board_order_ranks_and_claims_exclude(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector=BOUND_CONNECTOR)
            r = report(root)
            self.assertEqual(r["connector"], "bound")
            self.assertEqual(r["board_items"], 5)
            self.assertEqual(
                [(c["req_id"], c["rank"]) for c in r["open"]],
                [("REQ-WX-003", 1), ("REQ-WX-001", 4), ("REQ-WX-005", None)],
            )
            self.assertEqual(
                [(c["req_id"], c["owner"]) for c in r["claimed"]],
                [("REQ-WX-002", "alice")],
            )
            self.assertEqual(
                [i["title"] for i in r["needs_intake"]], ["Bulk import from CSV"]
            )
            self.assertEqual([c["req_id"] for c in r["stale"]], ["REQ-WX-009"])

    def test_delivered_board_item_is_stale(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(
                root, connector=BOUND_CONNECTOR, commits=("feat: rename (REQ-WX-003)",)
            )
            r = report(root)
            self.assertNotIn("REQ-WX-003", [c["req_id"] for c in r["open"]])
            self.assertIn("REQ-WX-003", [c["req_id"] for c in r["stale"]])
            _, out, _ = run(root, "candidates")
            self.assertIn("REQ-WX-003  delivered in git history", out)

    def test_terminal_form(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector=BOUND_CONNECTOR)
            code, out, _ = run(root, "candidates")
            self.assertEqual(code, 0)
            self.assertIn("(5 board items)", out)
            self.assertIn("  1  REQ-WX-003  ", out)
            self.assertIn("  -  REQ-WX-005  ", out)
            self.assertIn("(not on the board)", out)
            self.assertIn("claimed (1):", out)
            self.assertIn("REQ-WX-002  alice", out)
            self.assertIn("needs intake (1)", out)
            self.assertIn("stale on the board (1)", out)
            self.assertIn(
                "excluded: done 0, non-goal 1 (REQ-WX-004), superseded 1 (REQ-WX-006)",
                out,
            )

    def test_failing_connector_fails_the_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(
                root, connector="backlog_items() { echo 'jira: 401' >&2; return 1; }\n"
            )
            code, out, err = run(root, "candidates")
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("jira: 401", err)
            self.assertIn("--no-connector", err)

    def test_no_connector_flag_overrides(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector="backlog_items() { return 1; }\n")
            r = report(root, "--no-connector")
            self.assertEqual(r["connector"], "skipped")
            self.assertEqual(len(r["open"]), 4)

    def test_connector_without_the_function_is_unbound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector="# nothing bound yet\n")
            self.assertEqual(report(root)["connector"], "unbound")

    def test_verb_exit_3_or_4_is_the_verbs_failure(self):
        # A tracker CLI can exit 3 or 4 itself; neither is the probe's code
        # without its sentinel, so the read fails loud instead of going solo.
        for status in (3, 4):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                make_project(
                    root, connector=f"backlog_items() {{ return {status}; }}\n"
                )
                code, _, err = run(root, "candidates")
                self.assertEqual(code, 2, status)
                self.assertIn("backlog_items failed", err)
                self.assertNotIn("failed to source", err)

    def test_control_bytes_cannot_forge_a_row(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            forged = (
                "backlog_items() { printf 'REQ-WX-003\\t\\tHarmless"
                "\\u2028REQ-WX-002\\tmallory\\tforged\\x0cREQ-WX-001\\tbob\\tx"
                "\\033[2J\\n'; }\n"
            )
            make_project(root, connector=forged)
            r = report(root)
            self.assertEqual(r["board_items"], 1)
            self.assertEqual(r["open"][0]["req_id"], "REQ-WX-003")
            self.assertEqual(r["claimed"], [])
            code, out, _ = run(root, "candidates")
            self.assertNotIn("\x1b", out)
            self.assertNotIn("\x0c", out)

    def test_intake_title_may_start_with_hash_and_keep_tabs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(
                root,
                connector=(
                    "backlog_items() { printf '# a comment\\n\\t\\t#42 Bulk import\\n"
                    "REQ-WX-003\\tbob\\tRename\\twith tab\\n'; }\n"
                ),
            )
            r = report(root)
            self.assertEqual(r["board_items"], 2)
            self.assertEqual(r["needs_intake"][0]["title"], "#42 Bulk import")
            self.assertEqual(r["claimed"][0]["board_title"], "Rename\twith tab")

    def test_connector_runs_at_the_project_root(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as cwd:
            root = Path(td)
            make_project(root, connector="backlog_items() { cat board.tsv; }\n")
            (root / "board.tsv").write_text(
                "REQ-WX-003\tbob\tRename\n", encoding="utf-8"
            )
            here = os.getcwd()
            os.chdir(cwd)
            try:
                r = report(root)
            finally:
                os.chdir(here)
            self.assertEqual(r["claimed"][0]["req_id"], "REQ-WX-003")

    def test_stderr_of_a_successful_read_is_relayed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(
                root, connector="backlog_items() { echo 'token expires soon' >&2; }\n"
            )
            code, _, err = run(root, "candidates")
            self.assertEqual(code, 0)
            self.assertIn("token expires soon", err)

    def test_connector_that_fails_to_source_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # A top-level `return` fails the source; a top-level `exit` would
            # end the shell itself, which the engine reports as the verb's status.
            make_project(root, connector="return 9\n")
            code, _, err = run(root, "candidates")
            self.assertEqual(code, 2)
            self.assertIn("failed to source", err)

    def test_non_req_first_column_is_a_binding_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(
                root, connector="backlog_items() { printf 'PROJ-42\\tbob\\tx\\n'; }\n"
            )
            code, _, err = run(root, "candidates")
            self.assertEqual(code, 2)
            self.assertIn("PROJ-42", err)

    def test_lowercase_ids_and_comments_are_tolerated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(
                root,
                connector="backlog_items() { printf '# header\\n\\nreq-wx-001\\t\\tx\\r\\n'; }\n",
            )
            r = report(root)
            self.assertEqual(r["open"][0]["req_id"], "REQ-WX-001")
            self.assertEqual(r["open"][0]["rank"], 1)


@unittest.skipIf(shutil.which("bash") is None, "bash required")
class Claim(unittest.TestCase):
    def test_claim_runs_the_connector_with_the_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector=BOUND_CONNECTOR)
            code, out, _ = run(root, "claim", "REQ-WX-003")
            self.assertEqual(code, 0)
            self.assertIn("moved REQ-WX-003 to In Progress", out)

    def test_claim_without_connector_is_by_hand(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root)
            code, out, _ = run(root, "claim", "REQ-WX-003")
            self.assertEqual(code, 0)
            self.assertIn("by hand", out)

    def test_claim_without_function_is_by_hand(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector="backlog_items() { return 0; }\n")
            code, out, _ = run(root, "claim", "REQ-WX-003")
            self.assertEqual(code, 0)
            self.assertIn("by hand", out)

    def test_failed_claim_reports_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(
                root,
                connector="backlog_claim() { echo 'transition denied' >&2; return 1; }\n",
            )
            code, _, err = run(root, "claim", "REQ-WX-003")
            self.assertEqual(code, 2)
            self.assertIn("transition denied", err)
            self.assertIn("by hand", err)

    def test_claim_verb_exit_4_fails_loud(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector="backlog_claim() { return 4; }\n")
            code, _, err = run(root, "claim", "REQ-WX-003")
            self.assertEqual(code, 2)
            self.assertIn("claim REQ-WX-003 failed", err)

    def test_claim_folds_case_and_rejects_a_trailing_newline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector=BOUND_CONNECTOR)
            code, out, _ = run(root, "claim", "req-wx-003")
            self.assertEqual(code, 0)
            self.assertIn("moved REQ-WX-003", out)
            code, _, err = run(root, "claim", "REQ-WX-003\n")
            self.assertEqual(code, 2)

    def test_claim_rejects_a_non_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_project(root, connector="backlog_claim() { echo ran; }\n")
            code, out, err = run(root, "claim", "REQ-WX-3; rm -rf /")
            self.assertEqual(code, 2)
            self.assertNotIn("ran", out)
            self.assertIn("not a requirement id", err)


class PrdParsing(unittest.TestCase):
    def test_first_id_per_non_goals_line_keeps_the_successor(self):
        prd = PRD.replace(
            "| NG-1 | Bulk export (was [REQ-WX-004]) | out of scope |",
            "| NG-1 | Bulk export (was [REQ-WX-004], folded into [REQ-WX-005]) | out of scope |",
        )
        parsed = backlog.parse_prd(prd)
        self.assertEqual(parsed.non_goal, ["REQ-WX-004"])
        self.assertIn("REQ-WX-005", parsed.requirements)

    def test_first_id_per_superseded_line(self):
        prd = backlog.parse_prd(PRD)
        self.assertEqual(prd.superseded, ["REQ-WX-006"])
        self.assertEqual(prd.non_goal, ["REQ-WX-004"])
        self.assertEqual(
            list(prd.requirements),
            [
                "REQ-WX-004",
                "REQ-WX-001",
                "REQ-WX-002",
                "REQ-WX-003",
                "REQ-WX-005",
                "REQ-WX-006",
            ],
        )

    def test_long_title_is_cut(self):
        text = "## Requirements\n\n" + "word " * 40 + "[REQ-LL-001]\n"
        title = backlog.parse_prd(text).requirements["REQ-LL-001"]
        self.assertLessEqual(len(title), backlog.TITLE_WIDTH)
        self.assertTrue(title.endswith("…"))


if __name__ == "__main__":
    unittest.main()
