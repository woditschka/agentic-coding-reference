"""Run the static tools and the source-tree scans over the harness source."""

import ast
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from verify_harness.battery import Battery, shell_scripts
from verify_harness.text import HERE, ROOT, read_text, rel

# samples/ and plugins/ are byte-identical materialized copies, formatted by
# propagation and gated by faithfulness, never scanned here.
RUFF_TARGETS = ("harness", "tools", "evals")
SHOWN_IMPORT_HITS = 10
DEPENDENCY_MANIFESTS = (
    "requirements*.txt",
    "pyproject.toml",
    "Pipfile",
    "setup.py",
    "setup.cfg",
)


def _tool_available(b: Battery, tool: str, hint: str) -> bool:
    """Tell whether a static tool is on PATH, failing under --strict or skipping otherwise."""
    if shutil.which(tool) is not None:
        return True
    if b.strict:
        b.fail(
            f"{tool} required under --strict but not installed "
            f"(the push-time gates run --strict; {hint})"
        )
    else:
        b.skip(f"{tool} not installed ({hint})")
    return False


def _run_tool(b: Battery, argv: list[str], failure: str, passed: str) -> None:
    """Run one static tool from ROOT and report its verdict with its output on failure."""
    result = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT, check=False)
    if result.returncode != 0:
        b.fail(f"{failure}\n{result.stdout}{result.stderr}".rstrip())
    else:
        b.record_pass(passed)


