# Dynamic Tiering Is Verdict-Anchored and Evidence-Gated

**Status:** Accepted (stage A re-scoped measurement-only, front-door constraint added, by the [first in-file amendment](2026-09-01-evidence-gated-dynamic-tiering.md#amendment-2026-09-01-stage-a-is-measurement-only-the-front-door-stays-premium); stage B's hook mechanism recorded by the [second](2026-09-01-evidence-gated-dynamic-tiering.md#amendment-2026-09-01-second-stage-b-ships-as-a-rewrite-ahead-of-its-sweep); its acceptance sweep by the [third](2026-09-01-evidence-gated-dynamic-tiering.md#amendment-2026-09-02-stage-b-acceptance-sweep); the ladder relocated into the router, superseding the hook, by the [fourth](2026-09-01-evidence-gated-dynamic-tiering.md#amendment-2026-09-02-second-the-ladder-moves-into-the-router); the routine tier narrowed to fix rounds on the router sweep's quality evidence by the [fifth](2026-09-01-evidence-gated-dynamic-tiering.md#amendment-2026-09-03-the-router-sweep--routine-narrows-to-fix-rounds); the roster gap behind that evidence closed on both sides, with the bench's id minting corrected, by the [sixth](2026-09-01-evidence-gated-dynamic-tiering.md#amendment-2026-09-03-second-the-roster-gap-closes-on-both-sides))

## Context

[Model Tier Assignment](2026-06-11-model-tier-assignment.md) pins each role's model in agent frontmatter; the mixed reviewer fan-out priced at 70% of uniform-premium at decision time, near 50% after the 2026-08 sonnet-5 repricing. An outside proposal recommends per-dispatch model routing with hook enforcement, projecting 20–30% further savings from routing literature. Its primary citations could not be verified, so the claim needed local evidence.

A replay over the 98 committed v0.3.x eval runs ($1,017.66 accounted spend) joined each requirement's `design-block` verdict to its per-stage costs. The join is mechanical: `agent-costs.json` stages zip 1:1 with `handoff.jsonl` records, one trailing unclosed stage excepted. Stage costs fold the root session's supervising spend into the stages, so stage-basis shares exceed per-agent ones. Attribution uses each requirement's first verdict — the dispatch-time signal; a last-verdict replay looks ahead through three post-hoc re-ratings. Findings:

- The triage already rates complexity: the six-value `verdict` enum, recorded ahead of implementation. Five implementing runs carry no design-block; an absent record falls to the fail-closed default below.
- Spend concentration (stage basis): covered-verdict work holds 3.7% of all spend, minor 35.0%, new 25.7%. The root session holds 15.1% on the per-agent basis; the bases overlap and never sum.
- Build-failures per requirement: covered 0.00 (10 requirements), minor 0.74 (39), new 1.04 (24). Minor-verdict slices rework at 71% of the new rate while already on full premium.
- The corpus is too thin to test secondary design-block facts (paths, risks, integration points) as a rework predictor; the anchor stays the verdict alone.
- The live escalation channel is the superseding design-block loop: 74 instances. The consultation roundtrip opens 19 times and completes once; refusal-task pauses end most openings.
- Cost/pass punishes downgrade misses: one below-bar rep in a three-rep cell raises the cell's figure roughly 50%.

## Options Considered

1. **Static downgrade of covered-verdict slices** — addresses 3.7% of spend, nets an estimated 1–2%; the machinery does not pay for itself.
2. **Trained per-call router** — rejected: unverifiable evidence base, and a routing policy no script can audit.
3. **Immediate full-roster dynamic routing** — rejected: the miss asymmetry above, with no arm yet cleared.
4. **A staged program under fixed design constraints** (chosen).

## Decision

The static pins of [2026-06-11](2026-06-11-model-tier-assignment.md) stay operative. Dynamic tiering may enter only through the staged program, and any mechanism must hold four constraints:

- **The rating is a recorded fact.** The design-block `verdict` anchors the tier; no agent selects its own model or effort.
- **Enforcement is deterministic and fail-closed.** A dispatch-time downgrade is valid only when it matches the ledger-derived decision; absent or mismatched, the frontmatter pin stands. A PreToolUse hook on the dispatch checks the match.
- **Escalation is monotonic and capped.** Within a requirement the tier never decreases. A build-failure or an unresolved review round raises it one rung; the top rung is the static pin. The worst case converges to the current configuration after at most one attempt per lower rung.
- **Enforcement is Claude Code-only.** The other three tools run the frontmatter pins; the asymmetry note lands in the cross-tool strategy when the first enforcing stage ships.

The stages, each gated on the prior arm holding the 3/3 bar in a dev sweep:

- **A** — root pin to Sonnet; a pin change, no harness code.
- **B** — effort-medium first implementer dispatch on covered/minor verdicts, escalating on the ladder.
- **C** — model-tier routing, only if B shows capability-tier rather than reasoning-depth cost variance.

Any bar miss reverts the arm.

## Consequences

**Positive:** projected yields, unmeasured until the arms run — arm A tops out near 9% of cost/pass for a one-line pin, arms A plus B near 14%. A 20–25% ceiling opens only if the conditional stage C fires. The bar is protected structurally — every downgrade path terminates at today's configuration.

**Negative:** escalating slices lengthen wall clock, and the minor-tier bet may net ~0 (estimated breakeven near 60–65% first-attempt success). An arm's screening sweep costs ~$50 at one rep per task; clearing the 3/3 gate at three reps costs ~$160 accounted. The enforcement asymmetry across tools persists while one tool exposes dispatch overrides.

## Amendment 2026-09-01: Stage A Is Measurement-Only; the Front Door Stays Premium

A fifth constraint joins the Decision. **Intake and front-door judgment are outside downgrade scope.** The root session, product-requirements-expert, and system-design-expert keep their pins in every operating mode; tiering applies to the fix path. The bench measures unattended runs only. The root's interactive duties — the requirement dialogue, `foundational` consultations, escalations needing a human decision — have no instrument, so no sweep can license dulling them.

Stage A re-scopes from adoption arm to measurement, and stage B leads the program. The stage A screening sweep ran 2026-09-01: local dev label `dev-2ad60915`, one rep per task, never part of the committed trend. Results: bar 5/5 including the inverted refusal bar, refusal trajectory identical to the v0.3.8 ledgers, judge medians inside the baseline spread. The Sonnet parent spent $2.62 of the $29.74 row; repriced at the pin, its direct saving is ~$4. The row's −48% against v0.3.8 is dominated by condition drift — newer executing CLI, post-tag tree, API-side movement — and stays unattributed until a same-conditions Opus-root control runs.

## Amendment 2026-09-01 (second): Stage B Ships as a Rewrite, Ahead of Its Sweep

Stage B is built: a rendered `feature-implementer-fast` variant (`variant-of:`
render key, body byte-identical, battery-gated) and a `dispatch-tier-guard`
PreToolUse hook. Four mechanism decisions extend the Decision's letter:

- **The hook rewrites; it does not validate.** No agent ever names the tier —
  the coordinator dispatches the base, the hook swaps `subagent_type` to the
  ledger-derived tier in both directions. A stronger reading of "no agent
  selects its own model or effort" than the match-check the Decision sketched.
- **A third trigger joins the two named ones.** A superseding design-block
  re-rating the requirement outside covered/minor derives BASE — the ledger's
  highest-volume escalation channel (74 recorded instances) escalates the tier.
- **Ambiguity is a premium signal, not a ledger fact.** A dispatch prompt
  naming zero or two requirement ids derives BASE for that dispatch. The tier
  is a function of ledger plus prompt; the prompt half errs premium only.
- **The variant claims the base identity.** Its shared body records
  `author: "feature-implementer"`, deliberately: the routing engine, the
  schemas, and cost attribution key on the role. Accounting joins a role's
  `-fast` transcripts back to the role for the same reason.

Constraints the implementation adds: a variant must be named `<target>-fast`
with its target's model pin (battery-gated), and variant chains are refused —
a third rung for stage C extends `derive_tier`, never `variant-of`. On the
three tools without an input-rewriting hook the variant is inert by pins, not
prose (cross-tool strategy § Agents / Subagents, fulfilling the first
amendment's note).

The arm ships ahead of its dev sweep. The hook is fail-closed at every edge —
absent ledger, absent variant file, oversized ledger, any trigger — so the
unswept surface is the covered/minor fast path alone; reverting the arm is
deregistering the hook and deleting the variant. Two measurement notes: the
run artifacts identify the tier only through transcript agent types (the
eval runner's dispatch map reads the pre-rewrite input), and the stage B gate
needs only the bar and cost/pass, which the bench measures unchanged. The
arm-B dev sweep remains the acceptance gate before any release carries this.

## Amendment 2026-09-02: Stage B Acceptance Sweep

The arm-B screening sweep ran 2026-09-01/02: local dev label `dev-e74799e4`,
one rep per task, never committed. Above the ladder commit the swept tree adds
only a pricing-table edit for a model the sweep never invokes.

- **Bar 5/5.** The refusal task changed zero files and recorded its
  consultation checkpoint; judge medians on the four feature tasks sit inside
  the baseline spread.
- **The ladder fired on exactly the eligible set.** owners-page-param (first
  verdict `covered`) and visit-edit (`minor`) dispatched the fast variant
  first; the `new`-verdict cells and the refusal dispatched no variant.
- **Escalation stayed monotonic.** owners escalated on a `changes_requested`
  review, visit-edit on two build-failures; every post-trigger round ran the
  base, and no fast dispatch followed a trigger.
- **Row cost/pass $48.52 vs v0.3.8's $53.16 (−8.7%).** The three ladder-free
  cells alone moved −10% to −13%, so the row delta reads as single-rep
  variance plus condition drift — the stage A lesson repeating.
- **Implementer-stage spend on the fired cells matches baseline.**
  owners $1.71 against v0.3.8 reps at $1.02–1.71; visit-edit $4.71 against
  $3.64–5.63. The effort-medium rounds priced inside the premium per-round
  band.

Disposition: the bar held, so the arm stands. The mechanism performed to
specification — firing set, rewrite, monotonic escalation, fail-closed edges.
The projected saving is unresolved at one rep; the Consequences' ~0 breakeven
scenario is live, and one rep cannot separate a small ladder effect from rep
noise. Stage C stays closed — no capability-tier cost variance surfaced. The
next tagged release's three-rep row is the deciding measurement; a ladder
effect absent there retires the fast path as machinery without yield.

## Amendment 2026-09-02 (second): The Ladder Moves into the Router

Stage B's mechanism relocates: the deterministic router owns the tier, and
the PreToolUse hook retires unshipped — it existed only in unpushed commits,
so no released version ever carried it. Three findings drove the move:

- The hook's ladder duplicated, in a lenient standalone parser, a derivation
  the routing core computes natively over typed records.
- An input-rewriting hook exists in one tool; the router runs in all four.
- Traceability: a route rule is typed, tested, inventoried in
  `route-rules.md`, and re-derivable from the ledger by any consumer. The
  hook's rewrite was invisible everywhere but the transcript.

The relocated mechanism, replacing the second amendment's hook design:

- **The anchor is an explicit rating, not the verdict proxy.** The
  design-block gains optional `implementation_effort: routine | involved`,
  rated at triage by the system-design-expert — requirement, design, and
  touchpoints in context. The verdict keeps rating the design delta; the
  ratings are orthogonal. Absent reads as involved (fail-closed).
- **The rating's presence activates the ladder.** A slice with no
  `implementation_effort` on any design-block derives the base tier on every
  path, so an unrated ledger — pre-ladder, or a triage that never rates —
  routes exactly as before the ladder existed. The tier-2 audit added this
  gate: without it, 111 of the 247 committed ledgers would have taken a
  reduced-effort dispatch the fail-closed claim said they could not.
- **All-autofix fix rounds are routine work, on active slices.** A fix
  dispatch whose implementer-routed findings are all autofix-tagged runs the
  routine tier, whichever rating activated the slice. A round spans its
  whole review pass — interleaved dispatch records never split it, and
  dropped or empty findings read as mixed (both audit findings). Replay over
  the 98 v0.3.x runs: 63 of 77 non-approved rounds are mechanical by this
  test, holding $60.43 of implementer fix spend — 5.9% of corpus spend.
- **Recovery and resume dispatches run the base pin.** Build retries,
  truncation continuations, and the consultation return never take the
  routine tier — a budget or failure signal is answered at full effort.
- **Monotonicity is restated as routine-retirement.** One trigger inside a
  routine-predicted window — a build-failure, or substantive dissent on its
  pass — retires the routine tier for the slice permanently; a window the
  fold cannot attribute retires it too. Triggers under base windows no
  longer poison later mechanical fixes; the second amendment's blanket
  escalation over-served the bar.
- **Naming is two-layer.** The rating states the fact (`routine`/`involved`);
  the variant renames to `feature-implementer-routine` (`<target>-routine`
  render rule); tier vocabulary drops from user-visible surfaces.
- **The trace is the decision payload plus derivability.** Dispatch decisions
  carry `tier_reason`; `handoff.py tier` prints the derivation; the board
  annotates routine sessions from the same fold, scrubbing any self-claimed
  tier key from the agent-authored records first. This supersedes the letter
  of constraints 2 and 4: the derivation stays deterministic and fail-closed,
  but no hook checks the match, and no tool is singled out — adherence is
  dispatch discipline, verifiable after the fact from the ledger and the
  transcripts. The board performs that verification where transcripts are
  readable, flagging a session whose transcript tier contradicts the
  derivation. The hook's variant-file-availability check is
  deliberately dropped with it: both channels replace the runtime whole, the
  battery gates the producer side, and the doctor's version-skew warning
  covers a partially upgraded marketplace install.
- **Cross-tool posture flips from inert to active.** All four tools dispatch
  what the router names. The saving lands where an effort knob exists (Claude
  Code `effort: medium`, Junie `reasoningLevel: medium`); Copilot and
  OpenCode run the variant at base strength.

The acceptance gate is unchanged: the arm ships ahead of its sweep, the next
three-rep row decides, and a ladder effect absent there retires the routine
path — now by deleting a route rule, a schema field, and a rendered variant.

## Amendment 2026-09-03: The Router Sweep — Routine Narrows to Fix Rounds

The router-resident ladder's screening sweep ran 2026-09-02 (local label
`dev-0afffa4e-dirty`, one rep per task). The machine bar held 5/5, and the
mechanism engaged fully: the expert rated every slice, the ladder fired in
all four feature cells through three paths (a rating-routine initial, an
all-autofix fix, two post-re-triage initials), and one retirement latched as
specified. Routine dispatches priced $0.50–1.00; the row's cost/pass read
$45.42 against v0.3.8's $53.16, still drift-dominated at one rep.

The quality bar did not demonstrably hold. The one cell whose initial
implementation ran routine scored judge 3/3 on design fit and test quality —
unanimous across samples, below that task's every prior measurement — and
the misses are design-placement calls a severity-gated review passes
through. The three cells where routine ran only mechanical or re-mapped
work held their 4s. Under the output-quality invariant the burden falls on
the change, so the routine tier narrows to its proven-clean path:

- **Initial implementations always run the base implementer** (`initial`),
  whatever the rating's value. Design judgment is the work a reduced
  thinking budget degrades; the sweep measured exactly that.
- **All-autofix fix rounds on rated slices remain the routine tier's one
  path.** Every finding carries a suggested fix; no quality cost has
  appeared there in any measurement.
- **The rating stays.** Its presence activates the ladder; its value records
  the expert's judgment and calibrates this program's next decision.

The retirement rule, the trace surfaces, and the acceptance gate are
unchanged: the next three-rep row measures the narrowed arm, and a ladder
effect absent there retires the routine path.

## Amendment 2026-09-03 (second): The Roster Gap Closes on Both Sides

The judge dip behind the fifth amendment has a roster cause the router
sweep only exposed: no reviewer owned placement. The full-pin
implementer was the de-facto guardian, and a reduced budget removed the
only check. The code-quality reviewer gained the design-placement check
first; this amendment adds its test-side twin. Test-quality is the
trend's weakest facet: 3 on owners-page-param in v0.3.5 at the full
pin, 3 again in the router sweep. Every rationale names the same miss —
pure logic covered only through framework-booted tests because the rule
landed in the controller. Two owners-page-param reps swept on 2026-09-03
with the design-placement check in place, before this amendment, read
design-fit 4 · 4 and test-quality 4 · 3 (`dev-73c2e8a6-dirty`, never
committed).

The test-review skill gains a Test Placement section, with the web-layer
exception its design twin carries. The code-quality skill gains scope
and vocabulary items against the acceptance bullets, the non-goals, and
the ubiquitous language. The producer side moves in step: the
`tested-as-spec` clause and the implementer's self-review walk state
test level and vocabulary, so the reviewer enforces nothing the
implementer was never told. The review-planner and the roster table
name the new dimensions, so a focused plan never drops the guard.

A bench correction lands with them. The runner minted the requirement
id from the task name (`REQ-OWNERSPAGEPARAM-001`). The judge named that
id as a break from the PRD's `REQ-OWN-` vocabulary in 24 of the 27
owners-page-param samples across v0.3.5, v0.3.8, and the two dev
sweeps. The rationales place the remark in their documentation and
design clauses, never in a test clause. Doc-fit held at 5 throughout,
so the facet it cost, if any, is unattributed. From the next sweep the
seed mints the id as the intake skill would. The id is the task's
declared `req_prefix` plus one past the highest number under it in the
PRD at the epoch. The refusal arm's seeded id changes the same way.

Consequence for the gate: the next three-rep row measures the narrowed
arm, the roster change, and the re-minted id together. Its judge
medians against v0.3.8 read with all three conditions. The roster edit
can move cost per pass through added fix rounds. A `spec-grounded`
finding also widens its fix round to the doc-reviewer through the
planner's clause map. So the row's cost delta reads with the roster
condition too. The ladder's own evidence is the routine cells' implementer-stage
spend and the bar.

One roster gap the analysis surfaced stays open by decision. Reviewers
never read the slice's `design-block` (the fresh-eyes read-set), so a
risk the expert records there reaches no reviewer directly. A replay
over the v0.3.0 to v0.3.8 committed rows joined each of their 147
implementing design-blocks to whether the run's `change.patch` touched
`docs/system-design.md`: 140 did, 7 did not. The 7 carried risks that
instantiate recorded principles — trust-boundary input, identifier
tampering — which the security reviewer's checklist covers from the
brief. The disposition: the record is the implementer's briefing and
the briefs are the reviewers' wall. A risk no brief implies is a
missing principle to record in its owning brief, never slice detail
written into the design doc. The `design-validation` skill states the
rule; the reviewer read-set is unchanged.

## References

- [`2026-06-11-model-tier-assignment.md`](2026-06-11-model-tier-assignment.md) — the static policy this program may amend, never bypass
- [`2026-07-06-deterministic-mid-slice-routing.md`](2026-07-06-deterministic-mid-slice-routing.md) — the ledger-driven routing contract the enforcement extends
- [`2026-07-09-risk-proportional-review.md`](2026-07-09-risk-proportional-review.md) — the precedent for scaling compute to recorded risk
- [`2026-08-02-eval-bench-cost-per-pass.md`](2026-08-02-eval-bench-cost-per-pass.md) — the metric whose miss asymmetry sizes the conservatism
- [`2026-07-03-rendered-agent-mirror-bodies.md`](2026-07-03-rendered-agent-mirror-bodies.md) — the render contract the `variant-of:` key extends
