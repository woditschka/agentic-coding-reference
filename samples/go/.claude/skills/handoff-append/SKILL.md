---
name: handoff-append
description: >-
  The writer contract for the handoff log: how every pipeline agent appends
  records to .scratch/handoff.jsonl through scripts/handoff.py.
  Load when producing any handoff record — dispatch-start, a substantive
  record, or a consultation. The routing side lives in handoff-routing.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## The One Sanctioned Write

All writes to `.scratch/handoff.jsonl` go through `scripts/handoff.py` (Python 3 stdlib). Writing the file directly — shell redirection onto it (`>>`, `cat >>`, `echo >>`, `tee`), or a `Write`/`Edit` tool call — is prohibited. It skips validation and corrupts the log: a missing trailing newline glues two records onto one line, and the file stops parsing. Feeding a record to `append` on stdin is distinct from a raw write: a heredoc piped into `append` is the sanctioned input mechanism.

Append the record by piping it to stdin through a **quoted** heredoc — the quotes (`<<'EOF'`) keep the body literal so nothing in the JSON is shell-expanded:

```bash
python3 scripts/handoff.py append <type> <<'EOF'
{"type":"<type>","req_id":"<req-id>","ts":"<iso-8601>","author":"<agent>", …}
EOF
```

**The heredoc must sit directly on the `python3` command, exactly as above.** The command line must *begin* with `python3 scripts/handoff.py append <type>`. Do not wrap it as `cat <<'EOF' | python3 …`, and do not feed the record with `echo …|`, `printf …|`, or `cat file |`. A producer before the pipe makes the command start with `cat`/`echo`/`printf`, which no tool's auto-allow matches — the append then stalls on a permission prompt. The temptation is strongest for large records, where `cat <<'EOF' |` looks convenient. The direct heredoc above is the one shape every tool pre-approves, at any record size.

## Validation and the Receipt

`append` validates the record against `schemas/scratch/<type>.schema.json` before writing. An invalid record is rejected with the schema error — **fix the record, never the file**. Accepted records are written in canonical form: fields in schema declaration order (`type`, `req_id`, `ts`, `author` first, payload next, optional fields last), one record per line, newline-terminated.

On success `append` prints the new record's line number — use it for later `responding_to` and `in_response_to` references.

## Append-Only Discipline

Never edit, reorder, or delete a prior record. If a prior record has a mistake, append a new record that supersedes it (`supersedes_record_at` where the schema carries it, a fresh record otherwise). Prior records are the audit trail; the **latest record per `(req_id, type)`** is the active state.

## Writer Commands

| Operation | Command |
|---|---|
| Append a record | `python3 scripts/handoff.py append <type>` — record JSON on stdin (canonical form above) |
| Next retry counter | `python3 scripts/handoff.py next-retry --req-id <id>` — build-failure records for the `req_id` after the latest `design-block` line, plus one |
| Anchor a response (`responding_to`, `in_response_to`) | `python3 scripts/handoff.py latest --type <type> [--req-id <id>]` |
| Whole-file check | `python3 scripts/handoff.py validate` |
| Human inspection | `python3 scripts/handoff.py show [--last N]` |

Reading the whole log with the `Read` tool for context is fine. Routing decisions belong to the router — `route` and the coordinator (`handoff-routing` skill); writers read to anchor their own records, not to route.

Exit codes: 0 success, 1 validation or parse error, 2 usage error, 3 no matching record. The `grader-features` record is the one exception to the append command: `score-change.py extract` appends it directly under its own determinism contract.

## Permission Setup (One-Time, Per Tool)

`append` is the pipeline's only sanctioned write, and it is safe — append-only, schema-validated, scoped to the log. Each tool's permission layer must pre-approve it so routine appends do not prompt; the agent's tool grant alone does not.

- **Claude Code** — pre-approved by a committed `PreToolUse` hook (`.claude/hooks/handoff-allow.sh`, registered in `.claude/settings.json`). It auto-allows `python3 scripts/handoff.py` invocations and defers everything else; a prefix allow-rule cannot cover the heredoc form, so the hook is required. A companion guard (`.claude/hooks/handoff-log-guard.sh`) denies raw writes to the log — `Write`/`Edit` tool calls on it and shell redirection onto it.
- **OpenCode** — pipeline agents already declare `bash: allow`, which runs the command without a prompt; no extra setup.
- **Copilot CLI** — launch with `--allow-tool 'shell(python3:*)'`, or add a `preToolUse` hook to its user `config.json`.
- **Junie** — add an allowlist rule `{ "pattern": "python3 scripts/handoff.py **", "action": "allow" }` to `~/.junie/allowlist.json`, or run in brave mode.

Only Claude Code supports a committed deny on raw writes; the other tools shape the path by pre-approving the sanctioned form alone. The cross-tool backstop is deterministic detection: the quality gate runs `python3 scripts/handoff.py validate` (see the `code-quality-gate` skill), so a raw write that corrupts the log fails the gate before review on every tool.
