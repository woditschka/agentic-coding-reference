#!/usr/bin/env python3
"""Render the harness runtime into a plugin marketplace: one plugin per stack and plugin tool.

    harness/package-marketplace.py [output-dir]   # default: the repo root

The producer-side renderer, unlike materialize's byte-identical copy: it
reshapes the merged core and stack runtime into the plugin layout, bundles the
engine sliver the setup skill copies into a project, and rebuilds the whole
generation on every run, so an unchanged source renders an identical tree.
Stdlib only.
"""

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import (  # noqa: E402
    ENGINE_SLIVER,
    FAILURE_EXIT,
    PLUGIN_NAMESPACE,
    PLUGIN_TOOLS,
    STACKS,
    TOOLS,
    USAGE_EXIT,
    logical_abspath,
    read_stamp,
    runtime_files,
)

USAGE = "usage: package-marketplace.py [output-dir]"
MAX_ARGS = 2

STACK_LABELS = {
    "go": "Go",
    "java-spring-boot": "Java Spring Boot",
    "generic": "Generic",
}

# The marketplace entry name keys installs (`agent-team-spring-boot@agent-team`);
# "spring-boot" stays precise about the stack without the redundant "java".
PLUGIN_STACK_TOKENS = {"java-spring-boot": "spring-boot"}

MARKETPLACE_DESCRIPTION = (
    "Production agent configurations from the Agentic Coding Reference, as "
    "installable plugins. Read by Claude Code and Copilot CLI."
)
AUTHOR = {"name": "Agentic Coding Reference"}

# Every hook command must be exactly the project shape naming a shipped
# non-test script; validating before the prefix rewrite also rejects a
# skeleton already written in the plugin-root form, which would render a fine
# plugin while every copy-channel consumer's settings resolved nowhere.
HOOK_COMMAND_SHAPE = re.compile(
    r'^python3 "\$\{CLAUDE_PROJECT_DIR\}/\.claude/hooks/([^"/]+)"$'
)
PROJECT_HOOK_PREFIX = "${CLAUDE_PROJECT_DIR}/.claude/hooks/"
PLUGIN_HOOK_PREFIX = "${CLAUDE_PLUGIN_ROOT}/hooks/"
BUNDLED_PRODUCER_MODULES = ("init.py", "registry.py", "write_guard.py")


class PackageError(Exception):
    """A failure the packager reports on stderr and exits on."""


class Release(NamedTuple):
    """The harness version and its release date, as stamped in the tree."""

    version: str
    date: str


class Plugin(NamedTuple):
    """One rendered plugin's marketplace entry."""

    name: str
    description: str


def report(message: str) -> None:
    """Write one line to stderr."""
    print(message, file=sys.stderr)


def copy_merged(stack: str, rel_src: str, dest: Path) -> None:
    """Copy a merged core-then-stack subtree into dest, the stack winning on overlap."""
    for layer in ("core", f"stacks/{stack}"):
        src = HERE / layer / rel_src
        if not src.is_dir():
            continue
        for rel in runtime_files(src):
            target = dest / rel
            write_guard.mkdir(target.parent, parents=True, exist_ok=True)
            write_guard.copy(src / rel, target)


def copy_agents(stack: str, src_rel: str, suffix: str, dest: Path) -> None:
    """Copy a tool's agent files flat into dest, dropping any README-prefixed file."""
    # The drop is broader than the sanctioned doc stems on purpose: an
    # unlisted README fails the battery, but must never ship into a plugin's
    # agent discovery while the tree is red.
    write_guard.mkdir(dest, parents=True, exist_ok=True)
    for layer in ("core", f"stacks/{stack}"):
        src = HERE / layer / src_rel
        if not src.is_dir():
            continue
        for f in sorted(src.iterdir()):
            if (
                f.is_file()
                and f.name.endswith(suffix)
                and not f.name.startswith("README")
            ):
                write_guard.copy(f, dest / f.name)


def plugin_name(stack: str, tool: str) -> str:
    """Return the marketplace entry name: the shared namespace, the stack token, and the tool unless Claude."""
    name = f"{PLUGIN_NAMESPACE}-{PLUGIN_STACK_TOKENS.get(stack, stack)}"
    return name if tool == "claude" else f"{name}-{tool}"


