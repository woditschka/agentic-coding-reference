#!/usr/bin/env bash
# Render the harness runtime into a plugin marketplace.
#
#   harness/package-marketplace.sh [output-dir]   # default: the repo root
#
# Unlike materialize.sh (a byte-identical copy), this RENDERS: it reshapes the
# canonical core ∪ stack runtime into the Claude-plugin layout and fans it out
# per tool. The output is a marketplace — one .claude-plugin/marketplace.json
# plus one plugin per (stack, tool) under plugins/. Three of the four tools read
# the .claude-plugin/ format (Claude Code, Copilot CLI, Junie CLI); OpenCode is
# not a plugin target and is omitted.
#
# Engines are NOT bundled. A plugin carries only the tool-discovered surfaces
# (skills, agents, hooks). The consuming project keeps the engine sliver
# (scripts, schemas, templates) project-side — the marketplace channel — so the
# skills' project-relative references (scripts/handoff.py, schemas/…) resolve in
# the project, uniformly across tools. No ${CLAUDE_PLUGIN_ROOT} in skills; the
# only plugin-root reference is the Claude continuation hook, which is
# Claude-specific by nature. See docs/adr/2026-06-14-marketplace-plugin-channel.md.
#
# Deterministic and self-cleaning: it removes the previous generation and
# rebuilds, so a re-run on an unchanged source produces an identical tree (the
# faithfulness guard in check-sync.sh relies on this).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
out_arg="${1:-$here/..}"
out="$(cd "$out_arg" && pwd)"

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"   # STACKS + PLUGIN_TOOLS rosters, read_stamp

version="$(read_stamp "$here/VERSION" package-marketplace)"
version_date="$(read_stamp "$here/VERSION-DATE" package-marketplace)"

stack_label() { case "$1" in go) echo "Go";; java-spring-boot) echo "Java Spring Boot";; generic) echo "Generic";; *) echo "$1";; esac; }
tool_label()  { case "$1" in claude) echo "Claude Code";; copilot) echo "Copilot CLI";; junie) echo "Junie CLI";; *) echo "$1";; esac; }
# Short stack token for the plugin (and slash-namespace) name: keeps the
# user-typed prefix terse — java-spring-boot would make /java-spring-boot-junie:.
# Drops the redundant "java"; "spring-boot" stays precise about the stack.
plugin_stack() { case "$1" in java-spring-boot) echo "spring-boot";; *) echo "$1";; esac; }

# Copy a merged core+stack subtree (relative dir) into dest, pruning pycache.
copy_merged() { # <stack> <rel-src-dir> <dest-dir>
  local stack="$1" rel="$2" dest="$3" layer src f
  for layer in core "stacks/$stack"; do
    src="$here/$layer/$rel"
    [ -d "$src" ] || continue
    while IFS= read -r -d '' f; do
      f="${f#./}"
      mkdir -p "$dest/$(dirname "$f")"
      cp -p "$src/$f" "$dest/$f"
    done < <(cd "$src" && find . -type f ! -name '*.pyc' ! -path '*__pycache__*' -print0)
  done
}

# Copy a tool's agent files (flat) into dest, dropping any README.
copy_agents() { # <stack> <src-rel> <name-glob> <dest>
  local stack="$1" srcrel="$2" glob="$3" dest="$4" layer src f
  mkdir -p "$dest"
  for layer in core "stacks/$stack"; do
    src="$here/$layer/$srcrel"
    [ -d "$src" ] || continue
    while IFS= read -r -d '' f; do
      cp -p "$src/${f#./}" "$dest/${f#./}"
    done < <(cd "$src" && find . -maxdepth 1 -type f -name "$glob" ! -name 'README*' -print0)
  done
}

# Clean the prior generation — scoped paths only, never a blind rm at the root.
rm -rf "$out/plugins"
rm -f  "$out/.claude-plugin/marketplace.json"
mkdir -p "$out/plugins" "$out/.claude-plugin"

