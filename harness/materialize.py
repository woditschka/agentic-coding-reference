#!/usr/bin/env python3
"""Materialize the harness runtime into a consumer project.

    harness/materialize.py <stack> <target-dir>

Copies harness/core/ then harness/stacks/<stack>/ into the target, preserving
permissions. The stack layer is applied last, so it wins on any overlap. This
is a byte-identical copy, not a render: every materialized file already exists
in the tree in its final form (agents are pre-expanded per tool surface).

Only the tool surfaces the project uses are installed. The project declares
them in scripts/layout.toml [harness] tools; if the key is absent (an older
project), the set is auto-detected from the tool agent-dirs already present —
so an upgrade never adds a tool surface the project did not opt into. The
shared substrate (skills, templates, schemas, scripts) installs for every tool.

The target's own files — docs/ briefs, scripts/layout.toml, settings, build
files — are project-owned and never touched here.

Channel-aware (read from scripts/layout.toml [harness] channel). Under "copy"
and "manifest" the full runtime is installed. Under "marketplace" the
tool-discovered surfaces (skills, agents, hooks) ship as a plugin and are NOT
installed here; only the non-discovered engine sliver (scripts, schemas,
templates, tool config) is materialized — at project-relative paths every tool
resolves identically. See docs/adr/2026-06-14-marketplace-plugin-channel.md.

After installing, the script REPORTS (never deletes) "extras": files under the
harness-owned runtime directories (plus scripts/, minus the project-owned
layout.toml and, on the generic stack, stack.sh) that this install did not
produce. They are either stale orphans from an older harness or genuine project
extensions; the /materialize skill classifies and acts on them. This script
stays a safe, non-destructive primitive.

Stdlib only. Tested by test_materialize.py.
"""

import importlib.util
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import (  # noqa: E402
    ALL_TOOLS,
    STACKS,
    TOOLS,
    LayoutError,
    logical_abspath,
    marketplace_excludes,
    read_harness_layout,
    runtime_files,
    unsafe_extension_path,
)

USAGE = (
    "usage: materialize.py <stack> <target-dir> [--no-verify] [--dry-run | --show-plan]\n"
    "       materialize.py record-extension <target-dir> <runtime-path>"
)

# On the marketplace channel the tool-discovered surfaces (skills, agents,
# hooks) are delivered by the plugin, not materialized; the engine sliver
# (registry.ENGINE_SLIVER) and tool config (.junie/config.json) stay
# project-side. OpenCode is not a plugin target — under marketplace it is
# already excluded via its TOOLS surfaces unless the project lists it as a
# tool. Both mappings derive from the registry.TOOLS registry.


def runtime_dirs() -> list[str]:
    """The harness-owned runtime directories: derived from RUNTIME_PATHS in
    harness/core/scripts/doctor.py (the single source), taking the
    entries whose last segment has no extension. These trees are 100%
    harness-owned, so scanning them for extras never touches a project-owned
    file (.claude/settings*.json and scripts/layout.toml live outside them)."""
    spec = importlib.util.spec_from_file_location(
        "doctor", HERE / "core" / "scripts" / "doctor.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("materialize: cannot load doctor.py to derive runtime dirs")
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)
    return [p for p in doctor.RUNTIME_PATHS if "." not in p.rsplit("/", 1)[-1]]


def read_layout(target: Path) -> tuple[list[str] | None, str]:
    """(tools list or None, channel) from scripts/layout.toml [harness], via
    the shared registry.read_harness_layout.

    A layout the parser or a per-field check rejects fails LOUD: silently
    defaulting to copy + all-four-tools would install the full runtime —
    including plugin-delivered surfaces — into a marketplace or claude-only
    project whose declaration just went unreadable. The enum hazard is why
    this must abort before install(): "marketplce" is not == "marketplace" at
    excluded_prefixes, and the doctor flags the enum only after the damaging
    install."""
    try:
        layout = read_harness_layout(target)
    except LayoutError as exc:
        # The reader's messages carry their own actionable tail — no second one.
        raise SystemExit(f"materialize: {exc}") from None
    return layout.tools, layout.channel


