---
name: audit-consistency
description: >-
  Re-materialize the Go and Java Spring Boot samples from the /harness source,
  then audit them for consistency with root-level documentation, with that
  source, and with each other. Section 13 runs bootstrap.sh in place so one run
  both propagates /harness changes to the samples and proves they match source;
  the per-agent depth audit is delegated to /audit-agents run inside each
  materialized sample, with findings mapped back to /harness. Load when
  modifying root docs, the /harness tree, agent definitions, skills, or pipeline
  structure, or to verify cross-project alignment.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## When to Run

- After editing `docs/specialist-agent-workflow.md` or `docs/agentic-harness.md`
- After editing the `/harness` source (`core/`, `stacks/<stack>/`, `init/`) or running `materialize`/`init`
- After adding or changing agents or skills in either project
- After migrating content from an upstream template
- Periodically to catch drift

## Audit Checklist

**Source of truth.** `/harness` is the single canonical source; the samples are materialized instances of it (copy channel). **Run Section 13 first** — it re-materializes both samples from `/harness` in place, so the rest of the audit runs against the current source, not a stale snapshot. After it, the working-tree diff is the propagation of your `/harness` edits (commit it) or the revert of a drifted hand-edit (investigate). The per-agent depth audit is **delegated to `/audit-agents`** run inside each materialized sample (Section 3); the between-sample checks here (Skill Parity, Handbook Doc Drift) and the root-alignment checks corroborate the rest. When anything disagrees with `/harness`, `/harness` wins — edit the source and re-materialize, never a sample's committed runtime. **Every finding maps to a `/harness` path** by the rule in Section 3.

### 1. Root Doc Alignment

Verify both projects match the naming and structure in `docs/specialist-agent-workflow.md` and `docs/agentic-harness.md`.

**Scratch state:**

| Path | Producer | Notes |
|---|---|---|
| `.scratch/handoff.jsonl` | every pipeline agent | Append-only JSONL log; record types below |
| `.scratch/implementation-plan.md` | feature-implementer | Self-tracking only, no handoff gate |
| `.scratch/escalations.md` | feature-implementer | Human-read escalations |
| `.scratch/tmp/` | any agent | Intermediate computation; never use system `/tmp` |

**Record types in `handoff.jsonl`** (one JSON object per line, schema in `schemas/scratch/<type>.schema.json`):

| Record `type` | Producer | Purpose |
|---|---|---|
| `prd-entry` | product-requirements-expert | Active slice scope handed to SDE |
| `design-block` | system-design-expert | Triage verdict and implementation guidance handed to the implementer |
| `consultation-request` | any specialist mid-work (typically feature-implementer) | Focused question to another specialist that does not advance the pipeline |
| `consultation-response` | the consulted specialist | Focused answer; coordinator routes control back to the requester |
| `dispatch-start` | every substantive agent (as its first tool call); `pipeline-coordinator` and `change-grader` exempt | Per-dispatch start marker recording the Scoping Pre-Check |
| `build-failure` | feature-implementer | Quality-gate failure with error context and retry counter |
| `build-pass` | feature-implementer | Quality-gate success marker |
| `review-feedback` | each reviewer | Per-reviewer verdict and findings |
| `design-doc-autofix` | root (coordinator) | Audit trail for root-applied autofixes on design-doc paths |
| `grader-features` | change-grader (via `scripts/score-change.py extract`) | Deterministic structural row for the change-grade; advisory, terminal, never routes |
| `grader-verdict` | change-grader | Advisory facets, rationale, and `clear`/`concern` verdict; surfaced to the human, never routes |

The `review-feedback` record's `author` enum (`code-quality-reviewer`, `test-reviewer`, `security-reviewer`, `doc-reviewer`) is the canonical reviewer identity — there are no per-reviewer markdown files.

**Verdict enums (kept distinct):**

- `design-block.verdict` ∈ `{covered, minor, new, refactor-first, foundational, conflicting}`. The retired enum values (`needs_changes`, `revised`, `escalated`) must not appear in a design-block context — flag any occurrence. (`approved` and `blocked` remain valid for `review-feedback`; see below.)
- `review-feedback.verdict` ∈ `{approved, changes_requested, blocked}`. This is a *different* enum space from `design-block.verdict`; do not conflate.

