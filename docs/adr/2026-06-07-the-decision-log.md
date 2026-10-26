# The Decision Log Lives at the Root, Is Rewritable Until Published, and Is Compacted at a Boundary

**Status:** Accepted

## Context

The reference accumulated one ADR per harness capability, and each sample carried a near-identical copy. An adopting project inherited records about how the harness was built rather than about its own domain, and every capability multiplied copies. Deleting the history was wrong too: the options and trade-offs behind each capability are the most valuable part of an evolving reference.

Two rules then protected readers of a recorded decision: supersede rather than delete, and write in decision-time voice. Before a decision reaches the remote's default branch there are no such readers, and the rules produce chains nobody is served by. On 2026-10-24 the log held 116 ADRs: 37 carried a status qualifier beyond plain `Accepted`, 2 were superseded outright, and 21 carried an amendment note. The unpushed range held 4 commits and 3 new ADRs; one new ADR carried an amendment note pointing at another new ADR no reader had seen. The maintainer answered with two recurring prompts at feature close: clean up the ADRs, and restructure the unpushed changes into one to three commits.

The published side has the same shape at a larger scale. A standing decision is spread over a chain of files, and a reader wanting the current rule walks it. By 2026-10-26 the log held 118 ADRs for 31 standing decisions.

## Options Considered

1. **All ADRs in both samples.** Rejected: seeds carry build history, duplicated per sample.
2. **Delete the build-history ADRs.** Rejected: the why survives only in git.
3. **The decision log at the root, none in the samples.** Chosen.
4. **Keep the per-commit ADR and the supersede rule as they are.** Rejected: the chain grows with every commit of a feature, and the cleanup prompts recur by hand.
5. **Write ADRs only at feature close.** Rejected on 2026-10-24: decision-time context is the ADR's value, and the tier-1 audit reads the ADR with the commit it explains.
6. **One ADR per feature by rule.** Rejected: a feature holds as many decisions as it holds; the prompting feature held three.
7. **Rebuild the commits by staging paths onto the boundary.** Rejected after a prototype and an adversarial review. It loses rename sources and force-added ignored files, creates trees no gate ran on, and drops author dates.
8. **A publication boundary, with whole-commit regrouping.** Chosen.
9. **Keep the published chain and add a topic index.** Rejected: navigation only; the count stays 118.
10. **Compact the published log at a publication boundary, one ADR per standing decision.** Chosen.

## Decision

**Root `docs/adr/` is the reference's canonical decision log. A decision is a draft until it reaches the remote's default branch, folded at feature close. The published log is compacted at a publication boundary to one ADR per standing decision.**

- **Placement.** Every harness decision is recorded at the root. The samples ship no ADRs; a consumer's `docs/adr/` starts with only the README stub, and its decision log is its own. `docs/project-history.md` is the what/when timeline; the ADRs are the why. Root ADRs reference sample implementations by code span, not link, to stay sample-agnostic.
- **The publication boundary.** An ADR not yet on the remote's default branch is a draft; a later decision of the same feature edits it in place. A published ADR is amended or superseded. The `adr-template` skill and both ADR READMEs state the rule, so it reaches consumers.
- **The draft fold.** The core `prepare-ship` skill folds a feature's drafts and regroups its commits. Its fold scope is every ADR the range touched that is absent from the default branch; its regroup scope is the commits no remote-tracking ref reaches. The two scopes have two boundaries: the merge base with the bound published ref for the fold, and the merge base with the upstream for the regroup. A branch pushed to its tip has an empty regroup scope and still folds. It refuses a merge, a tag, or another author's commit inside the range. The folds commit first; after the regroup, the tree at HEAD equals that commit's tree exactly, or the rewrite is undone. The regroup cherry-picks whole commits in contiguous runs, one group per concern, after one confirmation. Each group keeps the author date of the last commit it folds, and every REQ id survives in its group's message. A doc's reference to a regrouped commit takes a stable label, since the surviving SHA exists only after the rewrite. The skill ships with six named bindings a project may restate; the root front-end adds the project history, the milestone line, the handbook delta, and Opus for judgment steps. It closes with the feature verdict, `/audit-harness` over the range.
- **The published compaction.** At a publication boundary the log is compacted to one ADR per standing decision. Context, Options Considered, Decision, and Consequences are written in the standing state, every amendment applied. The compaction of 2026-10-26 folded 118 ADRs into 31. It is the published-side counterpart of the draft fold and runs as a maintainer operation with no shipped skill, after a push, so the range has one boundary. The compaction rule is the reference's own, because its ADRs ship to no consumer; a consumer's rule is unchanged, supersede rather than delete. A compacted ADR is a new acceptance, not an edit. The ADRs it replaced stay in git under their old paths, and a citation of a folded decision names the holding ADR. Between compactions an accepted ADR is immutable apart from its status line; a new decision is a new ADR.

## Consequences

**Positive:**
- Seeds stay clean, the rationale is discoverable at one root, and a capability adds one ADR, not two sample copies.
- A pushed feature reads as one set of decisions made once; the two cleanup prompts became one invocation with a deterministic inventory, one confirmation, and one undo SHA.
- A reader gets the standing decision from one file, and the index resolves every folded date.

**Negative:**
- A feature's intermediate reasoning leaves the log at the draft fold; the reflog and the folded commits' audit verdicts keep it for the maintainer. At the published compaction it leaves the log too; git keeps the originals under their old paths.
- A consumer that pushes every commit to the default branch through `/ship` has no range to fold.
- The fold's precondition and oracle are prose shell, not a script with a test, and a commit that gated on tier 1 is folded with commits that did not.

## Implementation

`docs/adr/README.md` § Format and `harness/render-adr-index.py`; `harness/core/.claude/skills/adr-template/SKILL.md` and the consumer ADR README template. `harness/core/.claude/skills/prepare-ship/` and the root `.claude/skills/prepare-ship/SKILL.md`; the `audit-harness` range argument; the root `CLAUDE.md` maintainer loop step 4. The `ship` skill's multi-commit note and the once-pushed qualifier in the project history and `update-history`.

## References

- [Skill-Based Agent Architecture](2026-03-22-skill-based-agent-architecture.md) — the architecture this log opens with
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the decision that removed the sample seed ADR: a consumer's `adr/` starts with the README stub
- [Distribution Channels](2026-06-14-distribution-channels.md) — the tag as the published snapshot, which is why a tag inside a range stops the fold
- [Slice Sizing and the Checkpoint](2026-10-20-slice-sizing-and-the-checkpoint.md) — the draft ADR whose in-range amendment prompted the publication boundary
- [Tiered Maintainer Workflow](2026-07-02-tiered-maintainer-workflow.md) — the maintainer loop whose feature-close step runs the fold
- [Project History](../project-history.md) — the what/when timeline these ADRs explain
