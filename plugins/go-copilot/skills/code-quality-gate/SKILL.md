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

Before invoking reviewers, all checks must pass. Run `make ci` to execute the full pipeline.

### Required Checks

| Check | Command | What It Verifies |
|---|---|---|
| Tidy | `go mod tidy` | Dependencies are clean |
| Format | `go fmt ./...` | Code is formatted |
| Vet | `go vet ./...` | Common mistakes caught |
| Lint | `make lint` | golangci-lint rules pass |
| Deps | `make deps-check` | No prohibited dependencies |
| Test | `go test ./...` | All tests pass |
| Build | `go build -o bin/reference` | Binary compiles |
| Handoff log | `python3 scripts/handoff.py validate` | Every record in `.scratch/handoff.jsonl` parses and passes its schema — a raw write that corrupted the log fails here, on every tool. A failure appends a `build-failure` with `failed_check: "handoff-log"`. Absent log (no pipeline work yet): the check passes vacuously. |
| Autofix audit | `python3 scripts/handoff.py audit-autofix` (procedure below) | Every `design-doc-autofix` record stays within bounds; every uncommitted change to a design-doc path is covered by a `design-doc-autofix` or `design-block` record since last commit. |

### Autofix Audit Procedure

Run this before declaring the gate passed, before appending `build-pass`:

```bash
python3 scripts/handoff.py audit-autofix
```

The command executes the audit mechanically; the protocol's prose home is `handoff-routing` § Root-Applied Autofix on Design Docs. The audit is log-global — a record under any slice is audited. Step 1 re-validates every `design-doc-autofix` record not superseded by its own slice's latest `design-block`: eligible path, eligible category, the 5-line/200-char caps, no heading/anchor/REQ-ID/code-fence/link-target change, `new_content` byte-identical to `source_finding.fix`. Step 2 confirms every uncommitted design-doc change is covered by a `design-doc-autofix` or `design-block` record newer than the last commit.

Exit 0 declares the autofix-audit check green; record the outcome alongside the other quality-gate results. On a non-zero exit do NOT declare gate-pass. Append a `build-failure` record with `failed_check: "autofix-audit"` and `abort_reason: "design-mismatch"`, its `error_output` carrying the command's stderr. Build-Failure Recovery's abort short-circuit routes it to system-design-expert. The expert reverts or correctly re-applies the change under its own doc ownership. It then appends a `design-block` with `supersedes_record_at` covering the affected path — the substantive record that closes its dispatch and restarts the gate. Records at or before that `design-block` are superseded on the re-run; the supersession is what terminates the audit loop. Never author a `review-feedback` record — its schema admits reviewer authors only.

### Optional Checks

| Check | Command | When Required |
|---|---|---|
| Race detector | `go test -race ./...` | When concurrency is involved (requires gcc) |
| Container build | `make podman-build` | When project uses containers |

## IDE Static Analysis (optional)

When an IDE semantic oracle is available, run its static-analysis pre-check on the diff before declaring the gate passed: inspection **errors** fail the gate (treat like a compile error); **warnings** seed self-review findings. Accelerator only — `go vet ./... && make lint && go test ./... && go build -o bin/reference` stays authoritative, and a client without an oracle relies on the checks above. Procedure, error/warning classification, and the stale-index caveat live in the `goland` skill. Report this pre-check honestly: claim it only if you actually invoked the `mcp__goland__*` tools this run (see `goland` § Report only checks you actually ran). An un-run pre-check is reported as "not run / IDE not consulted", never as clean.

## Completion Criteria

A feature is complete when:

- [ ] All TDD cycles finished
- [ ] Self-review pass complete (see `tdd-workflow` § Self-Review Pass — a clause walk, not a record)
- [ ] All tests pass (`go test ./...`)
- [ ] IDE static-analysis pre-check clean on touched files — check this box only if the `mcp__goland__*` tools were actually invoked this run; otherwise mark it "n/a (IDE not consulted)" (see "IDE Static Analysis" above)
- [ ] Code formatted (`go fmt ./...`)
- [ ] Project builds (`go build -o bin/reference`)
- [ ] Lint passes (`make lint`)
- [ ] Dependency policy passes (`make deps-check`)
- [ ] Handoff log validates (`python3 scripts/handoff.py validate`; skip when `.scratch/handoff.jsonl` does not exist)
- [ ] `build-pass` carries `gate_checks_run` naming the check verbs that ran (schema-required, min one item) — the evidence the reviewer fan-out gates on
- [ ] Review plan emitted after `build-pass` (`python3 scripts/score-change.py review-plan --feature <req_id>`) — names the roster for this review pass; see `review-workflow` § Risk-Proportional Roster
- [ ] Autofix audit passes (see "Autofix Audit Procedure" above)
- [ ] Config example reflects any new/changed config fields (if applicable)
- [ ] All reviewers in the roster approve (four-reviewer floor plus any declared extras)
- [ ] No pending escalations (or human approved)

## Stop at done

Once every box above is checked, stop. Polish past the bar — extra refactors, additional tests for the same behavior, prose tightening on a passing PR — spends tokens without raising quality and is explicitly out of scope. The nine-clause bar is defined across `.claude/skills/tdd-workflow/tdd-principles.md`, `docs/testing-principles.md`, `docs/architecture-principles.md`, and `docs/security-principles.md`, with the canonical slug list in the `review-workflow` skill's `reference.md` § Quality-Bar Clause Mapping; if the diff meets the nine clauses, the work is done.