Check these names in: `pipeline-handoff` skill, `pipeline-coordinator` agent, agents README, and the schemas directory.

**Agent names:**

| Root Doc Name | File Stem |
|---|---|
| pipeline-coordinator | `pipeline-coordinator` |
| product-requirements-expert | `product-requirements-expert` |
| system-design-expert | `system-design-expert` |
| feature-implementer | `feature-implementer` |
| security-reviewer | `security-reviewer` |
| code-quality-reviewer | `code-quality-reviewer` |
| test-reviewer | `test-reviewer` |
| doc-reviewer | `doc-reviewer` |
| change-grader | `change-grader` |

Verify all 9 exist in `.claude/agents/`, `.github/agents/`, `.opencode/agents/`, and `.junie/agents/`.

**Reviewer names in root doc Section 5 (Project Structure):**
- `.claude/agents/`: `test-reviewer.md`, `doc-reviewer.md` (not `test-coverage-reviewer`, `documentation-reviewer`)
- `.github/agents/`: same stems with `.agent.md` suffix
- `.opencode/agents/`: same stems
- `.junie/agents/`: same stems

### 2. Cross-Tool Compatibility Rules

From `docs/specialist-agent-workflow.md` Section 2:

- [ ] No `AGENTS.md` file exists in either project
- [ ] No `.github/copilot-instructions.md` exists in either project
- [ ] Skills live in `.claude/skills/` only (no `.github/skills/`, no `.opencode/skills/`, no `.junie/skills/`)
- [ ] Agent definitions exist per-tool: `.claude/agents/`, `.github/agents/`, `.opencode/agents/`, `.junie/agents/`
- [ ] `CLAUDE.md` is the single rules file in each project (Junie reads it via `.junie/config.json`)

### 3. Agent Config Depth — delegated to `/audit-agents`

The per-agent rules — **thinness** (with the drift test that tells real duplication from parallel description), **write scope**, **reference integrity**, **reviewer conduct**, and the **state/enum** checks — are owned by the **`audit-agents`** skill, which ships inside every sample and carries the authoritative logic. Do not re-implement or re-grep them here; that only lets a weaker copy drift from the canonical one.

After Section 13 materializes the samples, run `/audit-agents` inside each, then map every finding back to `/harness`:

- [ ] `/audit-agents` run in `samples/go`; findings mapped to `/harness` and fixed at source.
- [ ] `/audit-agents` run in `samples/java-spring-boot`; findings mapped to `/harness` and fixed at source.

Because each sample is `materialize(core ∪ stacks)`, a clean `/audit-agents` on **both** samples is a clean `/harness` for every rule it owns. **Cross-Tool Parity (Section 6) is part of this delegation** — `audit-agents` § Cross-Tool Parity holds the four-tool comparison and the model-mapping table.

**Finding → `/harness` source mapping.** Every `/audit-agents` finding names a sample path; the fix goes to source, never the sample (the next materialize reverts a hand-edit). Map it:

- A finding in **both** samples, on a file sourced from `core/` → fix in `harness/core/…`.
- A finding in **one** sample only → fix in `harness/stacks/<stack>/…`.
- A finding on a project-owned committed file (`CLAUDE.md`, `scripts/layout.toml`, `docs/` briefs) → fix the skeleton in `harness/init/…` or the doctor template, not the sample.

Then re-materialize (Section 13) and re-run to confirm the finding clears.

### 4. Skill Parity

Both projects must have the same set of portable skills. Compare `.claude/skills/` directories.

**Expected skills (both projects):**

