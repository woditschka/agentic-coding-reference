# Additive Reviewer Roster: a Mandatory Four-Reviewer Floor, Extended Never Subtracted

**Status:** Accepted (unconditional-dispatch clause amended by [2026-07-09 risk-proportional-review](2026-07-09-risk-proportional-review.md))

> Amended 2026-07-09: the floor's membership, additivity, and doctor enforcement all still hold. What changed is dispatch — a logged `review-plan` sizes each pass's roster, with the full battery as the fail-closed default rather than the unconditional rule.

## Context

The pipeline runs four reviewers in parallel after `build-pass` — code-quality, test, security, doc — and Gate 4 completes only when all four return `approved`. The count "four" was a hardcoded constant in three layers: the coordinator gate prose, the `review-feedback` schema's `author` enum, and the `pipeline-handoff` / `review-checklist` / `agentic-harness` text.

Adopters asked to review more dimensions in parallel — idiomatic-language conformance, performance, accessibility. Adding one meant editing the gate prose, the schema enum, and the routing text by hand: a fork, not a registration. The reviewer roster was a closed literal where it should have been an open registration point.

The opposite failure matters more. The four reviewers are the project's quality floor. Making the roster a free-form list a project fully owns would let a project quietly drop security or test review. That is the exact silent downgrade the harness exists to prevent, and it contradicts the secure-by-design bar. So the roster is not one editable list. It is a closed floor plus an open extension.

## Options Considered

1. **Free-form roster in `layout.toml`.** One `reviewers` list the project owns end to end. Maximally open, but a project can delete a baseline reviewer — the floor becomes optional. Rejected: the floor is non-negotiable.
2. **Per-project schema enum generation.** Keep the four enum'd in source; have `/materialize` stamp `four + extras` into each project's `author` enum. Preserves strict schema-level determinism, but adds enum-stamping logic to `/materialize`, which today never rewrites a project's schema from `layout.toml`.
3. **Closed floor plus additive extension.** The four stay harness-owned and named literally in the gate; a project adds reviewers through an additive `extra_reviewers` list in `layout.toml [harness]`. The schema `author` relaxes to a reviewer-shaped string; the doctor enforces the floor and the extras as a checked invariant.

## Decision

**The four-reviewer floor is mandatory and doctor-enforced. A project extends the review roster additively through `extra_reviewers` in `scripts/layout.toml [harness]`, never subtractively. The effective roster is the four-reviewer floor plus every declared extra; Gate 4 completes only when every reviewer in the roster returns `approved`.**

- **The floor is closed.** The four reviewers stay harness-owned, named literally in the coordinator gate and shipped in `core/` and the stacks. They are not in any project-editable list, so a project cannot subtract them.
- **The extension is open and additive.** `extra_reviewers` is an optional list of reviewer names in `layout.toml [harness]`, defaulting to `[]`. A project appends; the effective roster is `floor + extra_reviewers`. The gate prose reads "every reviewer in the roster," resolved as the literal four plus the declared extras.
- **The schema validates shape, the doctor enforces the roster.** `review-feedback.author` relaxes from a four-value enum to a reviewer-shaped string (`*-reviewer`). `clarify_target` likewise relaxes — to a bounded pattern admitting the two expert agents plus any roster reviewer — so an extra reviewer can be a clarify target without dropping to a free string. Roster authority moves out of the schema and into the declared list, mirroring the engine/data split of [layout-sourced schema patterns](2026-06-14-layout-sourced-schema-patterns.md): a harness-owned engine (`brief_doctor.py`) reads project-owned data (`layout.toml`).
- **The doctor floor-check, channel-aware.** The doctor reads `extra_reviewers` and the declared `tools`, then asserts every floor reviewer has an agent body in every declared tool surface — a project that deleted one fails the doctor. Each extra reviewer must likewise have a body in every surface and be listed in `extensions`, so `/materialize` preserves it across upgrades instead of pruning it. On the marketplace channel the reviewer bodies ship in the plugin, not the project tree, so the existence check is skipped there (validated at package time).
- **Naming convention.** Reviewers are named `*-reviewer`. The convention lets the schema shape-check authors and lets `audit-agents` and the doctor recognize a reviewer body without a roster lookup.
- **Non-breaking.** `extra_reviewers` is optional and defaults to `[]`, which reproduces today's four-reviewer behavior. `spec_version` stays `0.1.0`; existing project layouts without the key remain valid.

## Consequences

**Positive:**
- Adding a parallel review dimension drops from "edit the gate prose, the schema enum, and the routing text" to "drop in the agent bodies, add one name to `extra_reviewers`, list it in `extensions`."
- The floor is now a checked invariant, not a convention: deleting a baseline reviewer fails the doctor instead of silently shrinking the gate.
- The roster opens only upward. A project can review more, never less.

**Negative:**
- The `author` enum relaxes to a shape pattern, so a typo in a floor reviewer's name (`code-qualty-reviewer`) passes the schema. It cannot cause a false pass. Gate 4 waits for the correctly named reviewer's `approved`; the typo'd record never fills that slot. The gate stalls — a liveness failure the human notices, never a silent approval. Accepted: the floor's authority lives in the gate and the doctor's body-and-roster checks, not in the schema.
- The doctor's remit widens from `docs/` briefs to the reviewer roster. Accepted: the roster is part of the harness-project API the doctor already validates, and the check is channel-aware.

## References

- The roster data: `scripts/layout.toml [harness] extra_reviewers`; the floor and tool-surface map: `scripts/brief-expectations.toml [reviewers]`.
- The gate: `harness/core/.claude/skills/pipeline-handoff/SKILL.md` § Gate 4 (the roster is defined inline there).
- The floor-check: `check_reviewer_roster` in `harness/core/scripts/brief_doctor.py`, with tests in `test_brief_doctor.py`.
- Extends the engine/data split of [layout-sourced schema patterns](2026-06-14-layout-sourced-schema-patterns.md) and the additive-extension model of [the generic stack verb contract](2026-06-17-generic-stack-verb-contract.md).
