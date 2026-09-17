"""Aggregate the battery's step verdicts and run its render-and-compare core."""

import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from verify_harness.text import ROOT

SHOWN_FAILURE_LINES = 40
SHEBANG_PROBE_BYTES = 120


class Battery:
    """Collect one run's step verdicts: notes and passes to stdout, failures to stderr."""

    def __init__(self, *, quick: bool, strict: bool = False) -> None:
        """Start a run: quick skips the guarded steps, strict fails on a missing tool."""
        self.quick = quick
        self.strict = strict
        self.failed = False

    def note(self, title: str) -> None:
        """Print a step header."""
        print(f"== {title} ==")

    def fail(self, message: str) -> None:
        """Record and print one failure."""
        print(f"FAIL: {message}", file=sys.stderr)
        self.failed = True

    def show_fail(self, output: str) -> None:
        """Print the tail of a failed sub-suite's output with the passing noise dropped."""
        lines = [line for line in output.splitlines() if not line.startswith("ok")]
        for line in lines[-SHOWN_FAILURE_LINES:]:
            print(f"    {line}", file=sys.stderr)

    def skip(self, message: str) -> None:
        """Print a step's skip line."""
        print(f"  SKIP ({message})")

    def record_pass(self, message: str) -> None:
        """Print a step's pass line."""
        print(f"  {message}")

    def report(self, problems: list[str], pass_line: str) -> None:
        """Fail once per problem, or print the pass line when there is none."""
        for problem in problems:
            self.fail(problem)
        if not problems:
            self.record_pass(pass_line)

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
            [*runner, str(ROOT / script)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            self.fail(f"{script} did not pass:")
            self.show_fail(output)
        elif skip_re and re.search(skip_re, output, re.MULTILINE):
            self.record_pass(skip_label or "skip")
        else:
            self.record_pass("pass")


def git_status(*paths: str) -> str:
    """Return the porcelain status of the given paths."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    return result.stdout


def _shebang_interpreter(path: Path) -> bytes:
    """Return the interpreter name a file's shebang resolves to, or b"" without one."""
    try:
        with path.open("rb") as handle:
            first = handle.readline(SHEBANG_PROBE_BYTES).rstrip()
    except OSError:
        return b""
    if not first.startswith(b"#!"):
        return b""
    tokens = first[2:].split()
    interpreter = tokens[0].rsplit(b"/", 1)[-1] if tokens else b""
    if interpreter == b"env" and len(tokens) > 1:
        interpreter = tokens[1]
    return interpreter


def shell_scripts(base: Path) -> Iterator[Path]:
    """Yield every shell script under base: *.sh plus extensionless sh or bash commands."""
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix == ".sh" or (
            not path.suffix and _shebang_interpreter(path) in (b"sh", b"bash")
        ):
            yield path


@dataclass(frozen=True, slots=True)
class RenderCheck:
    """One deterministic render whose tracked paths must come back unchanged."""

    paths: tuple[str, ...]
    command: tuple[str, ...]
    changed_message: str
    fix_message: str


def check_render_faithful(
    b: Battery,
    render: RenderCheck,
    on_result: Callable[[subprocess.CompletedProcess[str]], None] | None = None,
) -> bool:
    """Run a render between two status snapshots and fail on any change it introduced."""
    before = git_status(*render.paths)
    result = subprocess.run(
        list(render.command), capture_output=True, text=True, cwd=ROOT, check=False
    )
    if on_result:
        on_result(result)
    after = git_status(*render.paths)
    if before == after:
        return True
    before_set, after_set = set(before.splitlines()), set(after.splitlines())
    detail = [
        *(f"  < {line}" for line in sorted(before_set - after_set)),
        *(f"  > {line}" for line in sorted(after_set - before_set)),
        render.fix_message,
    ]
    b.fail(render.changed_message + "\n" + "\n".join(detail))
    return False
