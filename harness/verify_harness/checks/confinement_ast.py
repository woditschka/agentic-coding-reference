"""Detect network, spawn, and write capabilities in parsed Python, free of any policy."""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from verify_harness.text import rel

# Stdlib modules that open a network connection; the harness never needs one.
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

# Command-line network clients: a named denylist, not an allowlist. git is
# absent because its network subcommands are gated separately; `host` is
# absent because as a whole word it collides with ordinary assignments.
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
NETWORK_TOOL_RE = re.compile(
    r"(?<![\w-])(" + "|".join(sorted(NETWORK_TOOLS)) + r")(?![\w-])"
)

# Enforced only where the subcommand is a string literal; the shipped git
# gateways pass *args and are trusted through the import-boundary gate.
GIT_NETWORK_SUBCOMMANDS = frozenset(
    {"fetch", "pull", "push", "clone", "ls-remote", "remote", "submodule"}
)

# Modules that spawn a child outside subprocess's argv introspection.
SPAWN_MODULES = frozenset({"pty"})
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
# The only modules a sanctioned sys.executable spawner may run via -m.
PYTHON_M_ALLOWED = frozenset({"unittest"})
# subprocess helpers that take only a shell string, with no argv to inspect.
SHELL_STRING_CALLS = frozenset({"getoutput", "getstatusoutput"})

# Path methods that write. `.replace` is absent because datetime and str
# carry it too; Path.replace is matched separately by arity.
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
# os.open and os.fdopen are raw-fd writes that slip past the mode-string
# check, so they fire unconditionally; the rest create or alter entries or
# their metadata.
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
WRITE_TEMPFILE = frozenset(
    {"mkstemp", "mktemp", "NamedTemporaryFile", "TemporaryFile", "TemporaryDirectory"}
)
COMPRESS_OPEN_MODULES = frozenset({"gzip", "bz2", "lzma"})
# Modules whose import is itself the write capability: their open or connect
# creates the backing file with no call the write detector labels.
WRITE_MODULES = frozenset({"sqlite3", "dbm", "shelve"})
LOGGING_FILE_HANDLERS = frozenset(
    {
        "FileHandler",
        "RotatingFileHandler",
        "TimedRotatingFileHandler",
        "WatchedFileHandler",
    }
)
OPEN_WRITE_MODE_CHARS = "wax+"
ARCHIVE_WRITE_MODE_CHARS = "wax"

Bindings = tuple[dict[str, str], dict[str, tuple[str, str]]]


@dataclass(frozen=True, slots=True)
class EgressRules:
    """The policy a file is held to, dissolved into flags by the gate."""

    tier: str
    net_exempt: bool = False
    is_spawner: bool = False
    allowed: frozenset[str] = frozenset()
    egress: frozenset[tuple[str, str]] = frozenset()


def _str_const(node: ast.expr | None) -> str | None:
    """Return the value of a string-literal node, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _fstring_prefix(node: ast.expr | None) -> str | None:
    """Return the leading constant text of an f-string, else None."""
    if isinstance(node, ast.JoinedStr) and node.values:
        return _str_const(node.values[0])
    return None


def _attr_call(node: ast.Call) -> tuple[str | None, str]:
    """Return (receiver name, attribute) for `x.attr(...)`, else (None, attribute or '')."""
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value.id if isinstance(func.value, ast.Name) else None
        return base, func.attr
    return None, ""


def _import_bindings(tree: ast.Module) -> Bindings:
    """Map each imported local name to its module, and each from-import to (module, attr)."""
    module_of: dict[str, str] = {}
    from_bind: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                module_of[alias.asname or top] = top
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            top = node.module.split(".")[0]
            for alias in node.names:
                from_bind[alias.asname or alias.name] = (top, alias.name)
    return module_of, from_bind


def _imports_module(tree: ast.Module, names: frozenset[str]) -> bool:
    """Tell whether the file imports any of the named top-level modules."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] in names for alias in node.names):
                return True
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and not node.level
            and node.module.split(".")[0] in names
        ):
            return True
    return False


def _mode_argument(node: ast.Call, index: int) -> tuple[ast.expr | None, bool]:
    """Return the mode argument of an open-style call and whether it came by keyword."""
    keyword = next((k.value for k in node.keywords if k.arg == "mode"), None)
    if keyword is not None:
        return keyword, True
    return (node.args[index] if len(node.args) > index else None), False


def _open_write_label(
    prefix: str, node: ast.Call, index: int, *, strict_positional: bool = True
) -> str | None:
    """Label an open-style call that writes, failing closed on a non-literal mode."""
    # With strict_positional off, a non-literal positional is usually not a
    # mode at all (an opener's .open(request)), so only a keyword or a
    # literal positional is judged.
    arg, by_keyword = _mode_argument(node, index)
    if arg is None:
        return None
    mode = _str_const(arg)
    if mode is None:
        if by_keyword or strict_positional:
            return f"{prefix}(non-literal mode — not statically checkable)"
        return None
    return (
        f"{prefix}(write-mode)"
        if any(c in mode for c in OPEN_WRITE_MODE_CHARS)
        else None
    )


