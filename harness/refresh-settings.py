#!/usr/bin/env python3
"""Ensure the harness-owned keys of a consumer's .claude/settings.json.

    refresh-settings.py <target-settings.json> <template-settings.json> <target-root>

The marker-free analogue of the chapter refresh for settings: ownership is
the shipped template, and the operation is ensure-present only. Every env key
the template declares and every hook matcher whose script the install
delivered are added when absent; a project value, a project matcher, and the
rest of the file are never rewritten or removed. Stdlib only.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

USAGE = "usage: refresh-settings.py <target-settings.json> <template-settings.json> <target-root>"
ARGS = 4
USAGE_EXIT = 2
# .sh is parsed too, so a legacy matcher forms a recognized pair and a re-run
# stays idempotent on it; the stale entry lingers for a human to prune.
HOOK_RE = re.compile(r"\.claude/hooks/([A-Za-z0-9._-]+\.(?:py|sh))")

Settings = dict[str, Any]


def hook_filename(command: str | None) -> str | None:
    """Return the hook script a matcher command names, or None."""
    m = HOOK_RE.search(command or "")
    return m.group(1) if m else None


def registered_hooks(pre_entries: list[Any]) -> set[tuple[str, str]]:
    """Return every (matcher, hook script) pair the entries already register."""
    # Keyed by the pair: one script may guard two matchers, and basename-only
    # keying would silently drop the second entry.
    pairs: set[tuple[str, str]] = set()
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


def _read_target(path: Path) -> Settings | None:
    # The target is the project's: every shape is tolerated, and a skip is a
    # message with a zero exit, never a traceback mid-materialize.
    try:
        target = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("settings: skipped (target settings.json is not valid JSON)")
        return None
    if not isinstance(target, dict):
        print("settings: skipped (target settings.json is not a JSON object)")
        return None
    return target


def _ensure_env(target: Settings, template: Settings) -> list[str]:
    # A project value is never overwritten, and a project's non-object env is
    # left alone.
    env = target.get("env")
    if env is not None and not isinstance(env, dict):
        return []
    env = env if isinstance(env, dict) else {}
    changed: list[str] = []
    for key, value in template.get("env", {}).items():
        if key not in env:
            env[key] = value
            changed.append(f"env.{key}")
    if changed:
        target["env"] = env
    return changed


def _ensure_hooks(target: Settings, template: Settings, root: Path) -> list[str]:
    # Per event type the template declares; a matcher-less event keys its
    # pairs on the empty matcher. Registering only a script the target
    # carries makes this channel-correct: marketplace hooks ship in the plugin.
    template_hooks = template.get("hooks", {})
    hooks = target.get("hooks")
    if not isinstance(template_hooks, dict):
        return []
    if hooks is not None and not isinstance(hooks, dict):
        return []
    hooks = hooks if isinstance(hooks, dict) else {}
    changed: list[str] = []
    for event, template_entries in template_hooks.items():
        if not isinstance(template_entries, list) or not template_entries:
            continue
        entries = hooks.get(event)
        if entries is None:
            entries = []
        elif not isinstance(entries, list):
            continue
        added = _add_missing_matchers(entries, template_entries, event, root)
        if added:
            changed.extend(added)
            hooks[event] = entries
            target["hooks"] = hooks
    return changed


def _add_missing_matchers(
    entries: list[Any], template_entries: list[Any], event: str, root: Path
) -> list[str]:
    # Only the unregistered hooks of an entry are appended: the whole entry
    # would re-register a hook the target already carries under the same
    # matcher, and it would run twice.
    already = registered_hooks(entries)
    changed: list[str] = []
    for entry in template_entries:
        matcher = entry.get("matcher", "")
        missing = []
        for hook in entry.get("hooks", []):
            name = hook_filename(hook.get("command", ""))
            if not name or (matcher, name) in already:
                continue
            if not (root / ".claude" / "hooks" / name).is_file():
                continue
            missing.append(hook)
            already.add((matcher, name))
            changed.append(
                f"hook:{matcher}:{name}" if matcher else f"hook:{event}:{name}"
            )
        if missing:
            entries.append({**entry, "hooks": missing})
    return changed


def main(argv: list[str]) -> int:
    """Refresh the target settings from the command line and return the exit code."""
    if len(argv) != ARGS:
        print(USAGE, file=sys.stderr)
        return USAGE_EXIT
    target_path, template_path, root = Path(argv[1]), Path(argv[2]), Path(argv[3])
    # The template is harness-owned: a parse error there is a harness bug and raises.
    template = json.loads(template_path.read_text(encoding="utf-8"))
    target = _read_target(target_path)
    if target is None:
        return 0
    changed = _ensure_env(target, template) + _ensure_hooks(target, template, root)
    if changed:
        target_path.write_text(json.dumps(target, indent=2) + "\n", encoding="utf-8")
    print("settings: " + (", ".join(changed) if changed else "no change"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
