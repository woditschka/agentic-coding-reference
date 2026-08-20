#!/usr/bin/env python3
"""The retired-paths manifest: consumer-relative runtime paths the harness
once produced and no longer does.

    harness/retired_paths.py update <since-tag> <label>

The manifest (harness/retired-paths.txt) is cumulative and append-only: one
path per line, `#` comments and blank lines ignored, a trailing slash marks a
whole retired directory. It turns orphan classification into set arithmetic —
present − produced − extensions − retired — replacing per-file git
archaeology: materialize.py annotates manifest-listed extras, the marketplace
setup.sh prunes them via the bundled prune-retired.py, and the battery's
retired-paths check (checks/sync.py, step 3k) fails when a runtime path the
last v* tag produced is gone from the source without a manifest entry. The
`update` subcommand appends exactly that missing set; release-version.sh runs
it on every cut, so the record needs no human memory. A reintroduced path
must leave the manifest — the battery check enforces that direction too.

Stdlib only, producer-side (mypy --strict). Tested by test_retired_paths.py.
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MANIFEST = HERE / "retired-paths.txt"

# The runtime source layers whose files map to consumer-relative paths. Only
# core/ and stacks/ are runtime source: init/ scaffolds project-owned files,
# and marketplace/ is producer machinery.
_LAYER_ROOTS = ("harness/core", "harness/stacks")


def parse_manifest(text: str) -> tuple[list[str], list[str]]:
    """Parse manifest text into (entries, problems). Entries keep file order;
    a trailing slash marks a directory prefix. Comments are whole-line only —
    an inline `#` is a problem, not a comment (a silently inert entry
    otherwise). Problems also name duplicates, surrounding or internal
    whitespace, absolute paths, dot-dot traversal, and the bare project root
    (`.` / `./` — an entry that would cover everything)."""
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
        parts = Path(entry).parts
        if Path(entry).is_absolute() or ".." in parts:
            problems.append(f"line {lineno}: absolute or traversing path {entry!r}")
            continue
        if not parts or "." in parts:
            problems.append(f"line {lineno}: project-root entry {entry!r}")
            continue
        if "#" in entry or any(ch.isspace() for ch in entry):
            problems.append(
                f"line {lineno}: embedded '#' or whitespace in {entry!r} "
                "(comments are whole-line only)"
            )
            continue
        if entry in seen:
            problems.append(f"line {lineno}: duplicate entry {entry!r}")
            continue
        seen.add(entry)
        entries.append(entry)
    return entries, problems


def read_manifest(path: Path = MANIFEST) -> list[str]:
    """The manifest entries; loud (SystemExit) on a malformed file — callers
    that want to report instead of abort use parse_manifest directly."""
    if not path.is_file():
        raise SystemExit(f"retired-paths: missing {path}")
    entries, problems = parse_manifest(path.read_text(encoding="utf-8"))
    if problems:
        raise SystemExit(
            f"retired-paths: malformed {path}:\n  " + "\n  ".join(problems)
        )
    return entries


def covered(path: str, entries: list[str]) -> bool:
    """True when a consumer-relative path is retired by the manifest: an
    exact file entry, or under a directory entry (trailing slash)."""
    return any(path == e or (e.endswith("/") and path.startswith(e)) for e in entries)


def _consumer_path(repo_path: str) -> str | None:
    """Map a repo path under a runtime layer to its consumer-relative path:
    harness/core/<rel> -> <rel>, harness/stacks/<stack>/<rel> -> <rel>.
    None for a path outside the layers or a layer root itself."""
    if repo_path.startswith("harness/core/"):
        return repo_path[len("harness/core/") :]
    if repo_path.startswith("harness/stacks/"):
        rest = repo_path[len("harness/stacks/") :]
        _, _, rel = rest.partition("/")
        return rel or None
    return None


_CACHE_DIRS = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
# ls-tree long-format row: <mode> <type> <sha>\t<path>. Kept to blobs with a
# regular-file mode: symlinks (120000) never materialize (runtime_files
# skips them), so at-a-tag they must not count as produced — a committed
# symlink would otherwise register as a false retirement.
_BLOB_RE = re.compile(r"^100\d{3} blob [0-9a-f]+\t(.+)$")


def produced_paths(ref: str | None) -> set[str]:
    """The consumer-relative produced set — the union of every runtime file
    core/ and the stacks ship — at a git ref, or from the working tree when
    ref is None. Both sides apply the same exclusions (regular files only, no
    caches, no .pyc), mirroring registry.runtime_files, so retired_since
    never manufactures a retirement out of a filter asymmetry. Union across
    stacks on both sides: a path one stack drops while another still ships
    it stays produced and never enters the manifest — that stack's consumers
    keep the judgment path for it (accepted residual of a global manifest)."""
    if ref is None:
        sys.path.insert(0, str(HERE))
        from registry import runtime_files

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
    produced = set()
    for line in listing.stdout.splitlines():
        blob = _BLOB_RE.match(line)
        if blob is None:
            continue
        repo_path = blob.group(1)
        consumer = _consumer_path(repo_path)
        if consumer is None or consumer.endswith(".pyc"):
            continue
        if _CACHE_DIRS.intersection(Path(consumer).parts):
            continue
        produced.add(consumer)
    return produced


def retired_since(tag: str) -> set[str]:
    """Consumer-relative paths the runtime source produced at `tag` and no
    longer produces in the working tree — the exact set the manifest must
    cover before the next release."""
    return produced_paths(tag) - produced_paths(None)


def update(tag: str, label: str, path: Path = MANIFEST) -> list[str]:
    """Append the paths retired since `tag` that the manifest does not cover,
    under a `# retired after <tag> (<label>)` section. Idempotent: an empty
    missing set appends nothing. Returns the appended paths."""
    sys.path.insert(0, str(HERE))
    import write_guard

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
    if len(argv) == 4 and argv[1] == "update":
        appended = update(argv[2], argv[3])
        if appended:
            print(f"retired-paths: appended {len(appended)} path(s) since {argv[2]}:")
            for p in appended:
                print(f"  {p}")
        else:
            print(f"retired-paths: manifest already covers everything since {argv[2]}")
        return 0
    print(
        "usage: harness/retired_paths.py update <since-tag> <label>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
