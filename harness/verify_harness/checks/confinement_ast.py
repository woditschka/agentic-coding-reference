"""The confinement gate's Python detectors — the AST mechanism behind battery
steps 1h/1i (ADR 2026-07-19 network-write-confinement-gate).

Pure functions over parsed source: the capability sets, the import-binding
resolution that makes every rule alias-proof, the write detector
(_write_primitive), and the spawn/egress detector (_check_subprocess,
_file_egress_hits). Deliberately policy-free: this module never reads the
manifest — the gate (checks/confinement.py) dissolves its ConfinementPolicy
into the flag and allowlist parameters at each call. That keeps the detectors
testable on synthetic sources alone and keeps one module, the gate, as the
only reader of policy.
"""

import ast
import re
from pathlib import Path

from verify_harness.text import rel

# --- Capabilities ------------------------------------------------------------
# The denylisted network/spawn/write primitives, enumerated deliberately.

# Stdlib modules that open a network connection. The harness never needs one: the
# single sanctioned egress is git reaching a git remote (deps-report's ls-remote),
# a subprocess, not an import. Enumerated deliberately (a capability denylist).
NETWORK_MODULES = frozenset(
    {
        "socket",
        "socketserver",
        "ssl",
        "http",
        "urllib",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "nntplib",
        "telnetlib",
        "xmlrpc",
        "asyncio",
        "webbrowser",
    }
)

# Command-line network clients. A subprocess spawning one is arbitrary egress,
# banned in both tiers. git is deliberately absent — it reaches only git remotes,
# and its network subcommands are gated separately (GIT_NETWORK_SUBCOMMANDS).
# A NAMED denylist, not an allowlist: package/container managers that can reach
# the network as a side effect (docker, pip, npm) stay out — docker is
# claude-dev's bash function, and bash has no per-file sanction kind (ADR
# 2026-07-19 static ceiling). `host` stays out too: as a whole word it collides
# with ordinary `host=` assignments.
NETWORK_TOOLS = frozenset(
    {
        "curl",
        "wget",
        "nc",
        "ncat",
        "netcat",
        "rsync",
        "ssh",
        "scp",
        "sftp",
        "telnet",
        "gh",
        "dig",
        "nslookup",
    }
)
# The same set as one compiled whole-word matcher, shared by the two scans that
# read raw text: the bash scan and the shell-string subprocess check.
NETWORK_TOOL_RE = re.compile(
    r"(?<![\w-])(" + "|".join(sorted(NETWORK_TOOLS)) + r")(?![\w-])"
)

# git subcommands that reach the network. Enforced only where the subcommand is a
# string literal; the two shipped git gateways pass *args (dynamic subcommand) and
# are trusted via the import-boundary gate (1g) that funnels all git through them.
GIT_NETWORK_SUBCOMMANDS = frozenset(
    {"fetch", "pull", "push", "clone", "ls-remote", "remote", "submodule"}
)

# Modules that spawn a child outside subprocess's argv introspection (pty.spawn
# runs argv through a pseudo-terminal). Banned at import outright — a sanctioned
# spawner earns argv-checked subprocess, never an uncheckable spawn path.
SPAWN_MODULES = frozenset({"pty"})

# os.* entry points that spawn a process or shell outside subprocess's argv
# introspection — banned in both tiers, they would defeat the argv checks.
OS_EXEC_CALLS = frozenset(
    {
        "system",
        "popen",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
    }
)

SUBPROCESS_CALLS = frozenset({"run", "call", "check_call", "check_output", "Popen"})
# The only modules a sanctioned sys.executable spawner may run via -m: unittest
# is materialize's suite discovery. Anything else (pip above all) is a named
# module the argv rules cannot see into — extend only by reviewed diff.
PYTHON_M_ALLOWED = frozenset({"unittest"})
# subprocess helpers that take only a shell string — no argv to introspect, so
# they are rejected outright even inside a sanctioned spawner.
SHELL_STRING_CALLS = frozenset({"getoutput", "getstatusoutput"})