def _archive_write_label(prefix: str, node: ast.Call, index: int) -> str | None:
    """Label a zipfile or tarfile constructor that writes, failing closed on a non-literal mode."""
    # A tar mode carries a compression suffix ("r:xz"); only the part before
    # the separator names the direction.
    arg, _ = _mode_argument(node, index)
    if arg is None:
        return None
    mode = _str_const(arg)
    if mode is None:
        return f"{prefix}(non-literal mode — not statically checkable)"
    direction = re.split(r"[:|]", mode)[0]
    return (
        f"{prefix}(write-mode)"
        if any(c in direction for c in ARCHIVE_WRITE_MODE_CHARS)
        else None
    )


_MODULE_WRITE_TABLES = (
    ("shutil", WRITE_SHUTIL),
    ("os", WRITE_OS),
    ("tempfile", WRITE_TEMPFILE),
    ("logging", LOGGING_FILE_HANDLERS),
)


def _module_write(module: str, attr: str, node: ast.Call) -> str | None:
    """Label a module-level callable that writes, else None."""
    if any(module == name and attr in attrs for name, attrs in _MODULE_WRITE_TABLES):
        return f"{module}.{attr}"
    if attr == "open" and (
        module in ("io", "codecs") or module in COMPRESS_OPEN_MODULES
    ):
        return _open_write_label(f"{module}.open", node, 1)
    if module == "zipfile" and attr == "ZipFile":
        return _archive_write_label("zipfile.ZipFile", node, 1)
    if module == "tarfile" and attr in ("open", "TarFile"):
        return _archive_write_label(f"tarfile.{attr}", node, 1)
    return None


def _dyn_import_target(node: ast.Call, bindings: Bindings) -> str | None:
    """Return the literal module name a dynamic-import call names, else None."""
    module_of, from_bind = bindings
    func = node.func
    dynamic = False
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        base = func.value.id
        dynamic = (
            module_of.get(base, base) == "importlib" and func.attr == "import_module"
        )
    elif isinstance(func, ast.Name):
        dynamic = func.id == "__import__" or from_bind.get(func.id) == (
            "importlib",
            "import_module",
        )
    if not dynamic:
        return None
    return _str_const(node.args[0]) if node.args else None


def _is_path_replace(node: ast.Call) -> bool:
    """Tell whether a `.replace` call has Path.replace's arity: one target, no other keyword."""
    positional = len(node.args) == 1 and not node.keywords
    by_keyword = (
        not node.args and len(node.keywords) == 1 and node.keywords[0].arg == "target"
    )
    return positional or by_keyword


def _attribute_write(
    func: ast.Attribute, node: ast.Call, module_of: dict[str, str]
) -> str | None:
    """Label a `receiver.attr(...)` call that writes, else None."""
    attr = func.attr
    base = func.value.id if isinstance(func.value, ast.Name) else None
    module = module_of.get(base) if base else None
    if module == "write_guard":
        # The sanctioned wrapper, verified as the real imported module.
        return None
    if module is not None:
        return _module_write(module, attr, node)
    if attr in WRITE_METHODS:
        return f".{attr}(…)"
    if attr == "replace" and _is_path_replace(node):
        return ".replace(dst)"
    if attr == "open":
        return _open_write_label(".open", node, 0, strict_positional=False)
    return None


def _write_primitive(node: ast.Call, bindings: Bindings) -> str | None:
    """Label a call that writes raw to the filesystem, however it is spelled, else None."""
    module_of, from_bind = bindings
    dyn_name = _dyn_import_target(node, bindings)
    if dyn_name is not None and dyn_name.split(".")[0] in WRITE_MODULES:
        return f"dynamic import of {dyn_name.split('.')[0]}"
    func = node.func
    if isinstance(func, ast.Attribute):
        return _attribute_write(func, node, module_of)
    if isinstance(func, ast.Name):
        if func.id == "open" and func.id not in from_bind:
            return _open_write_label("open", node, 1)
        bound = from_bind.get(func.id)
        if bound:
            return _module_write(bound[0], bound[1], node)
    return None


def _argv0_token(node: ast.expr) -> str | None:
    """Return the manifest token an argv0 expression names, else None."""
    literal = _str_const(node)
    if literal is not None:
        return literal
    if (
        isinstance(node, ast.Attribute)
        and node.attr == "executable"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    ):
        return "sys.executable"
    return None


def _command_argument(node: ast.Call) -> ast.expr | None:
    """Return the command expression of a subprocess call, positional or `args=`."""
    if node.args:
        return node.args[0]
    return next((kw.value for kw in node.keywords if kw.arg == "args"), None)


