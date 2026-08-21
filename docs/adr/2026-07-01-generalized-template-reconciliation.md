# Materialize Keeps Every Template-Seeded File Current: Deterministic Additions, Advisory Residual

**Status:** Accepted

## Context

`/materialize` keeps a project's harness current by two mechanisms. The **runtime** is replaced wholesale. The **`CLAUDE.md` doctrine chapters** are refreshed in place from a single source, heading by heading. Everything else that `/init` seeds once from a template freezes at scaffold time: `scripts/layout.toml`, `.claude/settings.json`, the `docs/` briefs, the non-doctrine `CLAUDE.md` chapters, and the `.gitignore` runtime paths. When a template improves, the installed base never sees it.

[Materialize Proposes Skeleton Improvements](2026-06-23-materialize-rules-reconciliation.md) (Option 4) solved this for `CLAUDE.md`: diff the target against the shipped skeleton, let the model classify each delta as a generic improvement or a project divergence, and propose adoptions. It was scoped to `CLAUDE.md` alone. One day later, [Harness Doctrine Lives in Managed Chapters](2026-06-24-claude-md-managed-chapters.md) superseded that pass. The advisory prompt re-fired every upgrade, so the doctrine moved to deterministic managed chapters with no prompt, and the reconciliation itself was demoted to a one-time legacy migration.

Two facts remain after that supersession. First, the managed-chapter fix covers only the five doctrine chapters; every other template-seeded file is still frozen. Second, the `.gitignore` runtime block — documented across the harness as a "managed region" — was in fact append-once (`init.sh` appended it only when absent), so a new runtime path never reached an existing project. The drift the 2026-06-23 ADR named for `CLAUDE.md` is unaddressed everywhere else.

The lesson of the 2026-06-24 supersession is the design constraint: where content is harness-owned and *does not* legitimately diverge, a deterministic refresh beats an advisory prompt — it is reliable and it never re-nags. Where content *does* diverge, only judgment can separate a missing improvement from a deliberate choice.

## Options Considered

1. **Status quo.** Rejected: template improvements reach only greenfield consumers; the installed base freezes at scaffold time.
2. **Deterministic refresh via injected sentinels.** Wrap each managed span in `BEGIN`/`END` marker comments and replace between them, as conda and nvm do in shell rc files. Rejected: it writes harness markers into every project-owned file. The maintainer declined marker pollution; the files must stay clean.
3. **Deterministic marker-free refresh by matching the known template line-set.** For `.gitignore` and `settings.json` the harness-owned lines are a fixed set, so they can be ensured present by exact match against the template — no marker, no baseline. It does not, on its own, cover the briefs, whose harness-owned part is prose structure, not a line-set.
4. **Version-stamped baseline plus three-way merge.** Stamp the harness version at scaffold; diff baseline-vs-template-vs-project. Rejected, consistent with the 2026-06-23 ADR's Option 3: the stamp is a weak proxy (a deleted section is indistinguishable from one never received), and it is a new tracked artifact the battery must guard. Machinery without enough payoff.
5. **Marker-free advisory reconciliation for every template-seeded file.** Diff the shipped template against the project file, classify each delta by model judgment, propose, apply on approval — across `.gitignore`, `settings.json`, `layout.toml`, the briefs, and the non-doctrine `CLAUDE.md` chapters. Uniform, but it puts *mechanical* drift (a missing runtime path, an unregistered hook) on the judgment side, where it is neither reliable nor testable — the same class of drift the 2026-06-24 ADR moved to deterministic refresh.

## Decision

**Options 3 and 5, layered.** The mechanical subset gets a deterministic engine; the judgment subset and the residual get the advisory diff-check. Neither alone is right — 3 leaves the briefs uncovered, 5 puts mechanical drift on the unreliable judgment side — but composed they cover every file, each by the mechanism that fits it.

- **Tier 1 — deterministic, marker-free refresh (Option 3), in `materialize.sh`.** Two small scripts ensure the harness-owned lines of two project-owned files, identifying ownership by exact match against the shipped template — no sentinel, no baseline:
  - `refresh-gitignore.sh` ensures every harness runtime path present (channel-aware: `copy` commits the runtime, so only the `.scratch/` ledger; manifest and marketplace ensure the paths too).
  - `refresh-settings.py` ensures the agent-teams `env` flag and a `PreToolUse` matcher for each delivered `.claude/hooks/*.sh` present.

  Both are **ensure-present and additive**: they reliably deliver a new path or hook to an existing project, they never rewrite a project's own ignores/keys/hooks, and they never remove. This is the same harness-owned-content contract as the `CLAUDE.md` managed chapters, applied line- and key-wise, and it is unit-tested — the mechanical drift that actually bit the installed base is now closed by a mechanism, not a hope.