def resolve_tools(target: Path, declared: list[str] | None) -> list[str]:
    """The tool surfaces to install. Precedence: (1) the project's declared set
    in layout.toml; (2) an existing materialized project (a runtime dir already
    present) keeps its current surfaces — detect them, never add one (upgrade
    safety); (3) a greenfield target with no signal gets all four."""
    if declared:
        return declared
    if (target / ".claude/skills").is_dir() or (target / ".claude/agents").is_dir():
        tools = ["claude"]
        tools.extend(
            tool
            for tool, row in TOOLS.items()
            if tool != "claude" and (target / row["agents_dir"]).is_dir()
        )
        return tools
    return list(ALL_TOOLS)


def excluded_prefixes(tools: list[str], channel: str) -> list[str]:
    prefixes = [
        p for tool, row in TOOLS.items() if tool not in tools for p in row["surfaces"]
    ]
    if channel == "marketplace":
        prefixes.extend(marketplace_excludes())
    return prefixes


def _install_pairs(stack: str, prefixes: list[str]) -> Iterator[tuple[str, Path]]:
    """(rel, source path) for each runtime file an install would produce, in
    copy order: core then the stack layer, the stack winning on overlap.
    install() copies each; plan_install() stats each — one enumeration, so the
    preview cannot drift from the copy it previews."""
    for layer in ("core", f"stacks/{stack}"):
        src = HERE / layer
        if not src.is_dir():
            continue
        for rel in runtime_files(src):
            if any(rel.startswith(p) for p in prefixes):
                continue
            yield rel, src / rel


def install(stack: str, target: Path, prefixes: list[str]) -> tuple[set[str], int]:
    """Copy core then the stack layer into the target (stack wins on overlap).
    Returns (installed set, copy count — overlaps counted per copy)."""
    installed: set[str] = set()
    copied = 0
    for rel, src in _install_pairs(stack, prefixes):
        dest = target / rel
        write_guard.mkdir(dest.parent, parents=True, exist_ok=True)
        write_guard.copy(src, dest)
        installed.add(rel)
        copied += 1
    return installed, copied


def plan_install(
    stack: str, target: Path, prefixes: list[str]
) -> tuple[list[str], list[str]]:
    """(created, overwritten) rel paths a real install would produce, decided
    by a stat only — created = the dest is absent, overwritten = it is present
    (the copy would replace it). Each file is judged once against the pre-run
    disk state, so a core∪stack overlap counts as one entry, not two. This is
    the create-vs-overwrite split install()'s unconditional copy never computes;
    --dry-run renders it before any byte is written."""
    created: list[str] = []
    overwritten: list[str] = []
    seen: set[str] = set()
    for rel, _src in _install_pairs(stack, prefixes):
        if rel in seen:
            continue
        seen.add(rel)
        (overwritten if (target / rel).exists() else created).append(rel)
    return sorted(created), sorted(overwritten)


def show_plan(
    stack: str, target: Path, channel: str, tools: list[str], prefixes: list[str]
) -> int:
    """Print what a real materialize would change, then stop — the --dry-run /
    --show-plan surface. Every set is a pure read of the source tree and the
    target's current state; the plan is transient and never persisted (ADR
    2026-07-18). It reports extras as candidates only — the delete decision
    stays the /materialize skill's judgment, never this script's."""
    created, overwritten = plan_install(stack, target, prefixes)
    produced = set(created) | set(overwritten)
    extras = sorted(scan_present(target, stack, runtime_dirs()) - produced)
    print(
        f"plan stack={stack} channel={channel} tools={' '.join(tools)} "
        f"→ {target} (dry run — nothing written)"
    )
    print(f"  create:    {len(created)} runtime file(s)")
    print(f"  overwrite: {len(overwritten)} runtime file(s) (harness-owned; replaced)")
    # prefixes carries overlaps by construction (a tool surface a marketplace
    # install also excludes); dedupe for the display, order preserved.
    excluded = ", ".join(dict.fromkeys(prefixes))
    print(f"  excluded surfaces (not installed here): {excluded or 'none'}")
    print(
        f"  extras:    {len(extras)} file(s) the harness did not produce "
        "(kept; /materialize classifies)"
    )
    # The refreshes a real run applies to project-owned files. The managed-
    # chapter rewrite is the one edit that can overwrite project content placed
    # inside a harness-owned chapter — the plan names it so a consumer sees it
    # before the write, the only preview on a gitignored-runtime channel.
    if (target / "CLAUDE.md").is_file():
        print(
            "  refresh:   CLAUDE.md managed chapters (harness-owned regions rewritten)"
        )
    print("  refresh:   .gitignore runtime paths, .claude/settings.json keys (ensured)")
    for label, rels in (
        ("create", created),
        ("overwrite", overwritten),
        ("extras", extras),
    ):
        print(f"--- plan {label}: {len(rels)} ---")
        for rel in rels:
            print(rel)
    print("--- end plan ---")
    return 0


