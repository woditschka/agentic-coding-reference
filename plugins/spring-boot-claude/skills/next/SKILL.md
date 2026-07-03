---
name: next
description: >-
  Reset feature context and recommend what to work on next based on PRD coverage.
  Load when the user asks "what's next" or invokes /next.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/prd.md
metadata:
  version: "1.0"
  author: team
---

# Next

Clear the scratch directory, survey unimplemented PRD requirements, and recommend the next **REQ-XX-NNN** to work on — along with a slicing recommendation.

This skill drives the **outer loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). Each `/next` run picks one REQ to work on next; the actual slice (`prd-entry` record) is authored by `product-requirements-expert` and may cover the full REQ or just a portion of it. See [`agentic-harness.md`](../pipeline-handoff/agentic-harness.md) for the loop model and the two-layer model (requirements vs slices).

## Slicing Triage

The PRD is the durable record of *what the system does*; each REQ-XX-NNN is a coherent capability. **Slicing is an implementation detail**: a single REQ may be implemented across multiple `prd-entry` records, each one a slice of work the inner loop can complete in one cycle.

When recommending a candidate, also recommend how it should be sliced. A `prd-entry` is a **right-sized vertical slice** — cuts through every architectural layer the behavior touches, has a single primary deliverable surface, typically 3–10 TDD cycles, one coherent shippable unit. Both extremes break the loop:

- **Too big.** Inner loop can't complete in one session; design churns mid-implementation; rework climbs.
- **Too small.** Pipeline overhead (PRD lookup + design triage + TDD plan + roster reviews + change-grade) dominates the work.

For each candidate REQ, judge how it should enter the pipeline. Mark the recommendation:

| Tag | Meaning | Next action |
|---|---|---|
| `[one-shot]` | REQ is small; one `prd-entry` can cover all acceptance criteria. | Dispatch product-requirements-expert to author one `prd-entry` covering the full REQ. |
| `[needs-slicing: N]` | REQ is too big for one inner-loop cycle; estimated **N** slices needed. | Dispatch product-requirements-expert to author the first `prd-entry` covering one slice; further slices follow on later sessions, all sharing the same `req_id`. |
| `[batch-with: REQ-XX-NNN]` | REQ is too small alone; only makes sense alongside the named sibling. | Dispatch product-requirements-expert to author one `prd-entry` covering the combined work. |
| `[depends-on: REQ-XX-NNN]` | REQ has unmet dependencies. | Recommend the dependency first. |
| `[bounce: <reason>]` | REQ itself is malformed (e.g., shaped around code rather than behavior, ambiguous criteria). | Route to product-requirements-expert to revise the REQ in `docs/prd.md` before dispatching the pipeline. |

The same slice-sizing tests are applied at write-time by the `prd-authoring` skill when product-requirements-expert authors the actual `prd-entry`. Re-checking at selection time catches REQ drift (a REQ that accumulated acceptance criteria over time and now needs slicing).

## Prerequisite

A skill cannot invoke `/clear` — slash commands run in the harness, not Claude. If the prior conversation is large or unrelated, ask the user to run `/clear` first, then re-invoke `/next`.

## Instructions

1. Reset scratch state:

   ```bash
   rm -rf .scratch && mkdir -p .scratch/tmp
   ```

2. Extract requirement identifiers from the PRD:

   ```bash
   grep -oE 'REQ-[A-Z]+-[0-9]+' docs/prd.md | sort -u
   ```

3. Extract non-goal identifiers — requirements explicitly declined — from the PRD's Non-Goals table:

   ```bash
   grep -oE 'NG-[0-9]+' docs/prd.md | sort -u
   ```

   Non-goals are *not* candidates. They have been considered and declined; re-proposing them wastes a cycle. Treat any NG-* identifier the same as an implemented REQ-* identifier for the purposes of the candidate-set computation.

4. Extract requirement identifiers already addressed (implemented or withdrawn) from git history:

   ```bash
   git log --pretty=%s%n%b | grep -oiE 'REQ-[A-Z]+-[0-9]+' | tr a-z A-Z | sort -u
   ```

5. Compute the candidate set — REQ-* identifiers present in the PRD but absent from both git history and the non-goal set.

6. **Candidate triage.** For up to five candidates, read the requirement section from `docs/prd.md` and capture: identifier, title, one-line summary, and any dependency it declares on other requirements. Estimate the slicing shape using the *Slicing Triage* table above. Tag each candidate `[one-shot]`, `[needs-slicing: N]`, `[batch-with: REQ-XX-NNN]`, `[depends-on: REQ-XX-NNN]`, or `[bounce: <reason>]`.

7. Rank candidates by:
   - **Foundational first**: cross-cutting infrastructure before level-specific requirements.
   - **Dependency order**: a requirement whose dependencies are met outranks one that is blocked.
   - **Smallest viable next step**: prefer single-package requirements over cross-package ones.

8. Present a short recommendation: top pick with rationale and slicing tag, plus 2–3 alternates. `[bounce]` candidates are surfaced separately because their next action is a REQ revision, not a pipeline dispatch. Format:

   ```
   Recommended: REQ-XX-NNN — <title>     [one-shot]   (or [needs-slicing: N])
     Why: <one line>
     Next action: dispatch product-requirements-expert to author the first prd-entry

   Alternates:
     - REQ-XX-NNN — <title>              [one-shot]
     - REQ-XX-NNN — <title>              [needs-slicing: 3]
     - REQ-XX-NNN — <title>              [depends-on: REQ-XX-NNN]
     - REQ-XX-NNN — <title>              [batch-with: REQ-XX-NNN]

   Needs REQ revision (route to product-requirements-expert):
     - REQ-XX-NNN — <title>              [bounce: <reason>]
   ```

9. Stop and wait for the user to choose. Do not invoke `pipeline-coordinator` until the user confirms a target. If the user chooses a `[bounce]` candidate, route to `product-requirements-expert` to revise the REQ in `docs/prd.md` first, not to the full pipeline.

## Rules

- Never assume an identifier is implemented from grep alone — git history is the authority. A REQ mentioned in a comment or doc does not count as done.
- If the PRD and git history are in sync (no unimplemented requirements), report that and stop.
- If the user asks for the recommendation without resetting scratch (e.g. follow-up in the same conversation), skip step 1.
- Keep the recommendation under 15 lines. The user reads it, decides, then routes through `pipeline-coordinator`.
