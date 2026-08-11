# Bundled Skill Names Are Reserved

**Status:** Accepted

## Context

The 2026-08-11 eval backfill surfaced a security reviewer's escalate finding: the `security-review` skill content delivered with its dispatch was not the harness checklist. The session transcripts settle the scope. All 49 surviving security-reviewer transcripts — v0.1.1 through v0.2.4, Claude Code 2.1.220–2.1.227 — carry Claude Code's *bundled* `security-review` skill in place of the harness one. The sibling preloads (`handoff-append`, `review-workflow`) resolved from the installed plugin in the same dispatches. Only two ledgers record the substitution; the rest absorbed it silently.

The mechanism is documented resolution order, not a race. A bare skill name resolves enterprise > personal > project > bundled; plugin skills live in a `plugin:skill` namespace and win a bare name only when nothing above claims it. The eval bench installs the harness on the plugin channel, so the bundled skill won every time. The copy channel is unaffected — a project-level skill outranks the bundled one, verified in `samples/java-spring-boot`. This falsifies a sentence in [2026-08-01 shared-plugin-namespace](2026-08-01-shared-plugin-namespace.md): the bare-name collision needs no second enabled plugin — the tool itself is the second claimant.

The measurement condition is uniform across every recorded sweep, so the trend's version comparisons stand; the [TREND note](../../evals/results/TREND.md) of the same date records it. But no recorded security review ever worked the stack checklist, and the failure ran silent for eight versions.

## Options Considered

1. **Namespace the frontmatter reference (`plugin:skill`).** Rejected: the namespaced form is undocumented for frontmatter preloading, and the copy channel has no plugin namespace — one agent body could not serve both channels.
2. **Report upstream and wait.** Insufficient alone: the shipped harness must resolve correctly on the tools consumers run today. The documented "cannot conflict" guarantee is worth an upstream report, but not a dependency.
3. **Rename the skill and reserve the bundled roster** (chosen).

## Decision

**No shipped skill preloaded by agent frontmatter may carry a Claude Code bundled skill or command name.** The security skill ships renamed `security-review` → `security-checks` in all three stacks — skill directory, `name:` frontmatter, the security-reviewer's `skills:` list on every tool surface (the hand-owned Junie frontmatter included), and every by-name reference.

The battery enforces the class: check 2g compares every agent surface's `skills:` entries against `CLAUDE_CODE_BUNDLED_SKILLS`, a pinned roster in `harness/verify_harness/checks/sync.py` that `update-research` refreshes. The check scopes to frontmatter preloads — the transcript-proven silent channel — and fails loud on a zero-scan.

## Consequences

- Positive: the substituted reviewer content is gone from the next version's sweeps onward; the next bundled-name collision fails the battery instead of running silent for months.
- Negative: a consumer's project-owned `docs/security-principles.md` keeps its old skill pointer until edited — materialize never rewrites project-owned briefs. The pointer then names the bundled skill. The reference's three sample briefs are updated; a consumer migration nudge remains open.
- Known residual, out of the gate's scope by design: the root-invoked `doctor` and `init` skills share bundled *command* names. They are never frontmatter-preloaded, and the plugin channel reaches them by typed prefix; a bare-name model-invoked load resolves to the built-in.
- Historical records keep the old name: ADR decision-time voice, frozen eval run folders, and the dated TREND note.

## References

- [2026-08-01 shared-plugin-namespace](2026-08-01-shared-plugin-namespace.md) — its bare-name collision claim is narrowed by this discovery; the namespace decision itself stands.
- [2026-07-12 parity-gates-for-hand-owned-parallels](2026-07-12-parity-gates-for-hand-owned-parallels.md) — the severity-heading parity gate now binds the renamed copies.
- `evals/results/TREND.md` 2026-08-11 note — the measurement-condition record behind the 49-transcript figure.
