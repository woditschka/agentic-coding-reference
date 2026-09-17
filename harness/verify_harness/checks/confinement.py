"""Gate network egress and raw writes in the harness glue against one sanctioned-exception manifest."""

import ast
import functools
import re
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from verify_harness.battery import Battery, shell_scripts
from verify_harness.checks.confinement_ast import (
    GIT_NETWORK_SUBCOMMANDS,
    NETWORK_MODULES,
    NETWORK_TOOL_RE,
    WRITE_MODULES,
    EgressRules,
    _file_egress_hits,
    _import_bindings,
    _imports_module,
    _write_primitive,
)
from verify_harness.text import HERE, ROOT, read_text, rel

SHOWN_HITS = 15
# The scanned tiers: the shipped runtime that runs on a consumer machine,
# and the producer tooling with every user-level tool under tools/. The
# battery's own package is the checker and stays out.
# core and stacks are the shipped tier, scanned on their own; verify_harness
# is the checker itself; init holds project-owned skeletons, not glue.
UNSCANNED_TOP_DIRS = frozenset({"core", "stacks", "verify_harness", "init"})
HTTPS_PREFIX = "https://"


@dataclass(frozen=True)
class ConfinementPolicy:
    """The sanctioned exceptions to the egress and write gates, immutable all the way down."""

    writers: Mapping[str, str]
    egress: frozenset[tuple[str, str]]
    network: Mapping[str, str]
    spawners: Mapping[str, frozenset[str]]


def _sanctioned_egress(data: Any, path: Path) -> frozenset[tuple[str, str]]:  # noqa: ANN401
    """Parse the egress pairs of the loaded manifest, refusing a prefix that is not origin-bounded."""
    pairs = frozenset(
        (str(entry["subcommand"]), str(entry["url_prefix"]))
        for entry in data.get("sanctioned_egress", [])
    )
    for subcommand, prefix in pairs:
        # An empty prefix sanctions every host and a slash-less one admits
        # lookalike domains.
        if (
            not subcommand
            or not prefix.startswith(HTTPS_PREFIX)
            or "/" not in prefix[len(HTTPS_PREFIX) :]
        ):
            raise RuntimeError(
                f"confinement policy malformed ({path}): egress pair "
                f"({subcommand!r}, {prefix!r}) — the prefix must be https:// and "
                "extend past the host (origin-bounded), the subcommand non-empty"
            )
    return pairs


def _load_confinement_policy(path: Path | None = None) -> ConfinementPolicy:
    """Parse the confinement manifest into a policy, raising on any malformed entry."""
    path = path or HERE / "confinement-policy.toml"
    try:
        data = tomllib.loads(read_text(path))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(f"confinement policy unreadable ({path}): {exc}") from exc
    try:
        return ConfinementPolicy(
            writers=MappingProxyType(
                {
                    str(entry["path"]): str(entry["why"])
                    for entry in data.get("sanctioned_writer", [])
                }
            ),
            network=MappingProxyType(
                {
                    str(entry["path"]): str(entry["why"])
                    for entry in data.get("sanctioned_network", [])
                }
            ),
            egress=_sanctioned_egress(data, path),
            spawners=MappingProxyType(
                {
                    str(entry["path"]): frozenset(str(s) for s in entry["spawns"])
                    for entry in data.get("sanctioned_spawner", [])
                }
            ),
        )
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            f"confinement policy malformed ({path}): missing field {exc}"
        ) from exc


@functools.cache
def _policy() -> ConfinementPolicy:
    """Return the loaded manifest, parsed once and lazily."""
    # Lazy, so a broken manifest surfaces as a step failure inside the two
    # gate steps rather than an import-time crash before any step runs.
    return _load_confinement_policy()


def _is_test_file(path: Path) -> bool:
    """Tell whether a file is test scaffolding, which spawns and writes freely."""
    return "tests" in path.parts or path.name.startswith("test_")


def _python_under(root: Path) -> Iterator[Path]:
    """Yield the non-test Python files under root."""
    for path in root.rglob("*.py"):
        if "__pycache__" not in path.parts and not _is_test_file(path):
            yield path


def _tool_dirs() -> list[Path]:
    """List every directory under tools/, so a new tool cannot land unscanned."""
    tools = ROOT / "tools"
    if not tools.is_dir():
        return []
    return sorted(path for path in tools.iterdir() if path.is_dir())