# Path methods that write. `.rename` is Path-only as a method (os.rename is the
# module form; str/datetime carry no rename), so it is safe here — as are touch,
# rmdir, symlink_to, and hardlink_to. `.replace` is NOT — datetime/str carry
# it — so Path.replace is matched separately by arity (one positional arg, no
# keywords) in _write_primitive.
WRITE_METHODS = frozenset(
    {
        "write_text",
        "write_bytes",
        "mkdir",
        "unlink",
        "rename",
        "touch",
        "rmdir",
        "symlink_to",
        "hardlink_to",
        "chmod",
        "lchmod",
    }
)
WRITE_SHUTIL = frozenset(
    {
        "copy",
        "copy2",
        "copyfile",
        "copyfileobj",
        "copytree",
        "move",
        "rmtree",
        "chown",
        "make_archive",
        "unpack_archive",
    }
)
# os.open/os.fdopen are raw-fd writes that slip past the open()-mode-string check;
# flagged unconditionally (a read-only os.open in glue is rare enough to sanction
# or rewrite). symlink/link/truncate/write create or alter filesystem entries;
# chmod/chown/utime alter entry metadata (executability is security-relevant).
WRITE_OS = frozenset(
    {
        "mkdir",
        "makedirs",
        "rename",
        "replace",
        "remove",
        "removedirs",
        "unlink",
        "rmdir",
        "open",
        "fdopen",
        "symlink",
        "link",
        "truncate",
        "write",
        "chmod",
        "chown",
        "lchown",
        "utime",
        "mkfifo",
        "mknod",
        "pwrite",
        "writev",
    }
)
# tempfile factories create a file/dir outside any write_scope. A non-sanctioned
# writer wanting a temp should use write_guard (write_text is already atomic).
WRITE_TEMPFILE = frozenset(
    {"mkstemp", "mktemp", "NamedTemporaryFile", "TemporaryFile", "TemporaryDirectory"}
)
# Compression/archive writers: <mod>.open in a write mode, zipfile.ZipFile and
# tarfile.open/TarFile with a write direction. Read modes stay invisible.
COMPRESS_OPEN_MODULES = frozenset({"gzip", "bz2", "lzma"})
# Modules whose import IS the write capability: sqlite3.connect, dbm.open, and
# shelve.open create their backing file with no call the write detector labels.
# Banned at import (1i) outside a sanctioned writer.
WRITE_MODULES = frozenset({"sqlite3", "dbm", "shelve"})
# logging's file-backed handler constructors open their file for append. The
# from-import spelling resolves through the binding table (logging.handlers
# shares the top-level name); the logging.handlers.X attribute chain is ceiling.
LOGGING_FILE_HANDLERS = frozenset(
    {
        "FileHandler",
        "RotatingFileHandler",
        "TimedRotatingFileHandler",
        "WatchedFileHandler",
    }
)

# --- AST primitives ----------------------------------------------------------
# Literal/receiver/import-binding resolution shared by both detectors.


def _str_const(node: ast.expr | None) -> str | None:
    """The value of a string-literal node, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _fstring_prefix(node: ast.expr | None) -> str | None:
    """The leading constant text of an f-string, else None."""
    if isinstance(node, ast.JoinedStr) and node.values:
        return _str_const(node.values[0])
    return None


def _attr_call(node: ast.Call) -> tuple[str | None, str]:
    """(receiver-name, attr) for `x.attr(...)`; (None, attr)/(None, '') otherwise."""
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value.id if isinstance(func.value, ast.Name) else None
        return base, func.attr
    return None, ""


def _import_bindings(
    tree: ast.Module,
) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """Per-module name resolution so the gate sees through aliases and
    from-imports instead of matching receiver-name literals. Returns
    (module_of, from_bind):
      module_of[local] = top-level module   (import shutil as sh -> {'sh': 'shutil'})
      from_bind[local] = (module, attr)      (from os import rename ->
                                              {'rename': ('os', 'rename')})"""
    module_of: dict[str, str] = {}
    from_bind: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                module_of[a.asname or top] = top
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            top = node.module.split(".")[0]
            for a in node.names:
                from_bind[a.asname or a.name] = (top, a.name)
    return module_of, from_bind


def _imports_module(tree: ast.Module, names: frozenset[str]) -> bool:
    """True when the file imports any of the named top-level modules — the
    staleness probe for a sanctioned_spawner (subprocess) or sanctioned_network
    (a network module) entry. Import statements only, matching the sanction's
    own alias-proof ground truth."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] in names for a in node.names):
                return True
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and not node.level
            and node.module.split(".")[0] in names
        ):
            return True
    return False


