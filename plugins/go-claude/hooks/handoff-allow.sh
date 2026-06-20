#!/usr/bin/env bash
# PreToolUse(Bash) hook — auto-allow the sanctioned handoff-log tool, defer everything else.
#
# The pipeline's only sanctioned write to .scratch/handoff.jsonl is `python3
# scripts/handoff.py append`, fed its record on stdin (a quoted heredoc). The
# permission layer cannot pre-approve that form with a prefix allow-rule: a
# heredoc embeds the record content, so every append is a new command string no
# rule matches, and "always allow" saves it verbatim. The result is flaky
# permission prompts on a routine, safe, append-only operation. This hook closes
# that gap by inspecting the command and AUTO-ALLOWING it iff it is solely a
# handoff.py invocation — covering the read queries and the heredoc append alike.
#
# Safety model. The hook only ever ALLOWS or DEFERS; it never denies, so it can
# never block another command. It allows ONLY when the command is exclusively a
# handoff.py call: the command line must start with `python3 scripts/handoff.py`
# and carry no shell metacharacter that could chain, redirect to a file, or
# substitute another command ($ ` ; & | > ( )). The single exception is `<<` for
# a heredoc, whose delimiter MUST be quoted (`<<'EOF'`) so the body is inert
# data, and whose body must be terminated with nothing following the delimiter —
# no trailing command can ride after the record. Anything else DEFERS (exit 0,
# no decision) to the normal permission rules, so non-handoff bash is unaffected
# and a malformed or unexpected handoff command merely prompts as before.
#
# Fail safe: a missing jq, malformed stdin, or empty command all DEFER. The hook
# widens nothing on failure — the worst case is the prompt the pipeline had
# before this hook existed. Like the SendMessage hook, it is a convenience
# backstop, not a sole control; the whole-tool Bash grant and normal permission
# rules remain in force for everything it does not explicitly allow.

defer() { exit 0; }  # no decision -> fall through to normal permission rules
allow() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}\n'
  exit 0
}

command -v jq >/dev/null 2>&1 || defer

payload=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null)
[ -n "$cmd" ] || defer

# Split the first physical line (the command) from any heredoc body that follows.
first=${cmd%%$'\n'*}
rest=""
[ "$first" != "$cmd" ] && rest=${cmd#*$'\n'}

# Strip leading whitespace from the command line.
first=${first#"${first%%[![:space:]]*}"}

# The command line must carry no chaining / redirection-to-file / substitution
# metacharacter. `<` is the sole exception (heredoc / stdin redirect, both safe).
case "$first" in
  *'$'* | *'`'* | *';'* | *'&'* | *'|'* | *'>'* | *'('* | *')'*) defer ;;
esac

# The command must be exactly a handoff.py invocation.
case "$first" in
  'python3 scripts/handoff.py '*) : ;;
  *) defer ;;
esac

if [[ "$first" == *'<<'* ]]; then
  # Heredoc append. The only safe heredoc is the canonical append form with the
  # redirection operator as the whole tail of the command line: a quoted
  # delimiter at the very end, after a bare type token, with no other quoting or
  # text. The reason is subtle but decisive — `<<` is a heredoc operator ONLY
  # when unquoted. A `<<'EOF'` hidden inside a quoted argument is a literal
  # string to the shell, so the lines that follow it are real commands, not an
  # inert body. Telling the two apart by substring is impossible; only a strict
  # whole-line match guarantees a genuine heredoc. Anything else defers.
  printf '%s' "$first" | grep -qE "^python3 scripts/handoff\.py append [A-Za-z0-9_-]+ <<('[A-Za-z_][A-Za-z0-9_]*'|\"[A-Za-z_][A-Za-z0-9_]*\")$" || defer
  delim=$(printf '%s' "$first" | sed -E "s/.*<<['\"]//; s/['\"]$//")
  # Even a genuine heredoc runs any line after the closing delimiter, so the body
  # must end at the delimiter line with nothing executable following it.
  awk -v d="$delim" '
    seen { if ($0 ~ /[^ \t]/) extra=1; next }
    $0 == d { seen=1 }
    END { if (!seen || extra) exit 1 }
  ' <<<"$rest" || defer
else
  # No heredoc: there must be no trailing physical line carrying another command.
  if [ -n "$rest" ] && printf '%s' "$rest" | grep -q '[^[:space:]]'; then defer; fi
fi

allow