def render_plugin(stack: str, tool: str, out: Path, release: Release) -> Plugin:
    """Render one (stack, tool) plugin under out/plugins and return its marketplace entry."""
    if tool not in TOOLS or not TOOLS[tool]["plugin"]:
        raise PackageError(
            f"package-marketplace: tool '{tool}' is not a plugin "
            "target — add a registry.TOOLS row with plugin=True (or set it on the existing row)"
        )
    name = plugin_name(stack, tool)
    pdir = out / "plugins" / name
    write_guard.mkdir(pdir / ".claude-plugin", parents=True)
    copy_merged(stack, ".claude/skills", pdir / "skills")
    copy_agents(
        stack, TOOLS[tool]["agents_dir"], TOOLS[tool]["suffix"], pdir / "agents"
    )
    hooknote = _render_hooks(pdir) if tool == "claude" else ""
    _render_engine(stack, pdir)
    _render_setup_bundle(stack, pdir, release)
    _render_skill(pdir / "skills/init", "init-skill.md", {"{{STACK}}": stack})
    _render_skill(pdir / "skills/marketplace-setup", "setup-skill.md", {})
    description = (
        # A hard KeyError, never a fallback to the raw id as the marketplace label.
        f"{STACK_LABELS[stack]} agent harness for "
        f"{TOOLS[tool]['label']} — pipeline agents, "
        f"skills{hooknote}, plus the engine setup (re-run per update)."
    )
    # plugin.json `name` is the component namespace (the /agent-team: prefix),
    # distinct from the entry name that keys enabledPlugins; a consumer
    # enables one plugin per project, so the shared prefix never collides.
    plugin_json = {
        "name": PLUGIN_NAMESPACE,
        "description": description,
        "version": release.version,
        "author": AUTHOR,
    }
    _write_json(pdir / ".claude-plugin/plugin.json", plugin_json)
    return Plugin(name, description)


def _render_hooks(plugin_dir: Path) -> str:
    # The hooks are Claude-specific. The test_* siblings ship too, as every
    # shipped engine carries its tests. An empty glob is a renamed or gutted
    # hooks dir: fail loud, never a plugin whose hooks.json points at nothing.
    hook_files = sorted((HERE / "core/.claude/hooks").glob("*.py"))
    if not hook_files:
        raise PackageError(
            "package-marketplace: no hooks under "
            f"{HERE / 'core/.claude/hooks'} — dir renamed or gutted"
        )
    hooks = plugin_dir / "hooks"
    write_guard.mkdir(hooks)
    for f in hook_files:
        write_guard.copy(f, hooks / f.name)
    # One hook roster, two delivery forms: the project settings.json and the
    # plugin hooks.json differ only in the path prefix.
    skeleton = json.loads(
        (HERE / "init/core/.claude/settings.json").read_text(encoding="utf-8")
    )
    runnable = {f.name for f in hook_files if not f.name.startswith("test_")}
    _check_hook_commands(skeleton["hooks"], runnable)
    rendered = json.dumps({"hooks": skeleton["hooks"]}, indent=2) + "\n"
    rendered = rendered.replace(PROJECT_HOOK_PREFIX, PLUGIN_HOOK_PREFIX)
    write_guard.write_text(hooks / "hooks.json", rendered, encoding="utf-8")
    return ", continuation hook"


def _check_hook_commands(
    hooks: dict[str, list[dict[str, object]]], runnable: set[str]
) -> None:
    for entries in hooks.values():
        for entry in entries:
            hook_list = entry.get("hooks", [])
            if not isinstance(hook_list, list):
                raise PackageError(
                    f"package-marketplace: hook entry carries a non-list hooks value {hook_list!r} — "
                    "fix harness/init/core/.claude/settings.json"
                )
            for hook in hook_list:
                command = str(hook.get("command", ""))
                match = HOOK_COMMAND_SHAPE.match(command)
                if not match or match.group(1) not in runnable:
                    raise PackageError(
                        "package-marketplace: hook command is not "
                        'python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/'
                        f'<shipped non-test script>": {command!r} — fix '
                        "harness/init/core/.claude/settings.json"
                    )


def _render_engine(stack: str, plugin_dir: Path) -> None:
    # The plugin cache is read-only and the skills call engines by
    # project-relative path, so a consumer installs the sliver into the
    # project once through the setup skill.
    engine = plugin_dir / "_engine"
    for sliver in ENGINE_SLIVER:
        copy_merged(stack, sliver, engine / sliver)
    write_guard.copy(
        HERE / "init/core/gitignore-runtime.txt", engine / ".gitignore-block"
    )


