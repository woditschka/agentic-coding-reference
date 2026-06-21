# Fresh-Eyes Review Over a Canonical Change Set

**Status:** Accepted

## Context

A reviewer reads `.scratch/implementation-plan.md` — the implementer's working memory — and obtains the diff through an ad-hoc `git diff` with no defined base. Two failures follow.

First, the plan carries the implementer's narrative of intent. A reviewer that reads it judges "does this read cold?" while holding the exact context every future reader lacks. The cold-read that review exists to perform is contaminated.

Second, "the diff" is undefined. A naive `git diff` shows unstaged tracked edits but misses untracked new files. The plan's target-file list is the only thing currently backstopping that gap, so dropping the plan without defining the change set would leave reviewers blind to new files.

The reviewers and the change-grader must judge the same change. Today the grader pins its extraction (working-tree snapshot vs base) while reviewers do not, so the two can disagree about what changed.

## Options Considered

1. **Status quo.** Reviewers read the plan plus an ad-hoc `git diff`. Rejected: contaminates the cold-read and leaves the change set undefined.
2. **Drop the plan only.** Rejected: removes the file-set backstop without defining the change set; reviewers go blind to untracked files.
3. **Free-form project-owned `changeset.sh`.** Rejected: the change set defines review coverage; a hand-edited script can silently drop files and break the grader's determinism — the silent downgrade the harness exists to prevent.
4. **Fresh-eyes read-set plus a canonical change-set primitive** (harness engine, bounded project data), shared by reviewers and grader.

## Decision

**We adopt option 4. A reviewer reads durable memory and a canonically-defined change set, never the implementer's working memory; reviewers and the grader resolve the same change set through one engine.**

- **Read-set.** A reviewer judges the change set against long-term memory (`docs/`), reading the project on demand. It does not take the implementer's plan (`implementation-plan.md`) as review input. It reads the handoff log only to anchor its dispatch — the `build-pass` line — not to mine the design triage; `design-block` lives in that same log, so the discipline there is the reviewer's mandate, not a file it is denied.
- **Change set.** The uncommitted working tree against `HEAD`: tracked-modified, staged, and untracked-but-not-`.gitignore`d, with project `exclude_globs` layered on top. `base = HEAD` is branch-agnostic and needs no trunk configuration.
- **One engine, two consumers.** Reviewers and the change-grader resolve the change set through `scripts/changeset.sh` over the shared engine, so both review byte-identical sets. The grader's default base moves `main` → `HEAD` for the live worktree flow; the `--head`/`--base` override for post-hoc grading is unchanged.
- **The doctor enforces it.** A regression invariant fails any reviewer body that instructs reading the implementer's plan — the one concrete case a deterministic body-grep can catch — and the engine validates `exclude_globs` as bounded project data. Authority lives in the engine and the doctor, mirroring the engine/data split of [layout-sourced schema patterns](2026-06-14-layout-sourced-schema-patterns.md).

## Consequences

**Positive:**
- The cold-read becomes real: `legible-cold` and `semantic-surprise` are judged without the author's framing.
- Reviewers and grader review the same change set by construction, not by coordination.
- The change set fails safe — it carries the whole uncommitted delta plus untracked files, so it can over-include, never under-include.
- No trunk configuration, and the multi-slice-branch concern dissolves: prior slices are committed below `HEAD` and excluded automatically.

**Negative:**
- Two uncommitted units stacked with no commit between them — `refactor-first` without an intermediate commit — review as one delta. Safe (more context, not less); the clean separator is a recorded per-slice base, deferred until the case appears.
- The change set excludes work committed mid-slice. Accepted: the pipeline never commits mid-slice (only `/ship`, terminal), so the live change set is the full slice.
- The grader's base default changes. Accepted: on a feature branch it grades the uncommitted slice, matching the grader's stated premise that no commit exists yet; post-hoc grading is preserved through the explicit override.

## Implementation

**Non-goal:** This ADR records the decision. The rollout is two slices — the change-set primitive first ([refactor-first](../agentic-harness.md) order), then the reviewer read-set on top.

## References

- [Change-Grade Extractor Reads the Uncommitted Working Tree](2026-06-05-change-grade-extractor-worktree.md) — the worktree-snapshot definition this primitive shares
- [Change Grader: Always-On Advisory Risk Read](2026-06-05-change-grader.md) — the second consumer of the change set
- [Additive Reviewer Roster](2026-06-18-additive-reviewer-roster.md) — the roster whose members this read-set governs
- [Principles Over Rigid Rules in Harness Prose](2026-06-03-principles-over-rigid-rules.md) — the read-set is a hard contract; bare imperative, not softened
- [Generic Stack: a Lifecycle-Verb Contract](2026-06-17-generic-stack-verb-contract.md) — the `gate.sh` precedent for a named, project-resolved command surface
