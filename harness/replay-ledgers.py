#!/usr/bin/env python3
"""Replay every recorded eval ledger through a baseline tree and this one, and diff the decisions.

Usage: harness/replay-ledgers.py --baseline TREE [--ledgers DIR]

For every committed ledger under evals/results/runs (or DIR), every prefix of
the log is routed and the whole log is rendered in text, verbose text, and
Markdown, through both trees. A refactor that preserves behavior prints no
difference and exits 0. TREE is a checkout of the reference, typically a git
worktree at the last commit. Stdlib only. Tested by tests/test_replay_ledgers.py.
"""

import argparse
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import differential  # noqa: E402

ROOT = HERE.parent
VIEW_MODES: tuple[list[str], ...] = ([], ["--verbose"], ["--markdown"])


def ledgers(root: Path) -> list[Path]:
    """Return every recorded handoff ledger under the eval results, in path order."""
    return sorted(root.glob("v*/*/handoff.jsonl"))


def prefixes(ledger: Path) -> Iterator[tuple[int, bytes]]:
    """Yield the ledger's line-count prefixes as raw bytes, each newline-terminated."""
    lines = ledger.read_bytes().split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    for count in range(1, len(lines) + 1):
        yield count, b"\n".join(lines[:count]) + b"\n"


def replay(
    ledger: Path, trees: differential.Trees, scratch: Path
) -> list[differential.Difference]:
    """Route every prefix and render every view of one ledger through both trees."""
    log = scratch / "handoff.jsonl"
    label = (
        str(ledger.relative_to(ROOT)) if ledger.is_relative_to(ROOT) else str(ledger)
    )
    found: list[differential.Difference] = []
    for count, prefix in prefixes(ledger):
        log.write_bytes(prefix)
        difference = differential.compare(
            f"{label} route@{count}", trees, ["route", "--file", str(log)]
        )
        if difference is not None:
            found.append(difference)
    for mode in VIEW_MODES:
        difference = differential.compare(
            f"{label} view {' '.join(mode)}".rstrip(),
            trees,
            ["view", "--file", str(log), *mode],
        )
        if difference is not None:
            found.append(difference)
    return found


def main(argv: list[str]) -> int:
    """Replay the ledgers and print every difference; exit 1 when any exists."""
    parser = argparse.ArgumentParser(
        description="replay eval ledgers through two trees"
    )
    parser.add_argument(
        "--baseline", required=True, help="a checkout to compare against"
    )
    parser.add_argument(
        "--ledgers",
        default=str(ROOT / differential.LEDGER_ROOT),
        help="the runs directory",
    )
    args = parser.parse_args(argv[1:])
    try:
        baseline = differential.resolve_tree(args.baseline)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    recorded = ledgers(Path(args.ledgers))
    if not recorded:
        print(f"no ledgers under {args.ledgers}", file=sys.stderr)
        return 2
    trees = differential.Trees(baseline, ROOT)
    differences = 0
    with tempfile.TemporaryDirectory() as scratch:
        for ledger in recorded:
            for difference in replay(ledger, trees, Path(scratch)):
                differences += 1
                print(differential.report(difference))
            print(f"replayed {ledger.name} in {ledger.parent.name}", file=sys.stderr)
    print(f"{len(recorded)} ledgers, {differences} differences")
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
