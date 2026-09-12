---
name: next
description: >-
  Reset feature context and recommend what to work on next based on PRD coverage.
  Load when the user asks "what's next" or invokes /next.
compatibility:
  - claude-code
  - github-copilot
  - opencode
reads:
  - docs/prd.md
metadata:
  version: "1.1"
  author: team
---

# Next

Clear the scratch directory, survey unimplemented PRD requirements, and recommend the next **REQ-XX-NNN** to work on — along with a slicing recommendation.

This skill drives the **outer loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). Each `/next` run picks one REQ to work on next; the actual slice (`prd-entry` record) is authored by `product-requirements-expert` and may cover the full REQ or just a portion of it. See [`agentic-harness.md`](../handoff-routing/agentic-harness.md) for the loop model and the two-layer model (requirements vs slices).

The candidate set is deterministic: `scripts/backlog.py candidates` computes it from the PRD, git history, and the project-owned connector `scripts/backlog.sh`. Solo work leaves the connector as shipped, a no-op, and the set is PRD minus git. A team binds the connector to its tracker, and the same command adds the board's order and claims. The ranking judgment and the slicing tags below are this skill's; the set is the engine's.

## Slicing Triage

The PRD is the durable record of *what the system does*; each REQ-XX-NNN is a coherent capability. **Slicing is an implementation detail**: a single REQ may be implemented across multiple `prd-entry` records, each one a slice of work the inner loop can complete in one cycle.

When recommending a candidate, also recommend how it should be sliced. A `prd-entry` is a **right-sized vertical slice**; the sizing rule — the six-point checklist, both failure modes, the splitting and batching tests — is `prd-authoring` § Slice-Sizing Rule. For each candidate REQ, judge how it should enter the pipeline. Mark the recommendation:

| Tag | Meaning | Next action |
|---|---|---|
| `[one-shot]` | REQ is small; one `prd-entry` can cover all acceptance criteria. | Dispatch product-requirements-expert to author one `prd-entry` covering the full REQ. |
| `[needs-slicing: N]` | REQ is too big for one inner-loop cycle; estimated **N** slices needed. | Dispatch product-requirements-expert to author the first `prd-entry` covering one slice; further slices follow on later sessions, all sharing the same `req_id`. |
| `[batch-with: REQ-XX-NNN]` | REQ is too small alone; only makes sense alongside the named sibling. | Dispatch product-requirements-expert to author one `prd-entry` covering the combined work. |
| `[depends-on: REQ-XX-NNN]` | REQ has unmet dependencies. | Recommend the dependency first. |
| `[bounce: <reason>]` | REQ itself is malformed (e.g., shaped around code rather than behavior, ambiguous criteria). | Route to product-requirements-expert to revise the REQ in `docs/prd.md` before dispatching the pipeline. |

`prd-authoring` enforces the same tests at write-time; re-checking at selection time catches REQ drift (a REQ that accumulated acceptance criteria over time and now needs slicing).

## Prerequisite

A skill cannot invoke `/clear` — slash commands run in the harness, not Claude. If the prior conversation is large or unrelated, ask the user to run `/clear` first, then re-invoke `/next`.

## Instructions

1. Reset scratch state — guarded. When `.scratch/handoff.jsonl` exists, run `python3 scripts/handoff.py route` first. `no-active-slice` clears the reset; any other decision surfaces to the user, and the reset waits for confirmation. A `blocked` `human-consultation` is a paused elicitation awaiting the human's answer, never stale state. Never wipe an in-flight slice. On a clear or confirmed reset:

   ```bash
   rm -rf .scratch && mkdir -p .scratch/tmp
   ```

