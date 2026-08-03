"""Confined filesystem writes for the producer tools that rewrite whole trees
(materialize.py, package-marketplace.py, init.py, render-agent-mirrors.py).

Every write goes through _guard, which resolves the target and rejects anything
outside the roots the tool declared with write_scope(). The verify-harness write
gate (verify_harness/checks/confinement.py) bans raw write primitives outside this
module's sanctioned-writers allowlist, so the choke-point cannot be bypassed:
static proves every write funnels here, and _guard proves the resolved path is
in a declared root. Together they confine each tool to an enumerated destination
(ADR 2026-07-19 network-write-confinement-gate).

Pure producer: never copied into a plugin. The marketplace refreshers write a
single argv target and stay stdlib-only sanctioned sites, so they never import
this module."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

__all__ = [
    "WriteOutsideScopeError",
    "write_scope",
    "mkdir",
    "copy",
    "write_text",
    "remove_tree",
    "unlink",
]


class WriteOutsideScopeError(RuntimeError):
    """A producer tool tried to write outside its declared write_scope()."""


# Fail closed: with no scope open the default is empty, so every write raises.
# Each entry point opens exactly one scope in main(); a ContextVar (not a bare
# global) keeps the declaration re-entrant and thread/async-safe.
_scope: ContextVar[tuple[Path, ...]] = ContextVar("write_scope", default=())


@contextmanager
def write_scope(*roots: Path) -> Iterator[None]:
    """Declare the directory roots the enclosed code may write under. An inner
    scope REPLACES the outer roots until exit (narrowing, not union); exit
    restores the outer scope. A write to any path not at or under one of these
    resolved roots raises WriteOutsideScopeError."""
    resolved = tuple(root.resolve() for root in roots)
    token = _scope.set(resolved)
    try:
        yield
    finally:
        _scope.reset(token)


def _guard(dst: Path, *, follow: bool = True) -> Path:
    """Resolve dst and confirm it is at or under a declared root, else raise.
    Returns the resolved path so callers write to the canonical location.
    follow=False resolves only the parent: the delete verbs act on the entry
    itself — a symlink is removed as a link, never dereferenced into its
    target (which may sit outside the scope)."""
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
    _guard(dst).mkdir(parents=parents, exist_ok=exist_ok)


def copy(src: Path, dst: Path) -> None:
    """Copy one file to dst, metadata included (shutil.copy2 — the materialized
    copies keep source mtimes). src is a read, so only dst is guarded."""
    shutil.copy2(src, _guard(dst))


def write_text(dst: Path, data: str, *, encoding: str = "utf-8") -> None:
    """Atomically write text to dst: stage a sibling temp under the same
    (guarded) directory, then replace onto the target, so an interrupted write
    never truncates an existing file. An existing target keeps its mode — a
    filled executable skeleton keeps its +x; a fresh target takes the umask
    default. The pid-suffixed temp cannot collide across concurrent runs and
    is cleaned up on failure."""
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
    """Recursively delete a tree (ignore_errors, matching the call sites it
    replaces). A delete is a write, so the target is guarded — as the entry
    itself (follow=False): rmtree refuses a symlink, so a link is never a
    door to a tree outside the scope."""
    shutil.rmtree(_guard(dst, follow=False), ignore_errors=True)


def unlink(dst: Path, *, missing_ok: bool = False) -> None:
    """Remove one entry. A symlink is removed as the link itself, never
    dereferenced — pruning a linked mirror must not delete its target."""
    _guard(dst, follow=False).unlink(missing_ok=missing_ok)
