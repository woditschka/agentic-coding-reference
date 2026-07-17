#!/usr/bin/env python3
"""Render the harness runtime into a plugin marketplace.

    harness/package-marketplace.py [output-dir]   # default: the repo root

Unlike materialize.py (a byte-identical copy), this RENDERS: it reshapes the
canonical core ∪ stack runtime into the Claude-plugin layout and fans it out
per tool. The output is a marketplace — one .claude-plugin/marketplace.json
plus one plugin per (stack, tool) under plugins/. Three of the four tools read
the .claude-plugin/ format (Claude Code, Copilot CLI, Junie CLI); OpenCode is
not a plugin target and is omitted.

Engines are NOT bundled into the discovered surfaces. A plugin carries the
tool-discovered surfaces (skills, agents, hooks) plus an _engine/ payload the
marketplace-setup step copies INTO the project (re-run after every plugin
update) — the marketplace channel — so the
skills' project-relative references (scripts/handoff.py, schemas/…) resolve in
the project, uniformly across tools. No ${CLAUDE_PLUGIN_ROOT} in skills; the
only plugin-root reference is the Claude continuation hook, which is
Claude-specific by nature. See docs/adr/2026-06-14-marketplace-plugin-channel.md.

Deterministic and self-cleaning: it removes the previous generation and
rebuilds, so a re-run on an unchanged source produces an identical tree (the
faithfulness guard in check-sync.py relies on this).

Stdlib only. Battery coverage: check-sync steps 7–9 (marketplace faithfulness,
acceptance suite, real plugin install).
"""

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from helpers import (  # noqa: E402
    ENGINE_SLIVER,
    PLUGIN_TOOLS,
    STACKS,
    TOOLS,
    logical_abspath,
    read_stamp,
    runtime_files,
)

STACK_LABELS = {
    "go": "Go",
    "java-spring-boot": "Java Spring Boot",
    "generic": "Generic",
}

# Short stack token for the plugin (and slash-namespace) name: keeps the
# user-typed prefix terse — java-spring-boot would make /java-spring-boot-junie:.
# Drops the redundant "java"; "spring-boot" stays precise about the stack.
PLUGIN_STACK_TOKENS = {"java-spring-boot": "spring-boot"}

MARKETPLACE_DESCRIPTION = (
    "Production agent configurations from the Agentic Coding Reference, as "
    "installable plugins. Read by Claude Code, Copilot CLI, and Junie CLI."
)


def copy_merged(stack, rel_src, dest):
    """Copy a merged core+stack subtree (stack wins) into dest, perms kept."""
    for layer in ("core", f"stacks/{stack}"):
        src = HERE / layer / rel_src
        if not src.is_dir():
            continue
        for rel in runtime_files(src):
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, target)


def copy_agents(stack, src_rel, suffix, dest):
    """Copy a tool's agent files (flat) into dest, dropping any README."""
    dest.mkdir(parents=True, exist_ok=True)
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
                shutil.copy2(f, dest / f.name)


