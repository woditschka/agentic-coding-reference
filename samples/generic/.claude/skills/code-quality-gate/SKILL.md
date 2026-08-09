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
| Autofix audit | `python3 scripts/handoff.py audit-autofix` (procedure below) | Every `design-doc-autofix` and `prd-autofix` record stays within bounds; every uncommitted change to a design-doc path is covered by a `design-doc-autofix` or `design-block` record since last commit. |

A verb with no binding in `scripts/stack.sh` fails by design — it is not implemented yet, and a half-bound stack must not pass a gate it has not satisfied. Bind each verb to this stack's real commands in `scripts/stack.sh`; a verb that genuinely does not apply is an explicit `return 0` no-op there, never a silent skip.

### Autofix Audit Procedure

Run this before declaring the gate passed, before appending `build-pass`:

```bash
python3 scripts/handoff.py audit-autofix
```

The command executes the audit mechanically; the protocol's prose home is `handoff-routing` § Root-Applied Autofix on Doc Paths. The audit is log-global — a record under any slice is audited. Step 1 re-validates every autofix record not superseded by its own slice's latest owning-expert record — a `design-doc-autofix` by a later `design-block`, a `prd-autofix` by a later `prd-entry`. The checks: eligible path per record type, eligible category, the 5-line/200-char caps, no heading/anchor/REQ-ID/code-fence/link-target change, `new_content` byte-identical to `source_finding.fix`. Step 2 confirms every uncommitted design-doc change is covered by a `design-doc-autofix` or `design-block` record newer than the last commit. The scan is design-doc-scoped by decision — `docs/prd.md` has its own `prd-autofix` trail and stays outside it.

Exit 0 declares the autofix-audit check green; record the outcome alongside the other quality-gate results. On a non-zero exit do NOT declare gate-pass. Append a `build-failure` record with `failed_check: "autofix-audit"`, its `error_output` carrying the command's stderr. Set `abort_reason` by the failing record type: `"design-mismatch"` for a `design-doc-autofix` failure or an uncovered design-doc edit; `"prd-mismatch"` for a `prd-autofix` failure. When both classes fail, abort `"design-mismatch"` first — the re-run surfaces the PRD failures. Build-Failure Recovery's abort short-circuit routes the record to the owning expert, who reverts or correctly re-applies the change under its own doc ownership. It then appends its superseding record — a `design-block` with `supersedes_record_at`, or a `prd-entry` — the substantive record that closes its dispatch and restarts the gate. Records at or before that superseding record are superseded on the re-run; the supersession is what terminates the audit loop. Never author a `review-feedback` record — its schema admits reviewer authors only.

### Optional Checks

A stack may need checks beyond the five verbs — a race/concurrency detector, a container build, a vulnerability scan. Bind each inside the relevant verb (for example, fold a race detector into `verb_test`) or document it in `CLAUDE.md` as a project-specific step. Keep the verb surface stable; the pipeline calls only the verbs above.

## Completion Criteria

A feature is complete when:

- [ ] All TDD cycles finished
- [ ] Self-review pass complete (see `tdd-workflow` § Self-Review Pass — a clause walk, not a record)
- [ ] The full gate passes (`scripts/gate.sh verify`) — every lifecycle verb green
- [ ] Handoff log validates (`python3 scripts/handoff.py validate`; skip when `.scratch/handoff.jsonl` does not exist)
- [ ] `build-pass` carries `gate_checks_run` naming the check verbs that ran (schema-required, min one item) — the evidence the reviewer fan-out gates on
- [ ] Review plan emitted after `build-pass` (`python3 scripts/grading.py review-plan --feature <req_id>`) — names the roster for this review pass; see `review-workflow` § Risk-Proportional Roster
- [ ] Autofix audit passes (see "Autofix Audit Procedure" above)
- [ ] Config example reflects any new/changed config fields (if applicable)
- [ ] All reviewers in the roster approve (four-reviewer floor plus any declared extras)
- [ ] No pending escalations (or human approved)

## Stop at done

Once every box above is checked, stop. Polish past the bar — extra refactors, additional tests for the same behavior, prose tightening on a passing PR — spends tokens without raising quality and is explicitly out of scope. The nine-clause bar is defined across `.claude/skills/tdd-workflow/tdd-principles.md`, `docs/testing-principles.md`, `docs/architecture-principles.md`, and `docs/security-principles.md`, with the canonical slug list in the `review-workflow` skill's `reference.md` § Quality-Bar Clause Mapping; if the diff meets the nine clauses, the work is done.
