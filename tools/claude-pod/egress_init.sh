#!/usr/bin/env bash
# egress_init.sh — apply the pod's default-deny egress ruleset (ADR 2026-07-17).
#
# Runs INSIDE the one-shot init container: `--network container:<pod>` with
# NET_ADMIN, as root, before the agent process exists. It resolves the gateway
# in the pod's own namespace, emits the ruleset (egress_rules.py — the tested
# single source of the policy), applies it, and asserts the deny rule landed.
# Any failure exits non-zero; claude-pod warns loudly and the pod still runs.
#
# argv: <gateway-name> [ide-port ...]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd -P)"

gw_name="$1"; shift
# v4 and v6 resolved separately: getent hosts may lead with an AAAA, and the
# emitter needs the IPv4 for the subnet. Every AAAA the name carries becomes a
# v6 drop — an engine publishing one would otherwise bypass the IPv4 deny.
# `|| true`: getent exits non-zero on an unknown name, and set -e would kill
# the script mid-assignment — before the guard below can name the cause.
gw="$(getent ahostsv4 "$gw_name" | awk '{print $1; exit}')" || true
[ -n "$gw" ] || { echo "egress-init: cannot resolve gateway (IPv4): $gw_name" >&2; exit 1; }

rule_args=()
# v4-mapped entries (::ffff:a.b.c.d) are the v4 address again — their traffic
# leaves as IPv4, which the ip rules already deny — so only genuine v6 counts.
while read -r a; do [ -n "$a" ] && rule_args+=(--gateway-ip6 "$a"); done \
  < <(getent ahostsv6 "$gw_name" 2>/dev/null | awk '$1 ~ /:/ && $1 !~ /^::ffff:/ {print $1}' | sort -u)
for p in "$@"; do rule_args+=(--port "$p"); done
python3 "$here/egress_rules.py" --gateway-ip "$gw" ${rule_args[@]+"${rule_args[@]}"} | nft -f -

# Assert the policy is live, not just parsed: the chain must carry a drop.
nft list chain inet pod out | grep -q " drop" || { echo "egress-init: ruleset not active" >&2; exit 1; }

# One line states the whole policy: naming the denied subnet already says
# everything else is untouched.
allowed="DNS"
[ $# -gt 0 ] && allowed="DNS and IDE port $*"
echo "claude-pod: host egress: ${gw%.*}.0/24 denied ($allowed excepted)" >&2
