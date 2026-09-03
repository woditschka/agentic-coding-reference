"""Static-tool checks (ADR 2026-07-18 check-sync-decomposition): the steps
that shell out to static analyzers or walk source ASTs — shellcheck, bandit,
ruff, mypy, the import-boundary gate, the stdlib-only scan, and python
syntax. Evidence read: the source tree itself, never a rendered copy."""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

from verify_harness.battery import Battery, _shell_scripts
from verify_harness.text import HERE, ROOT, read_text, rel


def _tool_available(b: Battery, tool: str, hint: str) -> bool:
    """The shared presence contract of every static-tool step: True when tool
    is on PATH; otherwise FAIL under --strict (the push-time gates set it) or
    a loud SKIP — the dev-machine default. StrictToolPresence tests the pair."""
    if shutil.which(tool) is not None:
        return True
    if b.strict:
        b.fail(
            f"{tool} required under --strict but not installed "
            f"(the push-time gates run --strict; {hint})"
        )
    else:
        print(f"  SKIP: {tool} not installed ({hint})")
    return False


def check_shellcheck(b: Battery) -> None:
    """1. Shell lint (harness source scripts + the shipped user-level tooling)."""
    b.note("shellcheck (harness/ + tools/)")
    if not _tool_available(b, "shellcheck", "brew install shellcheck"):
        return
    ok = True
    for f in list(_shell_scripts(ROOT / "harness")) + list(
        _shell_scripts(ROOT / "tools")
    ):
        result = subprocess.run(
            ["shellcheck", "-S", "warning", str(f)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(result.stdout, end="")
            b.fail(f"shellcheck flagged {rel(f)}")
            ok = False
    if ok:
        print("  clean")


def check_bandit(b: Battery) -> None:
    """1b. Python security lint (medium+ severity), same contract as
    shellcheck: run when installed, loud SKIP when not. Gates the mechanical
    findings; trust-boundary judgment belongs to audit-harness Layer 3.
    --ignore-nosec so an in-tree `# nosec` comment cannot silently disarm a
    finding — suppression is a review decision, not a source-file one."""
    b.note("bandit (python security, harness/ + tools/ + evals/)")
    if not _tool_available(b, "bandit", "pipx install bandit"):
        return
    result = subprocess.run(
        [
            "bandit",
            "-q",
            "-r",
            "-ll",
            "--ignore-nosec",
            str(ROOT / "harness"),
            str(ROOT / "tools"),
            str(ROOT / "evals"),
            # evals/.runs is gitignored sweep scratch holding whole repo
            # copies (pruned marketplace sources); scanning it would make
            # the verdict depend on leftover state outside the working tree.
            "-x",
            str(ROOT / "evals" / ".runs"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        b.fail("bandit flagged python security findings (medium+ severity)")
    else:
        print("  clean")


# The maintainer + source Python ruff and mypy gate. Scope matches the
# one-time format pass (ADR 2026-07-17): harness/ (scripts, hooks, claude-md),
# tools/, and the evals/ bench. samples/ and plugins/ are byte-identical
# materialized copies — formatted by propagation, gated by faithfulness
# (step 3), never scanned here.
RUFF_TARGETS = ("harness", "tools", "evals")


def _mypy_scope() -> list[str]:
    """The [tool.mypy] files list from the root pyproject — the typed scope,
    now the full harness-core Python (ADR 2026-07-17 tail slice). Empty or
    absent means nothing is under the strict checker, so the mypy step passes
    trivially (the defensive path if the list is ever cleared)."""
    import tomllib

    try:
        cfg = tomllib.loads(read_text(ROOT / "pyproject.toml"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    files = cfg.get("tool", {}).get("mypy", {}).get("files", [])
    return files if isinstance(files, list) else []


def check_ruff_format(b: Battery) -> None:
    """1d. ruff format --check over the maintainer + source Python (ADR
    2026-07-17), same contract as shellcheck: run when installed, loud SKIP
    when not, FAIL under --strict. The formatter owns line width — lint (1e)
    ignores E501 for exactly this reason."""
    b.note(f"ruff format --check ({' + '.join(t + '/' for t in RUFF_TARGETS)})")
    if not _tool_available(b, "ruff", "pipx install ruff"):
        return
    result = subprocess.run(
        ["ruff", "format", "--check", *RUFF_TARGETS],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        b.fail(
            "ruff format --check found unformatted files "
            f"(run: ruff format {' '.join(RUFF_TARGETS)})"
        )
    else:
        print("  formatted")


def check_ruff_lint(b: Battery) -> None:
    """1e. ruff check (lint) over the maintainer + source Python. The select
    and ignore lists live in the root pyproject.toml; S (security) is absent
    because bandit (1b) owns it. Same skip-if-missing / FAIL-under-strict
    contract as shellcheck."""
    b.note(f"ruff check (lint, {' + '.join(t + '/' for t in RUFF_TARGETS)})")
    if not _tool_available(b, "ruff", "pipx install ruff"):
        return
    result = subprocess.run(
        ["ruff", "check", *RUFF_TARGETS],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        b.fail("ruff check flagged lint findings")
    else:
        print("  clean")


ENTRY_MODULES = (
    "harness/core/scripts/handoff.py",
    "harness/core/scripts/grading.py",
    "harness/core/scripts/changeset.py",
)


def check_mypy(b: Battery) -> None:
    """1f. mypy --strict over the typed scope declared in pyproject
    [tool.mypy].files. Same skip-if-missing / FAIL-under-strict contract as
    shellcheck. The scope is the full harness-core Python (ADR 2026-07-17 tail
    slice completed it) plus the producer-side orchestration widened in tranche
    by tranche (same ADR, producer-side-typed-scope amendment); an empty scope
    still passes trivially and says so, the defensive path if the list is ever
    cleared.

    Runs mypy once over the pyproject scope (the changeset/, handoff/, and
    grading/ packages plus the root modules), then once per composition-root
    entry (ENTRY_MODULES) alone (ADR 2026-07-17 runtime-package-layout). mypy
    refuses a same-named file and package in one build ("Duplicate module named
    'handoff'"), so the three same-named entries (handoff.py, grading.py,
    changeset.py) cannot join the pyproject scope. A solo run resolves an
    entry's submodule from-imports against the real package and strict-checks
    the launcher."""
    b.note("mypy --strict (typed scope from pyproject)")
    if not _tool_available(b, "mypy", "pipx install mypy"):
        return
    scope = _mypy_scope()
    if not scope:
        # Trivial pass for the pyproject scope only — the entry solo runs
        # below still execute, so clearing the files list can never silently
        # disarm the launchers' strict check too.
        print("  scope empty — no module under the pyproject strict scope")
    else:
        result = subprocess.run(
            ["mypy"], capture_output=True, text=True, cwd=ROOT, check=False
        )
        if result.returncode != 0:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            b.fail(
                f"mypy --strict found type errors in the typed scope ({len(scope)} path(s))"
            )
        else:
            print(f"  clean ({len(scope)} path(s) in scope)")
    # One solo run per composition-root entry (an entry cannot share a build
    # with its same-named package, and two entries cannot share one run
    # without each self-resolving the other's package name).
    for entry in ENTRY_MODULES:
        entry_result = subprocess.run(
            ["mypy", entry], capture_output=True, text=True, cwd=ROOT, check=False
        )
        if entry_result.returncode != 0:
            print(entry_result.stdout, end="")
            print(entry_result.stderr, end="", file=sys.stderr)
            b.fail(f"mypy --strict found type errors in the entry ({entry})")
        else:
            print(f"  clean (entry {entry})")


# 1g input: the one-way import graph of the scripts composition root (ADR
# 2026-07-17 runtime-package-layout). Keyed by path relative to core/scripts;
# the value is the set of LOCAL modules each file may depend on. Stdlib imports
# are invisible to the gate. A file under scripts/ absent from this table fails
# loudly — a new module must declare its allowed edges here.
IMPORT_LOCAL_ROOTS = {"changeset", "handoff", "grading", "accounting", "doctor"}
IMPORT_ALLOWED: dict[str, set[str]] = {
    "handoff/schema.py": set(),
    "handoff/records.py": set(),
    "handoff/routing.py": {"handoff.records", "handoff.schema"},
    "handoff/view.py": {"handoff.records", "handoff.schema", "accounting"},
    "handoff/__init__.py": {
        "handoff.schema",
        "handoff.records",
        "handoff.routing",
        "handoff.view",
    },
    # The entry is a launcher: submodule from-imports only. A bare `import
    # handoff` (dep "handoff") is a named failure below, not merely disallowed.
    "handoff.py": {
        "handoff.schema",
        "handoff.records",
        "handoff.routing",
        "handoff.view",
    },
    # The change-set layer (ADR 2026-07-17 runtime-package-layout): config is
    # the exclude-filter ACL (a leaf), git_facts the git gateway over it, and
    # emit the base/head resolution and emit verb over the gateway. Neutral of
    # grading — the changeset.py launcher and the grading package both compose it.
    "changeset/__init__.py": set(),
    "changeset/config.py": set(),
    "changeset/git_facts.py": {"changeset.config"},
    "changeset/emit.py": {"changeset.git_facts"},
    # The changeset launcher: submodule from-imports only. Like handoff.py and
    # grading.py, a bare `import changeset` (dep "changeset") resolves to the
    # entry itself under a solo strict run — a named failure below.
    "changeset.py": {"changeset.emit"},
    # The grading package's layer map (ADR 2026-07-17 runtime-package-layout):
    # config is a leaf, the model reads diffs through the changeset git gateway,
    # and the planner imports no gateway — its two git-backed reads are injected
    # by the entry as callables.
    "grading/__init__.py": set(),
    "grading/config.py": set(),
    "grading/features.py": {"grading.config", "changeset.git_facts"},
    # handoff_facts reaches the handoff package only through a lazy
    # importlib.import_module("handoff") (the validator API); a dynamic
    # import is invisible to the ast walk, so it is absent from the static
    # set. The gate certifies static imports only — a deliberate dynamic
    # edge must be named here in a comment, as this one is.
    "grading/handoff_facts.py": {"grading.config"},
    "grading/planner.py": {"grading.config", "grading.features"},
    # The gate's design-doc sync check: pure functions over two doc files,
    # stdlib only — a leaf like config.
    "grading/contracts.py": set(),
    "grading/coverage.py": set(),
    # The grading entry launcher: submodule from-imports only, like handoff.py.
    # It composes the grading package over the changeset package (the base rule
    # and git gateway).
    "grading.py": {
        "changeset.emit",
        "changeset.git_facts",
        "grading.config",
        "grading.contracts",
        "grading.coverage",
        "grading.features",
        "grading.handoff_facts",
        "grading.planner",
    },
    # The doctor validates layout.toml [[module]] rules with the engine's own
    # ACL validator (lazy in-function import; skips when the package is not on
    # the path in maintainer contexts).
    "doctor.py": {"grading.config"},
    "accounting.py": set(),
}
# The three composition-root entries whose bare self-import is a named failure.
IMPORT_ENTRIES = ("handoff.py", "grading.py", "changeset.py")

# 1g input, second tree: the battery's own verify_harness package (ADR 2026-07-18
# check-sync-decomposition). Same declaration style, keyed by path relative to
# harness/verify_harness. The graph is launcher → checks → battery → text; text is
# the leaf. `registry` is an external (producer-side) import and stays invisible
# here — only verify_harness-internal edges are gated. The launcher verify-harness.py
# is not a valid module name, so no module can import it; no entry rule needed.
VERIFY_HARNESS_LOCAL_ROOTS = {"verify_harness"}
VERIFY_HARNESS_ALLOWED: dict[str, set[str]] = {
    "__init__.py": set(),
    "text.py": set(),
    "battery.py": {"verify_harness.text"},
    "checks/__init__.py": set(),
    # The confinement gate is a pair: the gate (policy + steps) drives the
    # policy-free detector module beneath it — a one-way edge.
    "checks/confinement.py": {
        "verify_harness.battery",
        "verify_harness.checks.confinement_ast",
        "verify_harness.text",
    },
    "checks/confinement_ast.py": {"verify_harness.text"},
    "checks/lint.py": {"verify_harness.battery", "verify_harness.text"},
    "checks/sync.py": {"verify_harness.battery", "verify_harness.text"},
    "checks/suites.py": {"verify_harness.battery", "verify_harness.text"},
}


def _import_deps(
    tree: ast.Module, pkg: str, local_roots: set[str]
) -> list[tuple[str, int]]:
    """Local-module dependencies of one parsed file: [(dep, lineno)]. Relative
    imports resolve against pkg (the file's package); stdlib imports drop out."""
    deps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in local_roots:
                    deps.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # Relative (one level in this tree): from .mod -> pkg.mod,
                # from . import x -> pkg.
                mod = f"{pkg}.{node.module}" if node.module else pkg
                deps.append((mod, node.lineno))
            elif node.module and node.module.split(".")[0] in local_roots:
                deps.append((node.module, node.lineno))
    return deps


def _check_import_tree(
    b: Battery,
    base: Path,
    label: str,
    table_name: str,
    table: dict[str, set[str]],
    local_roots: set[str],
    root_pkg: str = "",
    entries: tuple[str, ...] = (),
) -> int | None:
    """One tree's one-way import graph against its declared table. Returns the
    module count when the graph holds, None when any edge (or the table's own
    coverage) failed. label prefixes messages; root_pkg is the tree's package
    name ('' for the scripts composition root, whose files are top-level)."""
    ok = True
    seen = set()
    for f in sorted(base.rglob("*.py")):
        if "__pycache__" in f.parts or "tests" in f.relative_to(base).parts:
            continue
        relpath = f.relative_to(base).as_posix()
        seen.add(relpath)
        allowed = table.get(relpath)
        if allowed is None:
            b.fail(
                f"{rel(f)}: outside the import-boundary table — a new {label} "
                f"module must declare its allowed local imports in {table_name}"
            )
            ok = False
            continue
        dirs = relpath.rsplit("/", 1)[0].replace("/", ".") if "/" in relpath else ""
        pkg = ".".join(p for p in (root_pkg, dirs) if p)
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"), str(f))
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            b.fail(f"{rel(f)}: unparseable for the boundary gate: {exc}")
            ok = False
            continue
        for dep, lineno in _import_deps(tree, pkg, local_roots):
            if relpath in entries and dep == relpath[:-3]:
                b.fail(
                    f"{label}/{relpath}:{lineno}: entry must import submodule-form; "
                    f"a bare `import {dep}` resolves to the entry itself "
                    "(see ADR 2026-07-17 runtime-package-layout)"
                )
                ok = False
            elif dep not in allowed:
                b.fail(
                    f"{label}/{relpath}:{lineno}: imports {dep!r} — outside its "
                    f"allowed set {sorted(allowed) or '{}'}"
                )
                ok = False
    missing = set(table) - seen
    if missing:
        # A table entry with no file: the gate would silently never check it.
        b.fail(f"{label} import-boundary table names absent files: {sorted(missing)}")
        ok = False
    return len(seen) if ok else None


def check_import_boundaries(b: Battery) -> None:
    """1g. The one-way import graphs of the two gated trees. First the scripts
    composition root (ADR 2026-07-17 runtime-package-layout): over every
    runtime .py under core/scripts (tests/ excluded), resolve each import to an
    absolute module and check it against the allowed edges: schema and records
    are leaves, routing and view depend only downward, the package __init__
    composes submodules, and the entry launcher does submodule from-imports
    only. No file may import the doctor or reach an entry as a module. Then the
    battery's own verify_harness package (ADR 2026-07-18 check-sync-decomposition):
    launcher → checks → battery → text, text the leaf. Static and fast — it
    runs in --quick too."""
    b.note("import boundaries (scripts composition root)")
    scripts_n = _check_import_tree(
        b,
        HERE / "core/scripts",
        "scripts",
        "IMPORT_ALLOWED",
        IMPORT_ALLOWED,
        IMPORT_LOCAL_ROOTS,
        entries=IMPORT_ENTRIES,
    )
    pkg_n = _check_import_tree(
        b,
        HERE / "verify_harness",
        "verify_harness",
        "VERIFY_HARNESS_ALLOWED",
        VERIFY_HARNESS_ALLOWED,
        VERIFY_HARNESS_LOCAL_ROOTS,
        root_pkg="verify_harness",
    )
    if scripts_n is not None and pkg_n is not None:
        print(
            f"  graph intact ({scripts_n} runtime modules + {pkg_n} verify_harness modules)"
        )


def check_stdlib_only(b: Battery) -> None:
    """1c. The shipped runtime is stdlib-only — the contract recorded by
    [logic-in-python] ("Stdlib only, Python 3.11+ for everything") and restated
    by [single-pricing-source]. Enforcement, not a new rule: a third-party
    import would add a dependency the consumer never chose to code that runs on
    their machine. Scope is every tree that reaches a consumer on any channel —
    core/ + stacks/ (copy) plus the two scripts package-marketplace.py copies
    into each plugin and setup.sh executes. Imports resolve against the
    standard library or a module in the importing file's own directory; a
    cross-directory sibling fails here because it also fails at runtime, where
    only that directory is on sys.path. Manifests are the claim's other half:
    a dependency file is a third-party dependency even with no import yet."""
    b.note("stdlib-only shipped runtime (no third-party imports)")
    roots = [HERE / "core", HERE / "stacks", HERE / "claude-md"]
    loose = [HERE / "refresh-gitignore.py"]
    missing = [p for p in roots + loose if not p.exists()]
    if missing:
        # A broken scan is a FAIL, not a pass — an absent tree must not report
        # "no third-party import" without having looked.
        b.fail(f"{', '.join(rel(m) for m in missing)} missing — cannot scan imports")
        return
    try:
        by_root = {
            r: sorted(f for f in r.rglob("*.py") if "__pycache__" not in f.parts)
            for r in roots
        }
        empty = [r for r, fs in by_root.items() if not fs]
        if empty:
            # Roots exist but hold no .py: the scan would look at nothing and
            # report clean. A silent [ -f ] guard once let the generic stack
            # run without its engine suite while the battery stayed green.
            b.fail(
                f"{', '.join(rel(r) for r in empty)} holds no .py — "
                "refusing to report 'stdlib only' having scanned nothing"
            )
            return
        files = [f for fs in by_root.values() for f in fs] + loose
        manifests = sorted(
            m
            for r in roots
            for pat in (
                "requirements*.txt",
                "pyproject.toml",
                "Pipfile",
                "setup.py",
                "setup.cfg",
            )
            for m in r.rglob(pat)
        )
        hits = [f"{rel(m)}: dependency manifest" for m in manifests]
        for f in files:
            try:
                tree = ast.parse(read_text(f), str(f))
            except (SyntaxError, ValueError):
                # step 2 owns syntax (it rglobs all of harness/, a superset)
                # and aggregates these as FAILs; a raise here would abort the
                # battery before the steps below ever run.
                continue
            siblings = {p.stem for p in f.parent.glob("*.py")}
            # Files under a scripts/ tree run with the scripts root on sys.path
            # (the entry bootstraps, the test loaders, `unittest discover
            # -t .`), so a module or package at that root is local too, not
            # third-party — the composition root's modules reach each other
            # across directories (ADR 2026-07-17 runtime-package-layout).
            if "scripts" in f.parts:
                sroot = Path(*f.parts[: f.parts.index("scripts") + 1])
                sroots = [sroot]
                # A stack's scripts tree ships MERGED with core's at
                # materialize time, so core's root modules and packages are
                # runtime siblings of a stack test — `from grading import …`
                # in stacks/<s>/scripts/tests/ resolves against the installed
                # core package, never a third-party one.
                if HERE / "stacks" in f.parents:
                    sroots.append(HERE / "core/scripts")
                for sr in sroots:
                    siblings |= {p.stem for p in sr.glob("*.py")}
                    siblings |= {
                        d.name for d in sr.iterdir() if (d / "__init__.py").is_file()
                    }
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [(a.name.split(".")[0], node.lineno) for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level or not node.module:
                        continue  # relative import — local by construction
                    names = [(node.module.split(".")[0], node.lineno)]
                else:
                    continue
                for name, line in names:
                    if name in sys.stdlib_module_names or name in siblings:
                        continue
                    hits.append(f"{rel(f)}:{line}: imports '{name}'")
    except OSError as exc:
        b.fail(f"could not scan the shipped runtime for imports: {exc}")
        return
    if hits:
        b.fail(
            "the shipped runtime is stdlib-only by contract (stdlib or a "
            "module in the same directory; no dependency manifest):"
        )
        for h in hits[:10]:
            print(f"    {h}", file=sys.stderr)
    else:
        print("  shipped runtime imports stdlib only")


def check_python_syntax(b: Battery) -> None:
    """2. Python syntax (compile in memory — no __pycache__ left behind)."""
    b.note("python syntax")
    ok = True
    for f in sorted((ROOT / "harness").rglob("*.py")):
        if "__pycache__" in f.parts:
            continue
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            # ValueError: NUL byte in source; UnicodeDecodeError: not UTF-8.
            # Both aggregate as FAILs — a traceback would abort the battery.
            b.fail(f"python syntax error in {rel(f)}: {exc}")
            ok = False
    if ok:
        print("  ok")