def scan_present(target: Path, stack: str, dirs: list[str]) -> set[str]:
    """Every file currently under the harness-owned runtime dirs, plus
    scripts/ minus the project-owned layout.toml and, on the generic stack,
    stack.sh — so a retired engine is reported instead of persisting silently.
    __pycache__/*.pyc are build artifacts, not orphans — excluded, matching
    the doctor."""
    present: set[str] = set()
    for d in dirs:
        root = target / d
        if not root.is_dir():
            continue
        present.update(f"{d}/{rel}" for rel in runtime_files(root))
    scripts = target / "scripts"
    if scripts.is_dir():
        skip = {"scripts/layout.toml"}
        if stack == "generic":
            skip.add("scripts/stack.sh")
        present.update(
            p
            for p in (f"scripts/{rel}" for rel in runtime_files(scripts))
            if p not in skip
        )
    return present


def run_refresh(script: Path, *args: str | Path) -> str:
    """Run a sibling refresh script and return its report line."""
    result = subprocess.run(
        [sys.executable, str(script), *[str(a) for a in args]],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout.strip()


# C0 controls (minus tab), DEL, and C1 — the escape-sequence alphabet. Suite
# output is target-influenced; a raw ESC reaching the terminal could rewrite
# what the operator believes the verify said.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def _diagnostic_tail(stderr: str, count: int = 5) -> list[str]:
    """The last stderr lines of a failed suite run, control characters
    stripped before they reach the operator's terminal."""
    return [
        _CONTROL_CHARS.sub("", line) for line in stderr.strip().splitlines()[-count:]
    ]


def verify_runtime(target: Path, suites: list[str]) -> int:
    """Install-time verification: run the vendored test suites THIS install
    produced, once, at the one lifecycle point where the runtime can change.
    Project builds do not run these suites (ADR 2026-07-13 in the reference
    repo): between installs the runtime is an immutable released artifact, so
    per-build re-testing verifies nothing new. This run catches what an
    install can break — a broken copy, a host python incompatibility.

    The scripts suites are a package tree under scripts/tests/ (ADR 2026-07-17
    runtime-package-layout): run them as one `unittest` invocation naming
    exactly the installed modules, from the scripts dir so `import handoff`
    and `import tests.*` resolve. The module list derives from the install's
    own file set — a project-authored test module under scripts/tests/ is
    never run as a suite (ADR 2026-08-16 exact-module-install-verification).
    The named suites still import from the target tree, so the trust boundary
    on the target stands. A missing suite file is an import error the run
    reports; a package missing its __init__.py resolves as a namespace
    package and its suites still run — the doctor's runtime roster pins every
    shipped __init__.py. The zero-tests check catches a truncated copy that
    imports clean and runs nothing; an all-skipped run (a channel-keyed
    setUpModule skip) is not a failure. The hook suites stay standalone
    scripts run from the target root. The run is isolated three ways: `-E`
    drops the caller's PYTHON* env, a pre-run purge drops stale __pycache__
    artifacts, and diagnostic tails are stripped of control characters.
    Returns the number of failing runs."""
    failures = 0
    script_suites = [r for r in suites if r.startswith("scripts/")]
    hook_suites = [r for r in suites if r.startswith(".claude/hooks/")]
    # The interpreter must see only the bytes this install laid down. The
    # guarded copy preserves mtime and size (copy2), which is exactly the
    # pyc invalidation key — a pre-existing __pycache__ artifact would stay
    # import-valid across the install. Purge before running anything.
    with write_guard.write_scope(target):
        for root in (target / "scripts", target / ".claude" / "hooks"):
            if root.is_dir():
                for cache in sorted(root.rglob("__pycache__")):
                    if cache.is_dir():
                        write_guard.remove_tree(cache)
    if script_suites:
        # The non-empty check is load-bearing: `python -m unittest` with no
        # module arguments IS `discover`, which would run the target's whole
        # tests tree — the exact thing the exact-module contract forbids.
        # The `--` keeps a module name from ever parsing as an option.
        modules = sorted(
            rel.removeprefix("scripts/").removesuffix(".py").replace("/", ".")
            for rel in script_suites
        )
        # -E ignores PYTHON* env vars: the caller's PYTHONPATH must never
        # put foreign roots on the verification interpreter's sys.path. -B
        # keeps the run from writing __pycache__ into the consumer's tree.
        result = subprocess.run(
            [sys.executable, "-E", "-B", "-m", "unittest", "--", *modules],
            cwd=target / "scripts",
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures += 1
            print("verify: scripts/tests suite run FAILED", file=sys.stderr)
            for line in _diagnostic_tail(result.stderr):
                print(f"  {line}", file=sys.stderr)
        elif not re.search(r"Ran [1-9][0-9]* tests?", result.stderr) and not re.search(
            r"\(skipped=\d+\)", result.stderr
        ):
            failures += 1
            print(
                "verify: scripts/tests suite run ran zero tests — suites empty "
                "or truncated",
                file=sys.stderr,
            )
    for rel in sorted(hook_suites):
        result = subprocess.run(
            [sys.executable, "-E", "-B", str(target / rel)],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures += 1
            print(f"verify: {rel} FAILED", file=sys.stderr)
            for line in _diagnostic_tail(result.stderr):
                print(f"  {line}", file=sys.stderr)
    if not failures:
        print(f"verified: {len(suites)} vendored suite(s) pass on this host")
    return failures


def _installed_suites(installed: set[str]) -> list[str]:
    """The test suites among an install's produced files: test_*.py under
    scripts/ or .claude/hooks/."""
    return [
        rel
        for rel in installed
        if rel.endswith(".py")
        and Path(rel).name.startswith("test_")
        and (rel.startswith("scripts/") or rel.startswith(".claude/hooks/"))
    ]


def restamp_spec_version(target: Path) -> str:
    """Deterministic refresh of the one harness-contract value inside the
    project-owned layout.toml: the declared spec_version follows the
    just-installed doctor manifest. Same managed-lines contract as the
    chapter and settings refreshes — the harness owns this value, the
    project owns the rest of the file. A missing file or declaration is
    reported and left to /init, never silently created."""
    manifest = target / "scripts" / "doctor-expectations.toml"
    layout = target / "scripts" / "layout.toml"
    try:
        spec = str(tomllib.loads(manifest.read_text(encoding="utf-8"))["spec_version"])
        text = layout.read_text(encoding="utf-8")
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return "spec_version: layout.toml or installed manifest unreadable — left for /init"
    new_text, count = re.subn(
        r'(?m)^spec_version = ".*?"$', f'spec_version = "{spec}"', text, count=1
    )
    if count == 0:
        return "spec_version: no declaration in layout.toml — left for /init"
    if new_text == text:
        return f"spec_version: current ({spec})"
    with write_guard.write_scope(target):
        write_guard.write_text(layout, new_text)
    return f"spec_version: restamped to {spec}"


def record_extension(target: Path, ext_path: str) -> int:
    """Record one kept project extension durably: add it to `[harness]
    extensions` in scripts/layout.toml and, on a gitignored-runtime channel,
    re-include it in .gitignore. Idempotent. The re-include form is encoded
    here once — `!<path>/` for a directory, `!<path>` for a file; a trailing
    slash on a file path would not re-include it."""
    ext_path = ext_path.strip("/")
    # The path lands verbatim inside layout.toml's extensions array and a
    # .gitignore line. The shared predicate rejects anything that could inject
    # config entries, corrupt the array's re-parse, or escape the target —
    # the same rule read_harness_layout applies to declared entries.
    if unsafe_extension_path(ext_path):
        print(
            f"materialize: extension path {ext_path!r} contains unsafe "
            "characters or traversal — record it by its plain "
            "target-relative path",
            file=sys.stderr,
        )
        return 1
    resolved = (target / ext_path).resolve()
    if not resolved.is_relative_to(target.resolve()):
        print(f"materialize: {ext_path} resolves outside {target}", file=sys.stderr)
        return 1
    if not (target / ext_path).exists():
        print(f"materialize: {ext_path} does not exist under {target}", file=sys.stderr)
        return 1
    lt = target / "scripts" / "layout.toml"
    if not lt.is_file():
        print(f"materialize: no {lt} — run /init first", file=sys.stderr)
        return 1
    # Validate the declaration (read_layout fails loud on an invalid channel
    # or tools value) BEFORE mutating the file — an abort must not leave the
    # extension half-recorded with the .gitignore re-include never written.
    _, channel = read_layout(target)
    text = lt.read_text(encoding="utf-8")
    m = re.search(r"^extensions = \[(.*)\]$", text, re.MULTILINE)
    if m is None:
        print(
            f"materialize: no `extensions = [...]` line in {lt} [harness]",
            file=sys.stderr,
        )
        return 1
    current = [e.strip().strip('"') for e in m.group(1).split(",") if e.strip()]
    changed = []
    if ext_path not in current:
        current.append(ext_path)
        new_line = "extensions = [" + ", ".join(f'"{e}"' for e in current) + "]"
        write_guard.write_text(
            lt, text[: m.start()] + new_line + text[m.end() :], encoding="utf-8"
        )
        changed.append("layout.toml")
    if channel != "copy":
        gi = target / ".gitignore"
        line = f"!{ext_path}/" if (target / ext_path).is_dir() else f"!{ext_path}"
        gi_text = gi.read_text(encoding="utf-8") if gi.is_file() else ""
        if line not in gi_text.splitlines():
            write_guard.write_text(
                gi, gi_text.rstrip("\n") + "\n" + line + "\n", encoding="utf-8"
            )
            changed.append(".gitignore")
        # git never descends into a directory ignored by a bare "dir/"
        # pattern, so a re-include under one is silently dead — verify the
        # line took effect and fail loud when it did not (exit 0 = ignored).
        probe = subprocess.run(
            ["git", "-C", str(target), "check-ignore", "-q", ext_path],
            capture_output=True,
            check=False,
        )
        if probe.returncode == 0:
            print(
                f"materialize: {ext_path} is still gitignored after the "
                "re-include — a parent directory is ignored by a bare "
                "dir/ pattern; switch it to the dir/* form (see the "
                "runtime .gitignore block) and re-run",
                file=sys.stderr,
            )
            return 1
    state = ", ".join(changed) if changed else "already recorded"
    print(f"record-extension {ext_path}: {state}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "record-extension":
        if len(argv) != 4:
            print(USAGE, file=sys.stderr)
            return 2
        target = logical_abspath(argv[2])
        if not target.is_dir():
            print(f"materialize: no such target directory {argv[2]}", file=sys.stderr)
            return 1
        with write_guard.write_scope(target):
            return record_extension(target, argv[3])
    # --no-verify skips the install-time suite run. For harness-internal
    # callers only (materialize-samples, faithfulness, self-tests): the battery runs
    # the same suites in its own step, so re-running them per materialize
    # would only slow the gate. Consumers get verification by default.
    verify = "--no-verify" not in argv
    # --dry-run (alias --show-plan): compute and print the plan, write nothing.
    # A preview of the overwrite blast radius before any byte lands — the only
    # such preview on a gitignored-runtime channel, where no git diff exists.
    dry_run = "--dry-run" in argv or "--show-plan" in argv
    argv = [a for a in argv if a not in ("--no-verify", "--dry-run", "--show-plan")]
    if len(argv) != 3:
        print(USAGE, file=sys.stderr)
        return 2
    stack, target = argv[1], logical_abspath(argv[2])
    # Validate the slug against registry.STACKS, the documented roster (its
    # parity with the harness/stacks/ directories is verify-harness-guarded). A
    # slug outside it would otherwise install core alone (install() skips the
    # missing layer) and report success — the `java` vs `java-spring-boot`
    # trap. Membership (not is_dir on a joined path) also rejects "", "..",
    # and absolute slugs, whose pathlib join resolves to a real directory and
    # would slip past an is_dir guard while install()'s relative
    # f"stacks/{stack}" still copied core alone; and a stray directory under
    # stacks/ cannot widen what the roster admits.
    if stack not in STACKS:
        print(
            f"materialize: unknown stack {stack!r} — no harness/stacks/{stack}/ "
            f"(valid: {', '.join(sorted(STACKS))})",
            file=sys.stderr,
        )
        return 2
    if not target.is_dir():
        print(f"materialize: no such target directory {argv[2]}", file=sys.stderr)
        return 1

    declared, channel = read_layout(target)
    tools = resolve_tools(target, declared)
    prefixes = excluded_prefixes(tools, channel)
    if dry_run:
        return show_plan(stack, target, channel, tools, prefixes)
    with write_guard.write_scope(target):
        installed, copied = install(stack, target, prefixes)

    print(
        f"materialized stack={stack} channel={channel} tools={' '.join(tools)}: "
        f"{copied} file(s) into {target}"
    )

    # Refresh the harness-managed chapters in the project-owned CLAUDE.md.
    # CLAUDE.md itself is the project's (scaffolded once, never overwritten),
    # but several chapters are stack-agnostic harness doctrine, each identified
    # by its heading — the same managed-region contract as the .gitignore
    # runtime block. Only those chapters are rewritten from the single source;
    # a missing heading is reported as "absent" and left for /init (greenfield)
    # or the /materialize reconciliation (legacy) — never a silent edit.
    if (target / "CLAUDE.md").is_file():
        # Fail fast on a broken harness tree, like init — refresh would
        # otherwise skip the stamp and only the later doctor would catch it.
        stamp = HERE / "VERSION-DATE"
        if not stamp.is_file() or not stamp.read_text(encoding="utf-8").strip():
            print(
                f"materialize: missing or empty {stamp} — cannot stamp CLAUDE.md",
                file=sys.stderr,
            )
            return 1
        ch_status = run_refresh(
            HERE / "claude-md" / "refresh-chapters.py", target / "CLAUDE.md", HERE
        )
        print(f"managed chapters: {ch_status}")

    # Refresh the harness-owned lines of two more project-owned files, the same
    # way: deterministically, in place, marker-free — the harness owns those
    # lines, the project owns the rest. Both are ENSURE-PRESENT and additive:
    # project-authored ignores, keys, and hooks are never rewritten. Files the
    # project fills with judgment (layout.toml data, docs/ briefs, non-doctrine
    # CLAUDE.md chapters) are NOT touched here — the /materialize skill
    # reconciles those advisorily.
    print(
        run_refresh(
            HERE / "refresh-gitignore.py",
            target / ".gitignore",
            HERE / "init" / "core" / "gitignore-runtime.txt",
            channel,
        )
    )
    print(
        run_refresh(
            HERE / "refresh-settings.py",
            target / ".claude" / "settings.json",
            HERE / "init" / "core" / ".claude" / "settings.json",
            target,
        )
    )
    print(restamp_spec_version(target))

    # Extras = files under the harness-owned runtime dirs that this install did
    # not produce. One path per line (relative to the target), between the
    # markers, so the /materialize skill can parse them.
    extras = sorted(scan_present(target, stack, runtime_dirs()) - installed)
    print(f"--- extras: {len(extras)} file(s) not produced by the harness ---")
    for path in extras:
        print(path)
    print("--- end extras ---")

    if verify and verify_runtime(target, _installed_suites(installed)):
        print(
            "materialize: the installed runtime is not healthy on this host",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
