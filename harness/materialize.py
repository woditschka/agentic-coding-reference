#!/usr/bin/env python3
"""Materialize the harness runtime into a consumer project, and report what the install did not produce.

    harness/materialize.py <stack> <target-dir> [--no-verify] [--dry-run | --show-plan]
    harness/materialize.py record-extension <target-dir> <runtime-path>

The producer-side installer: a byte-identical copy of harness/core/ then
harness/stacks/<stack>/, limited to the tool surfaces and the channel the
target declares, followed by the refreshes of the harness-owned lines in the
project's files. It never deletes: extras are reported for the /materialize
skill to classify. Stdlib only.
"""

import importlib.util
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import (  # noqa: E402
    ALL_TOOLS,
    FAILURE_EXIT,
    STACKS,
    TOOLS,
    USAGE_EXIT,
    LayoutError,
    logical_abspath,
    marketplace_excludes,
    read_harness_layout,
    runtime_files,
    unsafe_extension_path,
)
from retired_paths import covered, read_manifest  # noqa: E402

USAGE = (
    "usage: materialize.py <stack> <target-dir> [--no-verify] [--dry-run | --show-plan]\n"
    "       materialize.py record-extension <target-dir> <runtime-path>"
)
MATERIALIZE_ARGS = 3
RECORD_EXTENSION_ARGS = 4
VERB_ARGS = 2
DIAGNOSTIC_LINES = 5
RETIRED_NOTE = "  [retired — harness/retired-paths.txt]"

# Extras paths come from the target's filesystem, so a control character is
# stripped before the path reaches the operator's terminal.
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
# Suite output is target-influenced: C0 controls (minus tab), DEL, and C1 are
# the escape-sequence alphabet.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")


class MaterializeError(Exception):
    """A failure materialize reports on stderr and exits on with its code."""

    def __init__(self, code: int, message: str, *, verbatim: bool = False) -> None:
        """Carry the exit code and the message; verbatim writes the message as is."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.verbatim = verbatim


def report(message: str) -> None:
    """Write one line to stderr."""
    print(message, file=sys.stderr)


def _printable(text: str) -> str:
    return _CTRL_RE.sub("", text)


@dataclass(frozen=True, slots=True)
class Install:
    """One install resolved against its target: the stack, the channel, and the surfaces in scope."""

    stack: str
    target: Path
    channel: str
    tools: list[str]
    prefixes: list[str]


def runtime_dirs() -> list[str]:
    """Return the harness-owned runtime directories, derived from the doctor's runtime roster."""
    # The roster entries whose last segment has no extension. These trees are
    # wholly harness-owned, so scanning them for extras never touches a
    # project-owned file.
    spec = importlib.util.spec_from_file_location(
        "doctor", HERE / "core" / "scripts" / "doctor.py"
    )
    if spec is None or spec.loader is None:
        raise MaterializeError(
            FAILURE_EXIT, "materialize: cannot load doctor.py to derive runtime dirs"
        )
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)
    return [p for p in doctor.RUNTIME_PATHS if "." not in p.rsplit("/", 1)[-1]]


def read_layout(target: Path) -> tuple[list[str] | None, str]:
    """Read the declared tools and channel from the target's layout; an unreadable layout fails loud."""
    # Defaulting silently would install the full runtime into a marketplace
    # or single-tool project whose declaration just went unreadable.
    try:
        layout = read_harness_layout(target)
    except LayoutError as exc:
        raise MaterializeError(FAILURE_EXIT, f"materialize: {exc}") from None
    return layout.tools, layout.channel


def resolve_tools(target: Path, declared: list[str] | None) -> list[str]:
    """Return the tool surfaces to install: the declared set, else the present ones, else all."""
    # An existing install keeps its surfaces and never gains one on upgrade.
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
    """Return the runtime path prefixes an install leaves out for these tools and this channel."""
    prefixes = [
        p for tool, row in TOOLS.items() if tool not in tools for p in row["surfaces"]
    ]
    if channel == "marketplace":
        prefixes.extend(marketplace_excludes())
    return prefixes


