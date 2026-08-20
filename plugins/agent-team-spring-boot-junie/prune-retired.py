#!/usr/bin/env python3
"""Prune retired engine files from a consumer project (marketplace channel).

    python3 prune-retired.py <plugin-root> <target-dir> [--dry-run]

Reads the plugin's bundled retired-paths.txt — the cumulative manifest of
consumer-relative paths the harness once produced and no longer does — and
removes each one present in the target. Deletion is bounded by two hard rules,
then guarded:

- Only paths inside the engine-sliver namespaces (registry.ENGINE_SLIVER —
  scripts/, schemas/scratch/, .claude/templates/) are ever deleted: the space
  this channel's installs provably own. A manifest entry outside them (a
  copy-channel migration leftover such as a retired skill directory) is
  REPORTED for hand removal, never deleted — a consumer-authored file at a
  colliding name is indistinguishable from debris there.
- Only paths that resolve inside the target are ever deleted: a candidate
  whose resolved real path escapes the target (a symlink, or a file behind a
  symlinked directory) is skipped. Mirrors write_guard's follow=False rule,
  which this cache-shipped script cannot import.

Guards on the remainder: a path the current plugin still produces (present
under _engine/) is never pruned — a reintroduced path wins over a stale
manifest; a path under a declared `[harness] extensions` entry is kept and
reported; an unparseable layout.toml prunes nothing (fail-safe).

Every removal prints one report line (control characters stripped — path
names are consumer-filesystem input). A removal is permanent: retired paths
are gitignored on this channel and setup no longer ships them, so declare a
project's own file in `[harness] extensions` BEFORE re-running setup.
--dry-run reports without removing.

Stdlib only; runs from the read-only plugin cache (no bytecode written).
"""

import os
import re
import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def _printable(text: str) -> str:
    return _CTRL_RE.sub("", text)


def parse_manifest(text: str) -> list[str]:
    """Manifest lines minus whole-line comments and blanks; hostile or
    malformed shapes dropped — the producer battery validates the manifest,
    this is defense in depth. Dropped: absolute paths, dot-dot traversal,
    the bare project root (`.`, `./`), embedded `#`, internal whitespace."""
    entries = []
    for raw in text.splitlines():
        if raw.lstrip().startswith("#"):
            continue
        entry = raw.strip()
        if not entry:
            continue
        parts = Path(entry).parts
        if (
            Path(entry).is_absolute()
            or ".." in parts
            or "." in parts
            or not parts
            or "#" in entry
            or any(ch.isspace() for ch in entry)
        ):
            continue
        entries.append(entry)
    return entries


def engine_sliver(plugin_root: Path) -> tuple[str, ...] | None:
    """The deletable namespaces, from the bundled registry's ENGINE_SLIVER.
    None when the bundled registry is missing or unreadable (fail-safe:
    report-only, delete nothing)."""
    sys.path.insert(0, str(plugin_root))
    try:
        from registry import ENGINE_SLIVER
    except Exception:  # noqa: BLE001 — any import defect means report-only
        return None
    return tuple(f"{p.rstrip('/')}/" for p in ENGINE_SLIVER)


def declared_extensions(target: Path) -> list[str] | None:
    """The [harness] extensions entries, or None when layout.toml exists but
    cannot be parsed (the fail-safe: prune nothing)."""
    layout = target / "scripts" / "layout.toml"
    if not layout.is_file():
        return []
    import tomllib

    try:
        table = tomllib.loads(layout.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return None
    harness = table.get("harness")
    if not isinstance(harness, dict):
        return []
    exts = harness.get("extensions", [])
    if not isinstance(exts, list) or not all(isinstance(e, str) for e in exts):
        return None
    return exts


def under(path: str, prefixes: list[str] | tuple[str, ...]) -> bool:
    return any(
        path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/") for p in prefixes
    )


def _contained(candidate: Path, target_resolved: Path) -> bool:
    """True when the candidate's real path stays inside the target — a
    symlink (or a path through one) that resolves outside is never deleted."""
    try:
        return candidate.resolve(strict=True).is_relative_to(target_resolved)
    except OSError:
        return False


def _dir_files(base: Path) -> list[Path]:
    """Files under base, never following directory symlinks (os.walk
    followlinks=False — pathlib's rglob follows them on Python 3.11/3.12)."""
    found: list[Path] = []
    for root, _dirs, files in os.walk(base, followlinks=False):
        found.extend(Path(root) / name for name in files)
    return sorted(found)


def prune(plugin_root: Path, target: Path, dry_run: bool) -> int:
    manifest = plugin_root / "retired-paths.txt"
    if not manifest.is_file():
        print("prune: no bundled retired-paths.txt — nothing to prune")
        return 0
    entries = parse_manifest(manifest.read_text(encoding="utf-8"))
    sliver = engine_sliver(plugin_root)
    if sliver is None:
        print(
            "prune: bundled registry unreadable — reporting only, removing "
            "nothing (fail-safe)",
            file=sys.stderr,
        )
    engine = plugin_root / "_engine"
    produced = {
        p.relative_to(engine).as_posix() for p in engine.rglob("*") if p.is_file()
    }
    extensions = declared_extensions(target)
    if extensions is None:
        print(
            "prune: scripts/layout.toml unparseable — pruning nothing "
            "(fail-safe; fix the [harness] table and re-run setup)",
            file=sys.stderr,
        )
        return 0
    target_resolved = target.resolve()
    removed = 0
    for entry in entries:
        if entry.endswith("/"):
            base = target / entry.rstrip("/")
            candidates = (
                _dir_files(base) if base.is_dir() and not base.is_symlink() else []
            )
        else:
            f = target / entry
            candidates = [f] if f.is_file() else []
        for f in candidates:
            rel = f.relative_to(target).as_posix()
            shown = _printable(rel)
            if rel in produced or rel.startswith(".claude/agents/"):
                continue
            if under(rel, extensions):
                print(f"prune: kept {shown} (declared extension)")
                continue
            if sliver is None or not under(rel, sliver):
                # Outside the namespaces this channel's installs own: a
                # consumer file at a colliding name would be unrecoverable.
                print(
                    f"prune: retired path present, not auto-removed: {shown} "
                    "— remove by hand, or declare it in [harness] extensions "
                    "to keep it"
                )
                continue
            if not _contained(f, target_resolved):
                print(f"prune: skipped {shown} (resolves outside the project)")
                continue
            if dry_run:
                print(f"prune: would remove {shown} (retired)")
            else:
                f.unlink()
                print(f"prune: removed {shown} (retired)")
            removed += 1
        if not entry.endswith("/"):
            continue
        # A fully-emptied retired directory tree is itself debris; remove
        # empty dirs bottom-up, keeping any dir a kept file still lives in.
        base = target / entry.rstrip("/")
        if not dry_run and base.is_dir() and not base.is_symlink():
            subdirs = sorted(
                (p for p in base.rglob("*") if p.is_dir() and not p.is_symlink()),
                reverse=True,
            )
            for d in subdirs:
                if not any(d.iterdir()):
                    d.rmdir()
            if not any(base.iterdir()):
                base.rmdir()
    if removed == 0:
        print("prune: no retired files removed")
    return 0


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in argv[1:]
    if len(args) != 2:
        print(
            "usage: prune-retired.py <plugin-root> <target-dir> [--dry-run]",
            file=sys.stderr,
        )
        return 2
    return prune(Path(args[0]).resolve(), Path(args[1]).resolve(), dry_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
