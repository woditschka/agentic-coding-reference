#!/usr/bin/env bash
# review-survey: the deterministic measurements the /review-harness skill's
# five research agents anchor on. One script so every run (and every agent
# prompt) sees the same numbers — inconsistent re-derivation skews the
# synthesis. Judgment (angles, findings, dispositions) stays in the skill.
#
#   harness/review-survey.sh
#
# Sections: word sizes per doc surface, 6-month churn per file (samples/ and
# plugins/ excluded), and per-file cross-stack overlap line counts.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== sizes (words) =="
for glob in "docs" "harness/core/.claude/agents" "harness/core/.claude/skills" \
            "harness/stacks/go/.claude" ".claude/skills"; do
  total=0
  count=0
  while IFS= read -r -d '' f; do
    w=$(wc -w <"$f")
    total=$((total + w))
    count=$((count + 1))
  done < <(find "$glob" -name '*.md' -print0 2>/dev/null)
  printf '  %-38s %6d words in %3d file(s)\n' "$glob" "$total" "$count"
done

echo
echo "== top word counts (single files) =="
# head would EPIPE the upstream sort under pipefail; capture, then slice.
sizes=$(find docs harness/core/.claude .claude/skills -name '*.md' -print0 2>/dev/null \
  | xargs -0 wc -w | sort -rn)
sed -n '1,16p' <<<"$sizes" | sed 's/^/  /'

echo
echo "== churn: commits touching each file, last 6 months (samples/, plugins/ excluded) =="
# The pre-move top-level sample dirs (go/, java-spring-boot/, generic/) are
# excluded too: history predating the samples/ move would otherwise dominate
# the top-20 and double-count sample churn as root churn.
churn=$(git log --since="6 months ago" --name-only --pretty=format: -- . \
    ':!samples' ':!plugins' ':!go' ':!java-spring-boot' ':!generic' \
    2>/dev/null | sed '/^$/d' | sort | uniq -c | sort -rn)
sed -n '1,20p' <<<"$churn" | sed 's/^/  /'

echo
echo "== cross-stack overlap (identical lines per shared stack file, via comm) =="
while IFS= read -r f; do
  rel=${f#harness/stacks/go/}
  for other in java-spring-boot generic; do
    peer="harness/stacks/$other/$rel"
    [ -f "$peer" ] || continue
    shared=$(comm -12 <(sort "$f") <(sort "$peer") | wc -l)
    total=$(wc -l <"$f")
    printf '  %-58s go∩%-16s %4d/%4d lines\n' "$rel" "$other" "$shared" "$total"
  done
done < <(find harness/stacks/go -type f \( -name '*.md' -o -name '*.py' -o -name '*.sh' \) | sort)

echo
echo "== recent changes since the last v* tag =="
last_tag=$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null || echo "")
if [ -n "$last_tag" ]; then
  echo "  (since $last_tag)"
  git log --oneline "$last_tag"..HEAD | sed 's/^/  /'
else
  echo "  (no v* tag found)"
fi