| Skill | Purpose |
|---|---|
| `pipeline-handoff` | Routing table, handoff conditions, build-failure recovery, state files |
| `tdd-workflow` | TDD cycle, design-check decision tree, document ownership |
| `prd-authoring` | PRD format, boundary rules |
| `code-quality-gate` | Build/test/lint requirements, completion criteria |
| `review-checklist` | Feedback tags, review output format, review process |
| `code-quality-review` | Language-specific code quality checklist |
| `test-review` | Test quality checklist |
| `security-review` | Security checklists, threat model, severity |
| `document-writing` | Writing standards (authoring) + doc-form rules, review checklist, prohibited patterns |
| `design-validation` | Design principles, architectural validation checklist |
| `change-grading` | Terminal advisory change-grade: how much human attention a passing change deserves before merge |
| `new-feature` | Clear scratch directory |
| `adr-template` | ADR format and governance |
| `audit-agents` | Agent config consistency |
| `doc-sync` | Synchronize docs with codebase, maintenance rules |
| `doctor` | Deterministic blocking validation of `docs/` against the harness-project API |
| `audit-docs` | Advisory judgment review of the project briefs |
| `next` | Reset scratch and recommend the next PRD requirement to tackle |
| `ship` | Commit staged changes and push to remote in one step |

Report any skill present in one project but missing from the other. Exception: the Java sample's `intellij-idea` and `intellij-idea-doctor` are documented project-specific extensions (java agents README, java CLAUDE.md) — expected, not drift.

### 5. Template Placeholder Check

Grep for unfilled template placeholders in both projects:

```
{{PROJECT_NAME}}
{{PROJECT_DESCRIPTION}}
```

**Expected matches** (placeholders live here by design — `init` fills them when scaffolding a downstream project):

- `harness/init/stacks/<stack>/CLAUDE.md` — the skeleton's Project Overview header carries `{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}`
- `harness/core/.claude/skills/doctor/templates/*` — brief templates carry `{{PROJECT_NAME}}` and `{{HARNESS_DATE}}`
- Root `.claude/skills/init/SKILL.md`, `materialize/SKILL.md`, and `harvest/SKILL.md` (the onboarding/maintenance skills that document placeholders)
- `harness/init.sh` — the scaffolder that performs the substitution
- Root `README.md` and root `.claude/skills/audit-consistency/SKILL.md` — documentation about the template system

The reference repo keeps its **own samples in template state** by design — they double as a readable demonstration, and the `CLAUDE.md` Project Overview line documents the real identity in a comment. The brief provenance line is the exception: it is date-stamped with the concrete `<!-- harness: <date> -->` (the release date from `harness/VERSION-DATE`) like any materialized file, so it shows what a real consumer sees rather than a raw token. Expected placeholder locations inside each sample:

- `samples/<stack>/CLAUDE.md` — the Project Overview line `{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}` (carries its "`init` replaces the next line" comment)
- `samples/<stack>/docs/*` — brief titles carry `{{PROJECT_NAME}}` (the raw doctor-template form); the provenance line is date-stamped (`<!-- harness: <date> -->`), not literal
- `samples/go/Makefile` — the `init` target's `sed` references (`{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}`, `{{MODULE_PATH}}`)

A placeholder **anywhere else** is a bug: a runtime **agent or skill body**, a `settings.json`, or scattered through brief *content* (as opposed to the header/provenance line) — that is a leak, not the intentional template state. (A *downstream* consumer's project, by contrast, is `init`-filled and should carry no placeholders; this template-state exemption is specific to the reference repo's own samples.)

### 6. Cross-Tool Parity (per project)

Delegated to `/audit-agents` § Cross-Tool Parity — see Section 3. The per-agent four-tool comparison (persona, skill/doc references, write scope, reviewer conduct, tool permissions) and the authoritative **model-mapping table** live there; running `/audit-agents` inside each materialized sample covers this section. Map any finding to `/harness` via the source-mapping rule in Section 3.

### 7. Quality Gate Consistency

Verify the quality gate in each project matches across all locations:

**Go project:**
- `CLAUDE.md` "Quality Gate" section
- `.claude/skills/code-quality-gate/SKILL.md` required checks
- code-quality-reviewer agent permitted Bash commands

**Java project (must include format check):**
- `CLAUDE.md` "Quality Gate" section
- `.claude/skills/code-quality-gate/SKILL.md` required checks (must include `checkJavaFormat`)
- code-quality-reviewer agent permitted Bash commands (must include `checkJavaFormat`)
- `.claude/settings.local.json` permissions (must include `formatJava` and `checkJavaFormat`)

### 8. CLAUDE.md Skills Table

Verify the skills table in each project's `CLAUDE.md` lists every skill in `.claude/skills/`.

