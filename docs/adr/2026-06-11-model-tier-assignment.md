# Model Tier Assignment: Judgment Roles Premium, Checklist Roles Mid-Tier

**Status:** Accepted (extended by [ADR 2026-09-01](2026-09-01-evidence-gated-dynamic-tiering.md): the implementer gains a router-selected variant, since moved to the checklist tier; amended in-file three times: [Opus 5.5 premium tier](2026-06-11-model-tier-assignment.md#amendment-2026-09-23-the-premium-tier-moves-to-claude-opus-55), [Sonnet 5.5 checklist tier](2026-06-11-model-tier-assignment.md#amendment-2026-09-28-the-checklist-tier-moves-to-claude-sonnet-55), [effort pins and routine implementation](2026-06-11-model-tier-assignment.md#amendment-2026-09-30-the-effort-pins-move-and-routine-implementation-joins-the-checklist-tier))

## Context

Each sample runs nine specialists, each pinned to a model in its agent frontmatter. Current pricing per million input/output tokens: Opus 4.8 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5, Fable 5 $10/$50. Fable 5 additionally tokenizes the same content to roughly 30% more tokens. The selection question: which roles justify the premium tier, and how assignments respond to new model releases. The governing objective ordering is fixed: quality bar first, cost second, wall-clock time third.

## Options Considered

1. **Uniform premium (all Opus)** — maximizes per-hop capability. The four-reviewer fan-out costs 43% more than the mixed one, on facets where the rubric, not the model, does the work.
2. **Uniform mid-tier (all Sonnet)** — cheapest uniform option; fails the quality bar on open-ended roles. Security review hunts vulnerabilities no checklist names. The residual bugs in premium-written code are exactly the subtle ones a weaker reviewer misses.
3. **Task-type split (chosen)** — judgment roles on Opus 4.8: product-requirements-expert, system-design-expert, feature-implementer, security-reviewer, change-grader. Checklist and routing roles on Sonnet 4.6: pipeline-coordinator, code-quality-reviewer, test-reviewer, doc-reviewer.
4. **Deeper frugality (rejected for now)** — coordinator or doc-reviewer on Haiku 4.5. Routing hops are short, so absolute savings are small; the quality-first ordering gives that saving no priority over misroute risk.
5. **Fable 5 for judgment roles (declined)** — roughly 2.6× Opus cost for equivalent content (2× per token, ~30% more tokens). Declined until the quality bar demonstrably requires it.

## Decision

We adopt option 3, with the rules that keep it stable:

- **Verification asymmetry justifies the split.** Checking a diff against an explicit rubric is an easier task than generating the code. The mechanical quality gate (build, test, lint) precedes every reviewer as the correctness oracle.
- **Judgment reviewers track the implementer.** On any tier bump, security-reviewer and change-grader move with the feature-implementer — never below it. A reviewer judging output it cannot comprehend is the configuration this forbids.
- **Promote trigger for the borderline role.** Test-quality review sits between checklist and judgment. A defect escaping an approved test review, or two consecutive test-facet failures, promotes test-reviewer to the judgment tier.
- **Pins, not aliases.** Explicit model IDs in frontmatter; a model release shifts nothing until a deliberate `deps-upgrade` run. Lower per-tool ceilings (Copilot at Opus 4.7, Junie alias-only) are documented exceptions, not drift.

## Consequences

**Positive:**

- Premium spend concentrates where errors compound: requirements, architecture, implementation, off-checklist security, the terminal merge-attention grade.
- The mixed reviewer fan-out costs 70% of a uniform-Opus one with no rubric-facet quality loss.
- Wall-clock is unaffected. Reviewers fan out in parallel; the critical path is the Opus security review, which the quality bar locks regardless.

**Negative:**

- Checklist reviewers can miss findings a premium model would catch. Mitigations: the Opus security and grader hops, and the test-reviewer promote trigger.
- Pins go stale by design. Capability gains from new releases wait for the next `deps-upgrade` decision.

## Implementation

**Non-goal:** This is a harness configuration decision, not sample content. Assignments live in each sample's agent frontmatter and `.claude/agents/README.md` table; the cross-tool ID mapping lives in the `audit-agents` skill. The root README (§ Model Tier Assignment) states the current policy; this ADR records why. No sample prose duplicates the rationale.

## References

- [`2026-06-05-change-grader.md`](2026-06-05-change-grader.md) — the terminal advisory hop this policy keeps on the premium tier
- [`2026-03-22-skill-based-agent-architecture.md`](2026-03-22-skill-based-agent-architecture.md) — rubric knowledge lives in skills, which is what makes mid-tier verification viable

## Amendment 2026-09-23: The Premium Tier Moves to Claude Opus 5.5

Claude Opus 5.5 released on 2026-09-22 at $4/$20 per million tokens, below Claude Opus 5's $5/$25, with cache reads at 0.05× base input against 0.10×. Same context window, same tokenizer. Anthropic reports medium effort on Opus 5.5 above high effort on Opus 5 on coding evaluations. The quality-first ordering and the cost ordering point the same way, so the premium tier moves.

- **All six judgment roles move together.** product-requirements-expert, system-design-expert, feature-implementer and its routine variant, security-reviewer, and change-grader pin `claude-opus-5-5`. The rule that judgment reviewers track the implementer admits no partial move. The four checklist roles stay on Claude Sonnet 5; no Sonnet release accompanied this one.
- **Per-tool forms.** OpenCode names `openrouter/anthropic/claude-opus-5.5`, the dotted slug OpenRouter serves. Copilot lists `Claude Opus 5.5 (copilot)` first and keeps `Claude Opus 5 (copilot)` as its fallback.
- **The family rate is no longer uniform.** The Context above priced every served Opus tier alike. The accounting module now carries Opus 5.5 as a per-model override, the same mechanism Sonnet 5 took in August.
- **Effort pins carry over unchanged, pending measurement.** Opus 5.5 defaults to medium effort and thinks more per level than Opus 5, so a carried `high` pin can lengthen turns. The pins stay as they are for the first eval arm; a second arm lowers the four `high` pins to `medium`. The arm holding the bar at the lower cost per pass decides.
- **The eval root pin moves with the tier.** `evals/config.toml` roots on `claude-opus-5-5`, opening a new row set in the trend. The judge pin is untouched; the judge series does not break.
- **Pins, not aliases, held.** Claude Code 2.1.280 resolved its `opus` alias to Opus 5.5 on release day. No harness agent moved until this deliberate edit, which is what the rule exists to guarantee.

## Amendment 2026-09-28: The Checklist Tier Moves to Claude Sonnet 5.5

Claude Sonnet 5.5 released on 2026-09-28 at Claude Sonnet 5's $2/$10 per million tokens, with the standard 0.10× cache reads, the same tokenizer, and the same context window. Anthropic lists Claude Sonnet 5 as a legacy model from the same day and commits Sonnet 5.5 to no retirement before 2027-09-28. No published figure compares the two on checklist work, so the cost ordering is silent and no quality datum exists yet. The move is the deliberate pin advance the Decision names for a same-tier release; the arm below is its measurement.

- **All five checklist agents move together.** pipeline-coordinator, review-planner, code-quality-reviewer, test-reviewer, and doc-reviewer pin `claude-sonnet-5-5`. The first amendment counted four; review-planner has been a checklist role since [ADR 2026-07-09](2026-07-09-risk-proportional-review.md), so the roster is five. The judgment tier does not move.
- **Per-tool forms.** OpenCode names `openrouter/anthropic/claude-sonnet-5.5`. Copilot lists `Claude Sonnet 5.5 (copilot)` first and keeps `Claude Sonnet 5 (copilot)` as its fallback. GitHub's supported-models page and OpenRouter's model listing both carried the model on release day.
- **The family rate is untouched.** The accounting override that prices Sonnet 5 at $2/$10 matches Sonnet 5.5 through the same needles; no new override joins.
- **Effort pins carry over as the control arm.** Sonnet 5.5 recalibrated its effort levels; Anthropic's guidance starts multistep tool use at `medium` and reserves `low` for latency-sensitive chat. The three reviewers already pin `medium`. The coordinator and review-planner pin `low`, one step below that floor, and run unattended, where a check-in is a stall. The candidate arm raises those two pins to `medium`.
- **The arms run as tag plus dev.** The release tag carrying these pins is the control. Each candidate is a dev arm interleaved with that tag in one invocation, so the pair shares an epoch. The first amendment's Opus arm lowers the four `high` pins to `medium`; the checklist arm raises the two `low` pins. The arm holding the bar at the lower cost per pass decides, with a stalled rep counted as waste.
- **The eval pins do not move.** The root pin stays on the premium tier and the judge pin is untouched.
- **Pins, not aliases, held.** No harness agent moved until this deliberate edit.

## Amendment 2026-09-30: The Effort Pins Move and Routine Implementation Joins the Checklist Tier

The two prior amendments named their effort arms and deferred them to a tag-plus-dev sweep. Anthropic's published positioning of the 5.5 pair, read on 2026-09-30, moves both arms and one tier boundary as a single combined arm:

- **Opus effort.** Anthropic reports Opus 5.5 at `medium` above Opus 5 at `high` on its coding evaluations, and `medium` is the model's default. The four `high` pins move to `medium`: product-requirements-expert, system-design-expert, feature-implementer, change-grader.
- **Sonnet effort.** Sonnet 5.5's recalibrated levels start multistep tool use at `medium`. The coordinator and review-planner pins move from `low` to `medium`; the two roles hold 0.5% of spend.
- **Routine implementation moves tier.** Anthropic positions Sonnet 5.5 as "strongest at well-scoped everyday tasks, fixing bugs," level with Opus 5 across 118 real app builds at half the iterations. Opus 5.5 "remains clearly stronger at complex, open-ended work requiring sustained judgment." The harness already draws that line. Triage rates each slice's code work `routine` or `involved`, and a routine slice arrives with a PRD entry and a design block written on the premium tier. The routine variant therefore pins the checklist tier's `claude-sonnet-5-5` at the tier's `medium` and gains the `routine`-rated initial implementation as its second path ([tiering ADR, seventh amendment](2026-09-01-evidence-gated-dynamic-tiering.md#amendment-2026-09-30-stage-c-opens-on-the-rating)). The rule that judgment reviewers never sit below the implementer holds: security-reviewer and change-grader stay on Opus 5.5, above both implementer tiers.

The expected saving is priced at the v0.4.7 sweep's token volumes: $78.21 over 15 reps, the Opus roles at 87% of spend, and 10 of 12 feature reps rated `routine`. The tier move caps at 9.1% of sweep cost, half of the implementer's 18.2% on routine-rated reps; the routine fix rounds cap at 1.4%. The effort moves act on the other three Opus roles, whose output tokens are 14.1% of spend: a 25% to 40% cut is worth 3.5% to 5.6%. The implementer's own effort move counts only on `involved`-rated reps, under 1%. Netted, the arm is worth 14% to 17%. Cache reads price the same on both models ($0.20 per million tokens), so every model move saves at most half of a role's remaining spend.

- **The arms run combined, screen then bisect.** One rep per task screens the combined configuration; three reps per task accept it. Each sweep interleaves the v0.4.7 tag with the dev tree in one invocation, so control and candidate share an epoch. A miss bisects the implementer tier first, the only cell with a recorded quality miss, then the effort pins; the fix-round cell folds into the tier cell. The pass condition is the standing one: 15/15 on the machine bar and judge facet medians inside the control's spread. The screen ran on 2026-09-30 as tag plus dev at one rep per task. The arm cleared 5/5 at $18.50 against the control's $23.77, every judge facet inside the control row's spread. The SUT epoch is unchanged since the v0.4.7 row, so acceptance is the released version's three-rep row against that row, whose fourth rep is the screen's control.
- **Per-tool forms follow the checklist tier.** The variant's mirrors name `Claude Sonnet 5.5 (copilot)` and `openrouter/anthropic/claude-sonnet-5.5`. The model saving lands on every tool; the effort pin landed on Claude Code alone.
- **The eval pins do not move.** The root pin stays on the premium tier under the front-door constraint; the judge pin is untouched.
- **Pins, not aliases, held.** No harness agent moved until this deliberate edit.
- **Measured.** The v0.4.8 row cleared the gate on 2026-10-01: 15/15 on the bar, every judge facet median inside the v0.4.7 spread, a rep-set $20.08 against $23.77. Design-fit is the watch facet: its sweep mean read 4.42 against 4.56, with one 3 on a visit-edit rep. That rep's Sonnet initial extracted the existing date check as every v0.4.7 rep did. Its fix round, on the Opus pin at medium, applied a security autofix that added a date rule to the controller. The pins stand.