def _install_pairs(stack: str, prefixes: list[str]) -> Iterator[tuple[str, Path]]:
    # One enumeration serves the copy and the plan, so the preview cannot
    # drift from the copy it previews; the stack layer comes last and wins.
    for layer in ("core", f"stacks/{stack}"):
        src = HERE / layer
        if not src.is_dir():
            continue
        for rel in runtime_files(src):
            if any(rel.startswith(p) for p in prefixes):
                continue
            yield rel, src / rel


def install(stack: str, target: Path, prefixes: list[str]) -> tuple[set[str], int]:
    """Copy core then the stack layer into the target; return the installed set and the copy count."""
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
    """Return the (created, overwritten) paths a real install would produce, judged against the disk once."""
    created: list[str] = []
    overwritten: list[str] = []
    seen: set[str] = set()
    for rel, _src in _install_pairs(stack, prefixes):
        if rel in seen:
            continue
        seen.add(rel)
        (overwritten if (target / rel).exists() else created).append(rel)
    return sorted(created), sorted(overwritten)


def show_plan(plan: Install) -> int:
    """Print what a real materialize would change, and write nothing."""
    # The delete decision stays the /materialize skill's: extras are named as
    # candidates only.
    created, overwritten = plan_install(plan.stack, plan.target, plan.prefixes)
    produced = set(created) | set(overwritten)
    extras = sorted(scan_present(plan.target, plan.stack, runtime_dirs()) - produced)
    print(
        f"plan stack={plan.stack} channel={plan.channel} tools={' '.join(plan.tools)} "
        f"→ {plan.target} (dry run — nothing written)"
    )
    print(f"  create:    {len(created)} runtime file(s)")
    print(f"  overwrite: {len(overwritten)} runtime file(s) (harness-owned; replaced)")
    excluded = ", ".join(dict.fromkeys(plan.prefixes))
    print(f"  excluded surfaces (not installed here): {excluded or 'none'}")
    print(
        f"  extras:    {len(extras)} file(s) the harness did not produce "
        "(kept; /materialize classifies)"
    )
    # The chapter rewrite is the one edit that can overwrite project content
    # placed inside a harness-owned chapter, so the plan names it.
    if (plan.target / "CLAUDE.md").is_file():
        print(
            "  refresh:   CLAUDE.md managed chapters (harness-owned regions rewritten)"
        )
    print("  refresh:   .gitignore runtime paths, .claude/settings.json keys (ensured)")
    retired = read_manifest()
    for label, rels in (
        ("create", created),
        ("overwrite", overwritten),
        ("extras", extras),
    ):
        print(f"--- plan {label}: {len(rels)} ---")
        for rel in rels:
            print(_extra_line(rel, retired) if label == "extras" else rel)
    print("--- end plan ---")
    return 0


def _extra_line(rel: str, retired: list[str]) -> str:
    # A path the retired-paths manifest covers is a known orphan the skill
    # removes without archaeology; an unannotated extra keeps the judgment path.
    note = RETIRED_NOTE if covered(rel, retired) else ""
    return f"{_printable(rel)}{note}"


def scan_present(target: Path, stack: str, dirs: list[str]) -> set[str]:
    """Return every file under the runtime dirs, the retired dirs, and scripts/ minus the project-owned files."""
    # __pycache__ artifacts are excluded by the runtime walk, matching the
    # doctor. A retired directory is no longer a runtime dir, so it is
    # scanned on its own, or a retired tool surface would persist unreported.
    present: set[str] = set()
    for d in dirs:
        root = target / d
        if not root.is_dir():
            continue
        present.update(f"{d}/{rel}" for rel in runtime_files(root))
    for entry in read_manifest():
        if entry.endswith("/") and (target / entry).is_dir():
            present.update(f"{entry}{rel}" for rel in runtime_files(target / entry))
    scripts = target / "scripts"
    if scripts.is_dir():
        skip = {"scripts/layout.toml", "scripts/backlog.sh"}
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
        raise MaterializeError(result.returncode, result.stderr, verbatim=True)
    return result.stdout.strip()