- [ ] Every directory in `.claude/skills/` has a row in the table
- [ ] No table row references a skill that doesn't exist

### 9. Agents README Consistency

Verify `.claude/agents/README.md` in each project:

- [ ] Agent table lists all 9 agents
- [ ] Skills table lists all skills
- [ ] Scratch directory structure matches `pipeline-handoff` skill state files
- [ ] No `{{PROJECT_NAME}}` placeholders

### 10. Handbook Doc Drift

The harness-owned methodology docs live inside the samples' skill trees (installed locations); the monorepo root `docs/` carries the handbook source. Project briefs (`docs/testing-principles.md`, `docs/architecture-principles.md`, and the rest of the roster) are project-owned in each sample and are NOT compared to the root — the doctor templates carry the defaults instead. Sample projects must stand completely on their own: no sample doc may reference the other sample.

| Root (handbook source) | Sample copies (installed) | Equivalence rule |
|---|---|---|
| `docs/agentic-harness.md` | `<sample>/.claude/skills/pipeline-handoff/agentic-harness.md` | Content matches root except location-relative links and the doc-form pointers (root cites `ddd-principles.md`, which is not installed; installs cite the `architecture-principles` and `testing-principles` briefs); byte-identical between the two samples |
| `docs/ddd-principles.md` | *(root-only)* | Strategic handbook doc; not installed in samples. Tactical content ships via the `architecture-principles` doctor template |
| `doctor/templates/*` | `samples/go/.claude/skills/doctor/templates/`, `samples/java-spring-boot/.claude/skills/doctor/templates/` | Byte-identical across the two samples |

Verify with `diff` — between the two samples the copies must be byte-identical; against root, diffs are expected only on location-relative links. Any other difference is drift.

**Self-containment grep.** Each sample doc must contain no reference to the other sample. From `samples/go/docs/`, `grep -l 'java-spring-boot' *.md` must return nothing. From `samples/java-spring-boot/docs/`, `grep -l '\bgo/' *.md` must return nothing.

**Doctor pass.** Both samples must exit 0 from `python3 scripts/brief_doctor.py check`. A roster failure here outranks every other finding in this section.

For `agentic-harness.md`, the equivalence check here is necessary but not sufficient. The doc is the bar for what the deployed harness should look like; Section 15 below verifies the sample contents reflect what the doc says.

### 11. Consultation Routing Semantics

The consultation roundtrip lets a specialist mid-work (typically `feature-implementer`) get a focused answer from another specialist (typically `system-design-expert`) without advancing the pipeline. Verify the semantics are consistently described across both samples:

- [ ] `pipeline-handoff` skill: documents a gate for `consultation-request` and `consultation-response` records; states that after a `consultation-response` the coordinator routes control **back to the requesting specialist** named in the corresponding request, not forward to the next pipeline stage.
- [ ] `pipeline-coordinator` agent (all four tool versions): validation step recognizes the two consultation record types and follows the back-route semantics above.
- [ ] `tdd-workflow` skill: the design-check decision tree directs the implementer to append a `consultation-request` rather than block waiting; the inner loop resumes when the matching `consultation-response` arrives.
- [ ] `design-validation` skill: describes both triage mode (returns one of the six `design-block` verdicts) and consultation mode (returns a `consultation-response`); the agent branches on the input record type.
- [ ] `system-design-expert` agent: write scope explicitly allows appending `consultation-response` records; `docs/ubiquitous-language.md` is in scope **only** during the `foundational` triage path.
- [ ] `consultation-request.schema.json` and `consultation-response.schema.json` exist in both samples' `schemas/scratch/` directories with required fields matching the skill/agent descriptions.

### 12. SDE Triage Verdicts

Verify the six `design-block` verdicts are described consistently:

- [ ] `system-design-expert` agent (all four tool versions, both samples) names triage + consultation as the two modes and lists the six verdicts.
- [ ] `design-validation` skill enumerates the six verdicts with content guidance per verdict.
- [ ] `docs/agentic-harness.md` § The system-design-expert role in depth (root + both samples) lists the same six verdicts.
- [ ] `design-block.schema.json` (both samples) enum exactly matches the six verdict names: `covered`, `minor`, `new`, `refactor-first`, `foundational`, `conflicting`.
- [ ] The `foundational` path covers both greenfield projects and adoption (extracting candidate vocabulary from existing docs and source); same description across the SDE agent, `design-validation`, and `agentic-harness.md`.

