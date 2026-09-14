#!/usr/bin/env python3
"""Run identical synthetic projects through a baseline tree and this one, and diff every grading command.

Usage: harness/fuzz-grading.py --baseline TREE [--seed N] [--count N]

Each project is a small git repository of one stack with a generated
layout.toml, a change in the working tree or in a commit, a handoff ledger,
and a PRD. The change-set verb and every grading command run over it through
both trees, in one order, and the ledger each tree appended compares last. A
refactor that preserves behavior prints no difference and exits 0; a named
fix prints exactly the differences it names. Stdlib only. Tested by
tests/test_fuzz_grading.py.
"""

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import differential  # noqa: E402

ROOT = HERE.parent
Raw = dict[str, Any]
DEFAULT_COUNT = 25
REQ_ID = "REQ-A-001"
OTHER_REQ_ID = "REQ-B-002"
SOME_AUTHOR = ("t", "t@example.com")
STACKS = ("java-spring-boot", "go", "generic")
FLOOR = (
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
)
MALFORMED_LAYOUT = 0.1
COMMITTED_CHANGE = 0.4
EXCLUDES_DECLARED = 0.3
UNTRACKED_FILE = 0.4
BINARY_FILE = 0.2
DELETED_FILE = 0.3
MAX_BASE_FILES = 7
MAX_CHANGED_FILES = 5
MAX_LINES = 9
MAX_RECORDS = 10
GARBAGE_LINE = 0.1