def _diagnostic_tail(stderr: str, count: int = DIAGNOSTIC_LINES) -> list[str]:
    return [
        _CONTROL_CHARS.sub("", line) for line in stderr.strip().splitlines()[-count:]
    ]


def verify_runtime(target: Path, suites: list[str]) -> int:
    """Run the vendored suites this install produced and return the number of failing runs."""
    # The one lifecycle point where the runtime changes; between installs it
    # is an immutable artifact. Only the installed modules run, never the
    # target's whole tests tree, so a project-authored test never runs as a
    # suite.
    _purge_bytecode(target)
    script_suites = [r for r in suites if r.startswith("scripts/")]
    hook_suites = [r for r in suites if r.startswith(".claude/hooks/")]
    failures = _run_script_suites(target, script_suites)
    failures += sum(_run_hook_suite(target, rel) for rel in sorted(hook_suites))
    if not failures:
        print(f"verified: {len(suites)} vendored suite(s) pass on this host")
    return failures


def _purge_bytecode(target: Path) -> None:
    # The guarded copy preserves mtime and size, exactly the pyc invalidation
    # key, so a pre-existing artifact would stay import-valid across the install.
    with write_guard.write_scope(target):
        for root in (target / "scripts", target / ".claude" / "hooks"):
            if not root.is_dir():
                continue
            for cache in sorted(root.rglob("__pycache__")):
                if cache.is_dir():
                    write_guard.remove_tree(cache)


