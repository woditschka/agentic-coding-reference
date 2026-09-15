"""Run one shipped command through two trees and compare what each prints.

The runner behind the contract nets: a tree is a checkout of the reference,
the command is a shipped script with its arguments, and the outcome is the
exit code, stdout, and stderr with the stamped timestamps masked. A crash
compares by its exception line alone, so two trees that fail the same way
agree. Stdlib only.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

SCRIPTS = Path("harness") / "core" / "scripts"
HANDOFF = SCRIPTS / "handoff.py"
GRADING = SCRIPTS / "grading.py"
CHANGESET = SCRIPTS / "changeset.py"
SAMPLE = Path("samples") / "java-spring-boot"
LEDGER_ROOT = Path("evals") / "results" / "runs"
_STAMP = re.compile(r'"ts": "\d{4}-\d\d-\d\dT[0-9:.+Zz-]+"')
_MASKED_STAMP = '"ts": "T"'


class Outcome(NamedTuple):
    """What one handoff command printed: the exit code and both channels, normalized."""

    code: int
    stdout: str
    stderr: str


class Trees(NamedTuple):
    """The two checkouts a comparison runs through."""

    baseline: Path
    candidate: Path


class Difference(NamedTuple):
    """One command whose two outcomes differ."""

    label: str
    baseline: Outcome
    candidate: Outcome


def run_handoff(tree: Path, argv: list[str], stdin: str | None = None) -> Outcome:
    """Run `scripts/handoff.py argv` from a tree, in its Java sample, and normalize the outcome."""
    return run_script(tree / HANDOFF, argv, cwd=tree / SAMPLE, stdin=stdin)


def run_script(
    script: Path, argv: list[str], *, cwd: Path, stdin: str | None = None
) -> Outcome:
    """Run one shipped script from a working directory and normalize what it printed."""
    proc = subprocess.run(
        [sys.executable, "-E", "-B", str(script), *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        input=stdin,
        check=False,
    )
    return Outcome(proc.returncode, normalize(proc.stdout), normalize(proc.stderr))


def normalize(text: str) -> str:
    """Mask stamped timestamps and collapse a traceback to its exception line."""
    text = _STAMP.sub(_MASKED_STAMP, text)
    if "Traceback" in text:
        return "CRASH " + text.strip().splitlines()[-1]
    return text


def compare(
    label: str, trees: Trees, argv: list[str], stdin: str | None = None
) -> Difference | None:
    """Run one command through both trees and return the difference, or None when they agree."""
    old = run_handoff(trees.baseline, argv, stdin)
    new = run_handoff(trees.candidate, argv, stdin)
    return None if old == new else Difference(label, old, new)


def report(difference: Difference) -> str:
    """Render one difference for the terminal."""
    old, new = difference.baseline, difference.candidate
    return (
        f"DIFF {difference.label}\n"
        f"  baseline:  rc={old.code} stdout={old.stdout[:300]!r} stderr={old.stderr[:300]!r}\n"
        f"  candidate: rc={new.code} stdout={new.stdout[:300]!r} stderr={new.stderr[:300]!r}"
    )


def resolve_tree(argument: str, entry: Path = HANDOFF) -> Path:
    """Return the tree a --baseline argument names, or raise when it holds no such entry."""
    tree = Path(argument).expanduser().resolve()
    if not (tree / entry).is_file():
        raise ValueError(f"{tree} holds no {entry}")
    return tree
