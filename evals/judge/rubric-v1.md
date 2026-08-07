# Quality Judge Rubric v1

Frozen rubric for the Tier C advisory quality judgment (`run_eval.py --judge`).
Scores from this rubric never mix with scores from another rubric version;
editing the facets or anchors below requires creating `rubric-v2.md`.
Superseded rubrics stay in this directory — each `TREND.md` advisory row
names the rubric that produced it.

The judge receives the task statement, the sanitized patch (production,
test, and documentation sources; provenance-marked lines stripped), and the
project's testing and architecture principles. It is never told which tool,
workflow, or version produced the patch. Residual: agent-authored doc prose
in the patch can carry workflow vocabulary the filter cannot remove.

## Facets

Each facet scores 1–5 against the anchors. Scores are integers.

### design-fit

How well the change fits the project's architecture principles and existing
structure.

| Score | Anchor |
|-------|--------|
| 1 | Fights the existing structure: duplicated responsibilities, misplaced logic, broken layering |
| 3 | Fits where it must, with avoidable structural debt (logic in the controller that belongs lower, copy-paste variance) |
| 5 | Reads as if the original authors wrote it: right layer, right seams, no duplication |

### test-quality

How well the added or changed tests follow the project's testing principles
(behavior-named, phase-structured, no mock frameworks, meaningful data naming).

| Score | Anchor |
|-------|--------|
| 1 | No tests, assertion-free tests, or tests asserting implementation detail |
| 3 | Behavior covered, but naming or structure violates the stated principles |
| 5 | Tests read as specifications and satisfy the stated principles throughout |

### maintainability

How easily the next contributor changes this code safely.

| Score | Anchor |
|-------|--------|
| 1 | Fragile: hidden coupling, magic values, misleading names |
| 3 | Workable but rough: unclear names or noise comments that a reviewer would flag |
| 5 | Clear names, small surfaces, no dead weight; a reviewer would pass it unchanged |

### doc-fit

How completely the documentation the change makes stale is kept current,
judged only from the visible evidence: the patch and the provided
principles. Documentation the change never touched is invisible here and
never scores against it.

| Score | Anchor |
|-------|--------|
| 1 | A patch hunk plainly invalidates a claim in the provided principles or in a document visible in the patch, and no documentation moves |
| 3 | The primary affected document is updated; a stale claim visible in the evidence survives |
| 5 | Every documented claim visible in the evidence is current; no stale statement survives |

## Output Contract

The judge answers with a single JSON object and nothing else:

```json
{
  "design_fit": 1,
  "test_quality": 1,
  "maintainability": 1,
  "doc_fit": 1,
  "rationale": "one paragraph, max 120 words, citing concrete lines"
}
```
