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

Before invoking reviewers, all checks must pass.

### Required Checks

| Check | Command | What It Verifies |
|---|---|---|
| Build | `./gradlew build` | Project compiles; runs `check` (tests, format check) |
| Test | `./gradlew test` | All tests pass |
| Format | `./gradlew checkJavaFormat` | Code follows google-java-format |
| Handoff log | `python3 scripts/handoff.py validate` | Every record in `.scratch/handoff.jsonl` parses and passes its schema — a raw write that corrupted the log fails here, on every tool. A failure appends a `build-failure` with `failed_check: "handoff-log"`. Absent log (no pipeline work yet): the check passes vacuously. |
| Autofix audit | `python3 scripts/handoff.py audit-autofix` (procedure below) | Every `design-doc-autofix` and `prd-autofix` record stays within bounds; every uncommitted change to a design-doc path is covered by a `design-doc-autofix` or `design-block` record since last commit. |

### Autofix Audit Procedure

Run this before declaring the gate passed, before appending `build-pass`:

```bash
python3 scripts/handoff.py audit-autofix
```

The command executes the audit mechanically; the protocol's prose home is `handoff-routing` § Root-Applied Autofix on Doc Paths. The audit is log-global — a record under any slice is audited. Step 1 re-validates every autofix record not superseded by its own slice's latest owning-expert record — a `design-doc-autofix` by a later `design-block`, a `prd-autofix` by a later `prd-entry`. The checks: eligible path per record type, eligible category, the 5-line/200-char caps, no heading/anchor/REQ-ID/code-fence/link-target change, `new_content` byte-identical to `source_finding.fix`. Step 2 confirms every uncommitted design-doc change is covered by a `design-doc-autofix` or `design-block` record newer than the last commit. The scan is design-doc-scoped by decision — `docs/prd.md` stays outside it (the prd-autofix ADR records why).

Exit 0 declares the autofix-audit check green; record the outcome alongside the other quality-gate results. On a non-zero exit do NOT declare gate-pass. Append a `build-failure` record with `failed_check: "autofix-audit"`, its `error_output` carrying the command's stderr. Set `abort_reason` by the failing record type: `"design-mismatch"` for a `design-doc-autofix` failure or an uncovered design-doc edit; `"prd-mismatch"` for a `prd-autofix` failure. When both classes fail, abort `"design-mismatch"` first — the re-run surfaces the PRD failures. Build-Failure Recovery's abort short-circuit routes the record to the owning expert, who reverts or correctly re-applies the change under its own doc ownership. It then appends its superseding record — a `design-block` with `supersedes_record_at`, or a `prd-entry` — the substantive record that closes its dispatch and restarts the gate. Records at or before that superseding record are superseded on the re-run; the supersession is what terminates the audit loop. Never author a `review-feedback` record — its schema admits reviewer authors only.

### Fix Formatting

```bash
./gradlew formatJava
```

Formats all Java files with google-java-format. Run before `checkJavaFormat`.

## IDE Static Analysis (optional)

When an IDE semantic oracle is available, run its static-analysis pre-check on the diff before declaring the gate passed: inspection **errors** fail the gate (treat like a compile error); **warnings** seed self-review findings. Accelerator only — `./gradlew build && ./gradlew test && ./gradlew checkJavaFormat` stays authoritative, and a client without an oracle relies on the Gradle checks above. Procedure, error/warning classification, and the stale-index caveat live in the `intellij-idea` skill. Report this pre-check honestly: claim it only if you actually invoked the `mcp__idea__*` tools this run (see `intellij-idea` § Report only checks you actually ran). An un-run pre-check is reported as "not run / IDE not consulted", never as clean.

## Configuration Sync

After implementing a feature that adds or changes configuration properties, verify:

- [ ] New properties appear in `application.yml`
- [ ] `@ConfigurationProperties` record updated if needed
- [ ] prd.md configuration table updated (if user-facing property)
- [ ] Default values consistent across all locations

## Completion Criteria

A feature is complete when:

- [ ] All TDD cycles finished
- [ ] Self-review pass complete (see `tdd-workflow` § Self-Review Pass — a clause walk, not a record)
- [ ] All tests pass (`./gradlew test`)
- [ ] IDE static-analysis pre-check clean on touched files — check this box only if the `mcp__idea__*` tools were actually invoked this run; otherwise mark it "n/a (IDE not consulted)" (see "IDE Static Analysis" above)
- [ ] Code formatted (`./gradlew formatJava`)
- [ ] Format check passes (`./gradlew checkJavaFormat`)
- [ ] Project builds (`./gradlew build`)
- [ ] Handoff log validates (`python3 scripts/handoff.py validate`; skip when `.scratch/handoff.jsonl` does not exist)
- [ ] `build-pass` carries `gate_checks_run` naming the check verbs that ran (schema-required, min one item) — the evidence the reviewer fan-out gates on
- [ ] Review plan emitted after `build-pass` (`python3 scripts/grading.py review-plan --feature <req_id>`) — names the roster for this review pass; see `review-workflow` § Risk-Proportional Roster
- [ ] Autofix audit passes (see "Autofix Audit Procedure" above)
- [ ] Configuration synced (if config changed)
- [ ] All reviewers in the roster approve (four-reviewer floor plus any declared extras)
- [ ] No pending escalations (or human approved)

## Stop at done

Once every box above is checked, stop. Polish past the bar — extra refactors, additional tests for the same behavior, prose tightening on a passing PR — spends tokens without raising quality and is explicitly out of scope. The nine-clause bar is defined across `.claude/skills/tdd-workflow/tdd-principles.md`, `docs/testing-principles.md`, `docs/architecture-principles.md`, and `docs/security-principles.md`, with the canonical slug list in the `review-workflow` skill's `reference.md` § Quality-Bar Clause Mapping; if the diff meets the nine clauses, the work is done.
