# History Is Rewritable Until Published

**Status:** Accepted

## Context

The decision log says "supersede rather than delete", and a commit that records a decision writes its ADR in decision-time voice. Both rules protect readers who relied on a recorded decision. Before a decision reaches the remote's default branch there are no such readers, and the rules then produce chains nobody is served by. The log holds 116 ADRs. 37 carry a status qualifier beyond plain `Accepted`, 2 are superseded outright, and 21 carry an amendment note. The unpushed range on the day of this decision held 4 commits and 3 new ADRs. The new ADRs amended 3 published ADRs, which is the rule working as intended. One new ADR, the plan-file ADR of 2026-10-20, also carried an amendment note pointing at another new ADR no reader had seen. Its pending acceptance-arm result would have become a second note on the same file.

The maintainer answered this with two recurring prompts at feature close. The first: clean up the ADRs and the design docs, removing intermediate and superseded states that will not ship. The second: restructure the unpushed changes into one to three coherent commits. Both prompts restate one rule the harness did not hold: a decision nobody has read yet is a draft.

## Options Considered

1. **Keep the per-commit ADR and the supersede rule as they are.** Rejected: the chain grows with every commit of a feature, and the two cleanup prompts recur by hand.
2. **Write ADRs only at feature close.** Rejected: the decision-time context is the ADR's value, and the tier-1 audit reads the ADR with the commit it explains. The per-commit ADR is the better draft.
3. **One ADR per feature by rule.** Rejected: a feature holds as many decisions as it holds. The feature that prompted this held three distinct ones, and merging them would hide two.
4. **Rebuild the commits by staging paths onto the boundary.** Rejected after a prototype and an adversarial review. A rebuild by path loses rename sources and force-added ignored files, and creates trees no gate ran on. It drops author dates, and it collapses to one commit whenever two concerns share a file. At the root the ADR index and the project history are in nearly every feature commit.
5. **A publication boundary, with whole-commit regrouping.** Chosen. A decision is published when it reaches the remote's default branch. Below that line, on the published side, supersede and amend. Above it, among the drafts, edit in place, and fold them once at feature close. The commits regroup as cherry-picks of whole commits in contiguous runs.

## Decision

**We adopt option 5: history is rewritable until published, and `/prepare-ship` folds it at feature close.**

- An ADR that has not reached the remote's default branch is a draft. A later decision of the same feature edits it in place. A published ADR is amended or superseded as before. The `adr-template` skill and both ADR READMEs state the rule, so it reaches consumers through the skill.
- A core skill, `prepare-ship`, performs the fold. Its fold scope is every ADR the range touched that is absent from the default branch, an ordinary edit even on a pushed branch. Its regroup scope is the commits no remote-tracking ref reaches, since rewriting a pushed commit would need a force push. The two scopes have two boundaries: the merge base with the bound published ref, and the merge base with the upstream. A branch pushed to its tip has an empty regroup scope and still folds. The skill refuses a merge, a tag, or another author's commit inside the regroup range. A doc's reference to a regrouped commit's SHA takes a stable label, since the surviving SHA exists only after the rewrite.
- The folds are committed first. That one commit is the undo and the oracle: after the regroup, the tree at HEAD equals the fold commit's tree exactly, or the rewrite is undone.
- The regroup cherry-picks whole commits in contiguous runs, one group per concern, after one confirmation. Every intermediate tree is then a tree the range already had and already gated, and each group commit keeps the author date of the last commit it folds. A fix commit folds into the feature before it. Every REQ id a folded commit named survives in its group's message, since `/next` reads done ids from history.
- The skill ships in `harness/core` to every consumer with six named bindings a project may restate. They are the current-state docs a fold may edit, the doc checks that rerun, the ADR index, the commit-message files, the published ref, and the whole-feature review. The root keeps a thin front-end of the same name. Its current-state docs include the prose under `/harness`, the shipped skills' text, with propagate as the follow-through. It states the root's values and four additions: the project history, the milestone line, the handbook delta, and Opus for the judgment steps.
- The skill closes with the feature verdict, the range read once as one change. Did it raise the bar it set? Did it introduce a regression, lose coverage, or leave a surface incoherent? At the root that read is `/audit-harness` over the range, which gains a range argument for it.

## Consequences

**Positive:**
- A pushed feature reads as one set of decisions made once, with the amendments that remain all pointing at published history.
- The two cleanup prompts become one invocation with a deterministic inventory, one confirmation, and one undo SHA.
- The number of ADRs and commits per feature stays what the feature's decisions and concerns require. The fold removes states, not decisions.

**Negative:**
- A feature's intermediate reasoning leaves the log at the fold. The reflog and the audit verdicts of the folded commits keep it for the maintainer; the published log never had it.
- A consumer that pushes every commit to the default branch through `/ship` has no range to fold. The skill serves the consumer that batches commits, or works on a branch, before the merge; the rule serves everyone.
- The precondition and the oracle are prose shell, not a script with a test. A script follows once the skill has run on a few features and its checks have settled.
- A commit that gated on tier 1 is folded with commits that did not. The front-end names tier 1 as the owner's responsibility; the skill cannot verify it.

## Implementation

**Non-goal:** This is process, not a feature requirement. Surfaces:

- the core `prepare-ship` skill, with its rows in the managed CLAUDE.md chapters and the agents READMEs
- the root front-end `.claude/skills/prepare-ship/SKILL.md`, and the range argument of `audit-harness`
- the `adr-template` skill § When to Create an ADR, the consumer ADR README template, and `docs/adr/README.md` § Format
- the `ship` skill's multi-commit note, and the once-pushed qualifier in the project history and `update-history`
- the root `CLAUDE.md` maintainer loop step 4 and skills table

## References

- [The Implementer Keeps No Plan File](2026-10-20-the-implementer-keeps-no-plan-file.md) — the draft ADR whose in-range amendment, since folded, prompted this decision
- [Marketplace Plugin Channel](2026-06-14-marketplace-plugin-channel.md) — the tag as the published snapshot, which is why a tag inside the range stops the fold
