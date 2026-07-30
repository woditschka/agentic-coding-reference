"""The confinement gate — battery steps 1h (no network egress) and 1i
(confined writes) over the harness glue (ADR 2026-07-19
network-write-confinement-gate).

The gate is two confinement-owned modules: this one holds the POLICY side —
the manifest record and loader, the scan targets, the bash scan, and the two
check steps the battery calls — while checks/confinement_ast.py holds the
policy-free Python detectors it drives. The public surface is check_no_network
and check_confined_writes; everything else is internal. Replacing the gate
some day (a query engine, a kernel sandbox) means replacing this pair and
rewiring those two calls — nothing else in the battery knows how the gate
works. The runtime half of the pairing is harness/write_guard.py.
"""

import ast
import functools
import re
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from verify_harness.battery import Battery, _shell_scripts
from verify_harness.checks.confinement_ast import (
    GIT_NETWORK_SUBCOMMANDS,
    NETWORK_MODULES,
    NETWORK_TOOL_RE,
    WRITE_MODULES,
    _file_egress_hits,
    _import_bindings,
    _imports_module,
    _write_primitive,
)
from verify_harness.text import HERE, ROOT, read_text, rel

# --- 1h/1i inputs: the confinement gate (ADR 2026-07-19 network-write-confinement-gate).
# Scanned tiers: the SHIPPED runtime (core/ + stacks/, minus tests) that runs on a
# consumer machine; the PRODUCER tooling (the loose harness/*.py plus the
# managed-chapter python); and every user-level tool under tools/ (enumerated,
# so a new tool cannot land unscanned), held to the producer ruleset with their
# own recorded exceptions — claude-dev is network-facing by design, so its
# preflight probe is a confinement-policy.toml network entry rather than a
# blanket exemption. Only the battery's
# own verify_harness package stays out of scope: it is the checker. The sanctioned
# exceptions live in one explicit manifest — harness/confinement-policy.toml — not
# in code; the steps below load it once and dissolve it into the flag parameters
# of the policy-free detectors (checks/confinement_ast.py).

# --- Policy ------------------------------------------------------------------
# The sanctioned exceptions, loaded once from the manifest.


# The sanctioned exceptions are POLICY, not mechanism, and they span parts
# (harness core, producer, tools/). They live in ONE explicit manifest —
# harness/confinement-policy.toml — not buried here as code. The loader reads that
# manifest at the parse boundary into a frozen record; everything below is
# mechanism.
@dataclass(frozen=True)
class ConfinementPolicy:
    """The sanctioned exceptions to the 1h/1i gates, loaded from
    harness/confinement-policy.toml. writers and network map a ROOT-relative path
    to its justification; spawners maps a path to the argv0 tokens it may spawn
    ("sys.executable" names the interpreter) — importing subprocess anywhere else
    is banned; egress is the set of (git subcommand, URL prefix) pairs producer
    git may reach. Mappings are read-only proxies, so the record is immutable
    all the way down, not just frozen at the field level."""

    writers: Mapping[str, str]
    egress: frozenset[tuple[str, str]]
    network: Mapping[str, str]
    spawners: Mapping[str, frozenset[str]]


def _load_confinement_policy(path: Path | None = None) -> ConfinementPolicy:
    """Parse harness/confinement-policy.toml into a ConfinementPolicy. Raises on a
    missing, malformed, or incomplete manifest — the gate cannot run without its
    policy. path overrides the default only for tests."""
    path = path or HERE / "confinement-policy.toml"
    try:
        data = tomllib.loads(read_text(path))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(f"confinement policy unreadable ({path}): {exc}") from exc
    try:
        egress = frozenset(
            (str(e["subcommand"]), str(e["url_prefix"]))
            for e in data.get("sanctioned_egress", [])
        )
        for sub, prefix in egress:
            # Origin-bound the prefix at the parse boundary: an empty prefix
            # sanctions every host ("".startswith is always true) and a
            # slash-less one admits lookalike domains (github.com.evil.com).
            if not sub or not prefix.startswith("https://") or "/" not in prefix[8:]:
                raise RuntimeError(
                    f"confinement policy malformed ({path}): egress pair "
                    f"({sub!r}, {prefix!r}) — the prefix must be https:// and "
                    "extend past the host (origin-bounded), the subcommand "
                    "non-empty"
                )
        return ConfinementPolicy(
            writers=MappingProxyType(
                {
                    str(e["path"]): str(e["why"])
                    for e in data.get("sanctioned_writer", [])
                }
            ),
            network=MappingProxyType(
                {
                    str(e["path"]): str(e["why"])
                    for e in data.get("sanctioned_network", [])
                }
            ),
            egress=egress,
            spawners=MappingProxyType(
                {
                    str(e["path"]): frozenset(str(s) for s in e["spawns"])
                    for e in data.get("sanctioned_spawner", [])
                }
            ),
        )
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            f"confinement policy malformed ({path}): missing field {exc}"
        ) from exc


