#!/usr/bin/env python3
"""Prune retired engine files from a consumer project on the marketplace channel.

    python3 prune-retired.py <plugin-root> <target-dir> [--dry-run]

Removes each path of the plugin's bundled retired-paths manifest present in
the target, bounded to the engine-sliver namespaces this channel's installs
own and to paths that resolve inside the target; anything else is reported
for hand removal. Runs from the read-only plugin cache; stdlib only.
"""

import os
import re
import sys
import tomllib

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

USAGE = "usage: prune-retired.py <plugin-root> <target-dir> [--dry-run]"
POSITIONAL_ARGS = 2
USAGE_EXIT = 2
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
# The agent bodies of a copy-channel install never fall under a prune.
_NEVER_PRUNED_PREFIX = ".claude/agents/"


def _printable(text: str) -> str:
    return _CTRL_RE.sub("", text)


def parse_manifest(text: str) -> list[str]:
    """Return the manifest entries minus comments, blanks, and any hostile or malformed shape."""
    # The producer battery validates the manifest; this is defense in depth.
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
    """Return the deletable namespaces from the bundled registry, or None when it is unreadable."""
    # The bundled registry sits beside this script in the plugin cache.
    sys.path.insert(0, str(plugin_root))
    try:
        from registry import ENGINE_SLIVER  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — any import defect means report-only
        return None
    return tuple(f"{p.rstrip('/')}/" for p in ENGINE_SLIVER)


def declared_extensions(target: Path) -> list[str] | None:
    """Return the declared extension entries, or None when the layout exists and cannot be read."""
    layout = target / "scripts" / "layout.toml"
    if not layout.is_file():
        return []
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
    """Report whether a path is one of the prefixes or beneath one."""
    return any(
        path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/") for p in prefixes
    )


def _contained(candidate: Path, target_resolved: Path) -> bool:
    # A symlink, or a path through one, that resolves outside is never deleted.
    try:
        return candidate.resolve(strict=True).is_relative_to(target_resolved)
    except OSError:
        return False


def _dir_files(base: Path) -> list[Path]:
    # os.walk with followlinks=False: pathlib's rglob follows directory
    # symlinks on Python 3.11 and 3.12.
    found: list[Path] = []
    for root, _dirs, files in os.walk(base, followlinks=False):
        found.extend(Path(root) / name for name in files)
    return sorted(found)


def _candidates(target: Path, entry: str) -> list[Path]:
    if entry.endswith("/"):
        base = target / entry.rstrip("/")
        return _dir_files(base) if base.is_dir() and not base.is_symlink() else []
    path = target / entry
    return [path] if path.is_file() else []


class Pruner:
    """One prune over a target: the manifest, the plugin's produced set, and the guards."""

    def __init__(self, plugin_root: Path, target: Path, *, dry_run: bool) -> None:
        """Read the produced set, the sliver, and the target's declared extensions."""
        self.target = target
        self.target_resolved = target.resolve()
        self.dry_run = dry_run
        self.sliver = engine_sliver(plugin_root)
        engine = plugin_root / "_engine"
        self.produced = {
            p.relative_to(engine).as_posix() for p in engine.rglob("*") if p.is_file()
        }
        self.extensions = declared_extensions(target)
        self.removed = 0

    def prune_file(self, candidate: Path) -> None:
        """Remove one candidate, or report why it stays."""
        rel = candidate.relative_to(self.target).as_posix()
        shown = _printable(rel)
        # A path the current plugin still produces wins over a stale manifest.
        if rel in self.produced or rel.startswith(_NEVER_PRUNED_PREFIX):
            return
        if under(rel, self.extensions or []):
            print(f"prune: kept {shown} (declared extension)")
            return
        if self.sliver is None or not under(rel, self.sliver):
            # Outside the namespaces this channel's installs own, a consumer
            # file at a colliding name would be unrecoverable.
            print(
                f"prune: retired path present, not auto-removed: {shown} "
                "— remove by hand, or declare it in [harness] extensions "
                "to keep it"
            )
            return
        if not _contained(candidate, self.target_resolved):
            print(f"prune: skipped {shown} (resolves outside the project)")
            return
        if self.dry_run:
            print(f"prune: would remove {shown} (retired)")
        else:
            candidate.unlink()
            print(f"prune: removed {shown} (retired)")
        self.removed += 1

    def remove_empty_dirs(self, entry: str) -> None:
        """Remove a fully emptied retired directory tree bottom-up, keeping any dir a kept file lives in."""
        base = self.target / entry.rstrip("/")
        if self.dry_run or not base.is_dir() or base.is_symlink():
            return
        subdirs = sorted(
            (p for p in base.rglob("*") if p.is_dir() and not p.is_symlink()),
            reverse=True,
        )
        for d in subdirs:
            if not any(d.iterdir()):
                d.rmdir()
        if not any(base.iterdir()):
            base.rmdir()


def prune(plugin_root: Path, target: Path, *, dry_run: bool) -> int:
    """Prune the target against the plugin's manifest and return the exit code."""
    manifest = plugin_root / "retired-paths.txt"
    if not manifest.is_file():
        print("prune: no bundled retired-paths.txt — nothing to prune")
        return 0
    entries = parse_manifest(manifest.read_text(encoding="utf-8"))
    pruner = Pruner(plugin_root, target, dry_run=dry_run)
    if pruner.sliver is None:
        print(
            "prune: bundled registry unreadable — reporting only, removing "
            "nothing (fail-safe)",
            file=sys.stderr,
        )
    if pruner.extensions is None:
        print(
            "prune: scripts/layout.toml unparseable — pruning nothing "
            "(fail-safe; fix the [harness] table and re-run setup)",
            file=sys.stderr,
        )
        return 0
    for entry in entries:
        for candidate in _candidates(target, entry):
            pruner.prune_file(candidate)
        if entry.endswith("/"):
            pruner.remove_empty_dirs(entry)
    if pruner.removed == 0:
        print("prune: no retired files removed")
    return 0


def main(argv: list[str]) -> int:
    """Prune from the command line and return the exit code."""
    args = [a for a in argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in argv[1:]
    if len(args) != POSITIONAL_ARGS:
        print(USAGE, file=sys.stderr)
        return USAGE_EXIT
    return prune(Path(args[0]).resolve(), Path(args[1]).resolve(), dry_run=dry_run)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
