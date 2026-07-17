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
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from helpers import (  # noqa: E402
    ALL_TOOLS,
    CHANNELS,
    STACKS,
    TOOLS,
    logical_abspath,
    marketplace_excludes,
    runtime_files,
)

USAGE = (
    "usage: materialize.py <stack> <target-dir> [--no-verify]\n"
    "       materialize.py record-extension <target-dir> <runtime-path>"
)

# On the marketplace channel the tool-discovered surfaces (skills, agents,
# hooks) are delivered by the plugin, not materialized; the engine sliver
# (helpers.ENGINE_SLIVER) and tool config (.junie/config.json) stay
# project-side. OpenCode is not a plugin target — under marketplace it is
# already excluded via its TOOLS surfaces unless the project lists it as a
# tool. Both mappings derive from the helpers.TOOLS registry.


def runtime_dirs():
    """The harness-owned runtime directories: derived from RUNTIME_PATHS in
    harness/core/scripts/doctor.py (the single source), taking the
    entries whose last segment has no extension. These trees are 100%
    harness-owned, so scanning them for extras never touches a project-owned
    file (.claude/settings*.json and scripts/layout.toml live outside them)."""
    spec = importlib.util.spec_from_file_location(
        "doctor", HERE / "core" / "scripts" / "doctor.py"
    )
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)
    return [p for p in doctor.RUNTIME_PATHS if "." not in p.rsplit("/", 1)[-1]]


def read_layout(target):
    """(tools list or None, channel) from scripts/layout.toml [harness].

    A layout the parser rejects fails LOUD: silently defaulting to copy +
    all-four-tools would install the full runtime — including plugin-delivered
    surfaces — into a marketplace or claude-only project whose declaration
    just went unreadable."""
    lt = target / "scripts" / "layout.toml"
    if not lt.is_file():
        return None, "copy"
    try:
        data = tomllib.loads(lt.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit(
            f"materialize: {lt} unparseable: {exc} — fix the "
            "layout before materializing (the channel/tools "
            "declaration is unreadable)"
        ) from None
    harness = data.get("harness", {})
    if not isinstance(harness, dict):
        raise SystemExit(
            f"materialize: {lt} [harness] is not a table — fix "
            "the layout before materializing"
        )
    channel = harness.get("channel")
    channel = channel if isinstance(channel, str) and channel else "copy"
    if channel not in CHANNELS:
        # The docstring's own hazard: "marketplce" is not == "marketplace" at
        # excluded_prefixes, so the full runtime would land in a marketplace
        # project. The doctor flags the enum only after the damaging install.
        raise SystemExit(
            f"materialize: {lt} [harness] channel {channel!r} is "
            f"not one of {', '.join(CHANNELS)} — fix the "
            "declaration before materializing"
        )
    tools = harness.get("tools")
    if tools is None:
        return None, channel
    # A declared-but-malformed tools value is the same silent-divergence trap
    # as an unknown name: falling through to None would install every surface.
    if not (
        isinstance(tools, list) and tools and all(isinstance(t, str) for t in tools)
    ):
        raise SystemExit(
            f"materialize: {lt} [harness] tools must be a "
            "non-empty list of strings — fix the declaration "
            "or remove the key"
        )
    unknown = sorted(set(tools) - set(ALL_TOOLS))
    if unknown:
        raise SystemExit(
            f"materialize: {lt} [harness] tools names unknown "
            f"tool(s) {', '.join(unknown)} (valid: "
            f"{', '.join(ALL_TOOLS)}) — an unknown name would "
            "silently drop that tool's surfaces"
        )
    return tools, channel


def resolve_tools(target, declared):
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


def excluded_prefixes(tools, channel):
    prefixes = [
        p for tool, row in TOOLS.items() if tool not in tools for p in row["surfaces"]
    ]
    if channel == "marketplace":
        prefixes.extend(marketplace_excludes())
    return prefixes


def install(stack, target, prefixes):
    """Copy core then the stack layer into the target (stack wins on overlap).
    Returns (installed set, copy count — overlaps counted per copy)."""
    installed = set()
    copied = 0
    for layer in ("core", f"stacks/{stack}"):
        src = HERE / layer
        if not src.is_dir():
            continue
        for rel in runtime_files(src):
            if any(rel.startswith(p) for p in prefixes):
                continue
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, dest)
            installed.add(rel)
            copied += 1
    return installed, copied


def scan_present(target, stack, dirs):
    """Every file currently under the harness-owned runtime dirs, plus
    scripts/ minus the project-owned layout.toml and, on the generic stack,
    stack.sh — so a retired engine is reported instead of persisting silently.
    __pycache__/*.pyc are build artifacts, not orphans — excluded, matching
    the doctor."""
    present = set()
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


def run_refresh(script, *args):
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