@functools.cache
def _policy() -> ConfinementPolicy:
    """The loaded manifest, cached after the first successful parse. Lazy so a
    missing or malformed manifest surfaces as an aggregated step FAIL in the
    two gate steps (which fetch it first, under try) — never an import-time
    crash that aborts the battery before any step runs. The battery's sole
    sanctioned abort stays the materialize-samples crash in step 3."""
    return _load_confinement_policy()


# --- Scan targets ------------------------------------------------------------
# Which files the two steps read, by tier.


def _is_test_file(f: Path) -> bool:
    """Test scaffolding — under a tests/ dir or a test_*.py by name (the hook
    tests sit beside the hooks, not in a tests/ dir). Tests legitimately spawn
    sys.executable and write tempfiles; the battery runs them separately."""
    return "tests" in f.parts or f.name.startswith("test_")


def _gate_targets() -> tuple[list[Path], list[Path]]:
    """The (shipped, producer) file lists the confinement gate scans, minus
    __pycache__ and test scaffolding."""
    shipped: list[Path] = []
    for root in (HERE / "core", HERE / "stacks"):
        if root.exists():
            shipped += [
                f
                for f in root.rglob("*.py")
                if "__pycache__" not in f.parts and not _is_test_file(f)
            ]
    # Producer = every harness/*.py NOT under a scanned-elsewhere or excluded
    # subtree. Recursive, so a future writer at harness/<newdir>/foo.py cannot
    # escape the scan. core/ and stacks/ are the shipped tier above;
    # verify_harness/ is the checker itself; init/ holds project-owned skeletons.
    skip_top = {"core", "stacks", "verify_harness", "init"}
    producer = [
        f
        for f in HERE.rglob("*.py")
        if "__pycache__" not in f.parts
        and not _is_test_file(f)
        and f.relative_to(HERE).parts[0] not in skip_top
    ]
    # Every user-level tool rides the producer ruleset (network-facing
    # exceptions are recorded in confinement-policy.toml), so a stray egress or
    # write in tools/ is caught the same way. Enumerated, not hardcoded — a
    # third tool joins the scan the day its directory lands, the same
    # future-proofing the producer rglob gives harness/.
    producer += [
        f
        for troot in _tool_dirs()
        for f in troot.rglob("*.py")
        if "__pycache__" not in f.parts and not _is_test_file(f)
    ]
    return sorted(set(shipped)), sorted(set(producer))


def _tool_dirs() -> list[Path]:
    """Every directory under tools/ — the user-level tools tier, enumerated so
    a new tool cannot land outside the scan."""
    troot = ROOT / "tools"
    if not troot.is_dir():
        return []
    return sorted(p for p in troot.iterdir() if p.is_dir())


# --- Bash scan (1h) ----------------------------------------------------------
# Network CLIs and git network subcommands as executed shell words.

# A git network subcommand in one bash pipeline segment: `git`, any options and
# arguments, then the subcommand. Quotes are stripped before the search, so an
# option's quoted argument (`git -C "$target" push`) cannot hide the subcommand.
GIT_NETWORK_RE = re.compile(
    r"(?<![\w-])git\b[^|;&]*?(?<![\w-])("
    + "|".join(sorted(GIT_NETWORK_SUBCOMMANDS))
    + r")(?![\w-])"
)
# Escape-aware for double quotes (\" inside a string must not end the mask);
# bash single quotes admit no escapes, so their branch stays simple.
_QUOTED_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'[^\']*\'')
# Both command-substitution forms execute even inside double quotes.
_SUBSHELL_RE = re.compile(r"\$\(([^)]*)\)")
_BACKTICK_RE = re.compile(r"`([^`]*)`")


def _folded_lines(text: str) -> list[tuple[int, str]]:
    """(first-lineno, logical line) pairs with backslash continuations folded,
    so a wrapped `git -C x \\` + `push` scans as the one command it is."""
    out: list[tuple[int, str]] = []
    buf, start = "", 1
    for i, ln in enumerate(text.splitlines(), 1):
        if not buf:
            start = i
        if ln.endswith("\\") and not ln.endswith("\\\\"):
            buf += ln[:-1] + " "
            continue
        out.append((start, buf + ln))
        buf = ""
    if buf:
        out.append((start, buf))
    return out


