"""Confine the filesystem writes of the producer tools to the roots each declares.

Every write resolves its target and refuses one outside the declared scope; the
battery's write gate proves every producer write funnels through here. Pure
producer: never copied into a plugin.
"""

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

__all__ = [
    "WriteOutsideScopeError",
    "copy",
    "mkdir",
    "remove_tree",
    "unlink",
    "write_scope",
    "write_text",
]


class WriteOutsideScopeError(RuntimeError):
    """A producer tool tried to write outside its declared write_scope()."""


# Fail closed: with no scope open the default is empty, so every write raises.
# Each entry point opens exactly one scope in main(); a ContextVar (not a bare
# global) keeps the declaration re-entrant and thread/async-safe.
_scope: ContextVar[tuple[Path, ...]] = ContextVar("write_scope", default=())


@contextmanager
def write_scope(*roots: Path) -> Iterator[None]:
    """Declare the directory roots the enclosed code may write under."""
    # An inner scope replaces the outer roots until exit, narrowing rather
    # than widening; a write outside them raises WriteOutsideScopeError.
    resolved = tuple(root.resolve() for root in roots)
    token = _scope.set(resolved)
    try:
        yield
    finally:
        _scope.reset(token)


def _guard(dst: Path, *, follow: bool = True) -> Path:
    # follow=False resolves only the parent: a delete verb acts on the entry
    # itself, so a symlink is removed as a link and never dereferenced into a
    # target outside the scope.
    p = Path(dst)
    real = p.resolve() if follow else p.parent.resolve() / p.name
    roots = _scope.get()
    if not any(real == root or root in real.parents for root in roots):
        declared = [str(r) for r in roots] or "(none — no write_scope open)"
        raise WriteOutsideScopeError(
            f"write to {real} is outside the declared roots {declared}"
        )
    return real


def mkdir(dst: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
    """Create a directory inside the declared scope."""
    _guard(dst).mkdir(parents=parents, exist_ok=exist_ok)


def copy(src: Path, dst: Path) -> None:
    """Copy one file to dst with its metadata, so a materialized copy keeps the source mtime."""
    shutil.copy2(src, _guard(dst))


def write_text(dst: Path, data: str, *, encoding: str = "utf-8") -> None:
    """Write text to dst atomically through a sibling temp file, keeping an existing target's mode."""
    # An interrupted write never truncates an existing file; a filled
    # executable skeleton keeps its +x; the pid-suffixed temp cannot collide
    # across concurrent runs.
    real = _guard(dst)
    tmp = real.with_name(f"{real.name}.write_guard.{os.getpid()}.tmp")
    try:
        tmp.write_text(data, encoding=encoding)
        try:
            tmp.chmod(real.stat().st_mode & 0o7777)
        except FileNotFoundError:
            pass  # fresh target: the temp's umask-default mode stands
        tmp.replace(real)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def remove_tree(dst: Path) -> None:
    """Delete a tree inside the declared scope, ignoring errors."""
    shutil.rmtree(_guard(dst, follow=False), ignore_errors=True)


def unlink(dst: Path, *, missing_ok: bool = False) -> None:
    """Remove one entry inside the declared scope; a symlink is removed as the link itself."""
    _guard(dst, follow=False).unlink(missing_ok=missing_ok)
