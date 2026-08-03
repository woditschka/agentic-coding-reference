#!/usr/bin/env bash
# Deterministic acceptance test for the marketplace (plugin) distribution channel.
# It proves, without a running model, everything the channel guarantees up to the
# point a live agent invokes a skill:
#
#   1. Manifest integrity   — marketplace.json + every plugin.json well-formed,
#                             entry names unique, sources resolve, version ==
#                             VERSION, plugin.json name == the shared skill
#                             namespace (registry.PLUGIN_NAMESPACE).
#   2. Namespace safety      — no rendered skill/agent body hardcodes a skill
#                             prefix (bodies are channel-neutral: a copy-channel
#                             consumer has no prefix at all, and entry-name
#                             prefixes never exist as namespaces).
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
#   harness/tests/test-marketplace.sh        # needs bash, git, python3
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
harness="$(cd "$here/.." && pwd)"
root="$(cd "$harness/.." && pwd)"
cd "$root"

# shellcheck source=harness/registry.sh
. "$harness/registry.sh"   # note, empty_chapter

fail=0

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# 1–3. Static battery over the committed marketplace (one python pass).
note "static checks (manifest, namespace)"
if ! python3 -P - "$root" <<'PY'; then fail=1; fi
import json, os, re, sys

root = sys.argv[1]
errors = []

sys.path.insert(0, os.path.join(root, "harness"))
from registry import PLUGIN_NAMESPACE

# The namespace becomes plugin.json `name` in nine plugins and the typed
# prefix; an illegal token ships nine broken manifests with no other gate.
if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", PLUGIN_NAMESPACE):
    errors.append(f"PLUGIN_NAMESPACE '{PLUGIN_NAMESPACE}' is not a legal plugin-name token")

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

# Entry-name scheme: the namespace leads every entry; claude — the primary
# target — drops the tool suffix. The token map is an independent copy of the
# renderer's PLUGIN_STACK_TOKENS on purpose: one oracle per surface.
from registry import PLUGIN_TOOLS, STACKS
stack_tokens = {"java-spring-boot": "spring-boot"}
expected = {
    f"{PLUGIN_NAMESPACE}-{stack_tokens.get(s, s)}" + ("" if t == "claude" else f"-{t}")
    for s in STACKS
    for t in PLUGIN_TOOLS
}
if set(names) != expected:
    errors.append(
        f"marketplace entry names {sorted(names)} != expected scheme {sorted(expected)}"
    )

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
    if pj.get("name") != PLUGIN_NAMESPACE:
        errors.append(
            f"[{name}] plugin.json name '{pj.get('name')}' != shared namespace "
            f"'{PLUGIN_NAMESPACE}'"
        )
    if pj.get("version") != version:
        errors.append(f"[{name}] plugin.json version '{pj.get('version')}' != harness/VERSION '{version}'")
    # A plugin with no agents ships silently useless — copy_agents produced nothing
    # (e.g. a PLUGIN_TOOLS entry whose case arm globs the wrong dir or suffix).
    agents_dir = os.path.join(pdir, "agents")
    if not (os.path.isdir(agents_dir) and any(f.endswith(".md") for f in os.listdir(agents_dir))):
        errors.append(f"[{name}] agents/ missing or empty — the render produced no agent files")
    # The renderer must have substituted {{PLUGIN_NAMESPACE}} into the setup
    # skill — the namespace walk below skips marketplace-setup, and the CLI
    # install test self-skips without a claude binary, so this is the one
    # deterministic positive gate on the substitution.
    sk = os.path.join(pdir, "skills/marketplace-setup/SKILL.md")
    if not os.path.isfile(sk):
        errors.append(f"[{name}] missing skills/marketplace-setup/SKILL.md")
    else:
        text = open(sk, encoding="utf-8").read()
        if f"/{PLUGIN_NAMESPACE}:marketplace-setup" not in text:
            errors.append(f"[{name}] setup skill lacks the substituted invocation /{PLUGIN_NAMESPACE}:marketplace-setup")
        if "{{PLUGIN" in text:
            errors.append(f"[{name}] setup skill carries an unsubstituted placeholder")
    ik = os.path.join(pdir, "skills/init/SKILL.md")
    if not os.path.isfile(ik):
        errors.append(f"[{name}] missing skills/init/SKILL.md")
    else:
        text = open(ik, encoding="utf-8").read()
        if f"/{PLUGIN_NAMESPACE}:init" not in text:
            errors.append(f"[{name}] init skill lacks the substituted invocation /{PLUGIN_NAMESPACE}:init")
        if "{{PLUGIN" in text or "{{STACK" in text:
            errors.append(f"[{name}] init skill carries an unsubstituted placeholder")
        if "marketplace" not in text.split("init.py", 1)[-1][:400]:
            errors.append(f"[{name}] init skill does not pin the marketplace channel argument")

# --- 2. namespace safety: no skill-prefix literal in shared bodies ---
# marketplace-setup is the one user-typed entry point allowed to name itself.
# Both the shared namespace and the entry names are forbidden: bodies stay
# channel-neutral, and an entry-name prefix was never a valid namespace.
prefixes = [
    re.compile(re.escape(n) + r":") for n in plugin_names + [PLUGIN_NAMESPACE]
]
for p in mkt.get("plugins", []):
    pdir = os.path.normpath(os.path.join(root, p["source"]))
    for sub in ("skills", "agents"):
        base = os.path.join(pdir, sub)
        for dirpath, _, files in os.walk(base):
            # The two user-typed entry points name their own namespaced
            # invocation by design: setup and the bundled init (both are
            # rendered from marketplace/ templates with the substitution
            # positively gated above).
            if os.sep + "marketplace-setup" in dirpath + os.sep:
                continue
            if dirpath.rstrip(os.sep).endswith(os.path.join("skills", "init")):
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