def _bash_line_hits(sh: Path, lineno: int, line: str) -> list[str]:
    """The 1h hits for one bash line: a network CLI or a git network subcommand
    as an executed word. A quoted string is data (the printed `git push` hint
    in release-version.sh), but a `$(…)` or backtick substitution executes even
    inside double quotes, so its content is scanned before the quotes are
    stripped. Quotes are masked length-preserving BEFORE the comment cut, so a
    `#` inside a string cannot hide the rest of the line; the cut fires only
    where the ORIGINAL line opens a word with `#` (neither `${#arr[@]}` nor a
    quote-adjacent `""#` comments the tail away). The remaining ceiling: a
    quoted command word reaching execution (`"curl" url`, eval, `bash -c`) and
    a `)` literal inside a substitution truncating its extraction — deliberate
    construction, review's to catch."""
    masked = _QUOTED_RE.sub(lambda m: " " * len(m.group()), line)
    for hash_mark in re.finditer("#", masked):
        i = hash_mark.start()
        # Word-opening judged on the original line: masking turns quotes into
        # spaces and must not promote `""#` into a comment opener.
        if i == 0 or line[i - 1] in " \t":
            masked, line = masked[:i], line[:i]
            break
    hits: list[str] = []
    subs = [
        _QUOTED_RE.sub(" ", s)
        for pat in (_SUBSHELL_RE, _BACKTICK_RE)
        for s in pat.findall(line)
    ]
    for seg in [*subs, masked]:
        m = NETWORK_TOOL_RE.search(seg)
        if m:
            hits.append(f"{rel(sh)}:{lineno}: shell network tool {m.group(1)!r}")
        g = GIT_NETWORK_RE.search(seg)
        if g:
            hits.append(
                f"{rel(sh)}:{lineno}: shell git subcommand {g.group(1)!r} "
                "reaches the network"
            )
    return list(dict.fromkeys(hits))


# --- The two battery steps ---------------------------------------------------
# The gate's public surface — all the battery sees.


def check_no_network(b: Battery) -> None:
    """1h. No network egress from the harness glue (ADR 2026-07-19
    network-write-confinement-gate). Over the shipped runtime and the producer
    tooling (which also covers every tools/ user-level tool): no network-module
    import; importing subprocess (or an os exec/spawn name) only in a
    [[sanctioned_spawner]] file — an import statement names the real module, so
    this rule is alias-proof; inside a spawner, argv0 must be a sanctioned token
    (_check_subprocess). Call sites resolve receiver aliases through
    _import_bindings, so `import subprocess as sp` / `from subprocess import run`
    fire like the spelled-out forms. A policy-sanctioned network file (claude-dev's
    MCP probe) is exempt from the import check. Bash is scanned for the network
    CLIs and for git network subcommands (_bash_line_hits; quoted text is data).
    A git network subcommand fires anywhere in argv, so an option like -C
    cannot hide it; pty (spawn outside argv introspection) is banned outright.
    Sanctions must stay exercised: a spawner without a subprocess import, a
    network file without a network-module import, an egress pair no call
    matches, or an entry naming a missing or unscanned file is dead and fails.
    Static — runs in --quick."""
    b.note("no network egress (imports, subprocess, shell tools)")
    try:
        policy = _policy()
    except RuntimeError as exc:
        # A missing/malformed manifest is a step FAIL, not an import-time
        # crash — the rest of the battery still runs and reports.
        b.fail(str(exc))
        return
    shipped, producer = _gate_targets()
    scanned = {p.relative_to(ROOT).as_posix() for p in [*shipped, *producer]}
    hits: list[str] = []
    used_egress: set[tuple[str, str]] = set()
    for relp in list(policy.network) + list(policy.spawners):
        if not (ROOT / relp).is_file():
            hits.append(f"{relp}: confinement-policy.toml sanctions a missing file")
        elif relp not in scanned:
            # A sanction on an unscanned file (test scaffolding, the checker)
            # is dead: never enforced, never probed stale. Fail it here so the
            # manifest cannot outgrow the surface the gate actually reads.
            hits.append(
                f"{relp}: confinement-policy.toml sanctions a file outside the "
                "gate's scan targets — dead entry"
            )
    for f, tier in [(p, "shipped") for p in shipped] + [
        (p, "producer") for p in producer
    ]:
        try:
            tree = ast.parse(read_text(f), str(f))
        except (SyntaxError, ValueError, UnicodeDecodeError):
            continue  # step 2 owns syntax (a superset scan) and aggregates it
        relpath = f.relative_to(ROOT).as_posix()
        # Dissolve the policy record into the detector's flag parameters — the
        # detectors are policy-free; this loop is the only place the two meet.
        hits += _file_egress_hits(
            f,
            tree,
            tier,
            net_exempt=relpath in policy.network,
            is_spawner=relpath in policy.spawners,
            allowed=policy.spawners.get(relpath, frozenset()),
            egress=policy.egress,
            used_egress=used_egress,
        )
        if relpath in policy.spawners and not _imports_module(
            tree, frozenset({"subprocess"})
        ):
            hits.append(f"{relpath}: stale sanctioned_spawner — no subprocess import")
        if relpath in policy.network and not _imports_module(tree, NETWORK_MODULES):
            hits.append(
                f"{relpath}: stale sanctioned_network — no network-module import"
            )
    for sub, prefix in sorted(policy.egress - used_egress):
        hits.append(
            f"confinement-policy.toml: stale sanctioned_egress "
            f"({sub!r}, {prefix!r}) — no call exercises it"
        )
    for sh_base in [HERE, *_tool_dirs()]:
        for sh in _shell_scripts(sh_base):
            if sh_base == HERE and "init" in sh.relative_to(HERE).parts:
                continue  # init/ holds project-owned skeletons, not harness glue
            for i, line in _folded_lines(read_text(sh)):
                hits += _bash_line_hits(sh, i, line)
    if hits:
        b.fail("network egress is not permitted from the harness glue:")
        for h in hits[:15]:
            print(f"    {h}", file=sys.stderr)
        if len(hits) > 15:
            print(f"    … and {len(hits) - 15} more", file=sys.stderr)
    else:
        print(
            f"  no network egress ({len(shipped)} shipped + {len(producer)} producer)"
        )


