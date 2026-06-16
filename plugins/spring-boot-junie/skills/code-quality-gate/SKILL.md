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
| Build | `./gradlew build` | Project compiles; runs `check` (tests, format check, `testScripts` and `testHandoffScript` script suites) |
| Test | `./gradlew test` | All tests pass |
| Format | `./gradlew checkJavaFormat` | Code follows google-java-format |
| Autofix audit | — (procedure below) | Every `design-doc-autofix` record stays within bounds; every uncommitted change to a design-doc path is covered by a `design-doc-autofix` or `design-block` record since last commit. |

### Autofix Audit Procedure

Run this before declaring the gate passed. The audit enforces the protocol in `review-checklist` § Root-Applied Autofix on Design Docs. No script — the coordinator runs the checks the same way it follows the validation gates in `pipeline-handoff`.

**Step 1 — Static re-validation of every autofix record.** Read `.scratch/handoff.jsonl`. For each record where `type == "design-doc-autofix"`, verify:

| Check | Rule |
|---|---|
| File scope | `file` matches one of the design-doc paths declared in `document-writing` § Autofix on Design-Doc Paths (`docs/system-design.md` or any `docs/adr/*.md`). |
| Category | `category` is `writing-standards` or `structural`. Any other value fails. |
| Size bounds | `lines_changed` ≤ 5 AND `chars_changed` ≤ 200. |
| No heading touch | Neither `old_content` nor `new_content` contains a `## ` line. |
| No anchor change | `<a id="...">` values in `old_content` are identical to those in `new_content`. |
| No REQ-ID change | REQ-ID tokens (regex `REQ-[A-Z]+-\d{3}`) in `old_content` are identical to those in `new_content`. |
| No code-fence touch | Neither `old_content` nor `new_content` contains a `` ``` `` line. |
| No link-target change | Markdown link targets (the URL inside `](...)`) in `old_content` are identical to those in `new_content`. |
| Verbatim fix | `new_content` equals `source_finding.fix` byte-for-byte. |

Any failure: do NOT declare gate-pass. Append a `review-feedback` finding under your own coordinator role naming the failing record by `handoff.jsonl` line number, then route to system-design-expert with the failing record and instructions to revert the autofix and either redo it correctly or convert it to a substantive design-block.

**Step 2 — Direct-edit detection.** Run `git diff --name-only HEAD -- docs/system-design.md docs/adr/`. For each path returned:

- Read `.scratch/handoff.jsonl`. Confirm at least one of the following exists with `ts` later than the last commit's timestamp (`git log -1 --format=%cI`):
  - A `design-doc-autofix` record whose `file` equals the path, or
  - A `design-block` record listing the path in `primary_paths` or `supporting_paths`.
- If a path is dirty but no covering record exists, the gate fails. The change was made outside the protocol — revert it or write the missing record before re-running the gate.

**Step 3 — Result.** Only declare the autofix-audit check green when Steps 1 and 2 both pass. Record the outcome alongside the other quality-gate results.

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
- [ ] Autofix audit passes (see "Autofix Audit Procedure" above)
- [ ] Configuration synced (if config changed)
- [ ] All four reviewers approve
- [ ] No pending escalations (or human approved)

## Stop at done

Once every box above is checked, stop. Polish past the bar — extra refactors, additional tests for the same behavior, prose tightening on a passing PR — spends tokens without raising quality and is explicitly out of scope. The nine-clause bar is defined across `.claude/skills/tdd-workflow/tdd-principles.md`, `docs/testing-principles.md`, `docs/architecture-principles.md`, and `docs/security-principles.md`, with the canonical slug list in `review-checklist` § Quality-Bar Clause Mapping; if the diff meets the nine clauses, the work is done.