PATHS: dict[str, dict[str, list[str]]] = {
    "java-spring-boot": {
        "prod": [
            "src/main/java/com/acme/Foo.java",
            "src/main/java/com/acme/Bar.java",
            "src/main/java/com/acme/auth/Guard.java",
            "src/main/resources/application.yml",
        ],
        "test": [
            "src/test/java/com/acme/FooTest.java",
            "src/test/java/com/acme/BarIT.java",
        ],
    },
    "go": {
        "prod": [
            "internal/app/foo.go",
            "cmd/app/main.go",
            "pkg/auth/token.go",
            "main.go",
        ],
        "test": ["internal/app/foo_test.go", "cmd/app/main_test.go"],
    },
    "generic": {
        "prod": ["src/app/foo.txt", "src/auth/guard.txt", "src/lib/bar.txt"],
        "test": ["tests/foo_test.txt", "src/app/foo.spec"],
    },
}
SHARED_PATHS = [
    "docs/system-design.md",
    "README.md",
    "config/app.toml",
    "settings.json",
    "vendor/lib/x.txt",
    "notes.txt",
]
BINARY_PATH = "assets/logo.bin"
LATIN1_PATH = "src/notes-latin1.txt"
LATIN1_TEXT = b"caf\xe9 au lait\n"
LATIN1_FILE = 0.2
LINES = [
    '@GetMapping("/x")',
    "new File(name)",
    'HandleFunc("/", h)',
    'exec.Command("ls")',
    "// why: the cache is warm",
    "/* Copyright (c) 2026 Acme. Licensed under the Apache License */",
    'Foo f = new Foo(1, "a");',
    "x := Config{}",
    "y := Foo{}",
    "const LIMIT = 3",
    "static final int MAX = 5;",
    "assertEquals(42, total);",
    "import java.util.List;",
    "void shouldAddTwo() {",
    "func TestAdds(t *testing.T) {",
    "plain line",
    "\tindented line",
    "line with \x1b[31m escape",
    "\u202e bidi line",
    "",
]
TEST_NAMES = ["shouldAddTwo", "TestAdds", "shouldNotExist", "", 5]
EXCLUDE_GLOBS: list[Any] = [["vendor/**"], ["**/*.yml"], ["src/**"], [""], "x"]
REVIEW_OVERRIDES = [
    "",
    "",
    "",
    'mode = "always-full"\n',
    "size_threshold = 4\n",
    "security_surface = []\n",
    "security_surface = ['new File']\n",
    '[review.surface_reviewers]\ndocs = ["doc-reviewer", "code-quality-reviewer"]\n',
    'mode = "weird"\n',
    'size_threshold = "big"\n',
]
CONVENTIONS_OVERRIDES = [
    "",
    "",
    "",
    "[conventions]\nconstruction = 'new\\s+Foo'\n",
    "[conventions]\nconstruction_ignore = ['']\n",
    "[conventions]\ncomment_markers = 'x'\n",
]
EXTRA_REVIEWERS = ["", "", "", '"extra-reviewer"', '"nobody"']
MALFORMED_TOP = [
    'test = "x"\n',
    'prod_roots = [""]\n',
    '[[module]]\nmatch = 5\nfrom = "dir"\n',
]
GATE = {
    "java-spring-boot": (
        "./gradlew build",
        [
            "handoff-log",
            "build",
            "test",
            "format",
            "check",
            "autofix-audit",
            "contracts-sync",
        ],
    ),
    "go": (
        "make ci",
        ["handoff-log", "build", "test", "lint", "autofix-audit", "contracts-sync"],
    ),
    "generic": (
        "scripts/gate.sh verify",
        ["handoff-log", "test", "build", "autofix-audit", "contracts-sync"],
    ),
}
CLASSIFICATION = {
    "java-spring-boot": (
        'test = ["**/*Test.java", "**/*Tests.java", "**/*IT.java", "src/test/**"]\n'
        'prod_roots = ["src/main/java/", "src/main/"]\n'
        'sensitive = ["**/auth/**", "**/security/**", "**/*token*/**"]\n'
    ),
    "go": (
        'test = ["**/*_test.go", "*_test.go"]\n'
        'prod_roots = ["internal/", "cmd/", "pkg/", "main.go"]\n'
        'sensitive = ["**/auth/**", "**/*token*/**"]\n'
    ),
    "generic": (
        'test = ["**/*test*", "**/*spec*"]\n'
        'prod_roots = ["src/"]\n'
        'sensitive = ["**/auth/**", "**/*token*/**"]\n'
    ),
}
MODULES = {
    "java-spring-boot": (
        '[[module]]\nmatch = "src/main/java/**"\nfrom = "gradle"\n'
        '[[module]]\nmatch = "src/test/java/**"\nfrom = "gradle"\n'
    ),
    "go": '[[module]]\nmatch = "internal/**"\nfrom = "dir"\n[[module]]\nmatch = "cmd/**"\nfrom = "dir"\n',
    "generic": '[[module]]\nmatch = "src/**"\nfrom = "dir"\n',
}
PRD = """# PRD

## Adding
<a id="req-a-001"></a>
- `[REQ-A-001]` two numbers add
- `[REQ-A-001]` a negative number is refused

Edge cases:
1. zero
2. overflow
"""
DESIGN_WITH_ID = "# Design\n\n| Type | Implements |\n|---|---|\n| Adder | REQ-A-001 |\n"
DESIGN_WITHOUT_ID = "# Design\n\nNothing yet.\n"
GITIGNORE = "scripts/\nschemas/\n.scratch/\n"


@dataclass(frozen=True, slots=True)
class Project:
    """One synthetic project: its stack, layout, files at the base, the change, its ledger, and its docs."""

    stack: str
    layout: str
    base_files: dict[str, bytes]
    changed_files: dict[str, bytes | None]
    committed: bool
    ledger: str
    docs: dict[str, str]
    churn: bool


class Fixture(NamedTuple):
    """A materialized project: where it lives and the commit its change starts from."""

    path: Path
    base: str


