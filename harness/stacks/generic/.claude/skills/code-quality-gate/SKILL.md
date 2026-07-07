---
name: code-quality-gate
description: >-
  Build, test, format, and lint requirements that must pass before
  code review. Load when checking implementation completeness or
  running the quality gate.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/testing-principles.md
  - docs/architecture-principles.md
metadata:
  version: "1.0"
  author: team
---

## Quality Gate

Before invoking reviewers, all checks must pass. Run `scripts/gate.sh verify` to execute the full gate. It runs every lifecycle verb in order through the project's bindings in `scripts/stack.sh`. The pipeline speaks only in these verbs, never in tool names.

### Required Checks

| Verb | Invocation | What It Verifies |
|---|---|---|
| Deps | `scripts/gate.sh deps` | Dependencies are tidy; no prohibited or unused entries |
| Format | `scripts/gate.sh format` | Code is formatted (check mode, not rewrite) |
| Lint | `scripts/gate.sh lint` | Linters and static analysis pass |
| Test | `scripts/gate.sh test` | All tests pass |
| Build | `scripts/gate.sh build` | The artifact compiles or assembles |
| Handoff log | `python3 scripts/handoff.py validate` | Every record in `.scratch/handoff.jsonl` parses and passes its schema — a raw write that corrupted the log fails here, on every tool. A failure appends a `build-failure` with `failed_check: "handoff-log"`. Absent log (no pipeline work yet): the check passes vacuously. |
| Autofix audit | — (procedure below) | Every `design-doc-autofix` record stays within bounds; every uncommitted change to a design-doc path is covered by a `design-doc-autofix` or `design-block` record since last commit. |

A verb with no binding in `scripts/stack.sh` fails by design — it is not implemented yet, and a half-bound stack must not pass a gate it has not satisfied. Bind each verb to this stack's real commands in `scripts/stack.sh`; a verb that genuinely does not apply is an explicit `return 0` no-op there, never a silent skip.

### Autofix Audit Procedure

Run this before declaring the gate passed. The audit enforces the protocol in `handoff-routing` § Root-Applied Autofix on Design Docs. No script — the feature-implementer runs these checks as part of the quality gate, before appending `build-pass`.

**Step 1 — Static re-validation of autofix records.** Read `.scratch/handoff.jsonl`. For each record where `type == "design-doc-autofix"` appended after the latest `design-block` for the active `req_id`, verify:

| Check | Rule |
|---|---|
| File scope | `file` matches one of the design-doc paths declared in the `document-writing` skill's `review-checks.md` § Autofix on Design-Doc Paths (`docs/system-design.md` or any `docs/adr/*.md`). |
| Category | `category` is `writing-standards` or `structural`. Any other value fails. |
| Size bounds | `lines_changed` ≤ 5 AND `chars_changed` ≤ 200. |
| No heading touch | Neither `old_content` nor `new_content` contains a `## ` line. |
| No anchor change | `<a id="...">` values in `old_content` are identical to those in `new_content`. |
| No REQ-ID change | REQ-ID tokens (regex `REQ-[A-Z]+-\d{3}`) in `old_content` are identical to those in `new_content`. |
| No code-fence touch | Neither `old_content` nor `new_content` contains a `` ``` `` line. |
| No link-target change | Markdown link targets (the URL inside `](...)`) in `old_content` are identical to those in `new_content`. |
| Verbatim fix | `new_content` equals `source_finding.fix` byte-for-byte. |

Any failure: do NOT declare gate-pass. Append a `build-failure` record with `failed_check: "autofix-audit"` and `abort_reason: "design-mismatch"`, its `error_output` naming the failing record by `handoff.jsonl` line number. Build-Failure Recovery's abort short-circuit routes it to system-design-expert. The expert reverts or correctly re-applies the change under its own doc ownership. It then appends a `design-block` with `supersedes_record_at` covering the affected path — the substantive record that closes its dispatch and restarts the gate. Records at or before that `design-block` are superseded on the re-run; the supersession is what terminates the audit loop. Never author a `review-feedback` record — its schema admits reviewer authors only.

**Step 2 — Direct-edit detection.** Run `git diff --name-only HEAD -- docs/system-design.md docs/adr/`. For each path returned:

- Read `.scratch/handoff.jsonl`. Confirm at least one of the following exists with `ts` later than the last commit's timestamp (`git log -1 --format=%cI`):
  - A `design-doc-autofix` record whose `file` equals the path, or
  - A `design-block` record listing the path in `primary_paths` or `supporting_paths`.
- If a path is dirty but no covering record exists, the gate fails — the change was made outside the protocol. Append the same `failed_check: "autofix-audit"` / `abort_reason: "design-mismatch"` `build-failure` naming the dirty path; system-design-expert reconciles it — revert or re-apply — closed by the same superseding `design-block`.

**Step 3 — Result.** Only declare the autofix-audit check green when Steps 1 and 2 both pass. Record the outcome alongside the other quality-gate results.

### Optional Checks

A stack may need checks beyond the five verbs — a race/concurrency detector, a container build, a vulnerability scan. Bind each inside the relevant verb (for example, fold a race detector into `verb_test`) or document it in `CLAUDE.md` as a project-specific step. Keep the verb surface stable; the pipeline calls only the verbs above.

## Completion Criteria

A feature is complete when:

- [ ] All TDD cycles finished
- [ ] Self-review pass complete (see `tdd-workflow` § Self-Review Pass — a clause walk, not a record)
- [ ] The full gate passes (`scripts/gate.sh verify`) — every lifecycle verb green
- [ ] Handoff log validates (`python3 scripts/handoff.py validate`; skip when `.scratch/handoff.jsonl` does not exist)
- [ ] Autofix audit passes (see "Autofix Audit Procedure" above)
- [ ] Config example reflects any new/changed config fields (if applicable)
- [ ] All reviewers in the roster approve (four-reviewer floor plus any declared extras)
- [ ] No pending escalations (or human approved)

## Stop at done

Once every box above is checked, stop. Polish past the bar — extra refactors, additional tests for the same behavior, prose tightening on a passing PR — spends tokens without raising quality and is explicitly out of scope. The nine-clause bar is defined across `.claude/skills/tdd-workflow/tdd-principles.md`, `docs/testing-principles.md`, `docs/architecture-principles.md`, and `docs/security-principles.md`, with the canonical slug list in `review-workflow` § Quality-Bar Clause Mapping; if the diff meets the nine clauses, the work is done.