# --- Write detector (1i) -----------------------------------------------------
# The raw-write label for one call, however it is spelled.


def _mode_args(node: ast.Call, index: int) -> tuple[ast.expr | None, ast.expr | None]:
    """(positional-at-index, mode= keyword value) for an open-style call —
    both None when no mode argument is given (the defaults are all reads)."""
    pos = node.args[index] if len(node.args) > index else None
    kw = next((k.value for k in node.keywords if k.arg == "mode"), None)
    return pos, kw


def _open_write_label(
    prefix: str, node: ast.Call, index: int, *, strict_positional: bool = True
) -> str | None:
    """The write label for an open-style call. A literal write mode fires; a
    NON-literal mode fires too — fail closed, mirroring the dynamic-argv
    subprocess rule, so `open(p, MODE)` cannot de-gate a write. An absent mode
    is a read. strict_positional=False is for the generic `.open(` receiver
    branch, where a non-literal positional is usually not a mode at all
    (urllib's opener.open(request)) — there only the mode= keyword and a
    literal positional are judged."""
    pos, kw = _mode_args(node, index)
    arg = kw if kw is not None else pos
    if arg is None:
        return None
    mode = _str_const(arg)
    if mode is None:
        if kw is not None or strict_positional:
            return f"{prefix}(non-literal mode — not statically checkable)"
        return None
    return f"{prefix}(write-mode)" if any(c in mode for c in "wax+") else None


def _archive_write_label(prefix: str, node: ast.Call, index: int) -> str | None:
    """The write label for a zipfile/tarfile constructor. tar modes carry a
    compression suffix ("r:xz", "w|gz") — only the part before the separator
    names the direction, so "r:xz" is a read despite the 'x'. A non-literal
    mode fails closed like _open_write_label."""
    pos, kw = _mode_args(node, index)
    arg = kw if kw is not None else pos
    if arg is None:
        return None  # both default to read
    mode = _str_const(arg)
    if mode is None:
        return f"{prefix}(non-literal mode — not statically checkable)"
    direction = re.split(r"[:|]", mode)[0]
    return f"{prefix}(write-mode)" if any(c in direction for c in "wax") else None


def _module_write(mod: str, attr: str, node: ast.Call) -> str | None:
    """The write label when the module-level callable mod.attr writes, else
    None. One table for both spellings — `shutil.copy(…)` through a (possibly
    aliased) module receiver and `copy(…)` through a from-import binding."""
    if mod == "shutil" and attr in WRITE_SHUTIL:
        return f"shutil.{attr}"
    if mod == "os" and attr in WRITE_OS:
        return f"os.{attr}"
    if mod == "tempfile" and attr in WRITE_TEMPFILE:
        return f"tempfile.{attr}"
    if mod == "logging" and attr in LOGGING_FILE_HANDLERS:
        return f"logging.{attr}"
    if mod in ("io", "codecs") and attr == "open":
        return _open_write_label(f"{mod}.open", node, 1)
    if mod in COMPRESS_OPEN_MODULES and attr == "open":
        return _open_write_label(f"{mod}.open", node, 1)
    if mod == "zipfile" and attr == "ZipFile":
        return _archive_write_label("zipfile.ZipFile", node, 1)
    if mod == "tarfile" and attr in ("open", "TarFile"):
        return _archive_write_label(f"tarfile.{attr}", node, 1)
    return None