def render_plugin(stack, tool, out, version, version_date):
    """Render one (stack, tool) plugin; returns (name, description)."""
    name = f"{PLUGIN_STACK_TOKENS.get(stack, stack)}-{tool}"
    pdir = out / "plugins" / name
    (pdir / ".claude-plugin").mkdir(parents=True)

    # skills — identical across the tools of a stack (merged core+stack tree)
    copy_merged(stack, ".claude/skills", pdir / "skills")

    # agents — per tool (bodies identical; frontmatter and file suffix differ).
    # Every PLUGIN_TOOLS entry has its mapping by construction (both derive
    # from helpers.TOOLS); the guard keeps the render fail-loud for a
    # hand-passed non-plugin or unknown tool.
    if not TOOLS.get(tool, {}).get("plugin"):
        raise SystemExit(
            f"package-marketplace: tool '{tool}' is not a plugin "
            "target — add a helpers.TOOLS row with plugin=True (or set it on the existing row)"
        )
    copy_agents(
        stack, TOOLS[tool]["agents_dir"], TOOLS[tool]["suffix"], pdir / "agents"
    )

    # hooks — the SendMessage continuation hook is Claude-specific. The
    # test_* siblings ship too, matching the _engine/scripts precedent (every
    # shipped engine carries its tests). An empty glob is a renamed/gutted
    # hooks dir: fail loud, never a hookless plugin whose hooks.json points
    # at missing files.
    hooknote = ""
    if tool == "claude":
        hook_files = sorted((HERE / "core/.claude/hooks").glob("*.py"))
        if not hook_files:
            raise SystemExit(
                "package-marketplace: no hooks under "
                f"{HERE / 'core/.claude/hooks'} — dir renamed or gutted"
            )
        hooks = pdir / "hooks"
        hooks.mkdir()
        for f in hook_files:
            shutil.copy2(f, hooks / f.name)
        # hooks.json renders from the settings skeleton — one hook roster,
        # two delivery forms (project settings.json vs plugin hooks.json);
        # only the path prefix differs. The skeleton's env key is
        # project-only and does not ship.
        skeleton = json.loads(
            (HERE / "init/core/.claude/settings.json").read_text(encoding="utf-8")
        )
        # Pre-render invariant — an allowlist, never a blocklist: every hook
        # command must be exactly the project shape, referencing a shipped
        # non-test script (test_* files ship beside the hooks but never run
        # as one). A skeleton entry in any other form (unbraced or variant
        # prefix, relative path, inline command) fails the render, never
        # ships pointing into a consumer tree. Validating BEFORE the prefix
        # rewrite also rejects a skeleton already written in
        # ${CLAUDE_PLUGIN_ROOT} form — that would render a fine plugin while
        # every copy-channel consumer's settings.json resolved nowhere.
        runnable = {f.name for f in hook_files if not f.name.startswith("test_")}
        shape = re.compile(
            r'^python3 "\$\{CLAUDE_PROJECT_DIR\}/\.claude/hooks/([^"/]+)"$'
        )
        for entries in skeleton["hooks"].values():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    command = hook.get("command", "")
                    m = shape.match(command)
                    if not m or m.group(1) not in runnable:
                        raise SystemExit(
                            "package-marketplace: hook command is not "
                            'python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/'
                            f'<shipped non-test script>": {command!r} — fix '
                            "harness/init/core/.claude/settings.json"
                        )
        rendered = json.dumps({"hooks": skeleton["hooks"]}, indent=2) + "\n"
        rendered = rendered.replace(
            "${CLAUDE_PROJECT_DIR}/.claude/hooks/", "${CLAUDE_PLUGIN_ROOT}/hooks/"
        )
        (hooks / "hooks.json").write_text(rendered, encoding="utf-8")
        hooknote = ", continuation hook"

    # engine sliver, bundled — the plugin cache is read-only and the skills
    # call engines by project-relative path, so a consumer installs these INTO
    # the project once via the marketplace-setup skill. The subtree list is
    # helpers.ENGINE_SLIVER — the same definition materialize.py keeps
    # project-side on the marketplace channel (junie config added per tool).
    engine = pdir / "_engine"
    for sliver in ENGINE_SLIVER:
        copy_merged(stack, sliver, engine / sliver)
    junie_config = HERE / "core/.junie/config.json"
    if tool == "junie" and junie_config.is_file():
        (engine / ".junie").mkdir(parents=True)
        shutil.copy2(junie_config, engine / ".junie/config.json")
    shutil.copy2(HERE / "init/core/gitignore-runtime.txt", engine / ".gitignore-block")

    # the one-time installer + the skill that drives it (plugin-only). The
    # skill is the ONE place a plugin name is baked in — it is the user-typed
    # entry point, so {{PLUGIN_NAME}} is substituted to the namespaced
    # invocation. Skill and agent BODIES never carry a namespace (the source is
    # shared across all plugins); test-marketplace.sh enforces that invariant.
    shutil.copy2(HERE / "marketplace/setup.sh", pdir / "setup.sh")

    # the harness-managed CLAUDE.md chapters + their writer, bundled so
    # setup.sh can refresh them in the consumer's CLAUDE.md — the marketplace
    # equivalent of what materialize.py does on the copy channel. Lives in the
    # read-only plugin cache; unlike _engine it is NOT copied into the project
    # (the chapter content belongs in CLAUDE.md, not duplicated into the
    # runtime tree).
    claude_md = pdir / "claude-md"
    claude_md.mkdir()
    shutil.copy2(
        HERE / "claude-md/managed-chapters.md", claude_md / "managed-chapters.md"
    )
    shutil.copy2(
        HERE / "claude-md/refresh-chapters.py", claude_md / "refresh-chapters.py"
    )

    # the deterministic .gitignore refresh, bundled beside setup.sh so a plugin
    # UPGRADE ensures any newly-added runtime path present in the consumer's
    # .gitignore. Cache-side (read-only); setup.sh calls it, it is never copied
    # into the project. The settings.json refresh has no marketplace analogue:
    # hooks ship in the plugin's hooks.json, not the consumer's settings.
    shutil.copy2(HERE / "refresh-gitignore.py", pdir / "refresh-gitignore.py")

    # The harness release date at the plugin root, where refresh-chapters.py
    # reads it to stamp the consumer's CLAUDE.md — mirroring how it reads
    # harness/VERSION-DATE on the copy channel. setup.sh re-runs on a plugin
    # upgrade, so this keeps the stamp current with the installed plugin.
    (pdir / "VERSION-DATE").write_text(version_date + "\n", encoding="utf-8")

    setup_skill = (HERE / "marketplace/setup-skill.md").read_text(encoding="utf-8")
    skill_dir = pdir / "skills/marketplace-setup"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        setup_skill.replace("{{PLUGIN_NAME}}", name), encoding="utf-8"
    )

    description = (
        f"{STACK_LABELS.get(stack, stack)} agent harness for "
        f"{TOOLS[tool]['label']} — pipeline agents, "
        f"skills{hooknote}, plus the engine setup (re-run per update)."
    )
    plugin_json = {
        "name": name,
        "description": description,
        "version": version,
        "author": {"name": "Agentic Coding Reference"},
    }
    (pdir / ".claude-plugin/plugin.json").write_text(
        json.dumps(plugin_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return name, description


def main(argv):
    if len(argv) > 2:
        print("usage: package-marketplace.py [output-dir]", file=sys.stderr)
        return 2
    out = logical_abspath(argv[1]) if len(argv) == 2 else HERE.parent
    if not out.is_dir():
        print(
            f"package-marketplace: no such output directory {argv[1]}", file=sys.stderr
        )
        return 1

    version = read_stamp(HERE / "VERSION", "package-marketplace")
    version_date = read_stamp(HERE / "VERSION-DATE", "package-marketplace")

    # Clean the prior generation — scoped paths only, never a blind rm at the root.
    shutil.rmtree(out / "plugins", ignore_errors=True)
    (out / ".claude-plugin/marketplace.json").unlink(missing_ok=True)
    (out / "plugins").mkdir(parents=True)
    (out / ".claude-plugin").mkdir(exist_ok=True)

    plugins = []
    for stack in STACKS:
        for tool in PLUGIN_TOOLS:
            name, description = render_plugin(stack, tool, out, version, version_date)
            plugins.append(
                {
                    "name": name,
                    "source": f"./plugins/{name}",
                    "description": description,
                }
            )

    manifest = {
        "name": "agentic-harness",
        "description": MARKETPLACE_DESCRIPTION,
        "owner": {"name": "Agentic Coding Reference"},
        "metadata": {"version": version},
        "plugins": plugins,
    }
    (out / ".claude-plugin/marketplace.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        f"packaged marketplace 'agentic-harness' v{version}: {len(plugins)} plugin(s) "
        f"→ {out}/.claude-plugin/marketplace.json + {out}/plugins/"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