class Generator:
    """Random projects from one seeded source."""

    def __init__(self, seed: int) -> None:
        """Seed the source so a run is reproducible by its seed."""
        self.rng = random.Random(seed)

    def pick(self, options: list[Any]) -> Any:  # noqa: ANN401
        """Return one option."""
        return self.rng.choice(options)

    def pick_text(self, options: list[str]) -> str:
        """Return one text option."""
        return self.rng.choice(options)

    def binary(self) -> bytes:
        """Return a short binary body git never reads as text."""
        return b"\x00" + bytes(self.rng.randrange(256) for _ in range(8))

    def project(self) -> Project:
        """Return one project with a change worth grading."""
        stack = self.pick(list(STACKS))
        pool = [*PATHS[stack]["prod"], *PATHS[stack]["test"], *SHARED_PATHS]
        base = {path: self.text() for path in self.subset(pool, MAX_BASE_FILES)}
        if self.rng.random() < BINARY_FILE:
            base[BINARY_PATH] = self.binary()
        changed: dict[str, bytes | None] = {}
        for path in self.subset(pool, MAX_CHANGED_FILES):
            deleted = path in base and self.rng.random() < DELETED_FILE
            changed[path] = None if deleted else self.text()
        if self.rng.random() < BINARY_FILE:
            changed[BINARY_PATH] = self.binary()
        if self.rng.random() < LATIN1_FILE:
            changed[LATIN1_PATH] = LATIN1_TEXT
        return Project(
            stack=stack,
            layout=self.layout(stack),
            base_files=base,
            changed_files=changed,
            committed=self.rng.random() < COMMITTED_CHANGE,
            ledger=self.ledger(),
            docs={
                "docs/prd.md": self.pick([PRD, PRD, "# PRD\n"]),
                "docs/system-design.md": self.pick([DESIGN_WITH_ID, DESIGN_WITHOUT_ID]),
            },
            churn=self.rng.random() < COMMITTED_CHANGE,
        )

    def subset(self, pool: list[str], cap: int) -> list[str]:
        """Return a random subset of the pool, in pool order."""
        count = self.rng.randint(1, cap)
        chosen = set(self.rng.sample(pool, min(count, len(pool))))
        return [path for path in pool if path in chosen]

    def text(self) -> bytes:
        """Return a random file body."""
        count = self.rng.randint(1, MAX_LINES)
        lines = [self.pick(LINES) for _ in range(count)]
        return ("\n".join(lines) + "\n").encode("utf-8")

    def layout(self, stack: str) -> str:
        """Return one layout.toml text for the stack, sometimes malformed."""
        excludes = "[]"
        if self.rng.random() < EXCLUDES_DECLARED:
            excludes = json.dumps(self.pick(EXCLUDE_GLOBS))
        command, verbs = GATE[stack]
        text = (
            CLASSIFICATION[stack]
            + f"exclude_globs = {excludes}\n"
            + "[harness]\n"
            + 'channel = "copy"\nspec_version = "0.2.0"\ntools = ["claude"]\nextensions = []\n'
            + f"extra_reviewers = [{self.pick_text(EXTRA_REVIEWERS)}]\nauto_grade = true\n"
            + f"[gate]\ncommand = {json.dumps(command)}\nverbs = {json.dumps(verbs)}\n"
            + "[review]\n"
            + 'docs = ["**/*.md", "*.md", "docs/**"]\n'
            + 'config = ["**/*.toml", "*.toml", "**/*.yml", "*.yml", "**/*.json", "*.json"]\n'
            + self.pick_text(REVIEW_OVERRIDES)
            + MODULES[stack]
            + self.pick_text(CONVENTIONS_OVERRIDES)
        )
        if self.rng.random() < MALFORMED_LAYOUT:
            text = self.pick_text(MALFORMED_TOP) + text
        return text

    def ledger(self) -> str:
        """Return one ledger text over the slice, with the shapes the grading reads branch on."""
        count = self.rng.randint(0, MAX_RECORDS)
        lines = [
            json.dumps(self.record(no), ensure_ascii=False)
            for no in range(1, count + 1)
        ]
        if self.rng.random() < GARBAGE_LINE:
            lines.append("not json")
        return "".join(line + "\n" for line in lines)

    def record(self, line_no: int) -> Raw:
        """Return one record the grading engine reads, sometimes malformed."""
        kind = self.pick(list(_FIELDS))
        raw: Raw = {
            "type": kind,
            "req_id": self.pick([REQ_ID, REQ_ID, REQ_ID, OTHER_REQ_ID, None]),
            "ts": "2026-07-06T10:00:00Z",
            "author": self.pick(
                [*FLOOR, "feature-implementer", "review-plan-engine", ""]
            ),
        }
        raw.update(_FIELDS[kind](self, line_no))
        return raw


def _prd_entry(g: Generator, _line_no: int) -> Raw:
    return {
        "title": "Adding",
        "test_names": g.pick([[*TEST_NAMES], ["shouldAddTwo"], "x", None]),
    }