@dataclass(frozen=True, slots=True)
class _SpawnCall:
    """One subprocess call with its literal argv elements."""

    file: Path
    node: ast.Call
    elements: tuple[ast.expr, ...]

    @property
    def where(self) -> str:
        """Return the file:line prefix of a hit."""
        return f"{rel(self.file)}:{self.node.lineno}"


def _python_m_hits(call: _SpawnCall) -> list[str]:
    """Flag a `python -m` target outside the sanctioned modules."""
    hits = []
    elements = call.elements
    for index, element in enumerate(elements[1:], 1):
        if _str_const(element) != "-m":
            continue
        target = _str_const(elements[index + 1]) if len(elements) > index + 1 else None
        if target not in PYTHON_M_ALLOWED:
            hits.append(
                f"{call.where}: python -m {target or '<dynamic>'} runs a module "
                f"by name — only {sorted(PYTHON_M_ALLOWED)} is sanctioned"
            )
    return hits


def _git_destination(elements: tuple[ast.expr, ...], after: int) -> str | None:
    """Return the first non-option literal after the subcommand, the URL a git call reaches."""
    return next(
        (
            url
            for element in elements[after + 1 :]
            if (url := _str_const(element) or _fstring_prefix(element)) is not None
            and not url.startswith("-")
        ),
        None,
    )


def _git_egress_hit(
    call: _SpawnCall,
    rules: EgressRules,
    used_egress: set[tuple[str, str]] | None,
) -> str | None:
    """Judge a literal git network subcommand anywhere in argv against the tier's rules."""
    # The subcommand may hide behind options, so every literal element is
    # scanned; a colliding non-subcommand literal fails loud.
    position, subcommand = next(
        (
            (index, literal)
            for index, element in enumerate(call.elements[1:], 1)
            if (literal := _str_const(element)) in GIT_NETWORK_SUBCOMMANDS
        ),
        (0, None),
    )
    if subcommand is None:
        return None
    if rules.tier == "shipped":
        return (
            f"{call.where}: shipped-runtime git subcommand "
            f"{subcommand!r} reaches the network"
        )
    url = _git_destination(call.elements, position)
    matched = {
        (name, prefix)
        for name, prefix in rules.egress
        if url is not None and subcommand == name and url.startswith(prefix)
    }
    if not matched:
        return (
            f"{call.where}: producer git subcommand {subcommand!r} "
            "reaches the network (only a sanctioned_egress pair is allowed)"
        )
    if used_egress is not None:
        used_egress |= matched
    return None


def _shell_command_hit(where: str, command: ast.expr) -> str | None:
    """Reject a subprocess command that is not a list literal."""
    literal = _str_const(command) or _fstring_prefix(command)
    if literal is not None:
        match = NETWORK_TOOL_RE.search(literal)
        if match:
            return (
                f"{where}: subprocess shell command spawns network "
                f"tool {match.group(1)!r}"
            )
        return (
            f"{where}: subprocess argv must be a list literal "
            "(a shell string is not statically checkable)"
        )
    if not isinstance(command, (ast.List, ast.Tuple)):
        return (
            f"{where}: subprocess argv must be a list literal "
            "(dynamic argv is not statically checkable)"
        )
    return None


def _argv0_hit(where: str, argv0: str | None, rules: EgressRules) -> str | None:
    """Hold a list-literal argv0 to the file's sanctioned spawn tokens."""
    if argv0 is not None and argv0 in NETWORK_TOOLS:
        return f"{where}: subprocess spawns network tool {argv0!r}"
    if argv0 is None or argv0 not in rules.allowed:
        return (
            f"{where}: subprocess argv0 {argv0!r} is outside this "
            f"file's sanctioned spawns {sorted(rules.allowed) or '(none)'} "
            "(confinement-policy.toml [[sanctioned_spawner]])"
        )
    return None


def _check_subprocess(
    file: Path,
    node: ast.Call,
    rules: EgressRules,
    used_egress: set[tuple[str, str]] | None = None,
) -> list[str]:
    """Hold one subprocess call's argv to the sanctioned spawn tokens and egress pairs."""
    command = _command_argument(node)
    if command is None:
        return []
    where = f"{rel(file)}:{node.lineno}"
    shell_hit = _shell_command_hit(where, command)
    if shell_hit:
        return [shell_hit]
    elements = tuple(command.elts) if isinstance(command, (ast.List, ast.Tuple)) else ()
    if not elements:
        return []
    call = _SpawnCall(file, node, elements)
    argv0 = _argv0_token(elements[0])
    argv0_hit = _argv0_hit(where, argv0, rules)
    if argv0_hit:
        return [argv0_hit]
    if argv0 == "sys.executable":
        return _python_m_hits(call)
    hit = _git_egress_hit(call, rules, used_egress) if argv0 == "git" else None
    return [hit] if hit else []


