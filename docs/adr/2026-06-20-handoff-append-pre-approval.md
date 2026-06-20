# The Handoff Append Is Pre-Approved Per Tool, via a Hook on Claude Code

**Status:** Accepted

## Context

Every pipeline agent appends to `.scratch/handoff.jsonl` through `python3 scripts/handoff.py append`, fed its record on stdin (see [handoff log access tool](2026-06-11-handoff-log-access-tool.md)). The record is JSON, so the natural invocation is a quoted heredoc. Agents hit intermittent permission denials on this routine write.

The cause is a layer confusion. An agent's tool grant (Claude Code `tools: [Bash]`, Copilot `runTerminalCommand`, Junie `Bash`) governs tool *availability*, not per-command *approval*. Approval is a separate layer that still prompts. The append therefore prompts, and in a denying mode the prompt fails — but only on the write. The read queries (`latest`, `validate`) are plain commands a prefix rule matches once. The heredoc append embeds the record content, so every append is a new string no prefix rule matches at all.

The four tools do not share one permission mechanism. Claude Code, Copilot, and Junie prompt by default, with no per-command bash gating in agent frontmatter. OpenCode pipeline agents already declare `bash: allow`, a permission grant that runs the command without a prompt.

## Options Considered

1. **Broaden the agent frontmatter.** Rejected: no tool expresses a per-command bash allow in frontmatter, and the whole-tool grant is what already failed.
2. **Ship a Claude Code prefix allow-rule.** Rejected: prefix rules do not match the heredoc append, so it fixes the read queries and not the failing write.
3. **Change the append to a content-free file argument.** Rejected: it needs a file-write tool to stage the record, which Copilot reviewers lack, so it cannot be uniform.
4. **A Claude Code `PreToolUse` hook that inspects the command and pre-approves it.** A hook decision bypasses prefix matching, so it covers the heredoc on any form, and it fires for dispatched subagents.

## Decision

**The handoff append is pre-approved by each tool's own permission layer, not by the agent grant. Claude Code carries a committed `PreToolUse` hook; the other tools use their native mechanism.**

- **Claude Code: a hook.** `.claude/hooks/handoff-allow.sh`, registered in `.claude/settings.json` beside the [continue-only resume hook](2026-06-10-continue-only-resume.md), auto-allows a command that is solely a `python3 scripts/handoff.py` invocation. It defers everything else to normal permission rules. It only ever allows or defers, never denies, so it widens nothing it does not explicitly recognize. It allows the heredoc form only with a quoted delimiter and a terminated body with no trailing command; anything ambiguous defers. The hook is materialized to the samples and shipped in the marketplace plugin.
- **OpenCode: nothing.** Pipeline agents already declare `bash: allow`, which runs the command without a prompt.
- **Copilot and Junie: documented one-time setup.** Both keep command-approval in user space and ignore project-committed approval configs, so the harness cannot ship their fix. The `pipeline-handoff` skill § Log Access documents the launch flag (Copilot `--allow-tool 'shell(python3:*)'`) and the allowlist rule (Junie `~/.junie/allowlist.json`).
- **Registration is project-owned; the doctor gates it.** The hook *script* is harness-owned runtime, but its registration is a `PreToolUse` matcher in project-owned `.claude/settings.json`. `/init` scaffolds it for a greenfield project, but `/materialize` replaces only runtime — so an upgrade delivers the hook without wiring it. The doctor's `hook-registration` check fails on a delivered-but-unregistered hook, and `/materialize` proposes the additive matcher on consent. The split is deliberate: `settings.json` is the user's to own, so the harness gates the invariant rather than silently editing it.

The append stays a quoted-heredoc write to `handoff.py` stdin — the one form that needs no file-write tool, so every agent including read-only reviewers can use it.

## Consequences

**Positive:**
- Routine appends stop prompting under Claude Code's default and accept-edits modes, with no loss of gating on any other command.
- The fix matches each tool's design instead of forcing one mechanism across four permission models.
- The hook is a scoped pre-approval of one safe, append-only, schema-validated command — not a blanket bypass.

**Negative:**
- Copilot and Junie coverage is a documented manual step, not a committed file, because those tools place command-approval in user space.
- On the copy and manifest channels an upgrade delivers the hook script but not its registration, which lives in project-owned `settings.json`. The doctor's `hook-registration` check and the `/materialize` proposal close the gap, but it is a check-and-consent step, not automatic.
- The hook encodes a small command-parsing rule; a form it does not recognize defers to a prompt rather than failing, which is the safe direction but not zero-friction.