def _design_block(g: Generator, line_no: int) -> Raw:
    return {
        "verdict": g.pick(["covered", "minor", "new", "foundational", None]),
        "supersedes_record_at": g.pick([None, None, 1, line_no - 1, "1"]),
        "implementation_effort": g.pick([None, "routine", "involved"]),
    }


def _build_pass(g: Generator, _line_no: int) -> Raw:
    return {"gate_checks_run": g.pick([["build", "test"], []])}


def _build_failure(g: Generator, _line_no: int) -> Raw:
    return {"retry": g.pick([1, 2, None]), "failed_check": "test"}


def _review_feedback(g: Generator, _line_no: int) -> Raw:
    location = g.pick(
        [
            "src/main/java/com/acme/Foo.java:1",
            "docs/prd.md:3",
            "internal/app/foo.go:2",
            None,
        ]
    )
    return {
        "verdict": g.pick(["approved", "changes_requested", "blocked", None]),
        "findings": g.pick(
            [
                [],
                [{"tag": "autofix", "location": location, "description": "d"}],
                [
                    {
                        "tag": "blocked",
                        "severity": "critical",
                        "location": location,
                        "description": "d",
                    }
                ],
                "x",
            ]
        ),
    }


def _review_plan(g: Generator, _line_no: int) -> Raw:
    return {
        "risk": g.pick(["low", "high", "gray"]),
        "roster": g.pick([None, [], list(FLOOR[:1]), ["nobody"]]),
        "scope": g.pick(["surface", "full-diff", "fix-delta"]),
        "basis": g.pick(
            [
                {
                    "tree_sha": "BASE_TREE",
                    "files": [{"path": "README.md", "review_kind": "docs"}],
                },
                {"tree_sha": "BASE_TREE", "files": None},
                {"tree_sha": "-x"},
                {},
                "x",
            ]
        ),
    }


def _consultation_request(g: Generator, _line_no: int) -> Raw:
    return {"target": g.pick(["system-design-expert", "human"]), "question": "why?"}


_FIELDS = {
    "prd-entry": _prd_entry,
    "design-block": _design_block,
    "build-pass": _build_pass,
    "build-failure": _build_failure,
    "review-feedback": _review_feedback,
    "review-plan": _review_plan,
    "consultation-request": _consultation_request,
}