def _run_script_suites(target: Path, script_suites: list[str]) -> int:
    # `python -m unittest` with no module argument is `discover`, the run the
    # exact-module contract forbids; `--` keeps a module name from parsing as
    # an option. -E drops the caller's PYTHON* environment and -B keeps the
    # run from writing bytecode into the consumer's tree.
    if not script_suites:
        return 0
    modules = sorted(
        rel.removeprefix("scripts/").removesuffix(".py").replace("/", ".")
        for rel in script_suites
    )
    result = subprocess.run(
        [sys.executable, "-E", "-B", "-m", "unittest", "--", *modules],
        cwd=target / "scripts",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        report("verify: scripts/tests suite run FAILED")
        for line in _diagnostic_tail(result.stderr):
            report(f"  {line}")
        return 1
    # Python 3.13+ colorizes unittest output under FORCE_COLOR, which -E does
    # not strip. A zero-tests run is a truncated copy that imports clean; an
    # all-skipped run (a channel-keyed setUpModule skip) is not a failure.
    plain = _SGR_RE.sub("", result.stderr)
    if not re.search(r"Ran [1-9][0-9]* tests?", plain) and not re.search(
        r"\(skipped=\d+\)", plain
    ):
        report(
            "verify: scripts/tests suite run ran zero tests — suites empty or truncated"
        )
        return 1
    return 0


def _run_hook_suite(target: Path, rel: str) -> int:
    result = subprocess.run(
        [sys.executable, "-E", "-B", str(target / rel)],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return 0
    report(f"verify: {rel} FAILED")
    for line in _diagnostic_tail(result.stderr):
        report(f"  {line}")
    return 1


def _installed_suites(installed: set[str]) -> list[str]:
    return [
        rel
        for rel in installed
        if rel.endswith(".py")
        and Path(rel).name.startswith("test_")
        and rel.startswith(("scripts/", ".claude/hooks/"))
    ]


def restamp_spec_version(target: Path) -> str:
    """Follow the installed manifest's spec_version in the project's layout, and report the outcome."""
    # The one harness-contract value inside the project-owned layout; a
    # missing file or declaration is reported and left to /init.
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
    """Record one kept project extension in the layout and, off the copy channel, re-include it in .gitignore."""
    ext_path = ext_path.strip("/")
    # The path lands verbatim in the extensions array and a .gitignore line;
    # the shared predicate rejects what could inject entries or escape the target.
    if unsafe_extension_path(ext_path):
        report(
            f"materialize: extension path {ext_path!r} contains unsafe "
            "characters or traversal — record it by its plain "
            "target-relative path"
        )
        return FAILURE_EXIT
    resolved = (target / ext_path).resolve()
    if not resolved.is_relative_to(target.resolve()):
        report(f"materialize: {ext_path} resolves outside {target}")
        return FAILURE_EXIT
    if not (target / ext_path).exists():
        report(f"materialize: {ext_path} does not exist under {target}")
        return FAILURE_EXIT
    layout = target / "scripts" / "layout.toml"
    if not layout.is_file():
        report(f"materialize: no {layout} — run /init first")
        return FAILURE_EXIT
    # The declaration is validated before the file is touched, so an abort
    # never leaves the extension half-recorded.
    _, channel = read_layout(target)
    changed = _declare_extension(layout, ext_path)
    if channel != "copy":
        if _reinclude(target, ext_path):
            changed.append(".gitignore")
        if _still_ignored(target, ext_path):
            report(
                f"materialize: {ext_path} is still gitignored after the "
                "re-include — a parent directory is ignored by a bare "
                "dir/ pattern; switch it to the dir/* form (see the "
                "runtime .gitignore block) and re-run"
            )
            return FAILURE_EXIT
    state = ", ".join(changed) if changed else "already recorded"
    print(f"record-extension {ext_path}: {state}")
    return 0


def _declare_extension(layout: Path, ext_path: str) -> list[str]:
    text = layout.read_text(encoding="utf-8")
    match = re.search(r"^extensions = \[(.*)\]$", text, re.MULTILINE)
    if match is None:
        raise MaterializeError(
            FAILURE_EXIT,
            f"materialize: no `extensions = [...]` line in {layout} [harness]",
        )
    current = [e.strip().strip('"') for e in match.group(1).split(",") if e.strip()]
    if ext_path in current:
        return []
    current.append(ext_path)
    new_line = "extensions = [" + ", ".join(f'"{e}"' for e in current) + "]"
    write_guard.write_text(
        layout, text[: match.start()] + new_line + text[match.end() :], encoding="utf-8"
    )
    return ["layout.toml"]


def _reinclude(target: Path, ext_path: str) -> bool:
    # `!<path>/` for a directory and `!<path>` for a file: a trailing slash on
    # a file path would not re-include it.
    gitignore = target / ".gitignore"
    line = f"!{ext_path}/" if (target / ext_path).is_dir() else f"!{ext_path}"
    text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if line in text.splitlines():
        return False
    write_guard.write_text(
        gitignore, text.rstrip("\n") + "\n" + line + "\n", encoding="utf-8"
    )
    return True


def _still_ignored(target: Path, ext_path: str) -> bool:
    # git never descends into a directory ignored by a bare "dir/" pattern,
    # so a re-include under one is silently dead; exit 0 means still ignored.
    probe = subprocess.run(
        ["git", "-C", str(target), "check-ignore", "-q", "--", ext_path],
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


@dataclass(frozen=True, slots=True)
class Request:
    """A materialize invocation as asked on the command line."""

    stack: str
    target_arg: str
    verify: bool
    dry_run: bool


def parse_request(argv: list[str]) -> Request:
    """Read a materialize command line, rejecting a wrong shape or an unknown stack."""
    # --no-verify is for harness-internal callers, whose battery runs the
    # same suites; consumers verify by default. --dry-run (alias --show-plan)
    # is the one preview on a gitignored-runtime channel, where no git diff exists.
    verify = "--no-verify" not in argv
    dry_run = "--dry-run" in argv or "--show-plan" in argv
    positional = [
        a for a in argv if a not in ("--no-verify", "--dry-run", "--show-plan")
    ]
    if len(positional) != MATERIALIZE_ARGS:
        raise MaterializeError(USAGE_EXIT, USAGE)
    stack, target_arg = positional[1], positional[2]
    # Membership in the roster, not is_dir on a joined path: a slug outside
    # it would install core alone and report success, and "", "..", or an
    # absolute slug joins to a real directory an is_dir guard would admit.
    if stack not in STACKS:
        raise MaterializeError(
            USAGE_EXIT,
            f"materialize: unknown stack {stack!r} — no harness/stacks/{stack}/ "
            f"(valid: {', '.join(sorted(STACKS))})",
        )
    return Request(stack, target_arg, verify=verify, dry_run=dry_run)


def resolve_install(request: Request) -> Install:
    """Resolve the request against its target: the channel, the tools, and the excluded surfaces."""
    target = logical_abspath(request.target_arg)
    if not target.is_dir():
        raise MaterializeError(
            FAILURE_EXIT, f"materialize: no such target directory {request.target_arg}"
        )
    declared, channel = read_layout(target)
    tools = resolve_tools(target, declared)
    return Install(
        request.stack, target, channel, tools, excluded_prefixes(tools, channel)
    )


def materialize(request: Request) -> int:
    """Install the runtime, refresh the harness-owned lines, report the extras, and verify."""
    plan = resolve_install(request)
    if request.dry_run:
        return show_plan(plan)
    with write_guard.write_scope(plan.target):
        installed, copied = install(plan.stack, plan.target, plan.prefixes)
    print(
        f"materialized stack={plan.stack} channel={plan.channel} tools={' '.join(plan.tools)}: "
        f"{copied} file(s) into {plan.target}"
    )
    _refresh_managed_chapters(plan.target)
    _refresh_project_files(plan)
    _report_extras(plan, installed)
    if request.verify and verify_runtime(plan.target, _installed_suites(installed)):
        report("materialize: the installed runtime is not healthy on this host")
        return FAILURE_EXIT
    return 0


def _refresh_managed_chapters(target: Path) -> None:
    # CLAUDE.md is the project's, but its managed chapters are harness
    # doctrine identified by heading; only those are rewritten from the single
    # source, and a missing heading is reported, never silently added.
    if not (target / "CLAUDE.md").is_file():
        return
    stamp = HERE / "VERSION-DATE"
    if not stamp.is_file() or not stamp.read_text(encoding="utf-8").strip():
        raise MaterializeError(
            FAILURE_EXIT,
            f"materialize: missing or empty {stamp} — cannot stamp CLAUDE.md",
        )
    status = run_refresh(
        HERE / "claude-md" / "refresh-chapters.py", target / "CLAUDE.md", HERE
    )
    print(f"managed chapters: {status}")


def _refresh_project_files(plan: Install) -> None:
    # The harness owns some lines of three project-owned files and refreshes
    # them in place, additively; the files the project fills with judgment
    # are the /materialize skill's to reconcile.
    print(
        run_refresh(
            HERE / "refresh-gitignore.py",
            plan.target / ".gitignore",
            HERE / "init" / "core" / "gitignore-runtime.txt",
            plan.channel,
        )
    )
    print(
        run_refresh(
            HERE / "refresh-settings.py",
            plan.target / ".claude" / "settings.json",
            HERE / "init" / "core" / ".claude" / "settings.json",
            plan.target,
        )
    )
    print(restamp_spec_version(plan.target))


def _report_extras(plan: Install, installed: set[str]) -> None:
    # One path per line between the markers, so the /materialize skill can
    # parse them.
    extras = sorted(scan_present(plan.target, plan.stack, runtime_dirs()) - installed)
    retired = read_manifest()
    print(f"--- extras: {len(extras)} file(s) not produced by the harness ---")
    for path in extras:
        print(_extra_line(path, retired))
    print("--- end extras ---")


def record_extension_command(argv: list[str]) -> int:
    """Run the record-extension verb from the command line."""
    if len(argv) != RECORD_EXTENSION_ARGS:
        raise MaterializeError(USAGE_EXIT, USAGE)
    target = logical_abspath(argv[2])
    if not target.is_dir():
        raise MaterializeError(
            FAILURE_EXIT, f"materialize: no such target directory {argv[2]}"
        )
    with write_guard.write_scope(target):
        return record_extension(target, argv[3])


def main(argv: list[str]) -> int:
    """Run materialize from the command line and return the exit code."""
    try:
        if len(argv) >= VERB_ARGS and argv[1] == "record-extension":
            return record_extension_command(argv)
        return materialize(parse_request(argv))
    except MaterializeError as exc:
        if exc.verbatim:
            sys.stderr.write(exc.message)
        else:
            report(exc.message)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
