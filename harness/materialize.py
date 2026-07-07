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
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from helpers import (  # noqa: E402
    ALL_TOOLS, TOOLS, logical_abspath, marketplace_excludes, runtime_files,
)

USAGE = "usage: materialize.py <stack> <target-dir>"

# On the marketplace channel the tool-discovered surfaces (skills, agents,
# hooks) are delivered by the plugin, not materialized; the engine sliver
# (helpers.ENGINE_SLIVER) and tool config (.junie/config.json) stay
# project-side. OpenCode is not a plugin target — under marketplace it is
# already excluded via its TOOLS surfaces unless the project lists it as a
# tool. Both mappings derive from the helpers.TOOLS registry.


def runtime_dirs():
    """The harness-owned runtime directories: derived from RUNTIME_PATHS in
    harness/core/scripts/brief_doctor.py (the single source), taking the
    entries whose last segment has no extension. These trees are 100%
    harness-owned, so scanning them for extras never touches a project-owned
    file (.claude/settings*.json and scripts/layout.toml live outside them)."""
    spec = importlib.util.spec_from_file_location(
        "brief_doctor", HERE / "core" / "scripts" / "brief_doctor.py")
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
        raise SystemExit(f"materialize: {lt} unparseable: {exc} — fix the "
                         "layout before materializing (the channel/tools "
                         "declaration is unreadable)")
    harness = data.get("harness", {})
    if not isinstance(harness, dict):
        raise SystemExit(f"materialize: {lt} [harness] is not a table — fix "
                         "the layout before materializing")
    channel = harness.get("channel")
    channel = channel if isinstance(channel, str) and channel else "copy"
    tools = harness.get("tools")
    if isinstance(tools, list) and all(isinstance(t, str) for t in tools) and tools:
        return tools, channel
    return None, channel


def resolve_tools(target, declared):
    """The tool surfaces to install. Precedence: (1) the project's declared set
    in layout.toml; (2) an existing materialized project (a runtime dir already
    present) keeps its current surfaces — detect them, never add one (upgrade
    safety); (3) a greenfield target with no signal gets all four."""
    if declared:
        return declared
    if (target / ".claude/skills").is_dir() or (target / ".claude/agents").is_dir():
        tools = ["claude"]
        tools.extend(tool for tool, row in TOOLS.items()
                     if tool != "claude" and (target / row["agents_dir"]).is_dir())
        return tools
    return list(ALL_TOOLS)


def excluded_prefixes(tools, channel):
    prefixes = [p for tool, row in TOOLS.items()
                if tool not in tools for p in row["surfaces"]]
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
        present.update(p for p in (f"scripts/{rel}" for rel in runtime_files(scripts))
                       if p not in skip)
    return present


def run_refresh(script, *args):
    """Run a sibling refresh script and return its report line."""
    result = subprocess.run(
        [sys.executable, str(script), *[str(a) for a in args]],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout.strip()


def main(argv):
    if len(argv) != 3:
        print(USAGE, file=sys.stderr)
        return 2
    stack, target = argv[1], logical_abspath(argv[2])
    if not target.is_dir():
        print(f"materialize: no such target directory {argv[2]}", file=sys.stderr)
        return 1

    declared, channel = read_layout(target)
    tools = resolve_tools(target, declared)
    installed, copied = install(stack, target, excluded_prefixes(tools, channel))

    print(f"materialized stack={stack} channel={channel} tools={' '.join(tools)}: "
          f"{copied} file(s) into {target}")

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
            print(f"materialize: missing or empty {stamp} — cannot stamp CLAUDE.md",
                  file=sys.stderr)
            return 1
        ch_status = run_refresh(HERE / "claude-md" / "refresh-chapters.py",
                                target / "CLAUDE.md", HERE)
        print(f"managed chapters: {ch_status}")

    # Refresh the harness-owned lines of two more project-owned files, the same
    # way: deterministically, in place, marker-free — the harness owns those
    # lines, the project owns the rest. Both are ENSURE-PRESENT and additive:
    # project-authored ignores, keys, and hooks are never rewritten. Files the
    # project fills with judgment (layout.toml data, docs/ briefs, non-doctrine
    # CLAUDE.md chapters) are NOT touched here — the /materialize skill
    # reconciles those advisorily.
    print(run_refresh(HERE / "refresh-gitignore.py", target / ".gitignore",
                      HERE / "init" / "core" / "gitignore-runtime.txt", channel))
    print(run_refresh(HERE / "refresh-settings.py",
                      target / ".claude" / "settings.json",
                      HERE / "init" / "core" / ".claude" / "settings.json", target))

    # Extras = files under the harness-owned runtime dirs that this install did
    # not produce. One path per line (relative to the target), between the
    # markers, so the /materialize skill can parse them.
    extras = sorted(scan_present(target, stack, runtime_dirs()) - installed)
    print(f"--- extras: {len(extras)} file(s) not produced by the harness ---")
    for path in extras:
        print(path)
    print("--- end extras ---")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
