# Scratch Directory Contract

The reference half of the writer contract, shipped beside the append mechanics in `SKILL.md`: the `.scratch/` layout, the record roster with producers and schemas, the markdown templates, and the rules.

The `.scratch/` directory holds temporary files for the current feature cycle. It is git-ignored. Delete all files after feature merge.

## Structure

```
.scratch/
├── handoff.jsonl             # Append-only structured handoff log (all agents)
├── implementation-plan.md    # TDD cycle plan (from feature-implementer)
├── escalations.md            # Items requiring human decision
└── tmp/                      # Intermediate computation files (auto-cleaned)
```

`handoff.jsonl` carries every cross-agent handoff, one JSON object per line:

| Record `type` | Producer | Schema |
|---|---|---|
| `intake-decision` | `human` via root — the `intake` skill's exit, or headless seeding from the task prompt | `schemas/scratch/intake-decision.schema.json` |
| `prd-entry` | product-requirements-expert | `schemas/scratch/prd-entry.schema.json` |
| `design-block` | system-design-expert | `schemas/scratch/design-block.schema.json` |
| `consultation-request` | feature-implementer (or any specialist mid-work) | `schemas/scratch/consultation-request.schema.json` |
| `consultation-response` | the consulted specialist, or `human` via root on an elicitation pause | `schemas/scratch/consultation-response.schema.json` |
| `build-failure` | feature-implementer | `schemas/scratch/build-failure.schema.json` |
| `build-pass` | feature-implementer | `schemas/scratch/build-pass.schema.json` |
| `review-feedback` | each reviewer | `schemas/scratch/review-feedback.schema.json` |
| `review-plan` | the `build-pass` append (composing `scripts/grading.py review-plan`, `author: review-plan-engine`); review-planner on the gray path | `schemas/scratch/review-plan.schema.json` |
| `design-doc-autofix` | root | `schemas/scratch/design-doc-autofix.schema.json` |
| `prd-autofix` | root | `schemas/scratch/prd-autofix.schema.json` |
| `dispatch-start` | every substantive agent (as its first tool call); `pipeline-coordinator` and `change-grader` exempt | `schemas/scratch/dispatch-start.schema.json` |
| `grader-features` | change-grader (`scripts/grading.py extract`) | `schemas/scratch/grader-features.schema.json` |
| `grader-verdict` | change-grader | `schemas/scratch/grader-verdict.schema.json` |

Markdown is kept only for self-tracking (`implementation-plan.md`) and human-facing artifacts (`escalations.md`). One append-only JSONL file is replayable, line-addressable, and easier to validate against schema than scattered per-agent markdown files.

## File Lifecycle

See the `handoff-routing` skill for which agent appends each record type and how the routing gate validates them at agent transitions.

## File Templates

Templates for human-read markdown files are in `.claude/templates/`:

| Template | Used By | When |
|----------|---------|------|
| `implementation-plan.md` | feature-implementer | Before coding |
| `escalations.md` | feature-implementer; root (prerequisite-missing aborts, reviewer stalls, escalate findings on an `approved` verdict) | When `tag: "escalate"` findings or `design-block` records with `verdict: "conflicting"` exist |

JSONL records do not use markdown templates — they are validated against the JSON Schemas in `schemas/scratch/`.

## Rules

1. **One feature at a time** — Clear scratch before starting new feature.
2. **Agents own their record types** — Each agent appends only the record types listed above.
3. **Read before write** — Agents read upstream records before appending their own.
4. **Append-only** — Never edit, reorder, or delete prior records in `handoff.jsonl`. Use `supersedes_record_at` (where supported) to correct a prior decision.
5. **Traceability** — Every record references the requirement ID (`req_id` matching `^REQ-[A-Z]+-[0-9]{3}$`).
6. **No system /tmp** — Use `.scratch/tmp/` for intermediate computation files.