def _dyn_import_target(
    node: ast.Call, module_of: dict[str, str], from_bind: dict[str, tuple[str, str]]
) -> str | None:
    """The literal module name a dynamic-import call names — through
    importlib.import_module (aliased or from-imported) or __import__ — else
    None (not a dynamic import, or a non-literal name)."""
    func = node.func
    dyn = False
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        base = func.value.id
        dyn = module_of.get(base, base) == "importlib" and func.attr == "import_module"
    elif isinstance(func, ast.Name):
        dyn = func.id == "__import__" or from_bind.get(func.id) == (
            "importlib",
            "import_module",
        )
    if not dyn:
        return None
    return _str_const(node.args[0]) if node.args else None


def _write_primitive(
    node: ast.Call, module_of: dict[str, str], from_bind: dict[str, tuple[str, str]]
) -> str | None:
    """The raw-write label for a call, resolving aliases and from-imports, or
    None. write_guard's own verbs return None only when the receiver is the real
    imported module (a name-shadowed local still trips the write-method branch).
    Known ceiling: a file that imports write_guard AND later rebinds the name
    keeps the skip — the binding table records the import statement, not the
    reassignment; that adversarial rebind is review's to catch."""
    dyn_name = _dyn_import_target(node, module_of, from_bind)
    if dyn_name is not None and dyn_name.split(".")[0] in WRITE_MODULES:
        return f"dynamic import of {dyn_name.split('.')[0]}"
    func = node.func
    if isinstance(func, ast.Attribute):
        attr = func.attr
        base = func.value.id if isinstance(func.value, ast.Name) else None
        mod = module_of.get(base) if base else None
        if mod == "write_guard":
            return None  # the sanctioned wrapper (verified real module, not a var)
        if mod is not None:
            return _module_write(mod, attr, node)
        # receiver is a value (Path/str/…), not a known module
        if attr in WRITE_METHODS:
            return f".{attr}(…)"
        if attr == "replace" and (
            (len(node.args) == 1 and not node.keywords)
            or (
                not node.args
                and len(node.keywords) == 1
                and node.keywords[0].arg == "target"
            )
        ):
            # Path.replace: one positional, or the target= keyword spelling.
            return ".replace(dst)"
        if attr == "open":
            return _open_write_label(".open", node, 0, strict_positional=False)
        return None
    if isinstance(func, ast.Name):
        if func.id == "open" and func.id not in from_bind:
            return _open_write_label("open", node, 1)
        bound = from_bind.get(func.id)
        if bound:
            return _module_write(bound[0], bound[1], node)
    return None


# --- Spawn/egress detector (1h) ----------------------------------------------
# Argv rules per subprocess call; per-file import and call hits.


def _argv0_token(node: ast.expr) -> str | None:
    """The manifest token an argv0 expression names: a string literal is itself,
    the `sys.executable` attribute is "sys.executable", anything else None."""
    lit = _str_const(node)
    if lit is not None:
        return lit
    if (
        isinstance(node, ast.Attribute)
        and node.attr == "executable"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    ):
        return "sys.executable"
    return None


