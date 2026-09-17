#!/usr/bin/env python3
"""Keep the retired-paths manifest: the consumer-relative runtime paths the harness once produced and no longer does.

    harness/retired_paths.py update <since-tag> <label>

The manifest is cumulative and append-only, so orphan classification becomes
set arithmetic: present minus produced minus extensions minus retired. The
update verb appends exactly the paths a tag produced that the working tree no
longer does; the release script runs it on every cut. Stdlib only.
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import USAGE_EXIT, runtime_files  # noqa: E402

ROOT = HERE.parent
MANIFEST = HERE / "retired-paths.txt"
USAGE = "usage: harness/retired_paths.py update <since-tag> <label>"
UPDATE_ARGS = 4

# Only core/ and stacks/ are runtime source: init/ scaffolds project-owned
# files, and marketplace/ is producer machinery.
_LAYER_ROOTS = ("harness/core", "harness/stacks")
_CACHE_DIRS = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
# A long-format ls-tree row, kept to blobs with a regular-file mode: a
# committed symlink never materializes, so it must not count as produced.
_BLOB_RE = re.compile(r"^100\d{3} blob [0-9a-f]+\t(.+)$")


def parse_manifest(text: str) -> tuple[list[str], list[str]]:
    """Parse manifest text into its entries, in file order, and the problems found."""
    # A trailing slash marks a directory prefix. Comments are whole-line only,
    # so an inline `#` is a problem rather than a silently inert entry.
    entries: list[str] = []
    problems: list[str] = []
    seen: set[str] = set()
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if raw.lstrip().startswith("#"):
            continue
        entry = raw.strip()
        if not entry:
            continue
        if raw != entry:
            problems.append(f"line {lineno}: surrounding whitespace on {entry!r}")
        problem = _entry_problem(entry)
        if problem is not None:
            problems.append(f"line {lineno}: {problem}")
            continue
        if entry in seen:
            problems.append(f"line {lineno}: duplicate entry {entry!r}")
            continue
        seen.add(entry)
        entries.append(entry)
    return entries, problems


def _entry_problem(entry: str) -> str | None:
    parts = Path(entry).parts
    if Path(entry).is_absolute() or ".." in parts:
        return f"absolute or traversing path {entry!r}"
    if not parts or "." in parts:
        return f"project-root entry {entry!r}"
    if "#" in entry or any(ch.isspace() for ch in entry):
        return f"embedded '#' or whitespace in {entry!r} (comments are whole-line only)"
    return None


def read_manifest(path: Path = MANIFEST) -> list[str]:
    """Return the manifest entries, and exit loud on a malformed file."""
    if not path.is_file():
        raise SystemExit(f"retired-paths: missing {path}")
    entries, problems = parse_manifest(path.read_text(encoding="utf-8"))
    if problems:
        raise SystemExit(
            f"retired-paths: malformed {path}:\n  " + "\n  ".join(problems)
        )
    return entries


def covered(path: str, entries: list[str]) -> bool:
    """Report whether the manifest retires a consumer-relative path, by exact entry or directory prefix."""
    return any(path == e or (e.endswith("/") and path.startswith(e)) for e in entries)


def _consumer_path(repo_path: str) -> str | None:
    # harness/core/<rel> -> <rel>, harness/stacks/<stack>/<rel> -> <rel>;
    # None outside the layers or at a layer root.
    if repo_path.startswith("harness/core/"):
        return repo_path[len("harness/core/") :]
    if repo_path.startswith("harness/stacks/"):
        rest = repo_path[len("harness/stacks/") :]
        _, _, rel = rest.partition("/")
        return rel or None
    return None


def produced_paths(ref: str | None) -> set[str]:
    """Return the union of every runtime file core and the stacks ship, at a git ref or in the working tree."""
    # Both sides apply the same exclusions as the runtime walk, so a filter
    # asymmetry never manufactures a retirement. A path one stack drops while
    # another ships stays produced.
    if ref is None:
        produced: set[str] = set(runtime_files(HERE / "core"))
        for stack_dir in sorted((HERE / "stacks").iterdir()):
            if stack_dir.is_dir():
                produced.update(runtime_files(stack_dir))
        return produced
    if not _REF_RE.fullmatch(ref):
        raise SystemExit(f"retired-paths: refusing suspicious git ref {ref!r}")
    listing = subprocess.run(
        ["git", "ls-tree", "-r", ref, "--", *_LAYER_ROOTS],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    return {
        consumer
        for consumer in map(_consumer_blob, listing.stdout.splitlines())
        if consumer is not None
    }


def _consumer_blob(line: str) -> str | None:
    blob = _BLOB_RE.match(line)
    if blob is None:
        return None
    consumer = _consumer_path(blob.group(1))
    if consumer is None or consumer.endswith(".pyc"):
        return None
    if _CACHE_DIRS.intersection(Path(consumer).parts):
        return None
    return consumer


def retired_since(tag: str) -> set[str]:
    """Return the paths the runtime source produced at the tag and no longer produces."""
    return produced_paths(tag) - produced_paths(None)


def update(tag: str, label: str, path: Path = MANIFEST) -> list[str]:
    """Append the uncovered paths retired since the tag under a dated section, and return them."""
    entries = read_manifest(path)
    missing = sorted(p for p in retired_since(tag) if not covered(p, entries))
    if not missing:
        return []
    section = f"\n# retired after {tag} ({label})\n" + "".join(
        f"{p}\n" for p in missing
    )
    with write_guard.write_scope(path.parent):
        write_guard.write_text(
            path, path.read_text(encoding="utf-8") + section, encoding="utf-8"
        )
    return missing


def main(argv: list[str]) -> int:
    """Run the update verb from the command line and return the exit code."""
    if len(argv) != UPDATE_ARGS or argv[1] != "update":
        print(USAGE, file=sys.stderr)
        return USAGE_EXIT
    tag, label = argv[2], argv[3]
    appended = update(tag, label)
    if appended:
        print(f"retired-paths: appended {len(appended)} path(s) since {tag}:")
        for p in appended:
            print(f"  {p}")
    else:
        print(f"retired-paths: manifest already covers everything since {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