def git(repo: Path, *args: str) -> str:
    """Run git in the repository and return its stdout."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def build_repository(project: Project, repo: Path) -> Fixture:
    """Materialize the project as a git repository and return where it lives."""
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.name", SOME_AUTHOR[0])
    git(repo, "config", "user.email", SOME_AUTHOR[1])
    # No background maintenance: a copy of the repository must never race git.
    git(repo, "config", "gc.auto", "0")
    _write(repo, ".gitignore", GITIGNORE.encode("utf-8"))
    for path, text in project.docs.items():
        _write(repo, path, text.encode("utf-8"))
    for path, body in project.base_files.items():
        _write(repo, path, body)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    base_tree = git(repo, "rev-parse", "HEAD^{tree}")
    for path, change in project.changed_files.items():
        if change is None:
            (repo / path).unlink()
        else:
            _write(repo, path, change)
    if project.committed:
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "change")
    (repo / ".scratch").mkdir()
    ledger = project.ledger.replace("BASE_TREE", base_tree)
    (repo / ".scratch" / "handoff.jsonl").write_text(ledger, encoding="utf-8")
    return Fixture(repo, base)


def _write(repo: Path, path: str, body: bytes) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


def install_runtime(tree: Path, project: Project, repo: Path) -> None:
    """Copy the tree's shipped scripts and schemas into the repository, under the project's layout."""
    scripts = repo / "scripts"
    shutil.copytree(
        tree / differential.SCRIPTS,
        scripts,
        ignore=shutil.ignore_patterns("tests", "__pycache__"),
    )
    defaults = (
        tree / "harness" / "stacks" / project.stack / "scripts" / "layout-defaults.toml"
    )
    shutil.copy2(defaults, scripts / "layout-defaults.toml")
    (scripts / "layout.toml").write_text(project.layout, encoding="utf-8")
    shutil.copytree(tree / "harness" / "core" / "schemas", repo / "schemas")


def commands(project: Project, base: str) -> list[tuple[str, str, list[str]]]:
    """Return the command sequence one project runs: (label, script, argv), in order."""
    changeset, grading = "changeset", "grading"
    committed = ["--base", base, "--head", "HEAD"]
    churn = ["--churn"] if project.churn else []
    sequence = [
        ("changeset", changeset, []),
        ("changeset --name-only", changeset, ["--name-only"]),
        ("changeset --head HEAD", changeset, ["--head", "HEAD"]),
        ("changeset --base-tree HEAD", changeset, ["--base-tree", "HEAD"]),
        ("contracts-sync", grading, ["contracts-sync", "--feature", REQ_ID]),
        ("contracts-sync bad id", grading, ["contracts-sync", "--feature", "bad"]),
        ("coverage-map", grading, ["coverage-map", "--feature", REQ_ID]),
        ("conventions-map", grading, ["conventions-map"]),
        ("extract", grading, ["extract", "--feature", REQ_ID, *churn]),
        ("review-plan", grading, ["review-plan", "--feature", REQ_ID]),
        (
            "extract --head HEAD",
            grading,
            ["extract", "--feature", REQ_ID, "--head", "HEAD"],
        ),
    ]
    if project.committed:
        sequence += [
            ("changeset committed", changeset, committed),
            ("conventions-map committed", grading, ["conventions-map", *committed]),
            (
                "extract committed",
                grading,
                ["extract", "--feature", REQ_ID, *committed, *churn],
            ),
            (
                "review-plan committed",
                grading,
                ["review-plan", "--feature", REQ_ID, *committed],
            ),
        ]
    return sequence


def run_project(
    tree: Path, project: Project, fixture: Fixture, copy: Path
) -> list[tuple[str, differential.Outcome]]:
    """Run the project's command sequence through one tree and return every labeled outcome."""
    shutil.copytree(fixture.path, copy, symlinks=True)
    install_runtime(tree, project, copy)
    outcomes = []
    for label, script, argv in commands(project, fixture.base):
        outcome = differential.run_script(
            copy / "scripts" / f"{script}.py", argv, cwd=copy
        )
        outcomes.append((label, _unpath(outcome, copy)))
    ledger = (copy / ".scratch" / "handoff.jsonl").read_text(encoding="utf-8")
    outcomes.append(
        ("ledger", differential.Outcome(0, differential.normalize(ledger), ""))
    )
    return outcomes


def _unpath(outcome: differential.Outcome, copy: Path) -> differential.Outcome:
    mask = str(copy)
    return differential.Outcome(
        outcome.code,
        outcome.stdout.replace(mask, "<repo>"),
        outcome.stderr.replace(mask, "<repo>"),
    )


def compare_project(
    generator: Generator, index: int, trees: differential.Trees, scratch: Path
) -> list[differential.Difference]:
    """Run one synthetic project through both trees and collect the differences."""
    project = generator.project()
    fixture = build_repository(project, scratch / f"fixture-{index}")
    runs = [
        run_project(tree, project, fixture, scratch / f"{tag}-{index}")
        for tree, tag in zip(trees, ("baseline", "candidate"), strict=True)
    ]
    found = [
        differential.Difference(f"project {index} ({project.stack}) {label}", old, new)
        for (label, old), (_label, new) in zip(runs[0], runs[1], strict=True)
        if old != new
    ]
    for path in (
        fixture.path,
        scratch / f"baseline-{index}",
        scratch / f"candidate-{index}",
    ):
        shutil.rmtree(path)
    return found


def main(argv: list[str]) -> int:
    """Fuzz both trees and print every difference; exit 1 when any exists."""
    parser = argparse.ArgumentParser(
        description="differential fuzz of the grading commands"
    )
    parser.add_argument(
        "--baseline", required=True, help="a checkout to compare against"
    )
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT, help="projects to generate"
    )
    args = parser.parse_args(argv[1:])
    try:
        baseline = differential.resolve_tree(args.baseline, differential.GRADING)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    generator = Generator(args.seed)
    trees = differential.Trees(baseline, ROOT)
    differences = 0
    with tempfile.TemporaryDirectory() as scratch:
        for index in range(args.count):
            for difference in compare_project(generator, index, trees, Path(scratch)):
                differences += 1
                print(differential.report(difference))
    print(f"seed {args.seed}: {args.count} projects, {differences} differences")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
