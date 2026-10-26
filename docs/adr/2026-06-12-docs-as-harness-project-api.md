# The Project's Docs Are the Harness–Project API

**Status:** Accepted

## Context

The harness reaches a consumer by copying files out and harvesting improvements back. With more than five downstream projects, every harness release once cost one merge session per project, and a consumer who rewrote the testing philosophy was overwritten on upgrade. The testing policy was restated in five places per sample; drift was caught only after the fact.

Three later forces shaped the boundary inside the consumer's tree. A real migration (ccledger) carried two project-authored skills under `.claude/skills/` with nowhere durable to live, and received all tool surfaces whether it used them or not. Harness doctrine inside the project-owned `CLAUDE.md` (relay discipline, orchestrator economy, memory, writing standards) could reach an installed project only through a consented edit. The orchestrator was 44.6% of one project's spend, and the directive that trimmed it reached only greenfield consumers. Five doctrine chapters were byte-identical across three stack skeletons and had drifted in eight spots. Finally, transcript analysis needed each session attributed to a harness version; the version appeared in roughly 3% of transcripts, because only an opened brief carried it.

## Options Considered

1. **Status quo: seed by copy, merge per project.** Rejected: O(N) upgrades and preference collisions.
2. **Policy-variant skills plus a `conventions.md`.** Rejected: consumers would author skills instead of editing documents, sibling-skill loading is model-mediated, and a conventions file duplicates the role the briefs already play.
3. **Project docs as the API, harness versioned above them.** Chosen.
4. **Per-language runtime plugins.** Rejected: language variation is data (stack-indexed defaults) beside one universal core.
5. **Make all of `CLAUDE.md` harness-owned.** Rejected: it carries build commands and local rules; replacement clobbers customization.
6. **`@import` a harness-owned doctrine file.** Rejected: only Claude Code expands it; the doctrine would silently fail to load elsewhere.
7. **Marker-comment blocks (`BEGIN`/`END`) around managed spans.** Rejected: machine syntax in human-facing files; a chapter already has an identity in its `## ` heading.
8. **Advisory model reconciliation of `CLAUDE.md` on every upgrade.** Adopted 2026-06-23, then replaced: the prompt re-fired on every doctrine change, on every project. It survives only as the advisory tier over content that legitimately diverges.
9. **Version-stamped baseline plus three-way merge.** Rejected: a deleted section is indistinguishable from one never received, and the stamp is a new tracked artifact.
10. **Git SHA or semver as the session stamp.** Rejected: a SHA cannot be ordered into a trend and changes every commit; a semver exposes internal coupling in a project file.

## Decision

**The harness is a team; the project's `docs/` folder is the brief it reads, the expectation spec is the API, and everything harness-owned inside a project-owned file refreshes deterministically.**