# --- 3. docs oracle for the typed literal ---
# Both renderer and the checks above read registry.PLUGIN_NAMESPACE, so alone
# they cannot catch a silent constant edit. The adoption guide hardcodes the
# invocation a consumer types; a namespace change fails here until the
# consumer docs move with it.
guide = open(os.path.join(root, "docs/adoption-guide.md"), encoding="utf-8").read()
if f"/{PLUGIN_NAMESPACE}:marketplace-setup" not in guide:
    errors.append(
        f"docs/adoption-guide.md does not state the typed invocation "
        f"/{PLUGIN_NAMESPACE}:marketplace-setup — namespace and consumer docs disagree"
    )

if errors:
    for e in errors:
        print("FAIL:", e, file=sys.stderr)
    sys.exit(1)
print(f"  {len(plugin_names)} plugin(s): manifest + namespace + docs literal ok")
PY

# 4. Install simulation — scaffold a consumer, run setup.sh, exercise the engines.
#    Args: <plugin> <stack> <valid-test-name> <invalid-test-name>.
install_sim() {
  local plugin="$1" stack="$2" vt="$3" it="$4"
  local consumer="$tmp/c-$plugin" cache="$tmp/cache-$plugin"
  mkdir -p "$consumer" "$cache"
  git -C "$consumer" init -q

  cp -R "$root/plugins/$plugin/." "$cache/"
  # Scaffold with the BUNDLED init, not the harness tree's — the plugin must
  # onboard a project without a reference clone (plugin-shipped init).
  if ! python3 "$cache/init.py" "$stack" "$consumer" "mkt-$plugin" "acceptance" "" "claude" marketplace >/dev/null 2>&1; then
    echo "FAIL[$plugin]: bundled init (marketplace) failed" >&2; fail=1; return
  fi
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
  if ! bash "$cache/setup.sh" "$consumer" >/dev/null 2>&1; then
    echo "FAIL[$plugin]: setup.sh re-run (chapter refresh) exited non-zero" >&2; fail=1; return
  fi
  if ! grep -q 'Always use specialized agents' "$consumer/CLAUDE.md"; then
    echo "FAIL[$plugin]: setup.sh did not refresh the Agent Usage chapter from the bundled source" >&2; fail=1; return
  fi

  # setup.sh must ENSURE the .gitignore runtime paths present on every re-run —
  # the upgrade path. Drop a runtime path and add a project ignore, re-run setup,
  # and confirm the path is re-ensured while the project's own line survives (the
  # append-once freeze this replaces would have left the dropped path missing).
  printf 'my-own-secret/\n' >> "$consumer/.gitignore"
  grep -vxF 'scripts/doctor.py' "$consumer/.gitignore" > "$consumer/.gitignore.x" \
    && mv "$consumer/.gitignore.x" "$consumer/.gitignore"
  if ! bash "$cache/setup.sh" "$consumer" >/dev/null 2>&1; then
    echo "FAIL[$plugin]: setup.sh re-run (gitignore re-ensure) exited non-zero" >&2; fail=1; return
  fi
  if ! grep -qxF 'scripts/doctor.py' "$consumer/.gitignore"; then
    echo "FAIL[$plugin]: setup.sh did not re-ensure a dropped runtime path (upgrade freeze)" >&2; fail=1; return
  fi
  if [ "$(grep -cxF 'my-own-secret/' "$consumer/.gitignore" || true)" != 1 ]; then
    echo "FAIL[$plugin]: setup.sh lost or duplicated a project .gitignore line" >&2; fail=1; return
  fi

  # engines present and gitignored; project-owned files stay tracked.
  if ! ( cd "$consumer"
    for f in scripts/handoff.py scripts/doctor.py schemas/scratch/prd-entry.schema.json; do
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
  if ! dout="$( cd "$consumer" && python3 scripts/doctor.py check 2>&1 )"; then
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

note "install simulation (go + spring + generic)"
install_sim agent-team-go          go               TestSmokePasses    notATestName
install_sim agent-team-spring-boot java-spring-boot shouldComputeTotal BadStart
# generic's skeleton floor is ^.+$ (any non-empty name), so the empty string
# is the one invalid probe it can reject.
install_sim agent-team-generic     generic          runs_end_to_end    ""

# 5. Channel guardrail — a target declaring another channel gets the advisory
#    WARNING before install and verify. The vendored suites enforce channel
#    invariants inside the target, so setup fails on such a tree; the warning,
#    not the suite failure, must name the actual cause. Reuses the plugin
#    cache install_sim agent-team-generic created above.
note "channel guardrail (mis-declared target warns before verify)"
mis="$tmp/c-misdeclared"
mkdir -p "$mis"
git -C "$mis" init -q
if ! python3 "$harness/init.py" generic "$mis" mkt-mis "acceptance" "" claude copy >/dev/null 2>&1; then
  echo "FAIL[guardrail]: init (copy) failed" >&2; fail=1
elif serr="$(bash "$tmp/cache-agent-team-generic/setup.sh" "$mis" 2>&1 >/dev/null)"; then
  echo "FAIL[guardrail]: setup.sh succeeded on a copy-declared target" >&2; fail=1
elif ! printf '%s' "$serr" | grep -q 'declares channel = "copy"'; then
  echo "FAIL[guardrail]: channel warning did not fire on the mis-declared target" >&2; fail=1
else
  echo "  [guardrail] warning fired, setup failed loud"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS test-marketplace: manifest, namespace, install all green"
else
  echo "FAIL test-marketplace: see failures above" >&2
  exit 1
fi