def _gate_targets() -> tuple[list[Path], list[Path]]:
    """Return the (shipped, producer) file lists the gate scans."""
    shipped = [
        path
        for root in (HERE / "core", HERE / "stacks")
        if root.exists()
        for path in _python_under(root)
    ]
    producer = [
        path
        for path in _python_under(HERE)
        if path.relative_to(HERE).parts[0] not in UNSCANNED_TOP_DIRS
    ]
    producer.extend(path for tool in _tool_dirs() for path in _python_under(tool))
    return sorted(set(shipped)), sorted(set(producer))


# A git network subcommand in one bash pipeline segment, after any options
# and arguments; quotes are stripped before the search.
GIT_NETWORK_RE = re.compile(
    r"(?<![\w-])git\b[^|;&]*?(?<![\w-])("
    + "|".join(sorted(GIT_NETWORK_SUBCOMMANDS))
    + r")(?![\w-])"
)
# Escape-aware for double quotes; bash single quotes admit no escapes.
_QUOTED_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'[^\']*\'')
# Both command-substitution forms execute even inside double quotes.
_SUBSHELL_RE = re.compile(r"\$\(([^)]*)\)")
_BACKTICK_RE = re.compile(r"`([^`]*)`")


def _folded_lines(text: str) -> list[tuple[int, str]]:
    """Return (first line number, logical line) pairs with backslash continuations folded."""
    folded: list[tuple[int, str]] = []
    buffer, start = "", 1
    for number, line in enumerate(text.splitlines(), 1):
        if not buffer:
            start = number
        if line.endswith("\\") and not line.endswith("\\\\"):
            buffer += line[:-1] + " "
            continue
        folded.append((start, buffer + line))
        buffer = ""
    if buffer:
        folded.append((start, buffer))
    return folded


def _uncommented(line: str) -> tuple[str, str]:
    """Return (quote-masked line, original line) cut at the first word-opening `#`."""
    # Quotes are masked length-preserving before the comment cut, so a `#`
    # inside a string cannot hide the rest of the line; the cut is judged on
    # the original line, so masking never promotes `""#` into a comment.
    masked = _QUOTED_RE.sub(lambda m: " " * len(m.group()), line)
    for hash_mark in re.finditer("#", masked):
        index = hash_mark.start()
        if index == 0 or line[index - 1] in " \t":
            return masked[:index], line[:index]
    return masked, line


def _bash_line_hits(script: Path, lineno: int, line: str) -> list[str]:
    """List the network CLIs and git network subcommands one bash line executes."""
    # A quoted string is data, but a substitution executes even inside
    # double quotes, so its content is scanned before the quotes go. The
    # ceiling: a quoted command word reaching execution (`"curl" url`, eval,
    # `bash -c`) and a `)` literal truncating a substitution stay invisible.
    masked, line = _uncommented(line)
    substitutions = [
        _QUOTED_RE.sub(" ", inner)
        for pattern in (_SUBSHELL_RE, _BACKTICK_RE)
        for inner in pattern.findall(line)
    ]
    hits: list[str] = []
    for segment in [*substitutions, masked]:
        tool = NETWORK_TOOL_RE.search(segment)
        if tool:
            hits.append(f"{rel(script)}:{lineno}: shell network tool {tool.group(1)!r}")
        git = GIT_NETWORK_RE.search(segment)
        if git:
            hits.append(
                f"{rel(script)}:{lineno}: shell git subcommand {git.group(1)!r} "
                "reaches the network"
            )
    return list(dict.fromkeys(hits))


def _dead_sanction_hits(paths: list[str], scanned: set[str], kind: str) -> list[str]:
    """Flag a sanction naming a file that is missing or outside the scan targets."""
    hits = []
    for relpath in paths:
        if not (ROOT / relpath).is_file():
            hits.append(
                f"{relpath}: {kind} in confinement-policy.toml names a missing file"
            )
        elif relpath not in scanned:
            # A sanction the gate never reads is never enforced and never
            # probed stale.
            hits.append(
                f"{relpath}: confinement-policy.toml sanctions a file outside the "
                "gate's scan targets — dead entry"
            )
    return hits


def _parsed(path: Path) -> ast.Module | None:
    """Parse one file, or None when the syntax step owns its failure."""
    try:
        return ast.parse(read_text(path), str(path))
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return None


def _file_network_hits(
    path: Path, tier: str, policy: ConfinementPolicy, used_egress: set[tuple[str, str]]
) -> list[str]:
    """Judge one Python file's imports and spawns, then probe its sanctions for staleness."""
    tree = _parsed(path)
    if tree is None:
        return []
    relpath = path.relative_to(ROOT).as_posix()
    rules = EgressRules(
        tier,
        net_exempt=relpath in policy.network,
        is_spawner=relpath in policy.spawners,
        allowed=policy.spawners.get(relpath, frozenset()),
        egress=policy.egress,
    )
    hits = _file_egress_hits(path, tree, rules, used_egress)
    if rules.is_spawner and not _imports_module(tree, frozenset({"subprocess"})):
        hits.append(f"{relpath}: stale sanctioned_spawner — no subprocess import")
    if rules.net_exempt and not _imports_module(tree, NETWORK_MODULES):
        hits.append(f"{relpath}: stale sanctioned_network — no network-module import")
    return hits


