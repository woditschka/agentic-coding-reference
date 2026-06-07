# Change-Grade Extractor Reads the Uncommitted Working Tree

**Status:** Accepted

## Context

The change-grader runs as the terminal hop after the four reviewers approve and
before the human commits. Its extractor (`scripts/score-change.py extract`)
diffed `merge-base(base, HEAD)..HEAD`. At grader time the change has no commit
yet — it lives in the working tree — so that range is empty and every diff facet
comes back null. The grader was blind to the change it grades, and the
[`change-grade-report`](2026-06-05-change-grade-report.md) ADR deferred the
populated `Extracted:` line on exactly this gap.

## Options Considered

1. **Snapshot the working tree into a throwaway index (chosen).** One `git diff`
   covers staged, unstaged, and untracked changes through git's own machinery
   (renames, binary detection, hunks), with no mutation of the real index.
2. **`git diff <base>` plus per-file handling of untracked files.** Rejected:
   `git diff <base>` misses untracked new files, so each would need a separate
   `--no-index` pass — more code, more subprocess calls, easy to drift from git's
   numstat semantics.
3. **Move the grader after the commit.** Rejected: the grade exists to inform the
   human's commit/merge decision; producing it post-commit inverts the order and
   reframes the advisory node as a gate.

## Decision

The extractor diffs the base against a snapshot of the live working tree by
default. It stages every worktree file — tracked edits, deletions, and untracked
non-ignored files — into a throwaway index under `.scratch/tmp`. It then writes a
tree object and diffs `merge-base(base, HEAD)..<that tree>`. `git add -A` honours
`.gitignore`, so build output and scratch stay out. The real index and working
tree are never read or written.

The record gains a `head_kind` field: `worktree` for the default snapshot,
`commit` for the `--head <ref>` escape hatch that grades an already-committed
range after the fact. With the row now populated pre-commit, the report's
`Extracted:` line renders in the normal flow.

Determinism holds, conditioned on the working tree rather than a commit: the tree
is content-addressed, so an unchanged working tree hashes to the same SHA and two
runs agree. The tree SHA is recorded in `head_ref`, so the graded snapshot is
identifiable.

## Consequences

- The grader reads the actual change; the `Extracted:` line populates.
- `git add -A` hashes the worktree into dangling blobs git GCs later — cheap, and
  the throwaway index never touches the real one.
- Determinism is now conditioned on working-tree content, not a pinned commit.
  That is the correct contract for a pre-commit advisory: the graded artifact is
  the uncommitted change.

## Implementation

**Non-goal:** This is a harness tooling decision, not a feature requirement.
Implementation lives in
[`scripts/score-change.py`](../../scripts/score-change.py) (the snapshot and the
`--head` mode),
[`schemas/scratch/grader-features.schema.json`](../../schemas/scratch/grader-features.schema.json)
(the `head_kind` field), and
[`.claude/skills/change-grading/SKILL.md`](../../.claude/skills/change-grading/SKILL.md)
(the protocol and determinism prose). No code under `internal/` or `cmd/`
changes.

## References

- [`2026-06-05-change-grade-report.md`](2026-06-05-change-grade-report.md) — deferred the populated `Extracted:` line that this resolves
- [`2026-06-05-change-grader.md`](2026-06-05-change-grader.md) — the original change-grader decision
- [`.claude/skills/change-grading/SKILL.md`](../../.claude/skills/change-grading/SKILL.md) — the grading protocol