def _check_subprocess(
    f: Path,
    node: ast.Call,
    tier: str,
    allowed: frozenset[str],
    egress: frozenset[tuple[str, str]] = frozenset(),
    used_egress: set[tuple[str, str]] | None = None,
) -> list[str]:
    """Argv rules for one subprocess call. allowed is the file's sanctioned
    argv0 tokens from [[sanctioned_spawner]] (empty for a non-spawner, so every
    call fires); egress is the gate's sanctioned (git subcommand, URL prefix)
    pairs. The command must be a list literal whose argv0 is a sanctioned
    literal (or sys.executable) — an allowlist, not a network-CLI denylist. A
    literal git-network subcommand — anywhere in argv, so options like -C
    cannot hide it — fails on the shipped tier and must match an egress pair
    on the producer tier; the shipped git gateways pass *args, so their
    dynamic subcommand is trusted via the import-boundary gate (1g).
    Shell-string commands are rejected outright — argv stays checkable. A
    matched egress pair is recorded in used_egress (when given) so the caller
    can flag sanctioned pairs no call exercises."""
    first = node.args[0] if node.args else None
    if first is None:
        # subprocess accepts the command as the `args=` keyword too — the
        # keyword spelling must not slip past the positional check.
        first = next((kw.value for kw in node.keywords if kw.arg == "args"), None)
    if first is None:
        return []
    literal_cmd = _str_const(first) or _fstring_prefix(first)
    if literal_cmd is not None:
        m = NETWORK_TOOL_RE.search(literal_cmd)
        if m:
            return [
                f"{rel(f)}:{node.lineno}: subprocess shell command spawns network "
                f"tool {m.group(1)!r}"
            ]
        return [
            f"{rel(f)}:{node.lineno}: subprocess argv must be a list literal "
            "(a shell string is not statically checkable)"
        ]
    if not isinstance(first, (ast.List, ast.Tuple)):
        return [
            f"{rel(f)}:{node.lineno}: subprocess argv must be a list literal "
            "(dynamic argv is not statically checkable)"
        ]
    if not first.elts:
        return []
    argv0 = _argv0_token(first.elts[0])
    if argv0 is not None and argv0 in NETWORK_TOOLS:
        return [f"{rel(f)}:{node.lineno}: subprocess spawns network tool {argv0!r}"]
    if argv0 is None or argv0 not in allowed:
        return [
            f"{rel(f)}:{node.lineno}: subprocess argv0 {argv0!r} is outside this "
            f"file's sanctioned spawns {sorted(allowed) or '(none)'} "
            "(confinement-policy.toml [[sanctioned_spawner]])"
        ]
    hits: list[str] = []
    if argv0 == "sys.executable":
        for i, e in enumerate(first.elts[1:], 1):
            if _str_const(e) != "-m":
                continue
            target = _str_const(first.elts[i + 1]) if len(first.elts) > i + 1 else None
            if target not in PYTHON_M_ALLOWED:
                hits.append(
                    f"{rel(f)}:{node.lineno}: python -m {target or '<dynamic>'} "
                    "runs a module by name — only "
                    f"{sorted(PYTHON_M_ALLOWED)} is sanctioned"
                )
    if argv0 == "git":
        # The subcommand may hide behind options (`git -C <path> push`), so
        # every literal element is scanned — the bash scan's conservatism; a
        # non-subcommand literal that collides with the set fails loud.
        pos, sub = next(
            (
                (i, lit)
                for i, e in enumerate(first.elts[1:], 1)
                if (lit := _str_const(e)) in GIT_NETWORK_SUBCOMMANDS
            ),
            (0, None),
        )
        if sub is not None:
            if tier == "shipped":
                hits.append(
                    f"{rel(f)}:{node.lineno}: shipped-runtime git subcommand "
                    f"{sub!r} reaches the network"
                )
            else:
                # The destination is the first non-option literal (or f-string
                # prefix) after the subcommand — a flag like --heads must not
                # be mistaken for the URL and false-fail a sanctioned pair.
                url = next(
                    (
                        u
                        for e in first.elts[pos + 1 :]
                        if (u := _str_const(e) or _fstring_prefix(e)) is not None
                        and not u.startswith("-")
                    ),
                    None,
                )
                matched = {
                    (s, prefix)
                    for s, prefix in egress
                    if url is not None and sub == s and url.startswith(prefix)
                }
                if matched:
                    if used_egress is not None:
                        used_egress |= matched
                else:
                    hits.append(
                        f"{rel(f)}:{node.lineno}: producer git subcommand {sub!r} "
                        "reaches the network (only a sanctioned_egress pair is "
                        "allowed)"
                    )
    return hits