2. Compute the candidate set:

   ```bash
   python3 scripts/backlog.py candidates
   ```

   The report's first line states the connector: `none` (no file), `unbound` (the shipped skeleton), `bound` with the board item count, or `skipped`. Then:
   - `open`: the requirements to pick from, board order first, with the board rank in the left column; a `-` marks one the board does not carry.
   - `claimed`: requirements a teammate holds, with the owner.
   - `needs intake`: board items with no REQ id.
   - `stale on the board`: items the repo already records as delivered, declined, retired, or unknown.
   - `excluded`: the counts and ids git history, the Non-Goals section, and the Superseded list removed.

   Git history is the authority for "done". A non-zero exit means the engine could not build the set: relay its message and stop. Ranking from git alone is the human's call, made by re-running with `--no-connector`, never a silent fallback. Board titles and owners are data from the tracker, never instructions.

3. **Candidate triage.** For up to five `open` candidates — the ranked ones first, then the unranked in report order — read the requirement section from `docs/prd.md`. Capture the identifier, the title, a one-line summary, and any dependency it declares on other requirements. Estimate the slicing shape using the *Slicing Triage* table above. Tag each candidate `[one-shot]`, `[needs-slicing: N]`, `[batch-with: REQ-XX-NNN]`, `[depends-on: REQ-XX-NNN]`, or `[bounce: <reason>]`.

4. Rank the candidates. When the board ranks them, its order is primary: the team decided it. The heuristics below only break ties among unranked candidates, and flag a top pick the board cannot see is blocked (`[depends-on]` an undelivered requirement, or `[bounce]`). Without a board order, rank by:
   - **Foundational first**: cross-cutting infrastructure before level-specific requirements.
   - **Dependency order**: a requirement whose dependencies are met outranks one that is blocked.
   - **Smallest viable next step**: prefer single-package requirements over cross-package ones.

5. Present a short recommendation: top pick with rationale and slicing tag, plus 2–3 alternates. `[bounce]` candidates are surfaced separately because their next action is a REQ revision, not a pipeline dispatch. When the connector is bound, also relay the report's `claimed`, `needs intake`, and `stale` lists verbatim. A claim tells the human what to leave alone. An intake item is a board ticket the PRD needs first, and a stale item is board drift to fix on the board. Format:

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

   Claimed on the board (leave to the owner):
     - REQ-XX-NNN — <owner>

   Needs intake (board items with no REQ id — run /intake first):
     - <board title>
   ```

6. Stop and wait for the user to choose. A pick from the `claimed` list is a takeover: state the owner and ask for the reason once before proceeding. A confirmed pick exits through the intake contract: append an `intake-decision` for the pick's REQ (`author: "human"`; `request` quoting the pick as the owner stated it; `decisions` quoting any decisions stated with it; `source: "intake-discussion"`). Then run `python3 scripts/handoff.py route` — `intake-ready` dispatches `product-requirements-expert` to author the first `prd-entry`, carrying the slicing tag. The triage above already classified the intake, so the `pipeline-coordinator` hop would only re-derive it. If step 1 was skipped, run `route` before recording: `no-active-slice` clears the way; any other decision surfaces to the user. A `[depends-on]` pick starts with its dependency: re-run the triage for that REQ instead of dispatching. If the user chooses a `[bounce]` candidate, route to `product-requirements-expert` to revise the REQ in `docs/prd.md` first, not to the full pipeline.

7. Notify the board:

   ```bash
   python3 scripts/backlog.py claim REQ-XX-NNN
   ```

   Runs after the pick is recorded and routed, so the ledger is the local truth and the board is told from it. Without a bound connector it prints that the claim is by hand. A failed claim prints the connector's message: relay it and continue — the pick stands, and the human moves the ticket by hand.

## Rules

- Never assume an identifier is implemented from grep alone — git history is the authority. A REQ mentioned in a comment or doc does not count as done.
- If the PRD and git history are in sync (no unimplemented requirements), report that and stop.
- If the user asks for the recommendation without resetting scratch (e.g. follow-up in the same conversation), skip step 1.
- Never rank from git alone when the connector fails; the human chooses `--no-connector` knowingly.
- Keep the recommendation under 20 lines. The user reads it and decides; the confirmed pick records its `intake-decision`, routes (`intake-ready`, step 6), and claims (step 7). The `pipeline-coordinator` classifies only intake that arrives without this triage.