def _render_setup_bundle(stack: str, plugin_dir: Path, release: Release) -> None:
    # Everything setup.sh and a plugin upgrade need beside it, cache-side: the
    # managed chapters and their writer, the gitignore refresh, the retired
    # paths and their pruner, the release date, and the scaffolder with this
    # stack's skeletons. Nothing here is copied wholesale into the project.
    write_guard.copy(HERE / "marketplace/setup.sh", plugin_dir / "setup.sh")
    claude_md = plugin_dir / "claude-md"
    write_guard.mkdir(claude_md)
    write_guard.copy(
        HERE / "claude-md/managed-chapters.md", claude_md / "managed-chapters.md"
    )
    write_guard.copy(
        HERE / "claude-md/refresh-chapters.py", claude_md / "refresh-chapters.py"
    )
    write_guard.copy(HERE / "refresh-gitignore.py", plugin_dir / "refresh-gitignore.py")
    write_guard.copy(HERE / "retired-paths.txt", plugin_dir / "retired-paths.txt")
    write_guard.copy(
        HERE / "marketplace/prune-retired.py", plugin_dir / "prune-retired.py"
    )
    write_guard.write_text(
        plugin_dir / "VERSION-DATE", release.date + "\n", encoding="utf-8"
    )
    for mod in BUNDLED_PRODUCER_MODULES:
        write_guard.copy(HERE / mod, plugin_dir / mod)
    for layer in ("core", f"stacks/{stack}"):
        src = HERE / "init" / layer
        for rel in runtime_files(src):
            target = plugin_dir / "init" / layer / rel
            write_guard.mkdir(target.parent, parents=True, exist_ok=True)
            write_guard.copy(src / rel, target)
    write_guard.write_text(
        plugin_dir / "VERSION", release.version + "\n", encoding="utf-8"
    )


def _render_skill(skill_dir: Path, template: str, replacements: dict[str, str]) -> None:
    # The plugin-only skills are the one place the namespace is baked in:
    # they are the user-typed entry points. Skill and agent bodies stay
    # channel-neutral.
    text = (HERE / "marketplace" / template).read_text(encoding="utf-8")
    text = text.replace("{{PLUGIN_NAMESPACE}}", PLUGIN_NAMESPACE)
    for token, value in replacements.items():
        text = text.replace(token, value)
    write_guard.mkdir(skill_dir, parents=True, exist_ok=True)
    write_guard.write_text(skill_dir / "SKILL.md", text, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    write_guard.write_text(
        path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def package(out: Path) -> int:
    """Rebuild the marketplace under out and return the exit code."""
    release = Release(
        read_stamp(HERE / "VERSION", "package-marketplace"),
        read_stamp(HERE / "VERSION-DATE", "package-marketplace"),
    )
    with write_guard.write_scope(out / "plugins", out / ".claude-plugin"):
        # The prior generation goes first, scoped paths only.
        write_guard.remove_tree(out / "plugins")
        write_guard.unlink(out / ".claude-plugin/marketplace.json", missing_ok=True)
        write_guard.mkdir(out / "plugins", parents=True)
        write_guard.mkdir(out / ".claude-plugin", exist_ok=True)
        plugins = [
            render_plugin(stack, tool, out, release)
            for stack in STACKS
            for tool in PLUGIN_TOOLS
        ]
        manifest = {
            # One name across the marketplace, its entries, and the skill prefix.
            "name": PLUGIN_NAMESPACE,
            "description": MARKETPLACE_DESCRIPTION,
            "owner": AUTHOR,
            "metadata": {"version": release.version},
            "plugins": [
                {
                    "name": plugin.name,
                    "source": f"./plugins/{plugin.name}",
                    "description": plugin.description,
                }
                for plugin in plugins
            ],
        }
        _write_json(out / ".claude-plugin/marketplace.json", manifest)
    print(
        f"packaged marketplace '{PLUGIN_NAMESPACE}' v{release.version}: {len(plugins)} plugin(s) "
        f"→ {out}/.claude-plugin/marketplace.json + {out}/plugins/"
    )
    return 0


def main(argv: list[str]) -> int:
    """Package the marketplace from the command line and return the exit code."""
    if len(argv) > MAX_ARGS:
        report(USAGE)
        return USAGE_EXIT
    out = logical_abspath(argv[1]) if len(argv) == MAX_ARGS else HERE.parent
    if not out.is_dir():
        report(f"package-marketplace: no such output directory {argv[1]}")
        return FAILURE_EXIT
    try:
        return package(out)
    except PackageError as exc:
        report(str(exc))
        return FAILURE_EXIT


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