def check_shellcheck(b: Battery) -> None:
    """Lint every harness and tools shell script at shellcheck's warning level."""
    b.note("shellcheck (harness/ + tools/)")
    if not _tool_available(b, "shellcheck", "brew install shellcheck"):
        return
    problems = []
    scripts = [*shell_scripts(ROOT / "harness"), *shell_scripts(ROOT / "tools")]
    for script in scripts:
        result = subprocess.run(
            ["shellcheck", "-S", "warning", str(script)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            problems.append(
                f"shellcheck flagged {rel(script)}\n{result.stdout}".rstrip()
            )
    b.report(problems, "clean")


def check_bandit(b: Battery) -> None:
    """Run bandit at medium severity over the maintainer and source Python."""
    b.note("bandit (python security, harness/ + tools/ + evals/)")
    if not _tool_available(b, "bandit", "pipx install bandit"):
        return
    # --ignore-nosec keeps suppression a review decision, never a source-file
    # one. evals/.runs holds whole repo copies outside the working tree.
    _run_tool(
        b,
        [
            "bandit",
            "-q",
            "-r",
            "-ll",
            "--ignore-nosec",
            str(ROOT / "harness"),
            str(ROOT / "tools"),
            str(ROOT / "evals"),
            "-x",
            str(ROOT / "evals" / ".runs"),
        ],
        "bandit flagged python security findings (medium+ severity)",
        "clean",
    )


def _mypy_scope() -> list[str]:
    """Return the [tool.mypy] files list from the root pyproject, or [] when unreadable."""
    try:
        config = tomllib.loads(read_text(ROOT / "pyproject.toml"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    files = config.get("tool", {}).get("mypy", {}).get("files", [])
    return files if isinstance(files, list) else []


def check_ruff_format(b: Battery) -> None:
    """Hold the maintainer and source Python to ruff's formatter."""
    b.note(f"ruff format --check ({' + '.join(t + '/' for t in RUFF_TARGETS)})")
    if not _tool_available(b, "ruff", "pipx install ruff"):
        return
    _run_tool(
        b,
        ["ruff", "format", "--check", *RUFF_TARGETS],
        f"ruff format --check found unformatted files (run: ruff format {' '.join(RUFF_TARGETS)})",
        "formatted",
    )


def check_ruff_lint(b: Battery) -> None:
    """Lint the maintainer and source Python with the root pyproject's rule set."""
    b.note(f"ruff check (lint, {' + '.join(t + '/' for t in RUFF_TARGETS)})")
    if not _tool_available(b, "ruff", "pipx install ruff"):
        return
    _run_tool(
        b, ["ruff", "check", *RUFF_TARGETS], "ruff check flagged lint findings", "clean"
    )


# mypy refuses a same-named file and package in one build, so each
# composition-root entry is checked alone, after the pyproject scope.
ENTRY_MODULES = (
    "harness/core/scripts/handoff.py",
    "harness/core/scripts/grading.py",
    "harness/core/scripts/changeset.py",
)


def check_mypy(b: Battery) -> None:
    """Type-check the pyproject scope strictly, then each composition-root entry alone."""
    b.note("mypy --strict (typed scope from pyproject)")
    if not _tool_available(b, "mypy", "pipx install mypy"):
        return
    scope = _mypy_scope()
    if not scope:
        b.record_pass("scope empty — no module under the pyproject strict scope")
    else:
        _run_tool(
            b,
            ["mypy"],
            f"mypy --strict found type errors in the typed scope ({len(scope)} path(s))",
            f"clean ({len(scope)} path(s) in scope)",
        )
    for entry in ENTRY_MODULES:
        _run_tool(
            b,
            ["mypy", entry],
            f"mypy --strict found type errors in the entry ({entry})",
            f"clean (entry {entry})",
        )


# The one-way import graph of the scripts composition root, keyed by path
# relative to core/scripts; the value is the set of local modules a file may
# depend on. A file absent from the table fails loudly.
IMPORT_LOCAL_ROOTS = {
    "changeset",
    "handoff",
    "grading",
    "accounting",
    "doctor",
    "backlog",
}
IMPORT_ALLOWED: dict[str, set[str]] = {
    "handoff/schema.py": set(),
    "handoff/records.py": set(),
    "handoff/ledger.py": {"handoff.records", "handoff.schema"},
    "handoff/findings.py": {"handoff.ledger", "handoff.records"},
    "handoff/tiers.py": {"handoff.findings", "handoff.ledger", "handoff.records"},
    "handoff/roster.py": {"handoff.ledger", "handoff.records", "handoff.schema"},
    "handoff/ladder.py": {
        "handoff.findings",
        "handoff.ledger",
        "handoff.records",
        "handoff.roster",
    },
    "handoff/scope_lock.py": {"handoff.ledger", "handoff.records"},
    "handoff/repository.py": {"handoff.timestamps"},
    "handoff/non_goals.py": {"handoff.repository"},
    "handoff/autofix.py": {
        "handoff.ledger",
        "handoff.non_goals",
        "handoff.records",
        "handoff.repository",
        "handoff.timestamps",
    },
    "handoff/gates.py": {
        "handoff.autofix",
        "handoff.ledger",
        "handoff.records",
        "handoff.repository",
        "handoff.schema",
    },
    "handoff/routing.py": {
        "handoff.findings",
        "handoff.ladder",
        "handoff.ledger",
        "handoff.records",
        "handoff.roster",
        "handoff.schema",
        "handoff.scope_lock",
        "handoff.tiers",
    },
    "handoff/text.py": set(),
    "handoff/timestamps.py": set(),
    "handoff/cost.py": {
        "handoff.ledger",
        "handoff.records",
        "handoff.timestamps",
        "accounting",
    },
    "handoff/board.py": {
        "handoff.cost",
        "handoff.ledger",
        "handoff.records",
        "handoff.schema",
        "handoff.timestamps",
    },
    "handoff/view.py": {
        "handoff.board",
        "handoff.cost",
        "handoff.ledger",
        "handoff.records",
        "handoff.schema",
        "handoff.text",
        "handoff.timestamps",
    },
    "handoff/__init__.py": {
        "handoff.autofix",
        "handoff.board",
        "handoff.cost",
        "handoff.findings",
        "handoff.gates",
        "handoff.ladder",
        "handoff.ledger",
        "handoff.non_goals",
        "handoff.records",
        "handoff.repository",
        "handoff.roster",
        "handoff.routing",
        "handoff.schema",
        "handoff.scope_lock",
        "handoff.text",
        "handoff.tiers",
        "handoff.timestamps",
        "handoff.view",
    },
    # An entry is a launcher: submodule from-imports only. Its bare
    # self-import is a named failure, not merely a disallowed edge.
    "handoff.py": {
        "handoff.schema",
        "handoff.records",
        "handoff.cost",
        "handoff.timestamps",
        "handoff.tiers",
        "handoff.roster",
        "handoff.autofix",
        "handoff.gates",
        "handoff.non_goals",
        "handoff.repository",
        "handoff.ledger",
        "handoff.routing",
        "handoff.board",
        "handoff.view",
    },
    "changeset/__init__.py": set(),
    "changeset/config.py": set(),
    "changeset/git_facts.py": set(),
    "changeset/emit.py": {"changeset.config", "changeset.git_facts"},
    "changeset.py": {"changeset.config", "changeset.emit", "changeset.git_facts"},
    "grading/__init__.py": set(),
    "grading/config.py": {"grading.conventions"},
    "grading/features.py": {
        "grading.config",
        "grading.conventions",
        "changeset.git_facts",
    },
    # handoff_facts reaches the handoff package through a lazy
    # importlib.import_module, invisible to the ast walk; the gate certifies
    # static imports only, so that deliberate dynamic edge is named here.
    "grading/handoff_facts.py": {"grading.config"},
    "grading/planner.py": {"grading.config", "grading.features"},
    "grading/contracts.py": set(),
    "grading/coverage.py": set(),
    "grading/conventions.py": set(),
    "grading.py": {
        "changeset.config",
        "changeset.emit",
        "changeset.git_facts",
        "grading.config",
        "grading.contracts",
        "grading.conventions",
        "grading.coverage",
        "grading.features",
        "grading.handoff_facts",
        "grading.planner",
    },
    # The doctor's grading import is guarded: a maintainer script loading the
    # doctor by path has no grading package beside it.
    "doctor.py": {"grading.config"},
    "accounting.py": set(),
    "backlog.py": set(),
}
IMPORT_ENTRIES = ("handoff.py", "grading.py", "changeset.py")

# The battery's own package, keyed by path relative to harness/verify_harness:
# launcher → checks → battery → text. registry is an external import and
# stays invisible; the hyphenated launcher is not an importable module.
VERIFY_HARNESS_LOCAL_ROOTS = {"verify_harness"}
VERIFY_HARNESS_ALLOWED: dict[str, set[str]] = {
    "__init__.py": set(),
    "text.py": set(),
    "battery.py": {"verify_harness.text"},
    "checks/__init__.py": set(),
    # The confinement gate drives the policy-free detector module beneath it.
    "checks/confinement.py": {
        "verify_harness.battery",
        "verify_harness.checks.confinement_ast",
        "verify_harness.text",
    },
    "checks/confinement_ast.py": {"verify_harness.text"},
    "checks/lint.py": {"verify_harness.battery", "verify_harness.text"},
    # The annotation probe runs as a subprocess on the shipped tree, so a
    # shipped module never sees the checker.
    "probe_annotations.py": set(),
    "checks/sync.py": {"verify_harness.battery", "verify_harness.text"},
    "checks/suites.py": {"verify_harness.battery", "verify_harness.text"},
}


@dataclass(frozen=True, slots=True)
class ImportTree:
    """One gated tree: its files, its declared edges, and the local module roots."""

    base: Path
    label: str
    table_name: str
    table: dict[str, set[str]]
    local_roots: set[str]
    root_package: str = ""
    entries: tuple[str, ...] = ()


def _gated_trees() -> tuple[ImportTree, ImportTree]:
    """Return the two gated trees under the current harness root."""
    scripts = ImportTree(
        base=HERE / "core/scripts",
        label="scripts",
        table_name="IMPORT_ALLOWED",
        table=IMPORT_ALLOWED,
        local_roots=IMPORT_LOCAL_ROOTS,
        entries=IMPORT_ENTRIES,
    )
    package = ImportTree(
        base=HERE / "verify_harness",
        label="verify_harness",
        table_name="VERIFY_HARNESS_ALLOWED",
        table=VERIFY_HARNESS_ALLOWED,
        local_roots=VERIFY_HARNESS_LOCAL_ROOTS,
        root_package="verify_harness",
    )
    return scripts, package


def _import_deps(
    tree: ast.Module, package: str, local_roots: set[str]
) -> list[tuple[str, int]]:
    """List the (module, line) local dependencies of one parsed file."""
    deps: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            deps.extend(
                (alias.name, node.lineno)
                for alias in node.names
                if alias.name.split(".")[0] in local_roots
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                deps.append(
                    (
                        f"{package}.{node.module}" if node.module else package,
                        node.lineno,
                    )
                )
            elif node.module and node.module.split(".")[0] in local_roots:
                deps.append((node.module, node.lineno))
    return deps


def _file_import_problems(tree: ImportTree, file: Path) -> list[str]:
    """Check one file's local imports against its declared edges."""
    relpath = file.relative_to(tree.base).as_posix()
    allowed = tree.table.get(relpath)
    if allowed is None:
        return [
            f"{rel(file)}: outside the import-boundary table — a new {tree.label} "
            f"module must declare its allowed local imports in {tree.table_name}"
        ]
    directories = relpath.rsplit("/", 1)[0].replace("/", ".") if "/" in relpath else ""
    package = ".".join(part for part in (tree.root_package, directories) if part)
    try:
        parsed = ast.parse(file.read_text(encoding="utf-8"), str(file))
    except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
        return [f"{rel(file)}: unparseable for the boundary gate: {exc}"]
    problems = []
    for dep, lineno in _import_deps(parsed, package, tree.local_roots):
        if relpath in tree.entries and dep == relpath[:-3]:
            problems.append(
                f"{tree.label}/{relpath}:{lineno}: entry must import submodule-form; "
                f"a bare `import {dep}` resolves to the entry itself; the design "
                "document's package map names the allowed edges"
            )
        elif dep not in allowed:
            problems.append(
                f"{tree.label}/{relpath}:{lineno}: imports {dep!r} — outside its "
                f"allowed set {sorted(allowed) or '{}'}"
            )
    return problems


def _import_tree_problems(tree: ImportTree) -> tuple[int, list[str]]:
    """Check one tree's import graph, returning its module count and the problems."""
    files = [
        file
        for file in sorted(tree.base.rglob("*.py"))
        if "__pycache__" not in file.parts
        and "tests" not in file.relative_to(tree.base).parts
    ]
    problems = [
        problem for file in files for problem in _file_import_problems(tree, file)
    ]
    seen = {file.relative_to(tree.base).as_posix() for file in files}
    missing = set(tree.table) - seen
    if missing:
        # A table entry with no file would silently never be checked.
        problems.append(
            f"{tree.label} import-boundary table names absent files: {sorted(missing)}"
        )
    return len(files), problems


def check_import_boundaries(b: Battery) -> None:
    """Hold the scripts composition root and the battery package to their one-way import graphs."""
    b.note("import boundaries (scripts composition root)")
    scripts_tree, package_tree = _gated_trees()
    scripts_count, problems = _import_tree_problems(scripts_tree)
    package_count, package_problems = _import_tree_problems(package_tree)
    b.report(
        [*problems, *package_problems],
        f"graph intact ({scripts_count} runtime modules + {package_count} verify_harness modules)",
    )


def _local_names(file: Path) -> set[str]:
    """Return the module names a shipped file resolves locally at runtime."""
    siblings = {path.stem for path in file.parent.glob("*.py")}
    if "scripts" not in file.parts:
        return siblings
    # A file under a scripts/ tree runs with the scripts root on sys.path, and
    # a stack's scripts tree ships merged with core's, so core's root modules
    # and packages are runtime siblings of a stack test.
    roots = [Path(*file.parts[: file.parts.index("scripts") + 1])]
    if HERE / "stacks" in file.parents:
        roots.append(HERE / "core/scripts")
    for root in roots:
        siblings |= {path.stem for path in root.glob("*.py")}
        siblings |= {
            path.name for path in root.iterdir() if (path / "__init__.py").is_file()
        }
    return siblings


def _third_party_imports(file: Path, tree: ast.Module, local: set[str]) -> list[str]:
    """List the imports of one file that resolve to neither the stdlib nor a local module."""
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [(alias.name.split(".")[0], node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            names = [(node.module.split(".")[0], node.lineno)]
        else:
            continue
        hits.extend(
            f"{rel(file)}:{line}: imports '{name}'"
            for name, line in names
            if name not in sys.stdlib_module_names and name not in local
        )
    return hits


def _shipped_python(roots: list[Path]) -> dict[Path, list[Path]]:
    """Map each shipped root to its Python files."""
    return {
        root: sorted(
            path for path in root.rglob("*.py") if "__pycache__" not in path.parts
        )
        for root in roots
    }


def _stdlib_only_hits(files: list[Path], roots: list[Path]) -> list[str]:
    """List every dependency manifest and third-party import across the shipped files."""
    manifests = sorted(
        manifest
        for root in roots
        for pattern in DEPENDENCY_MANIFESTS
        for manifest in root.rglob(pattern)
    )
    hits = [f"{rel(manifest)}: dependency manifest" for manifest in manifests]
    for file in files:
        try:
            tree = ast.parse(read_text(file), str(file))
        except (SyntaxError, ValueError):
            # The syntax step owns and aggregates unparseable files.
            continue
        hits.extend(_third_party_imports(file, tree, _local_names(file)))
    return hits


def check_stdlib_only(b: Battery) -> None:
    """Refuse any third-party import or dependency manifest in the shipped runtime."""
    b.note("stdlib-only shipped runtime (no third-party imports)")
    roots = [HERE / "core", HERE / "stacks", HERE / "claude-md"]
    loose = [HERE / "refresh-gitignore.py"]
    missing = [path for path in roots + loose if not path.exists()]
    if missing:
        # An absent tree must not report "no third-party import" unscanned.
        b.fail(f"{', '.join(rel(m) for m in missing)} missing — cannot scan imports")
        return
    try:
        by_root = _shipped_python(roots)
        empty = [root for root, files in by_root.items() if not files]
        if empty:
            b.fail(
                f"{', '.join(rel(r) for r in empty)} holds no .py — "
                "refusing to report 'stdlib only' having scanned nothing"
            )
            return
        files = [file for files in by_root.values() for file in files] + loose
        hits = _stdlib_only_hits(files, roots)
    except OSError as exc:
        b.fail(f"could not scan the shipped runtime for imports: {exc}")
        return
    if hits:
        shown = "\n".join(f"    {hit}" for hit in hits[:SHOWN_IMPORT_HITS])
        b.fail(
            "the shipped runtime is stdlib-only by contract (stdlib or a "
            f"module in the same directory; no dependency manifest):\n{shown}"
        )
    else:
        b.record_pass("shipped runtime imports stdlib only")


# Shipped modules a producer script also loads by path, without the packages
# beside them; a name bound only under a guarded import must not reach a
# signature unquoted there.
LOADED_BY_PATH = ("doctor.py",)


def check_annotation_evaluation(b: Battery) -> None:
    """Evaluate every shipped signature annotation on this interpreter."""
    b.note("annotation evaluation (shipped runtime)")
    scripts = HERE / "core" / "scripts"
    modules = sorted(
        path
        for path in scripts.rglob("*.py")
        if "tests" not in path.parts and "__pycache__" not in path.parts
    )
    by_path = [str(scripts / name) for name in LOADED_BY_PATH]
    probe = HERE / "verify_harness" / "probe_annotations.py"
    proc = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(probe),
            str(scripts),
            *map(str, modules),
            "--by-path",
            *by_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stdout + proc.stderr).strip()
        b.fail(f"an annotation in the shipped runtime does not evaluate:\n    {detail}")
        return
    b.record_pass(proc.stdout.strip())


def check_python_syntax(b: Battery) -> None:
    """Compile every harness Python file in memory."""
    b.note("python syntax")
    problems = []
    for file in sorted((ROOT / "harness").rglob("*.py")):
        if "__pycache__" in file.parts:
            continue
        try:
            compile(file.read_text(encoding="utf-8"), str(file), "exec")
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            problems.append(f"python syntax error in {rel(file)}: {exc}")
    b.report(problems, "ok")
