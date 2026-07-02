---
name: audit-consistency
description: >-
  The judgment half of the consistency audit. The deterministic battery
  (harness/check-sync.sh) owns the mechanical checks: faithfulness, parity,
  layout invariants, rosters, placeholders, handbook delta, enums, links. This
  skill audits what a script cannot judge — agent-config depth via
  /audit-agents in each sample, semantic cross-tool parity,
  consultation-routing semantics, triage-verdict descriptions, and whether the
  samples reflect docs/agentic-harness.md. Load when modifying root docs, the
  /harness tree, agents, skills, or pipeline structure. Root-only (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "2.0"
  author: team
---

# audit-consistency

The judgment pass over the reference's consistency. The mechanical half lives in
`harness/check-sync.sh` — its header is the authoritative step list; this skill
never re-implements a battery check. When anything disagrees with `/harness`,
`/harness` wins: fix the source, re-materialize, never a sample's committed runtime.

## What the battery already proves (do not re-check)

| Retired section | Now proven by |
|---|---|
| Samples match source; skill parity between samples; orphans | check-sync step 3 (faithfulness; extras count) |
| Cross-tool layout rules (no AGENTS.md, skills in `.claude/skills/` only, all surfaces present); copy-channel invariants (`channel="copy"`, `extensions=[]`, runtime tracked, `.gitignore` scope) | step 3b |
| Skills-table name rows (both directions), agents README roster, init skeleton coverage, brief roster, sample `docs/adr/` holds only README.md | step 3c — row *descriptions* stay judgment (Process 5) |
| Template placeholders confined to documented locations (per-file allowlist) | step 3d — token *placement* inside an allowed brief stays judgment |
| Root handbook vs installed copy (pinned delta); sample doc self-containment | step 3e — a change to `handbook-delta.expected` itself is reviewed as content drift |
| `design-block` / `review-feedback` verdict enums | step 3f |
| Stack-agnostic core (no stack token in `harness/core/`) | step 3g |
| Root markdown links resolve | step 3h — bare path tokens outside link syntax stay judgment (Process 5) |
| Byte-level agent body parity across the four tool copies | step 2b |

## Process

**0. Run the battery first.** `harness/check-sync.sh` (or `harness/release-prep.sh`
after a `/harness` edit — it propagates, then runs the battery). A non-zero exit
is a hard stop; fix at source before judging anything. Skip this step when the
battery just ran green — inside `/audit-harness`, Layer 1 already ran it.

**1. Agent config depth — delegated to `/audit-agents`.** The per-agent rules
are owned by the `audit-agents` skill that ships inside every sample: thinness,
write scope, reference integrity, reviewer conduct, state/enum checks, and the
four-tool comparison with the model-mapping table. Run it inside each
materialized sample; a clean run on the samples is a clean `/harness` for every
rule it owns. Map every finding back to source:

- A finding in **every** sample, on a file sourced from `core/` → fix in `harness/core/…`.
- A finding confined to **one stack** → fix in `harness/stacks/<stack>/…`.
- A finding on a project-owned committed file (`CLAUDE.md`, `scripts/layout.toml`, `docs/` briefs) → fix the skeleton in `harness/init/…` or the doctor template.

Then re-materialize and re-run to confirm the finding clears.

**2. Semantic cross-tool parity.** Step 2b proves the four per-tool bodies are
*identical*; judge what identical bytes cannot show. Does the model mapping fit
each tool? Do tool permissions in the frontmatter match the body's needs? Can
all four tools actually follow the instructions, or only Claude Code?

**3. Consultation routing semantics.** Verify the roundtrip is described
consistently across the samples:

- [ ] `pipeline-handoff`: after a `consultation-response`, the coordinator routes **back to the requesting specialist**, never forward.
- [ ] `pipeline-coordinator` agent: recognizes both consultation record types and follows the back-route.
- [ ] `tdd-workflow`: the design-check tree appends a `consultation-request` rather than blocking; the inner loop resumes on the matching response.
- [ ] `design-validation`: describes triage mode (six `design-block` verdicts) and consultation mode; the agent branches on the input record type.
- [ ] `system-design-expert`: write scope allows appending `consultation-response`; `docs/ubiquitous-language.md` is in scope only during the `foundational` triage path.
- [ ] Both consultation schemas exist with fields matching the skill/agent descriptions.

**4. SDE triage verdicts.** The schema enum is pinned by step 3f; judge the
*descriptions*. The SDE agent, `design-validation`, and `docs/agentic-harness.md`
must name the same six verdicts with compatible guidance. The `foundational`
path covers both greenfield and adoption the same way in all three. Flag the
retired verdict values (`needs_changes`, `revised`, `escalated`) anywhere in a
design-block context; `approved`/`blocked` stay valid for `review-feedback`.

**5. Root doc and quality-gate alignment.**

- Scratch-state names, record types, and agent names in root docs agree with the canonical homes: the `pipeline-handoff` skill and `schemas/scratch/`. The `review-feedback` `author` enum is the canonical reviewer identity — there are no per-reviewer markdown files.
- Skills-table row *descriptions* in each sample's `CLAUDE.md` match what the skill actually does — step 3c gates only the name rosters.
- Per sample, the quality gate agrees across its three homes: the `CLAUDE.md` Quality Gate chapter, the `code-quality-gate` skill, and the code-quality-reviewer's permitted commands. Java additionally carries `formatJava` and `checkJavaFormat` where each applies, including `.claude/settings.local.json`.
- Anchors in root cross-references resolve to a real heading — step 3h checks only file existence, not `#fragments`.
- Bare path-shaped tokens outside markdown-link syntax (backticked paths in prose, fenced usage lines) resolve — step 3h checks markdown-link targets only.

**6. Samples reflect `docs/agentic-harness.md`.** The doc is the bar for what
the deployed harness looks like and how it behaves. Read it end-to-end; for
each checkable claim — write-scope tables, record-type lists, do/don't pairs,
named contracts — verify the samples reflect it. Claims with explicit examples
turn into greps; structural claims check against the filesystem. Two worked
examples of the shape:

- *Self-containment:* agent prompts, skills, and schema descriptions cite no specific ADR file or REQ identifier (write-scope mentions of `docs/adr/` are exempt).
- *Tool-agnostic prose:* concrete numeric budgets live in agent frontmatter; skill prose names `toolCallBudget` without a value; harness-level structural constants (retry count, reviewer count) are fine.

## Output format

```
## Consistency Audit: <date>

Battery: PASS (prerequisite)
1 Agent config depth: [OK] /audit-agents clean in all samples | [ISSUE] <finding> → <harness path>
2 Semantic parity:    [OK] | [ISSUE] ...
3 Consultation:       [OK] | [ISSUE] ...
4 Triage verdicts:    [OK] | [ISSUE] ...
5 Root doc prose:     [OK] | [ISSUE] ...
6 Doc-reflects-samples: [OK] | [ISSUE] ...

Summary: <N> issues, each mapped to a /harness (or root) path.
```