def verify_runtime(target, suites):
    """Install-time verification: run the vendored test suites THIS install
    produced, once, at the one lifecycle point where the runtime can change.
    Project builds do not run these suites (ADR 2026-07-13 in the reference
    repo): between installs the runtime is an immutable released artifact, so
    per-build re-testing verifies nothing new. This run catches what an
    install can break — a broken copy, a host python incompatibility.

    The scripts suites are a package tree under scripts/tests/ (ADR 2026-07-17
    runtime-package-layout): run them as one `unittest discover` from the
    scripts dir, so `import handoff` and `import tests.*` resolve. Discovery
    executes the target's tests tree, so a project-authored test module under
    scripts/tests/ runs too — the tests tree is the verification surface;
    point materialize only at trees you trust (the boundary the interpreter's
    import path already concedes). Two guards close discovery's silent-skip
    class: every install-produced suite's directory must be a package (a
    missing __init__.py makes discovery skip it without error), and a
    discovery run that executes zero tests fails. The hook suites stay
    standalone scripts run from the target root.
    Returns the number of failing runs."""
    failures = 0
    script_suites = [r for r in suites if r.startswith("scripts/")]
    hook_suites = [r for r in suites if r.startswith(".claude/hooks/")]
    if script_suites:
        broken_pkgs = set()
        for rel in sorted(script_suites):
            d = (target / rel).parent
            while d != target / "scripts":
                if not (d / "__init__.py").is_file():
                    broken_pkgs.add(d.relative_to(target).as_posix())
                d = d.parent
        for pkg in sorted(broken_pkgs):
            failures += 1
            print(
                f"verify: {pkg} holds suites but no __init__.py — discovery "
                "would skip it silently",
                file=sys.stderr,
            )
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
            cwd=target / "scripts",
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures += 1
            print("verify: scripts/tests discovery FAILED", file=sys.stderr)
            for line in result.stderr.strip().splitlines()[-5:]:
                print(f"  {line}", file=sys.stderr)
        elif not re.search(r"Ran [1-9][0-9]* tests?", result.stderr):
            failures += 1
            print(
                "verify: scripts/tests discovery ran zero tests — suites missing "
                "or skipped",
                file=sys.stderr,
            )
    for rel in sorted(hook_suites):
        result = subprocess.run(
            [sys.executable, str(target / rel)],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures += 1
            print(f"verify: {rel} FAILED", file=sys.stderr)
            for line in result.stderr.strip().splitlines()[-5:]:
                print(f"  {line}", file=sys.stderr)
    if not failures:
        print(f"verified: {len(suites)} vendored suite(s) pass on this host")
    return failures


def _installed_suites(installed):
    """The test suites among an install's produced files: test_*.py under
    scripts/ or .claude/hooks/."""
    return [
        rel
        for rel in installed
        if rel.endswith(".py")
        and Path(rel).name.startswith("test_")
        and (rel.startswith("scripts/") or rel.startswith(".claude/hooks/"))
    ]


def record_extension(target, ext_path):
    """Record one kept project extension durably: add it to `[harness]
    extensions` in scripts/layout.toml and, on a gitignored-runtime channel,
    re-include it in .gitignore. Idempotent. The re-include form is encoded
    here once — `!<path>/` for a directory, `!<path>` for a file; a trailing
    slash on a file path would not re-include it."""
    ext_path = ext_path.strip("/")
    # The path lands verbatim inside layout.toml's extensions array and a
    # .gitignore line. A quote, bracket, comma, backslash, control char, or
    # dot-dot segment could inject config entries, corrupt the array's
    # comma-joined re-parse, or escape the target — reject, never escape.
    # An empty or "." result would record the whole target as an extension.
    if (
        not ext_path
        or ext_path == "."
        or any(ch in ext_path for ch in '"[],\\')
        or ext_path != ext_path.strip()
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in ext_path)
        or ".." in Path(ext_path).parts
        or Path(ext_path).is_absolute()
    ):
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
        lt.write_text(text[: m.start()] + new_line + text[m.end() :], encoding="utf-8")
        changed.append("layout.toml")
    if channel != "copy":
        gi = target / ".gitignore"
        line = f"!{ext_path}/" if (target / ext_path).is_dir() else f"!{ext_path}"
        gi_text = gi.read_text(encoding="utf-8") if gi.is_file() else ""
        if line not in gi_text.splitlines():
            gi.write_text(gi_text.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
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


def main(argv):
    if len(argv) >= 2 and argv[1] == "record-extension":
        if len(argv) != 4:
            print(USAGE, file=sys.stderr)
            return 2
        target = logical_abspath(argv[2])
        if not target.is_dir():
            print(f"materialize: no such target directory {argv[2]}", file=sys.stderr)
            return 1
        return record_extension(target, argv[3])
    # --no-verify skips the install-time suite run. For harness-internal
    # callers only (bootstrap, faithfulness, self-tests): the battery runs
    # the same suites in its own step, so re-running them per materialize
    # would only slow the gate. Consumers get verification by default.
    verify = "--no-verify" not in argv
    argv = [a for a in argv if a != "--no-verify"]
    if len(argv) != 3:
        print(USAGE, file=sys.stderr)
        return 2
    stack, target = argv[1], logical_abspath(argv[2])
    # Validate the slug against helpers.STACKS, the documented roster (its
    # parity with the harness/stacks/ directories is check-sync-guarded). A
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
    installed, copied = install(stack, target, excluded_prefixes(tools, channel))

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