- **Kernel, closed.** TDD-first; the four strategic-DDD properties (ubiquitous language, bounded modules, isolated domain core, state-vs-history split); spec-driven delivery; the append-only ledger. Principles-over-rules with the writing standards; the record, tag, and verdict vocabularies. Selection over configuration.
- **Project truth, consumer-owned.** `prd.md`, `system-design.md`, `adr/`, `ubiquitous-language.md`, `testing-principles.md`, `architecture-principles.md`, `security-principles.md`. Values live inside the briefs; there is no conventions file. Skills read briefs at dispatch via roster and `reads:` declarations, never via links. Documents reference downward only.
- **Handbook, harness-owned.** The method docs ship with the harness and are never committed downstream; runtime surfaces never reference handbook paths. A consumer's `adr/` starts empty.
- **Agents adopt the brief** as their own convictions and raise brief-defect findings instead of compensating.
- **The expectation spec is the formal API.** `docs/harness-project-api.md` is the human-readable spec. The machine-checkable subset is `scripts/doctor-expectations.toml` read by the stdlib engine `scripts/doctor.py`, project-relative so every channel resolves it. The `audit-docs` skill holds the judgment checks. The doctor blocks deterministically; judgment is advisory, judges form never philosophy, and never contains philosophy terms.
- **Briefs feed agents; data files feed engines.** Engine-consumed facts live in `scripts/layout.toml`. Its `[harness]` table declares `channel` (copy by default), `tools`, and `extensions`. `tools` lists the surfaces installed: claude always on, copilot and opencode optional, and an upgrade never adds one. `extensions` lists runtime-relative paths the project owns: never pruned, excluded from the untracked-runtime check, re-included in the gitignore block. Classification of an unknown runtime file is set arithmetic, present − produced − extensions − retired; judgment is the fallback only for paths the retired-paths manifest predates.
- **Stack-agnostic core; language is data.** The runtime carries no stack-specific fact; defaults are a stack-indexed library picked by the consumer's build marker. Root `/harness` is the one source; samples are materialized outputs, never hand-edited.
- **Harness-owned content inside project-owned files refreshes without a prompt.** Five managed chapters of `CLAUDE.md` are the `## ` sections of `harness/claude-md/managed-chapters.md`. `harness/claude-md/refresh-chapters.py` rewrites each from its heading to the next on every materialize, init, and marketplace setup. Order is set once and never disturbed; content is byte-identical across stacks; stack-specific skill rows live in a project-owned chapter. The doctor's `required-chapter` check fails on a missing or empty chapter. The same writer upserts one first line, `<!-- harness: YYYY-MM-DD -->`, from `harness/VERSION-DATE`, which `release-version` stamps beside `harness/VERSION`. The stamp is the release date, never the run date, so re-materializing is byte-identical. The doctor's `harness-stamp` check rejects a missing, duplicated, or malformed stamp. Briefs carry the same token on line 1 as scaffold provenance; session attribution keys on `CLAUDE.md` alone. `harness/refresh-gitignore.py` and `harness/refresh-settings.py` ensure the runtime ignore paths, the agent-teams env flag, and every hook matcher the settings skeleton declares, under its event. They identify ownership by exact match against the template: additive, marker-free, never removing a project's own lines.
- **Everything else project-owned changes only by consented proposal.** The `/materialize` skill diffs each template-seeded file (`.gitignore`, `settings.json`, `layout.toml`, the briefs, the non-doctrine `CLAUDE.md` chapters) against its shipped template. A deliberate project change is preserved; a harness migration is proposed; a collision shows both versions to the human. Declines are not persisted. The enforcing agent owns the brief it reads and edits it only as a consented diff.
- **Distribution.** Runtime content follows one declared channel per repo (copy, manifest, marketplace), owned by the distribution-channels decision.

## Consequences

**Positive:**
- Each fact lives once; upgrades are a version bump plus review feedback instead of a merge.
- Consumer divergence is collision-free by construction.
- Doctrine reaches every installed project and every tool with zero prompts; the three-way duplication of five chapters collapses to one source.
- Session attribution rises from about 3% to every transcript, extractable by one regex.
- Project files carry no markers, no stamp beyond one line, and no new tracked artifact.

**Negative:**
- Prose policy is less checkable than structured config, so a weak brief degrades review fidelity gradually.
- `CLAUDE.md` is a hybrid file; a project that writes inside a managed chapter loses that text on refresh, caught only by the post-refresh review.
- Stack-specific skill rows no longer auto-upgrade.
- Two refresh mechanisms coexist: the deterministic tier adds, the advisory tier removes and judges. A declined proposal re-surfaces on the next run.
- The marketplace channel gets only the additive half, and its hooks ship in the plugin, so it has no `settings.json` refresh.
- Recovering a version name from the stamp needs the release timeline.
- The expectation spec is a public API; changes to it are breaking changes for consumers.

## References

- [2026-06-11-materialize](2026-06-11-materialize.md) — the install that applies this contract: complete runtime replacement, extras classification, and the refreshes above
- [2026-06-14-distribution-channels](2026-06-14-distribution-channels.md) — the copy, manifest, and marketplace channels the runtime follows
- [2026-06-14-the-doctor](2026-06-14-the-doctor.md) — the deterministic gate that enforces the spec, the chapters, and the stamp
- [2026-06-14-layout-declares-the-project](2026-06-14-layout-declares-the-project.md) — the engine-read data file that carries the `[harness]` table
- [2026-06-13-documentation-standards](2026-06-13-documentation-standards.md) — the form the kernel requires of every brief
- [2026-06-03-principles-over-rigid-rules](2026-06-03-principles-over-rigid-rules.md) — the form requirement the expectation spec enforces
- [2026-06-18-the-reviewer-roster](2026-06-18-the-reviewer-roster.md) — `extra_reviewers`, the other `[harness]` declaration that leans on `extensions`
- [`docs/harness-project-api.md`](../harness-project-api.md) — the spec itself: roster, required sections, managed chapters, versioning
- [`docs/adoption-guide.md`](../adoption-guide.md) — the consumer-facing statement of the contract and the channels