- **Tier 2 — advisory diff-check (Option 5), in the skill (steps 8–9).** The model diffs *every* template-seeded file against its shipped template and proposes each remaining delta, applying only on approval. For each delta it classifies *intent* and **protects both sides**. A **deliberate project change** is preserved, never reverted to the template. A **harness migration** — the template evolved as the harness improved — is proposed for adoption. A **collision** where both changed goes to the human with both versions shown, never auto-resolved. Over the two mechanical files it is the **completeness backstop** — it catches what an additive pass cannot safely decide: a template line the harness *dropped* that now lingers, a *stale* matcher for a renamed hook, a harness key the project overrode. Over `layout.toml` data, the `docs/` briefs, and the non-doctrine `CLAUDE.md` chapters — which Tier 1 does not touch — it is the whole mechanism. Deterministic reliability first, judgment as the backstop over the same diffs.
- **Marker-free, no baseline.** Neither tier writes a sentinel or stamps a version. Tier 1 matches the template line-set; Tier 2 diffs against the shipped template with model judgment as the stand-in for a baseline. This is the maintainer's stated preference and holds the 2026-06-13 no-stored-baseline stance.
- **Doctrine chapters stay deterministic.** The 2026-06-24 managed chapters are unchanged; only the *non-doctrine* `CLAUDE.md` chapters join Tier 2.
- **Declines are not persisted.** A declined Tier-2 proposal re-surfaces on the next `/materialize` — acceptable for an occasionally-run command, and an idempotent run proposes nothing. The `declined_reconciliations` skip-list the 2026-06-23 ADR called "polish, not core — ship without it" stays deferred; it is the pre-authorized next step if re-prompting proves real.

## Consequences

**Positive:**
- The mechanical drift that motivated this — a new runtime path or hook not reaching an existing project — is closed **deterministically and testably**, consistent with the harness's engine-plus-judgment spine and the 2026-06-24 lesson.
- Template improvements reach the installed base for every seeded file, not only `CLAUDE.md` — the living-reference premise holds.
- Project files stay clean: no markers, no stamp, no new tracked artifact.
- The `.gitignore` append-once freeze is fixed by Tier 1; deeper cleanup (dropped lines, stale matchers) is the Tier-2 backstop.

**Negative:**
- Two mechanisms, not one — a deterministic engine and an advisory pass. The seam (Tier 1 adds, Tier 2 removes/judges) must be understood to reason about behavior.
- Tier 1 is additive only: it never removes a dropped path or a stale matcher. On copy and manifest that residual rides on Tier 2's judgment, which is approval-gated, not proven. The marketplace channel has **no Tier-2 analogue** — its consumers run the `marketplace-setup` skill, not `/materialize` — so there a dropped or stale ignore is pruned by nothing automated; it waits on a human. Low-severity, since an over-broad ignore of an absent path is inert, but it is a real asymmetry: marketplace gets only the additive half.
- Tier 1's `.gitignore` refresh reaches all three channels: `materialize.sh` runs it on copy and manifest, and the marketplace `setup.sh` runs the same bundled script on every plugin upgrade (mirroring how it already re-runs `claude-md/refresh-chapters.sh`). Its `settings.json` refresh has **no marketplace analogue**, and needs none: marketplace hooks ship in the plugin's `hooks.json`, registered by the tool from the read-only cache, so the consumer has no harness `settings.json` to keep current. The doctor's `hook-registration` check is skipped on that channel for the same reason.
- A deliberately declined Tier-2 divergence re-prompts each upgrade until the deferred `declined_reconciliations` skip-list is built.

## Implementation

Tier 1: `harness/refresh-gitignore.sh` and `harness/refresh-settings.py`, invoked from `materialize.sh` after the managed-chapters refresh, both no-ops on an up-to-date project (so materialization faithfulness holds). Unit-tested in `harness/test-materialize.sh`. On the marketplace channel, `package-marketplace.sh` bundles `refresh-gitignore.sh` into each plugin and `setup.sh` runs it on every upgrade — the same ensure-present pass, tested in `harness/test-marketplace.sh`; `refresh-settings.py` has no marketplace analogue (hooks ship in the plugin, not the consumer's settings). Tier 2: the `/materialize` skill's step 8 diff-checks `.gitignore`, `.claude/settings.json`, `scripts/layout.toml`, and the `docs/` briefs; step 9 extends the `CLAUDE.md` review to non-doctrine chapters. The `brief_doctor.py` and doctor-skill notes on the `hook-registration` check now describe deterministic registration on upgrade. `declined_reconciliations` is documented as the deferred escape hatch, not added to the templates.

## References

- [Materialize Is a Complete Replacement, Not an Additive Copy](2026-06-13-materialize-complete-replacement.md) — the runtime-only invariant and the no-stored-baseline stance this extends
- [Materialize Proposes Skeleton Improvements to a Project's CLAUDE.md](2026-06-23-materialize-rules-reconciliation.md) — Option 4 (now Superseded), the advisory reconciliation Tier 2 revives and generalizes
- [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](2026-06-24-claude-md-managed-chapters.md) — the deterministic-beats-advisory lesson Tier 1 applies to `.gitignore` and `settings.json`
- [The Handoff Append Is Pre-Approved Per Tool, via a Hook on Claude Code](2026-06-20-handoff-append-pre-approval.md) — the hook registration Tier 1's `refresh-settings.py` now delivers deterministically on upgrade
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the project-owned/runtime split both tiers respect
- [Seed and Harvest at the Root](2026-06-11-root-seed-harvest.md) — the classify-and-ask model Tier 2 runs in the forward direction
- [Project History](../../README.md#project-history) — the what/when timeline