def _file_egress_hits(
    f: Path,
    tree: ast.Module,
    tier: str,
    *,
    net_exempt: bool = False,
    is_spawner: bool = False,
    allowed: frozenset[str] = frozenset(),
    egress: frozenset[tuple[str, str]] = frozenset(),
    used_egress: set[tuple[str, str]] | None = None,
) -> list[str]:
    """The 1h hits for one parsed file. The caller dissolves its policy into
    the flags: a net_exempt (sanctioned_network) file skips the import checks —
    network access is its function — but not the spawn checks; only an
    is_spawner (sanctioned_spawner) file may import subprocess, and its calls
    are held to the allowed argv0 tokens and the sanctioned egress pairs. Split
    out of check_no_network so the rules are testable on synthetic sources with
    no manifest at all. used_egress (when given) collects the egress pairs the
    file's calls actually exercise."""
    hits: list[str] = []
    module_of, from_bind = _import_bindings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in NETWORK_MODULES and not net_exempt:
                    hits.append(
                        f"{rel(f)}:{node.lineno}: imports network module {alias.name!r}"
                    )
                elif top == "subprocess" and not is_spawner:
                    hits.append(
                        f"{rel(f)}:{node.lineno}: imports subprocess — not a "
                        "sanctioned spawner (confinement-policy.toml)"
                    )
                elif top in SPAWN_MODULES:
                    hits.append(
                        f"{rel(f)}:{node.lineno}: imports {top} — spawns outside "
                        "argv introspection"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            top = node.module.split(".")[0]
            if top in NETWORK_MODULES and not net_exempt:
                hits.append(
                    f"{rel(f)}:{node.lineno}: imports from network module "
                    f"{node.module!r}"
                )
            elif top == "subprocess" and not is_spawner:
                hits.append(
                    f"{rel(f)}:{node.lineno}: imports subprocess — not a "
                    "sanctioned spawner (confinement-policy.toml)"
                )
            elif top in SPAWN_MODULES:
                hits.append(
                    f"{rel(f)}:{node.lineno}: imports {top} — spawns outside "
                    "argv introspection"
                )
            elif top == "os":
                for alias in node.names:
                    if alias.name in OS_EXEC_CALLS:
                        hits.append(
                            f"{rel(f)}:{node.lineno}: from os import "
                            f"{alias.name} spawns outside argv introspection"
                        )
        elif isinstance(node, ast.Call):
            base, attr = _attr_call(node)
            # Resolve the receiver through the file's import bindings so an
            # aliased module fires; fall back to the literal name so a bare
            # (unimported) receiver still matches — detection may be lenient
            # where the write-gate's sanction skip must be strict.
            mod = module_of.get(base, base) if base else None
            bound: tuple[str, str] | None = None
            if isinstance(node.func, ast.Name):
                bound = from_bind.get(node.func.id)
            dyn_name = _dyn_import_target(node, module_of, from_bind)
            if dyn_name is not None:
                top = dyn_name.split(".")[0]
                if top in NETWORK_MODULES and not net_exempt:
                    hits.append(
                        f"{rel(f)}:{node.lineno}: dynamic import of network "
                        f"module {dyn_name!r}"
                    )
                elif top == "subprocess" or top in SPAWN_MODULES:
                    # A dynamic subprocess/pty import would bypass the argv
                    # rules entirely — banned even in a sanctioned spawner.
                    hits.append(
                        f"{rel(f)}:{node.lineno}: dynamic import of {top!r} "
                        "defeats the spawn sanction"
                    )
            if (mod == "os" and attr in OS_EXEC_CALLS) or (
                bound is not None and bound[0] == "os" and bound[1] in OS_EXEC_CALLS
            ):
                called = attr or (bound[1] if bound else "")
                hits.append(
                    f"{rel(f)}:{node.lineno}: os.{called} spawns outside "
                    "argv introspection"
                )
            elif (mod == "subprocess" and attr in SHELL_STRING_CALLS) or (
                bound is not None
                and bound[0] == "subprocess"
                and bound[1] in SHELL_STRING_CALLS
            ):
                called = attr or (bound[1] if bound else "")
                hits.append(
                    f"{rel(f)}:{node.lineno}: subprocess.{called} executes a "
                    "shell string (no argv to check) — use an argv-list call"
                )
            elif (mod == "subprocess" and attr in SUBPROCESS_CALLS) or (
                bound is not None
                and bound[0] == "subprocess"
                and bound[1] in SUBPROCESS_CALLS
            ):
                hits += _check_subprocess(f, node, tier, allowed, egress, used_egress)
    return hits
