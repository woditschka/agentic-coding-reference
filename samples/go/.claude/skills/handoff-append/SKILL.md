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
  version: "1.1"
  author: team
---

The scratch-directory reference — the `.scratch/` layout, the record roster with producers and schemas, the templates, and the rules — lives in [`scratch-contract.md`](scratch-contract.md).

## The One Sanctioned Write

All writes to `.scratch/handoff.jsonl` go through `scripts/handoff.py` (Python 3 stdlib). Writing the file directly — shell redirection onto it (`>>`, `cat >>`, `echo >>`, `tee`), or a file-editing tool call — is prohibited. It skips validation and corrupts the log: a missing trailing newline glues two records onto one line, and the file stops parsing. Feeding a record to `append` on stdin is distinct from a raw write: a heredoc piped into `append` is the sanctioned input mechanism.

Append the record by piping it to stdin through a **quoted** heredoc — the quotes (`<<'EOF'`) keep the body literal so nothing in the JSON is shell-expanded:

```bash
python3 scripts/handoff.py append <type> <<'EOF'
{"type":"<type>","req_id":"<req-id>","author":"<agent>", …}
EOF
```

**The heredoc must sit directly on the `python3` command, exactly as above.** The command line must *begin* with `python3 scripts/handoff.py append <type>`. Do not wrap it as `cat <<'EOF' | python3 …`, and do not feed the record with `echo …|`, `printf …|`, or `cat file |`. A producer before the pipe makes the command start with `cat`/`echo`/`printf`, which no tool's auto-allow matches — the append then stalls on a permission prompt. The temptation is strongest for large records, where `cat <<'EOF' |` looks convenient. The direct heredoc above is the one shape every tool pre-approves, at any record size.

## Validation and the Receipt

`append` stamps `ts` from the system clock — never compose one; a supplied value is overwritten. Ledger time is wall-clock time by construction, which the board's durations and cost windows depend on. It then validates the stamped record against `schemas/scratch/<type>.schema.json` before writing. An invalid record is rejected with the schema error — **fix the record, never the file**. Accepted records are written in canonical form: fields in schema declaration order (`type`, `req_id`, `ts`, `author` first, payload next, optional fields last), one record per line, newline-terminated.

On success `append` prints the new record's line number — use it for later `responding_to` and `in_response_to` references.

## Append-Only Discipline

Never edit, reorder, or delete a prior record. If a prior record has a mistake, append a new record that supersedes it (`supersedes_record_at` where the schema carries it, a fresh record otherwise). Prior records are the audit trail; the **latest record per `(req_id, type)`** is the active state.

## Dispatch-Start (First Tool Call)

Every dispatched project-defined agent except `pipeline-coordinator` and the terminal `change-grader` appends one `dispatch-start` record as its **first tool call**, right after its Scoping Pre-Check sentences (where the dispatch runs one). Skipping it leaves the harness blind to the dispatch's outcome: the record is the start half of the dispatch-event contract, and truncation detection keys on it (`handoff-routing` skill § Dispatch Truncation Detection).

```bash
python3 scripts/handoff.py append dispatch-start <<'EOF'
{"type":"dispatch-start","req_id":"<active req>","author":"<your agent name>","responding_to":[<line>]}
EOF
```

`author` is your agent name. `responding_to` lists the 1-indexed line number(s) of the inbound record(s) the dispatch responds to — your agent definition names the typical anchor; a fresh feature dispatch anchors to its `intake-decision` line, and `[0]` is only for a dispatch with no inbound record at all.

## Writer Commands

| Operation | Command |
|---|---|
| Append a record | `python3 scripts/handoff.py append <type>` — record JSON on stdin (canonical form above). A `build-pass` append also runs the review-plan engine and echoes its `review-plan: appended …` line; an engine warning leaves the append green (`route` fails closed to the full battery) |
| Next retry counter | `python3 scripts/handoff.py next-retry --req-id <id>` — build-failure records for the `req_id` after the latest `design-block` line, plus one |
| Anchor a response (`responding_to`, `in_response_to`) | `python3 scripts/handoff.py latest --type <type> [--req-id <id>]` |
| Whole-file check | `python3 scripts/handoff.py validate` |
| Human inspection (raw records) | `python3 scripts/handoff.py show [--last N]` |
| Slice board | `python3 scripts/handoff.py view [--req-id <id>]` — the `handoff-board` skill |

Reading the whole log for context is fine. Routing decisions belong to the router — `route` and the coordinator (`handoff-routing` skill); writers read to anchor their own records, not to route.

Exit codes: 0 success, 1 validation or parse error, 2 usage error, 3 no matching record. `view` exits 0 on a missing or dirty log and 3 only for `--req-id` with no records. Two engine-authored records bypass the append command under their own determinism contracts: `grading.py extract` appends `grader-features`, and `grading.py review-plan` appends the engine's `review-plan`. Two records are root-appended on the human's behalf: the `consultation-response` closing a `human-consultation` halt (`author: "human"`, `in_response_to` the request's line), and the `intake-decision` recording an intake exit (`author: "human"`, the `intake` skill's protocol). Both transcribe words the human actually supplied, never text root composed: the response carries the human's reply; the intake record carries the request and decisions as stated. A `consultation-response` exists only when a human replied; absent a reply the halt stands.

## Permission Setup (One-Time, Per Tool)

`append` is pre-approved per tool at adoption time — one-time consumer setup, not dispatch-time work; the reference's Adoption Guide § Handoff Append Pre-Approval holds the per-tool table. What holds at runtime: `append` is the only sanctioned write to the log, a raw write is denied (Claude Code hooks) or caught deterministically — the quality gate runs `python3 scripts/handoff.py validate` (see the `code-quality-gate` skill), so a corrupted log fails the gate before review on every tool.