def _bash_network_hits() -> list[str]:
    """Scan every harness and tools shell script for network CLIs and git network subcommands."""
    hits = []
    for base in [HERE, *_tool_dirs()]:
        for script in shell_scripts(base):
            # init/ holds project-owned skeletons, not harness glue.
            if base == HERE and "init" in script.relative_to(HERE).parts:
                continue
            for lineno, line in _folded_lines(read_text(script)):
                hits.extend(_bash_line_hits(script, lineno, line))
    return hits


def _report_hits(b: Battery, header: str, hits: list[str]) -> None:
    """Fail once with the first hits listed and the overflow counted."""
    shown = [f"    {hit}" for hit in hits[:SHOWN_HITS]]
    if len(hits) > SHOWN_HITS:
        shown.append(f"    … and {len(hits) - SHOWN_HITS} more")
    b.fail(header + "\n" + "\n".join(shown))


def check_no_network(b: Battery) -> None:
    """Refuse network egress from the shipped runtime and the producer tooling."""
    b.note("no network egress (imports, subprocess, shell tools)")
    try:
        policy = _policy()
    except RuntimeError as exc:
        b.fail(str(exc))
        return
    shipped, producer = _gate_targets()
    scanned = {path.relative_to(ROOT).as_posix() for path in [*shipped, *producer]}
    hits = _dead_sanction_hits(
        [*policy.network, *policy.spawners], scanned, "sanctioned entry"
    )
    used_egress: set[tuple[str, str]] = set()
    tiers = [
        *((path, "shipped") for path in shipped),
        *((path, "producer") for path in producer),
    ]
    for path, tier in tiers:
        hits.extend(_file_network_hits(path, tier, policy, used_egress))
    hits.extend(
        f"confinement-policy.toml: stale sanctioned_egress "
        f"({subcommand!r}, {prefix!r}) — no call exercises it"
        for subcommand, prefix in sorted(policy.egress - used_egress)
    )
    hits.extend(_bash_network_hits())
    if hits:
        _report_hits(b, "network egress is not permitted from the harness glue:", hits)
    else:
        b.record_pass(
            f"no network egress ({len(shipped)} shipped + {len(producer)} producer)"
        )


def _file_write_hits(path: Path, policy: ConfinementPolicy) -> list[str]:
    """Judge one Python file's raw writes, or probe its writer sanction for staleness."""
    tree = _parsed(path)
    if tree is None:
        return []
    relpath = path.relative_to(ROOT).as_posix()
    bindings = _import_bindings(tree)
    raw = [
        (node.lineno, hit)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and (hit := _write_primitive(node, bindings))
    ]
    # A WRITE_MODULES import is itself the write capability, so it keeps a
    # sanction exercised even with no labelable call.
    if relpath in policy.writers:
        if not raw and not _imports_module(tree, WRITE_MODULES):
            return [f"{relpath}: stale sanctioned_writer — no raw write left"]
        return []
    hits = []
    if _imports_module(tree, WRITE_MODULES):
        hits.append(
            f"{relpath}: imports a file-creating module "
            f"({'/'.join(sorted(WRITE_MODULES))}) — route through "
            "write_guard or sanction the file"
        )
    hits.extend(
        f"{rel(path)}:{lineno}: raw write {hit} — route through write_guard"
        for lineno, hit in raw
    )
    return hits


def check_confined_writes(b: Battery) -> None:
    """Confine raw filesystem writes to the sanctioned writer files."""
    b.note("confined writes (raw writes only in sanctioned files)")
    try:
        policy = _policy()
    except RuntimeError as exc:
        b.fail(str(exc))
        return
    shipped, producer = _gate_targets()
    scanned = sorted(set(shipped) | set(producer))
    scanned_rel = {path.relative_to(ROOT).as_posix() for path in scanned}
    hits = _dead_sanction_hits(list(policy.writers), scanned_rel, "sanctioned_writer")
    for path in scanned:
        hits.extend(_file_write_hits(path, policy))
    if hits:
        _report_hits(
            b,
            "raw filesystem writes must route through write_guard "
            "(or the file be sanctioned in confinement-policy.toml):",
            hits,
        )
    else:
        b.record_pass(
            f"writes confined ({len(policy.writers)} sanctioned, all others via write_guard)"
        )
