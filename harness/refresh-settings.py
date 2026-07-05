#!/usr/bin/env python3
"""Ensure the harness-owned keys of a consumer's .claude/settings.json.

The deterministic, marker-free analogue of refresh-chapters.sh for settings:
it makes the harness-owned keys current without any sentinel, identifying
ownership by the shipped template rather than by a recorded region.

    refresh-settings.py <target-settings.json> <template-settings.json> <target-root>

Harness-owned in settings.json, and all this touches:
  - every `env` key the template declares (the agent-teams flag);
  - each `PreToolUse` matcher whose command targets a `.claude/hooks/*.sh`
    the install actually delivered into the target tree.

The operation is ENSURE-PRESENT, and only that. A harness key or matcher the
target lacks is added; a key the project set itself, a matcher it wrote, and
every other part of the file are left untouched. It never rewrites a project
value and never removes a matcher — a hook renamed away leaves an inert matcher
for the advisory pass or a human to prune. Registering only hooks that exist in
the tree makes it channel-correct for free: on the marketplace channel the hooks
ship in the plugin, not `.claude/hooks/`, so no matcher is added there.

Robustness: a target that is missing, unparseable, or not a JSON object is
skipped with a message and a zero exit — never a traceback that would abort the
materialize mid-run. A project value that is the wrong shape (e.g. a non-object
`env`) is left untouched rather than overwritten.

Idempotent: the file is rewritten only when something actually changed, so a
re-materialize on an up-to-date project produces no diff (and no reformat).
"""
import json
import re
import sys
from pathlib import Path

USAGE = "usage: refresh-settings.py <target-settings.json> <template-settings.json> <target-root>"
HOOK_RE = re.compile(r"\.claude/hooks/([A-Za-z0-9._-]+\.sh)")


def hook_filename(command):
    m = HOOK_RE.search(command or "")
    return m.group(1) if m else None


def registered_hooks(pre_entries):
    """Every (matcher, hook-script basename) pair already registered.

    Keyed by the pair, not the basename alone: one script may legitimately
    register under two matchers (handoff-log-guard.sh guards both the
    Write/Edit tools and Bash), and basename-only keying would silently drop
    the second entry."""
    pairs = set()
    for entry in pre_entries:
        if not isinstance(entry, dict):
            continue
        matcher = entry.get("matcher", "")
        for hook in entry.get("hooks", []) or []:
            if isinstance(hook, dict):
                name = hook_filename(hook.get("command", ""))
                if name:
                    pairs.add((matcher, name))
    return pairs


def main(argv):
    if len(argv) != 4:
        print(USAGE, file=sys.stderr)
        return 2
    target_path, template_path, root = argv[1], argv[2], Path(argv[3])

    # The template is ours — a parse error there is a harness bug, so let it raise.
    template = json.loads(Path(template_path).read_text(encoding="utf-8"))

    # The target is the project's — tolerate every shape it might be in.
    try:
        target = json.loads(Path(target_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        target = {}
    except json.JSONDecodeError:
        print("settings: skipped (target settings.json is not valid JSON)")
        return 0
    if not isinstance(target, dict):
        print("settings: skipped (target settings.json is not a JSON object)")
        return 0

    changed = []

    # 1. env flags — ensure-present-if-absent; never overwrite a project value,
    #    and never clobber a project's non-object env.
    env = target.get("env")
    if isinstance(env, dict) or env is None:
        env = env if isinstance(env, dict) else {}
        added_env = False
        for key, value in template.get("env", {}).items():
            if key not in env:
                env[key] = value
                changed.append(f"env.{key}")
                added_env = True
        if added_env:
            target["env"] = env

    # 2. PreToolUse matchers for delivered hooks the target has not registered.
    template_pre = template.get("hooks", {}).get("PreToolUse", [])
    hooks = target.get("hooks")
    if template_pre and (isinstance(hooks, dict) or hooks is None):
        hooks = hooks if isinstance(hooks, dict) else {}
        pre = hooks.get("PreToolUse")
        pre = pre if isinstance(pre, list) else ([] if pre is None else None)
        if pre is not None:
            already = registered_hooks(pre)
            added_hook = False
            for entry in template_pre:
                matcher = entry.get("matcher", "")
                for hook in entry.get("hooks", []):
                    name = hook_filename(hook.get("command", ""))
                    # Register only a hook the project carries, once per
                    # (matcher, script) pair — a script may guard two matchers.
                    if not name or (matcher, name) in already:
                        continue
                    if not (root / ".claude" / "hooks" / name).is_file():
                        continue
                    pre.append(entry)
                    already.add((matcher, name))
                    changed.append(f"hook:{matcher}:{name}")
                    added_hook = True
                    break
            if added_hook:
                hooks["PreToolUse"] = pre
                target["hooks"] = hooks

    if changed:
        Path(target_path).write_text(
            json.dumps(target, indent=2) + "\n", encoding="utf-8"
        )
    print("settings: " + (", ".join(changed) if changed else "no change"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
