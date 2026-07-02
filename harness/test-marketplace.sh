#!/usr/bin/env bash
# Deterministic acceptance test for the marketplace (plugin) distribution channel.
# It proves, without a running model, everything the channel guarantees up to the
# point a live agent invokes a skill:
#
#   1. Manifest integrity   — marketplace.json + every plugin.json well-formed,
#                             names unique, sources resolve, version == VERSION.
#   2. Namespace safety      — no rendered skill/agent body hardcodes a plugin
#                             prefix (the source is shared across all plugins, so
#                             a baked-in `go-claude:` would break every other one).
#                             The user-typed marketplace-setup skill is the lone
#                             allowed exception.
#   3. Install simulation     — for one Go and one Spring plugin: scaffold a
#                             consumer (init, marketplace channel), run the
#                             bundled setup.sh, then assert the engines land
#                             gitignored, project files stay tracked, the doctor
#                             passes with the untracked invariant, and handoff.py
#                             appends a valid record while rejecting an invalid
#                             test name via the project's layout pattern.
#
# What it does NOT cover: a live agent model-invoking a namespaced plugin skill
# inside a subagent. That needs a running tool and a restart, so it is a manual
# release-checklist step — see docs/adr/2026-06-14-marketplace-plugin-channel.md.
# The namespace-safety check (2) is its deterministic stand-in.
#
#   harness/test-marketplace.sh        # needs bash, git, python3
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
cd "$root"

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"   # note, empty_chapter

fail=0

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# 1–3. Static battery over the committed marketplace (one python pass).
note "static checks (manifest, namespace)"
if ! python3 - "$root" <<'PY'; then fail=1; fi
import json, os, re, sys

root = sys.argv[1]
errors = []

version = open(os.path.join(root, "harness/VERSION")).read().strip()
mkt_path = os.path.join(root, ".claude-plugin/marketplace.json")
mkt = json.load(open(mkt_path))

# --- 1. manifest integrity ---
for key in ("name", "owner", "plugins"):
    if key not in mkt:
        errors.append(f"marketplace.json missing required key '{key}'")
if "name" not in mkt.get("owner", {}):
    errors.append("marketplace.json owner missing 'name'")

names = [p.get("name") for p in mkt.get("plugins", [])]
if len(names) != len(set(names)):
    errors.append(f"duplicate plugin names in marketplace.json: {names}")

plugin_names = []
for p in mkt.get("plugins", []):
    name, src = p.get("name"), p.get("source")
    if not name or not src:
        errors.append(f"plugin entry missing name/source: {p}")
        continue
    plugin_names.append(name)
    pdir = os.path.normpath(os.path.join(root, src))
    if not os.path.isdir(pdir):
        errors.append(f"[{name}] source path does not exist: {src}")
        continue
    man = os.path.join(pdir, ".claude-plugin/plugin.json")
    if not os.path.isfile(man):
        errors.append(f"[{name}] missing .claude-plugin/plugin.json")
        continue
    pj = json.load(open(man))
    if pj.get("name") != name:
        errors.append(f"[{name}] plugin.json name '{pj.get('name')}' != marketplace entry")
    if pj.get("version") != version:
        errors.append(f"[{name}] plugin.json version '{pj.get('version')}' != harness/VERSION '{version}'")
    # A plugin with no agents ships silently useless — copy_agents produced nothing
    # (e.g. a PLUGIN_TOOLS entry whose case arm globs the wrong dir or suffix).
    agents_dir = os.path.join(pdir, "agents")
    if not (os.path.isdir(agents_dir) and any(f.endswith(".md") for f in os.listdir(agents_dir))):
        errors.append(f"[{name}] agents/ missing or empty — the render produced no agent files")

# --- 2. namespace safety: no plugin-prefix literal in shared bodies ---
# marketplace-setup is the one user-typed entry point allowed to name itself.
prefixes = [re.compile(re.escape(n) + r":") for n in plugin_names]
for p in mkt.get("plugins", []):
    pdir = os.path.normpath(os.path.join(root, p["source"]))
    for sub in ("skills", "agents"):
        base = os.path.join(pdir, sub)
        for dirpath, _, files in os.walk(base):
            if os.sep + "marketplace-setup" in dirpath + os.sep:
                continue
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                fp = os.path.join(dirpath, fn)
                text = open(fp, encoding="utf-8").read()
                for rx in prefixes:
                    if rx.search(text):
                        rel = os.path.relpath(fp, root)
                        errors.append(f"[{p['name']}] hardcoded plugin namespace '{rx.pattern}' in {rel}")
                        break

if errors:
    for e in errors:
        print("FAIL:", e, file=sys.stderr)
    sys.exit(1)
print(f"  {len(plugin_names)} plugin(s): manifest + namespace ok")
PY