def _spawn_import_hit(where: str, top: str, rules: EgressRules) -> str | None:
    """Flag an imported top-level module that spawns outside a sanction."""
    if top == "subprocess" and not rules.is_spawner:
        return (
            f"{where}: imports subprocess — not a sanctioned spawner "
            "(confinement-policy.toml)"
        )
    if top in SPAWN_MODULES:
        return f"{where}: imports {top} — spawns outside argv introspection"
    return None


def _import_hits(file: Path, node: ast.Import, rules: EgressRules) -> list[str]:
    """Judge one `import` statement."""
    where = f"{rel(file)}:{node.lineno}"
    hits = []
    for alias in node.names:
        top = alias.name.split(".")[0]
        if top in NETWORK_MODULES and not rules.net_exempt:
            hits.append(f"{where}: imports network module {alias.name!r}")
            continue
        hit = _spawn_import_hit(where, top, rules)
        if hit:
            hits.append(hit)
    return hits


def _import_from_hits(
    file: Path, node: ast.ImportFrom, rules: EgressRules
) -> list[str]:
    """Judge one `from ... import` statement."""
    if node.level or not node.module:
        return []
    where = f"{rel(file)}:{node.lineno}"
    top = node.module.split(".")[0]
    if top in NETWORK_MODULES and not rules.net_exempt:
        return [f"{where}: imports from network module {node.module!r}"]
    hit = _spawn_import_hit(where, top, rules)
    if hit:
        return [hit]
    if top == "os":
        return [
            f"{where}: from os import {alias.name} spawns outside argv introspection"
            for alias in node.names
            if alias.name in OS_EXEC_CALLS
        ]
    return []


def _dynamic_import_hit(
    file: Path, node: ast.Call, dyn_name: str, rules: EgressRules
) -> str | None:
    """Flag a dynamic import of a network module or of a spawn capability."""
    top = dyn_name.partition(".")[0]
    if top in NETWORK_MODULES and not rules.net_exempt:
        return (
            f"{rel(file)}:{node.lineno}: dynamic import of network module {dyn_name!r}"
        )
    if top == "subprocess" or top in SPAWN_MODULES:
        # A dynamic spawn import would bypass the argv rules entirely.
        return f"{rel(file)}:{node.lineno}: dynamic import of {top!r} defeats the spawn sanction"
    return None


def _resolved_call(node: ast.Call, bindings: Bindings) -> tuple[str | None, str]:
    """Resolve a call to (module, attribute) through the file's import bindings."""
    # A bare unimported receiver still matches by its literal name, so
    # detection stays lenient where the write gate's sanction skip is strict.
    module_of, from_bind = bindings
    base, attr = _attr_call(node)
    if base:
        return module_of.get(base, base), attr
    if isinstance(node.func, ast.Name) and node.func.id in from_bind:
        return from_bind[node.func.id]
    return None, attr


@dataclass(frozen=True, slots=True)
class _FileScan:
    """One file's egress scan: its rules, its import bindings, and the egress ledger."""

    file: Path
    rules: EgressRules
    bindings: Bindings
    used_egress: set[tuple[str, str]] | None


def _call_hits(scan: _FileScan, node: ast.Call) -> list[str]:
    """Judge one call expression."""
    hits = []
    dyn_name = _dyn_import_target(node, scan.bindings)
    if dyn_name is not None:
        hit = _dynamic_import_hit(scan.file, node, dyn_name, scan.rules)
        if hit:
            hits.append(hit)
    module, called = _resolved_call(node, scan.bindings)
    where = f"{rel(scan.file)}:{node.lineno}"
    if module == "os" and called in OS_EXEC_CALLS:
        hits.append(f"{where}: os.{called} spawns outside argv introspection")
    elif module == "subprocess" and called in SHELL_STRING_CALLS:
        hits.append(
            f"{where}: subprocess.{called} executes a "
            "shell string (no argv to check) — use an argv-list call"
        )
    elif module == "subprocess" and called in SUBPROCESS_CALLS:
        hits.extend(_check_subprocess(scan.file, node, scan.rules, scan.used_egress))
    return hits


def _file_egress_hits(
    file: Path,
    tree: ast.Module,
    rules: EgressRules,
    used_egress: set[tuple[str, str]] | None = None,
) -> list[str]:
    """List every network or unchecked-spawn hit in one parsed file under its rules."""
    hits: list[str] = []
    scan = _FileScan(file, rules, _import_bindings(tree), used_egress)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hits.extend(_import_hits(file, node, rules))
        elif isinstance(node, ast.ImportFrom):
            hits.extend(_import_from_hits(file, node, rules))
        elif isinstance(node, ast.Call):
            hits.extend(_call_hits(scan, node))
    return hits
