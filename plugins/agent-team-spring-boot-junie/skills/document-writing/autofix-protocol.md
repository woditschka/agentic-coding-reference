# Autofix Eligibility on Owned Doc Paths

The closed eligibility rules for `tag: "autofix"` findings on the expert-owned doc paths, shipped once from the harness core beside the stack's `review-checks.md`, whose checklist applies them. Root's apply procedure lives in the `handoff-routing` skill § Root-Applied Autofix on Doc Paths; `scripts/handoff.py audit-autofix` re-checks the bounds mechanically at gate time.

## Autofix on Design-Doc Paths

Design-doc paths are `docs/system-design.md` and any file under `docs/adr/`. Only the system-design-expert may make substantive edits to these files. The autofix protocol exists so root can apply mechanical fixes without redispatching system-design-expert for every typo.

A finding may carry `tag: "autofix"` on a design-doc path only when **every** condition below holds:

1. The finding's check category is one of: **writing-standards** (sentence length, prohibited words without data, vague adjectives, missing periods on bullet points) or **structural** (missing `<a id="...">` anchor for an existing REQ-ID, missing language tag on a code fence, em-dash vs hyphen in ADR refs, table column-count fix, broken intra-file link).
2. The `fix` field is present and is a literal replacement string — not a description of what to change, not a sketch, not a TODO. Root applies it verbatim via Edit.
3. The proposed change is bounded: ≤5 lines and ≤200 characters of file content.
4. The proposed change does NOT modify any `## ` heading line, any `<a id="..."></a>` anchor value, any REQ-ID reference, any provenance mark (`derive-briefs` forms), any content inside a fenced code block, or any markdown link target (link text is fixable).

Findings that fail any of these conditions on a design-doc path must use `tag: "blocked"` or `tag: "clarify"` with `clarify_target: "system-design-expert"`. Coherence, PRD-boundary, and project-specific coherence findings on design-doc paths are **never** autofix-eligible — regardless of how mechanical the fix appears, they exercise architectural judgement and route to system-design-expert.

The conditions are also re-checked mechanically at gate time by `python3 scripts/handoff.py audit-autofix` (the `code-quality-gate` skill's autofix audit) — if doc-reviewer mis-tags a finding, the gate fails closed.

## Autofix on the PRD Path

The PRD path is `docs/prd.md`. Only the product-requirements-expert may make substantive edits to this file. The same protocol applies: root fixes mechanically, recording a `prd-autofix` record. The record keeps a doc-only PRD fix in the current review round — the alternative, a fresh `prd-entry`, re-enters the pipeline at design triage.

A finding may carry `tag: "autofix"` on `docs/prd.md` only when every condition in § Autofix on Design-Doc Paths holds for the PRD path. In addition, these are **never** autofix-eligible on the PRD, regardless of how mechanical the fix appears:

1. Any change to a "Done when" bullet's meaning — its conditions, outcomes, or given/when/then content.
2. Any change to requirement scope, a non-goal, an edge-case item, or lifecycle status (the narrative's active set, the `## Superseded` list). For a Non-Goals table row this is also enforced mechanically: `audit-autofix` rejects a `prd-autofix` touching a `| NG-n |` line, and Gate 1's scope-lock reads such an edit as an uncovered row change.
3. Any PRD-boundary content — mechanism moving in or out of the PRD is a boundary finding, not a style fix.

Findings that fail any condition on the PRD path must use `tag: "blocked"` or `tag: "clarify"` with `clarify_target: "product-requirements-expert"`. The gate re-checks the mechanical bounds via the same `audit-autofix` command; the product-requirements-expert judges every applied record on its next dispatch (`prd-authoring` skill § Autofix Audit).