# 4. Install simulation — scaffold a consumer, run setup.sh, exercise the engines.
#    Args: <plugin> <stack> <valid-test-name> <invalid-test-name>.
install_sim() {
  local plugin="$1" stack="$2" vt="$3" it="$4"
  local consumer="$tmp/c-$plugin" cache="$tmp/cache-$plugin"
  mkdir -p "$consumer" "$cache"
  git -C "$consumer" init -q

  if ! bash "$here/init.sh" "$stack" "$consumer" "mkt-$plugin" "acceptance" "" "claude" marketplace >/dev/null 2>&1; then
    echo "FAIL[$plugin]: init (marketplace) failed" >&2; fail=1; return
  fi
  cp -R "$root/plugins/$plugin/." "$cache/"
  if ! bash "$cache/setup.sh" "$consumer" >/dev/null 2>&1; then
    echo "FAIL[$plugin]: setup.sh failed" >&2; fail=1; return
  fi

  # setup.sh must REFRESH the harness-managed chapters, not just install engines.
  # Empty the Agent Usage chapter, re-run setup, and confirm it is refilled from
  # the bundled claude-md/ — independent of init's fill (the marketplace upgrade
  # path: re-run setup after a plugin update).
  empty_chapter "$consumer/CLAUDE.md" '## Agent Usage (Mandatory)'
  if grep -q 'Always use specialized agents' "$consumer/CLAUDE.md"; then
    echo "FAIL[$plugin]: test could not empty the Agent Usage chapter" >&2; fail=1; return
  fi
  bash "$cache/setup.sh" "$consumer" >/dev/null 2>&1
  if ! grep -q 'Always use specialized agents' "$consumer/CLAUDE.md"; then
    echo "FAIL[$plugin]: setup.sh did not refresh the Agent Usage chapter from the bundled source" >&2; fail=1; return
  fi

  # setup.sh must ENSURE the .gitignore runtime paths present on every re-run —
  # the upgrade path. Drop a runtime path and add a project ignore, re-run setup,
  # and confirm the path is re-ensured while the project's own line survives (the
  # append-once freeze this replaces would have left the dropped path missing).
  printf 'my-own-secret/\n' >> "$consumer/.gitignore"
  grep -vxF 'scripts/brief_doctor.py' "$consumer/.gitignore" > "$consumer/.gitignore.x" \
    && mv "$consumer/.gitignore.x" "$consumer/.gitignore"
  bash "$cache/setup.sh" "$consumer" >/dev/null 2>&1
  if ! grep -qxF 'scripts/brief_doctor.py' "$consumer/.gitignore"; then
    echo "FAIL[$plugin]: setup.sh did not re-ensure a dropped runtime path (upgrade freeze)" >&2; fail=1; return
  fi
  if [ "$(grep -cxF 'my-own-secret/' "$consumer/.gitignore" || true)" != 1 ]; then
    echo "FAIL[$plugin]: setup.sh lost or duplicated a project .gitignore line" >&2; fail=1; return
  fi

  # engines present and gitignored; project-owned files stay tracked.
  if ! ( cd "$consumer"
    for f in scripts/handoff.py scripts/brief_doctor.py schemas/scratch/prd-entry.schema.json; do
      [ -f "$f" ] || { echo "missing engine $f" >&2; exit 1; }
      git check-ignore -q "$f" || { echo "engine $f not gitignored" >&2; exit 1; }
    done
    for f in scripts/layout.toml CLAUDE.md; do
      ! git check-ignore -q "$f" || { echo "project file $f is gitignored" >&2; exit 1; }
    done
  ); then
    echo "FAIL[$plugin]: engine/project tracking boundary wrong" >&2; fail=1; return
  fi

  # doctor green AND reports the marketplace untracked invariant.
  local dout
  if ! dout="$( cd "$consumer" && python3 scripts/brief_doctor.py check 2>&1 )"; then
    echo "FAIL[$plugin]: doctor check exited non-zero" >&2; fail=1; return
  fi
  if ! printf '%s' "$dout" | grep -q 'marketplace channel: no harness runtime files tracked'; then
    echo "FAIL[$plugin]: doctor missing marketplace untracked invariant" >&2; fail=1; return
  fi

  # handoff engine runs from the installed location: valid appends, invalid rejected.
  local rec='{"type":"prd-entry","req_id":"REQ-MKT-001","ts":"2026-06-14T00:00:00Z","author":"product-requirements-expert","title":"t","summary":"s","acceptance_criteria":["a"],"file_targets":["f"],"test_names":["__T__"]}'
  if ! ( cd "$consumer" && printf '%s' "${rec/__T__/$vt}" | python3 scripts/handoff.py append prd-entry >/dev/null 2>&1 ); then
    echo "FAIL[$plugin]: valid record (test '$vt') was rejected" >&2; fail=1; return
  fi
  if ( cd "$consumer" && printf '%s' "${rec/__T__/$it}" | python3 scripts/handoff.py append prd-entry >/dev/null 2>&1 ); then
    echo "FAIL[$plugin]: invalid test name '$it' was accepted" >&2; fail=1; return
  fi
  echo "  [$plugin] init → setup → doctor → handoff ok"
}

note "install simulation (go + spring)"
install_sim go-claude          go               TestSmokePasses    notATestName
install_sim spring-boot-claude java-spring-boot shouldComputeTotal BadStart

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS test-marketplace: manifest, namespace, install all green"
else
  echo "FAIL test-marketplace: see failures above" >&2
  exit 1
fi
