"""The battery aggregator and run harness (ADR 2026-07-18
check-sync-decomposition): the Battery step/failure aggregator, the git
porcelain snapshot, shell-script discovery, and the shared render-and-compare
core (check_render_faithful) the two faithfulness checks parameterize. Imports
only the text leaf; the checks modules import this, never the reverse."""

import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

from check_sync.text import ROOT


class Battery:
    def __init__(self, quick: bool, strict: bool = False) -> None:
        self.quick = quick
        self.strict = strict
        self.failed = False

    def note(self, title: str) -> None:
        print(f"== {title} ==")

    def fail(self, message: str) -> None:
        print(f"FAIL: {message}", file=sys.stderr)
        self.failed = True

    def show_fail(self, output: str) -> None:
        """A failed sub-suite's output with the passing noise dropped."""
        lines = [l for l in output.splitlines() if not l.startswith("ok")]
        for line in lines[-40:]:
            print(f"    {line}", file=sys.stderr)

    def skip(self, message: str) -> None:
        print(f"  SKIP ({message})")

    def run_suite(
        self,
        label: str,
        script: str,
        skip_re: str | None = None,
        skip_label: str | None = None,
    ) -> None:
        """Run a battery sub-suite, aggregating its failure like every step."""
        runner = [sys.executable] if script.endswith(".py") else ["bash"]
        self.note(label)
        if self.quick:
            self.skip("--quick: inputs proven untouched by the guard")
            return
        result = subprocess.run(
            runner + [str(ROOT / script)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            self.fail(f"{script} did not pass:")
            self.show_fail(output)
        elif skip_re and re.search(skip_re, output, re.M):
            print(f"  {skip_label}")
        else:
            print("  pass")


def git_status(*paths: str) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    return result.stdout


def _shell_scripts(base: Path) -> Iterator[Path]:
    """Every shell script under base: *.sh plus extensionless shebang scripts.

    The .sh glob alone missed tools/claude-pod/claude-pod — the 400-line
    launcher shipped as a command, exactly the file with the most bash surface.
    An extensionless file counts when its shebang interpreter resolves to sh or
    bash — through env, and tolerant of shebang arguments (`#!/bin/bash -eu`)."""
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix == ".sh":
            yield f
        elif not f.suffix:
            try:
                with f.open("rb") as fh:
                    first = fh.readline(120).rstrip()
            except OSError:
                continue
            if not first.startswith(b"#!"):
                continue
            tokens = first[2:].split()
            interp = tokens[0].rsplit(b"/", 1)[-1] if tokens else b""
            if interp == b"env" and len(tokens) > 1:
                interp = tokens[1]
            if interp in (b"sh", b"bash"):
                yield f


def check_render_faithful(
    b: Battery,
    paths: tuple[str, ...],
    cmd: list[str],
    changed_msg: str,
    fix_msg: str,
    on_result: Callable[[subprocess.CompletedProcess[str]], None] | None = None,
) -> bool:
    """Shared core of the two faithfulness checks (steps 3 and 7): snapshot
    git status over paths, run the deterministic render, re-snapshot, and fail
    with a before/after set diff plus the fix hint when the render changed the
    tree. on_result(result) runs between render and compare — the per-check
    hook for return-code handling and output parsing; it may b.fail or abort.
    Returns True when the render left the tree unchanged."""
    before = git_status(*paths)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
    if on_result:
        on_result(result)
    after = git_status(*paths)
    if before != after:
        b.fail(changed_msg)
        before_set, after_set = set(before.splitlines()), set(after.splitlines())
        for line in sorted(before_set - after_set):
            print(f"  < {line}", file=sys.stderr)
        for line in sorted(after_set - before_set):
            print(f"  > {line}", file=sys.stderr)
        print(fix_msg, file=sys.stderr)
        return False
    return True