def check_confined_writes(b: Battery) -> None:
    """1i. Writes are confined (ADR 2026-07-19 network-write-confinement-gate).
    Over the shipped runtime and the producer tooling, every raw filesystem write
    must sit in a policy-sanctioned file (confinement-policy.toml); every other file routes writes through
    write_guard, whose runtime guard confines each to its declared roots.
    _write_primitive resolves module aliases and from-imports, so shutil/os/
    tempfile/compression writes, metadata writes (chmod/chown/utime), logging
    file handlers, Path methods (including .rename/.replace/.touch), io.open,
    and open() in a write mode fire however they are spelled — a capability
    check, not a name match. Importing a module whose import IS the write
    capability (sqlite3/dbm/shelve) fires too. A sanctioned_writer with no raw
    write left, or naming a missing or unscanned file, is a dead entry and
    fails. Genuine reflection (getattr, dynamic import) is the ceiling. Runs
    in --quick."""
    b.note("confined writes (raw writes only in sanctioned files)")
    try:
        policy = _policy()
    except RuntimeError as exc:
        # Same contract as check_no_network: aggregate, do not abort.
        b.fail(str(exc))
        return
    shipped, producer = _gate_targets()
    scanned = sorted(set(shipped) | set(producer))
    scanned_rel = {p.relative_to(ROOT).as_posix() for p in scanned}
    hits: list[str] = []
    for relp in policy.writers:
        if not (ROOT / relp).is_file():
            hits.append(
                f"{relp}: sanctioned_writer in confinement-policy.toml names a "
                "missing file"
            )
        elif relp not in scanned_rel:
            # Same rule as 1h: a sanction the gate never reads is a dead entry.
            hits.append(
                f"{relp}: confinement-policy.toml sanctions a file outside the "
                "gate's scan targets — dead entry"
            )
    for f in scanned:
        relpath = f.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(read_text(f), str(f))
        except (SyntaxError, ValueError, UnicodeDecodeError):
            continue
        module_of, from_bind = _import_bindings(tree)
        raw = [
            (node.lineno, hit)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (hit := _write_primitive(node, module_of, from_bind))
        ]
        if relpath in policy.writers:
            # A WRITE_MODULES import is itself the write capability, so it
            # keeps a sanction exercised even with no labelable call.
            if not raw and not _imports_module(tree, WRITE_MODULES):
                hits.append(f"{relpath}: stale sanctioned_writer — no raw write left")
            continue
        if _imports_module(tree, WRITE_MODULES):
            # sqlite3/dbm/shelve create their backing file with no call the
            # write detector labels — the import is the capability.
            hits.append(
                f"{relpath}: imports a file-creating module "
                f"({'/'.join(sorted(WRITE_MODULES))}) — route through "
                "write_guard or sanction the file"
            )
        hits += [
            f"{rel(f)}:{lineno}: raw write {hit} — route through write_guard"
            for lineno, hit in raw
        ]
    if hits:
        b.fail(
            "raw filesystem writes must route through write_guard "
            "(or the file be sanctioned in confinement-policy.toml):"
        )
        for h in hits[:15]:
            print(f"    {h}", file=sys.stderr)
        if len(hits) > 15:
            print(f"    … and {len(hits) - 15} more", file=sys.stderr)
    else:
        print(
            f"  writes confined ({len(policy.writers)} sanctioned, "
            "all others via write_guard)"
        )
