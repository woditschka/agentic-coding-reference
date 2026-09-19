"""Read the workspace's member table from scripts/layout.toml; a single repository declares none.

The anti-corruption layer for the one layout section the workspace owns: the
members, each with its sibling path, its stack, its contract paths, and the
members it depends on.
"""

import fnmatch
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .config import is_glob

# A key names the member in records, the gate, and the review plan, so it is
# a plain slug that can never read as an option or a path.
MEMBER_KEY = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
STACK_NAME = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
# A control byte in a path would forge a diff header or shift a numstat column.
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
PARENT = ".."
# A sibling path is the parent step plus at least one name.
SIBLING_PARTS = 2


class WorkspaceError(ValueError):
    """A [workspace] value the members cannot be resolved from."""


@dataclass(frozen=True, slots=True)
class Member:
    """One declared member: its key, its path relative to the umbrella, its stack, its contract globs, and its dependencies."""

    key: str
    path: str
    stack: str | None
    contracts: tuple[str, ...]
    depends_on: tuple[str, ...]

    @property
    def prefix(self) -> str:
        """Return what every change-set path of this member carries in front of git's own spelling."""
        return f"{self.path}/"

    def root(self, umbrella: Path) -> Path:
        """Return the member's directory beside the umbrella."""
        return umbrella / self.path

    def is_present(self, umbrella: Path) -> bool:
        """Return whether the member is checked out: its directory holds a git repository or worktree link."""
        return (self.root(umbrella) / ".git").exists()


def load_members(scripts_dir: Path) -> tuple[Member, ...]:
    """Read [workspace.members] from the layout beside the launchers; an absent table is a single repository."""
    path = scripts_dir / "layout.toml"
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise WorkspaceError(f"{path.name}: {exc}") from exc
    workspace = raw.get("workspace", {})
    if not isinstance(workspace, dict):
        raise WorkspaceError("layout.toml: [workspace] must be a table")
    table = workspace.get("members", {})
    if not isinstance(table, dict):
        raise WorkspaceError("layout.toml: [workspace.members] must be a table")
    umbrella = scripts_dir.resolve().parent
    members = tuple(_member(key, entry, umbrella) for key, entry in table.items())
    _check_dependencies(members)
    return members


def unreached_globs(globs: Sequence[str], members: Sequence[Member]) -> tuple[str, ...]:
    """Return the globs under a parent step that match no declared member's path; each is a dead exclude."""
    return tuple(
        g
        for g in globs
        if g.startswith(f"{PARENT}/")
        and not any(fnmatch.fnmatchcase(m.path, _member_segment(g)) for m in members)
    )


def _member_segment(glob: str) -> str:
    """Return the leading ../<name> of a glob, the part that names a member."""
    head, _separator, _rest = glob[len(PARENT) + 1 :].partition("/")
    return f"{PARENT}/{head}"


def _member(key: str, entry: object, umbrella: Path) -> Member:
    if not MEMBER_KEY.match(key):
        raise WorkspaceError(
            f"layout.toml: [workspace.members] key {key!r} must match {MEMBER_KEY.pattern}"
        )
    if not isinstance(entry, dict):
        raise WorkspaceError(f"layout.toml: [workspace.members] {key} must be a table")
    return Member(
        key=key,
        path=_sibling_path(key, entry.get("path"), umbrella),
        stack=_stack(key, entry.get("stack")),
        contracts=_globs(key, entry.get("contracts", [])),
        depends_on=_keys(key, entry.get("depends_on", [])),
    )


def _sibling_path(key: str, value: object, umbrella: Path) -> str:
    """Return the declared path when it names a directory beside the umbrella, never inside it and never the umbrella itself."""
    if not isinstance(value, str) or not value or _CONTROL.search(value):
        raise WorkspaceError(
            f"layout.toml: [workspace.members] {key} needs a relative path without "
            f"control characters (got {value!r})"
        )
    parts = PurePosixPath(value).parts
    outside = (
        not PurePosixPath(value).is_absolute()
        and not value.endswith("/")
        and len(parts) >= SIBLING_PARTS
        and parts[0] == PARENT
        and all(part not in (PARENT, ".") for part in parts[1:])
    )
    if outside:
        target = (umbrella / value).resolve()
        outside = target != umbrella and not target.is_relative_to(umbrella)
    if not outside:
        raise WorkspaceError(
            f"layout.toml: [workspace.members] {key} path {value!r} must name a "
            "sibling of the umbrella, such as ../<repository>"
        )
    return value


def _stack(key: str, value: object) -> str | None:
    """Return the declared stack name, or None when the member declares none; nothing reads it yet."""
    if value is None:
        return None
    if not isinstance(value, str) or not STACK_NAME.match(value):
        raise WorkspaceError(
            f"layout.toml: [workspace.members] {key} stack must be a name (got {value!r})"
        )
    return value


def _globs(key: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(is_glob(g) for g in value):
        raise WorkspaceError(
            f"layout.toml: [workspace.members] {key} contracts must be a list of "
            f"non-empty glob strings (got {value!r})"
        )
    return tuple(value)


def _keys(key: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(k, str) and MEMBER_KEY.match(k) for k in value
    ):
        raise WorkspaceError(
            f"layout.toml: [workspace.members] {key} depends_on must be a list of "
            f"member keys (got {value!r})"
        )
    return tuple(value)


def _check_dependencies(members: tuple[Member, ...]) -> None:
    """Reject a dependency on an undeclared member or on the member itself."""
    declared: Mapping[str, Member] = {m.key: m for m in members}
    for member in members:
        for dependency in member.depends_on:
            if dependency == member.key:
                raise WorkspaceError(
                    f"layout.toml: [workspace.members] {member.key} depends on itself"
                )
            if dependency not in declared:
                raise WorkspaceError(
                    f"layout.toml: [workspace.members] {member.key} depends on "
                    f"{dependency!r}, which is not a declared member"
                )
