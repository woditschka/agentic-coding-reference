# Route Rules — the generated decision inventory

<!-- GENERATED from scripts/handoff/routing.py — do not edit by hand;
     regenerated and drift-gated upstream in the reference. -->

Every rule `scripts/handoff.py route` can print, with its decision kind and
dispatch target. The decision JSON names the matched rule; this inventory is
the lookup. The narrative contract is `route-spec.md`; the judgment-facing
summaries are `SKILL.md`'s. A target of *(computed)* is resolved from the log
at decision time (the roster, the requester, the recorded upstream).

| Rule | Decision | Dispatches |
|---|---|---|
| `abort-design-mismatch` | dispatch | `system-design-expert` |
| `abort-prd-mismatch` | dispatch | `product-requirements-expert` |
| `abort-prerequisite` | blocked | — |
| `abort-unknown` | escalate | — |
| `abort-wrong-shape` | dispatch | `product-requirements-expert` |
| `autofix-only-round` | escalate | — |
| `build-non-convergence` | dispatch | `system-design-expert` |
| `build-record-invalid` | dispatch (bounce) | `feature-implementer` |
| `build-retry` | dispatch | (computed) |
| `consultation-dispatch` | dispatch | (computed) |
| `consultation-invalid` | blocked · dispatch (bounce) | — · (computed) |
| `consultation-return` | dispatch | (computed) |
| `design-approved` | dispatch | (computed) |
| `design-conflict` | blocked | — |
| `design-gate-failed` | dispatch (bounce) | `system-design-expert` |
| `escalate-finding-halt` | blocked | — |
| `escalate-on-approved` | blocked | — |
| `failure-without-design` | escalate | — |
| `feature-complete` | blocked | — |
| `grade` | dispatch | `change-grader` |
| `grade-continue` | dispatch | `change-grader` |
| `human-consultation` | blocked | — |
| `intake-ready` | dispatch | `product-requirements-expert` |
| `intake-record-invalid` | blocked | — |
| `layout-invalid` | blocked | — |
| `missing-req-id` | blocked | — |
| `no-active-slice` | escalate | — |
| `no-substantive-record` | escalate | — |
| `outstanding-dissent` | dispatch | (computed) |
| `plan-gray` | dispatch | `review-planner` |
| `plan-gray-invalid` | dispatch (bounce) | `review-planner` |
| `planner-stall-retry` | dispatch | `review-planner` |
| `planner-stalled` | blocked | — |
| `prd-approved` | dispatch | `system-design-expert` |
| `prd-gate-failed` | dispatch (bounce) | `product-requirements-expert` |
| `process-findings` | dispatch | (computed) |
| `refactor-first` | escalate | — |
| `refactor-resume` | dispatch | `system-design-expert` |
| `review-non-convergence` | blocked | — |
| `review-record-invalid` | dispatch (bounce) | (computed) |
| `review-without-build-pass` | escalate | — |
| `reviewer-empty-findings` | dispatch | (computed) |
| `reviewer-stall-retry` | dispatch | (computed) |
| `reviewer-stalled` | blocked | — |
| `reviews-needed` | dispatch | (computed) |
| `truncation-before-design` | escalate | — |
| `truncation-continue` | dispatch | `feature-implementer` |
| `truncation-non-convergence` | dispatch | `system-design-expert` |
| `truncation-undefined` | escalate | — |
| `unknown-req-id` | blocked | — |
| `unroutable-state` | escalate | — |

51 rules.