### 13. Harness Source Integrity & Materialization

`/harness` is the single canonical source (`core/` shared by every stack, `stacks/<stack>/` stack-specific). The samples are **materialized instances** of it on the **copy** channel — their runtime is committed (not gitignored), reproduced by `harness/materialize.sh`. `init` lays down the project-owned files from `harness/init/` and the doctor templates. This section **re-materializes the samples in place, then verifies the result** — one run propagates `/harness` to the samples and proves they match source. See [`harness/README.md`](../../../harness/README.md).

**Check A — materialize in place, then the tree is clean.** Run the multi-target installer; it detects each sample's stack and reinstalls the runtime from `/harness` into the real `samples/` directories:

```
harness/bootstrap.sh
```

Per sample it prints the file count and an **extras** block — runtime files the install did *not* produce. The samples declare no `extensions`, so **every extra is an orphan**: a file left behind by a renamed or removed harness unit (e.g. a skill directory after a rename). Remove each (`git rm -r <path>`) and re-run until the extras block reads `0 file(s)`. Then review what the in-place materialize changed:

```
git status --short samples/ && git diff -- samples/
```

- **Expected diff** — the propagation of a `/harness` edit you just made. Commit it together with the source change.
- **Unexpected diff** — a sample file you did *not* change in `/harness` moved, which means its committed runtime had been hand-edited and drifted; the materialize reverted it. Confirm the diff is a clean revert, not a regression. (Hand-edits never survive a re-materialize — the diff *is* the drift signal, no scratch-dir compare needed.)
- **Clean** (no diff, no extras) — the samples already matched source.

Parity *between* the two samples for `core/`-sourced files is guaranteed by construction. Run the materialize self-test too: `bash harness/test-materialize.sh` must end `PASS test-materialize` (it guards the extras-scan roots `RUNTIME_DIRS` against `brief_doctor.py` `RUNTIME_PATHS`, and the orphan/extension detection).

**Then audit the assembled agent config.** With the samples freshly materialized, run `/audit-agents` inside each (Section 3) — that is how the `audit-agents` rules (thinness, cross-tool parity, reference integrity, reviewer conduct, enums) reach the `/harness` content. Map each finding back to source by the Section 3 rule.

**Check B — the channel rule holds.** For each sample:
- `scripts/layout.toml` `[harness]` declares `channel = "copy"`, `tools` (the installed surfaces; both samples declare all four), and `extensions` (`[]` for the samples — they add none).
- The runtime is committed: every `RUNTIME_PATHS` entry is tracked (`git ls-files -- <paths>` returns the runtime files). The doctor's `channel` check passes copy by design — confirm it PASSes.
- The `.gitignore` ignores only `.scratch/`; the runtime is committed, not ignored. (The runtime block is appended only on the manifest channel.)

**Check C — `init` covers every project-owned committed file.** Every file a sample commits that is *not* user code or build output must have a skeleton source, or a freshly `init`-ed project will lack it. Verify each has its source:

| Committed project-owned file | Skeleton source |
|---|---|
| `CLAUDE.md` | `harness/init/stacks/<stack>/CLAUDE.md` |
| `.claude/settings.json` | `harness/init/core/.claude/settings.json` |
| `scripts/layout.toml` | `harness/init/stacks/<stack>/scripts/layout.toml` |
| `.gitignore` runtime block | `harness/init/core/gitignore-runtime.txt` |
| `docs/` roster (`prd.md`, `system-design.md`, `ubiquitous-language.md`, `testing-principles.md`, `architecture-principles.md`, `adr/README.md`) | `harness/core/.claude/skills/doctor/templates/` (`adr-README.md` → `docs/adr/README.md`) |

A committed project-owned file with no skeleton source is a coverage gap. `init.sh` never overwrites an existing project file — confirm a re-run on a sample reports `0 created`.

**Check D — the stack-agnostic core invariant.** No file under `harness/core/` (runtime or `init/core/`) may carry a stack-specific fact. Grep core for stack tokens and classify each hit; any genuine stack fact in core must move to `stacks/<stack>/`:

```
grep -rnE '\bgo\.mod\b|gradlew|build\.gradle|pom\.xml|\.go\b|\.java\b|golangci|spotless|JUnit|com/example' harness/core/
```

Test-name regexes, lint commands, build tasks, and language file-extensions are the canonical stack facts — they belong in `stacks/<stack>/`, in a brief, or in `scripts/layout.toml`, never in `core/`.

**ADR placement** (enforces ADR `2026-06-07-adr-placement`). Each sample's `docs/adr/` contains only `README.md` — the decision log is project-owned and starts empty; no harness ADR is materialized. `ls samples/go/docs/adr samples/java-spring-boot/docs/adr` should each show only `README.md`. The reference's full decision log lives at root `docs/adr/`.

Report format:
- `[OK] Samples re-materialized in place; tree clean (no extras, no unexpected diff), channel=copy, init coverage complete, core stack-agnostic`
- `[OK] Samples re-materialized; <N> file(s) changed — propagation of <harness edit>, ready to commit`
- `[ISSUE] <sample>/<path> is an orphan (extra not produced by materialize) — git rm it, then re-run bootstrap`
- `[ISSUE] <sample>/<path> reverted by re-materialize — committed runtime had drifted (hand-edited); confirm the revert is correct`
- `[ISSUE] <sample> committed project-owned file <path> has no skeleton source in harness/init/ or doctor templates`
- `[ISSUE] harness/core/<path> carries a stack-specific fact: <token> — move to stacks/<stack>/`
- `[ISSUE] <sample>/scripts/layout.toml channel is <x>, expected copy`

### 14. Root Reference Integrity

The rule is uniform: **every path-shaped string in root-level files must resolve to an existing file or directory** at the project root. Path-shaped means a token containing `/` and ending in a known extension (`.md`, `.go`, `.java`, `.yaml`, `.yml`, `.json`, `.jsonl`, `.sh`) or referring to a known directory (`docs/`, `.claude/`, `tools/`, `schemas/`, `samples/go/`, `samples/java-spring-boot/`).

This section covers references in **root-level** files only. References inside each sample (e.g., `samples/go/.claude/agents/...` pointing to `samples/go/docs/...`) are handled by that sample's `audit-agents` skill. Cross-sample references from root files (e.g., a root doc linking to `samples/go/CLAUDE.md`) are caught here.

- [ ] Every path-shaped reference in `.claude/skills/`, `CLAUDE.md`, `README.md`, `docs/`, and `tools/` resolves to a real file or directory at the project root.
- [ ] Every `docs/X.md#anchor` reference (including cross-sample anchors like `samples/go/docs/system-design.md#section`) points to an existing heading or `<a id="...">` anchor.
- [ ] **Self-audit:** apply the same check to this skill (`.claude/skills/audit-consistency/SKILL.md`). Stale references in the audit skill itself propagate into every audit run.

Use grep to find candidates:

```
grep -rohE '[A-Za-z0-9_./-]+\.(md|go|java|py|toml|ya?ml|json|jsonl|sh)' \
  .claude/ CLAUDE.md README.md docs/ tools/ | sort -u
```

Then check each against the filesystem. Same for directory references.

### 15. Sample Harness Reflects `docs/agentic-harness.md`

`docs/agentic-harness.md` is the bar for what the deployed harness (`.claude/`, `schemas/scratch/`) should look like and how it should behave. Section 10 verifies the doc itself is byte-equivalent across copies. This section is the deeper check: **read the doc and verify the sample contents reflect what it says**.

How to run the check:

1. Read `docs/agentic-harness.md` end-to-end.
2. For each claim that is checkable against sample contents — write-scope tables, record-type lists, do/don't pairs, named contracts, prohibitions stated with positive and negative examples — verify the samples reflect it.
3. Claims with explicit "do this / not this" examples turn into greps; structural claims (record schemas, verdict enums, agent roster) check against the filesystem.
4. Report anything that violates the doc's stated rules or contradicts its examples.

Two recurring patterns from the doc, as worked examples of how a claim turns into a grep:

- *Self-containment of the deployed harness.* The doc says agent prompts, skills, and schema descriptions don't cite specific ADR files or specific REQ identifiers — those couple the portable harness to a host project's historical record. Exemptions: `docs/adr/` as a write-scope or path-pattern mention is fine. Grep: `grep -rn -E 'docs/adr/[a-z0-9-]+\.md' <sample>/.claude/agents/ <sample>/.claude/skills/` and classify each match against the doc's exemption list.
- *Tool-agnostic prose.* The doc says concrete numeric budgets live in agent front-matter; prose uses generic phrasing. Skills name `toolCallBudget` without citing a value. Harness-level structural constants (retry count, reviewer count, verdict count) are fine. Grep agent bodies and skill prose for digits adjacent to `toolCallBudget`, `maxTurns`, `budget`, or `tool call`, and classify.

These illustrate the *shape* of the check; new contracts, do/don't pairs, or named rules added to the doc fall under the same mandate.

## Output Format

```
## Sync Audit: [date]

### Root Doc Alignment
- [OK] Scratch file names match
- [ISSUE] samples/go/.claude/agents/pipeline-coordinator.md:42 — references `.scratch/prd-handoff.md`, should be `.scratch/current-feature.md`

### Cross-Tool Compatibility
- [OK] No AGENTS.md
- [OK] Skills in .claude/skills/ only

### Agent Config Depth (delegated to /audit-agents)
- [OK] /audit-agents run in both samples; all findings mapped to /harness
- [ISSUE] /audit-agents flagged code-quality-reviewer inline Review Focus checklist in BOTH samples → fix in harness/core/.claude/agents/code-quality-reviewer.md (core-sourced)

### Skill Parity
- [OK] Both projects have 18 skills
- [ISSUE] samples/go/.claude/skills/tdd-workflow/ missing (present in java-spring-boot)

### Template Placeholders
- [OK] No unfilled placeholders
- [ISSUE] samples/java-spring-boot/docs/prd.md:7 — contains {{PROJECT_NAME}} after a real materialize run

### Cross-Tool Parity
- [OK] Delegated to /audit-agents (see Agent Config Depth) — parity clean in both samples

### Handbook Doc Drift
- [OK] tdd-workflow SKILL.md byte-identical across both samples
- [ISSUE] samples/go/.claude/skills/pipeline-handoff/agentic-harness.md diverges from java copy at line 42

### Quality Gate
- [OK] Go: build + test + lint consistent
- [ISSUE] Java: settings.local.json missing checkJavaFormat permission

### CLAUDE.md Skills Table
- [OK] All skills listed

### Agents README
- [OK] All agents and skills listed

### Harness Source Integrity & Materialization
- [OK] Samples re-materialized in place; tree clean, channel=copy, init coverage complete, core stack-agnostic
- [ISSUE] samples/go/.claude/skills/old-skill/ is an orphan (extra not produced by materialize) — git rm it, then re-run bootstrap
- [ISSUE] samples/go/.claude/skills/doctor/SKILL.md reverted by re-materialize — committed runtime had drifted (hand-edited)
- [ISSUE] harness/core/.claude/agents/feature-implementer.md cites `go test` — stack fact belongs in stacks/<stack>/

### Root Reference Integrity
- [OK] All root-level path-shaped references resolve
- [ISSUE] docs/agentic-harness.md:312 — references `../tools/old-name/` (does not exist)
- [ISSUE] .claude/skills/audit-consistency/SKILL.md:NN — self-audit found broken anchor `#removed-section`

### Sample Harness Reflects docs/agentic-harness.md
- [OK] Self-containment — no specific ADR/REQ citations in agent or skill prose
- [OK] Tool-agnostic prose — numeric budgets in front-matter, generic phrasing in prose
- [ISSUE] samples/go/.claude/skills/pipeline-handoff/SKILL.md:52 cites `docs/adr/2026-06-07-skill-based-agent-architecture.md` as rationale — doc says harness states *what*, ADRs state *why*
- [ISSUE] samples/java-spring-boot/.claude/agents/system-design-expert.md:48 hardcodes `27` in prose — doc says concrete values stay in front-matter

### Summary
- X checks passed
- Y issues found
```