plugins_meta=""   # "name|description" per line, for the marketplace manifest
count=0
for stack in "${STACKS[@]}"; do
  slabel="$(stack_label "$stack")"
  for tool in "${PLUGIN_TOOLS[@]}"; do
    tlabel="$(tool_label "$tool")"
    pname="$(plugin_stack "$stack")-$tool"
    pdir="$out/plugins/$pname"
    mkdir -p "$pdir/.claude-plugin"

    # skills — identical across the tools of a stack (merged core+stack tree)
    copy_merged "$stack" ".claude/skills" "$pdir/skills"

    # agents — per tool (bodies identical; frontmatter and file suffix differ)
    case "$tool" in
      claude)  copy_agents "$stack" ".claude/agents" '*.md'       "$pdir/agents" ;;
      copilot) copy_agents "$stack" ".github/agents" '*.agent.md' "$pdir/agents" ;;
      junie)   copy_agents "$stack" ".junie/agents"  '*.md'       "$pdir/agents" ;;
      *) echo "package-marketplace: tool '$tool' has no agents mapping — a PLUGIN_TOOLS entry needs an arm here" >&2
         exit 1 ;;
    esac

    # hooks — the SendMessage continuation hook is Claude-specific
    hooknote=""
    if [ "$tool" = "claude" ]; then
      mkdir -p "$pdir/hooks"
      cp -p "$here"/core/.claude/hooks/*.sh "$pdir/hooks/"
      cp -p "$here/marketplace/hooks.json" "$pdir/hooks/hooks.json"
      hooknote=", continuation hook"
    fi

    # engine sliver, bundled — the plugin cache is read-only and the skills call
    # engines by project-relative path, so a consumer installs these INTO the
    # project once via the marketplace-setup skill. Mirrors the marketplace
    # materialize sliver (scripts, schemas, templates; junie config for junie).
    eng="$pdir/_engine"
    copy_merged "$stack" "scripts"           "$eng/scripts"
    copy_merged "$stack" "schemas/scratch"   "$eng/schemas/scratch"
    copy_merged "$stack" ".claude/templates" "$eng/.claude/templates"
    if [ "$tool" = "junie" ] && [ -f "$here/core/.junie/config.json" ]; then
      mkdir -p "$eng/.junie"
      cp -p "$here/core/.junie/config.json" "$eng/.junie/config.json"
    fi
    cp -p "$here/init/core/gitignore-runtime.txt" "$eng/.gitignore-block"

    # the one-time installer + the skill that drives it (plugin-only). The skill
    # is the ONE place a plugin name is baked in — it is the user-typed entry
    # point, so {{PLUGIN_NAME}} is substituted to the namespaced invocation. Skill
    # and agent BODIES never carry a namespace (the source is shared across all
    # plugins); test-marketplace.sh enforces that plugin-safety invariant.
    cp -p "$here/marketplace/setup.sh" "$pdir/setup.sh"

    # the harness-managed CLAUDE.md chapters + their writer, bundled so setup.sh
    # can refresh them in the consumer's CLAUDE.md — the marketplace equivalent of
    # what materialize.sh does on the copy channel. Lives in the read-only plugin
    # cache; unlike _engine it is NOT copied into the project (the chapter content
    # belongs in CLAUDE.md, not duplicated into the runtime tree).
    mkdir -p "$pdir/claude-md"
    cp -p "$here/claude-md/managed-chapters.md" "$pdir/claude-md/managed-chapters.md"
    cp -p "$here/claude-md/refresh-chapters.sh" "$pdir/claude-md/refresh-chapters.sh"

    # the deterministic .gitignore refresh, bundled beside setup.sh so a plugin
    # UPGRADE ensures any newly-added runtime path present in the consumer's
    # .gitignore — the marketplace equivalent of what materialize.sh runs on the
    # copy/manifest channels. Cache-side (read-only); setup.sh calls it, it is
    # never copied into the project. The settings.json refresh has no marketplace
    # analogue: hooks ship in the plugin's hooks.json, not the consumer's settings.
    cp -p "$here/refresh-gitignore.sh" "$pdir/refresh-gitignore.sh"

    # The harness release date at the plugin root, where refresh-chapters.sh reads
    # it to stamp the consumer's CLAUDE.md — mirroring how it reads harness/VERSION-
    # DATE on the copy channel. setup.sh re-runs on a plugin upgrade, so this keeps
    # the stamp current with the installed plugin.
    printf '%s\n' "$version_date" > "$pdir/VERSION-DATE"

    mkdir -p "$pdir/skills/marketplace-setup"
    sed "s/{{PLUGIN_NAME}}/$pname/g" \
      "$here/marketplace/setup-skill.md" > "$pdir/skills/marketplace-setup/SKILL.md"

    desc="$slabel agent harness for $tlabel — pipeline agents, skills$hooknote, plus a one-time engine setup."
    cat > "$pdir/.claude-plugin/plugin.json" <<JSON
{
  "name": "$pname",
  "description": "$desc",
  "version": "$version",
  "author": {
    "name": "Agentic Coding Reference"
  }
}
JSON
    plugins_meta="$plugins_meta$pname|$desc
"
    count=$((count + 1))
  done
done

# Marketplace manifest — built with python so the JSON is always well-formed.
mkt_desc="Production agent configurations from the Agentic Coding Reference, as installable plugins. Read by Claude Code, Copilot CLI, and Junie CLI."
PLUGINS_META="$plugins_meta" python3 - "$out/.claude-plugin/marketplace.json" "$version" "$mkt_desc" <<'PY'
import json, os, sys
out_path, version, mkt_desc = sys.argv[1], sys.argv[2], sys.argv[3]
plugins = []
for line in os.environ["PLUGINS_META"].splitlines():
    if not line.strip():
        continue
    name, desc = line.split("|", 1)
    plugins.append({"name": name, "source": f"./plugins/{name}", "description": desc})
doc = {
    "name": "agentic-harness",
    "description": mkt_desc,
    "owner": {"name": "Agentic Coding Reference"},
    "metadata": {"version": version},
    "plugins": plugins,
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY

echo "packaged marketplace 'agentic-harness' v$version: $count plugin(s) → $out/.claude-plugin/marketplace.json + $out/plugins/"
