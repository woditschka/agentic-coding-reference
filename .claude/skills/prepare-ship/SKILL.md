---
name: prepare-ship
description: >-
  Close a feature of this reference before its push: fold the unpushed range
  (origin/main..HEAD) into the shape it ships in. Front-end for the core
  prepare-ship skill (harness/core/.claude/skills/prepare-ship/SKILL.md),
  stating the root's bindings: the ADR index renderer, the quick battery or
  propagate-harness, the project history, and the battery as the green gate.
  ADR drafts fold to one ADR per decision; the commits regroup, whole commits
  in contiguous runs, into one per concern after one confirmation. Closes
  with the feature verdict: /audit-harness over the range. Never
  rewrites a pushed commit, never pushes. Run on a clean tree once the
  feature's last commit has landed, before /release-version. Root-only
  (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# prepare-ship

The procedure is the core skill's
([`harness/core/.claude/skills/prepare-ship/SKILL.md`](../../../harness/core/.claude/skills/prepare-ship/SKILL.md)):
precondition, inventory, fold, group, confirm once, rewrite, verify, verdict. This
front-end states the root's values for the six bindings the core skill names,
four further names the procedure uses at the root, and the additions the
root's own docs need
([the publication-boundary ADR](../../../docs/adr/2026-06-07-the-decision-log.md)).

## Root Bindings

| Name in the core skill, or the root's own | At the root |
|---|---|
| the current-state docs a fold may edit | root `docs/*.md`, `CLAUDE.md`, and the prose under `/harness`, the shipped skills' text. `samples/` and `plugins/` follow through propagate, which the battery gates |
| the doc checks that rerun after a fold | `harness/verify-harness.py --quick`; `harness/propagate-harness.sh` instead when a fold touched `/harness` |
| the ADR index | `python3 harness/render-adr-index.py`; never hand-edited |
| the commit-message files, `<MSGDIR>` | the session's temporary directory; the root has no `.scratch/` |
| the boundaries `<P>` and `<B>` | the merge base of `origin/main` and HEAD, one 40-hex SHA carried as a literal. The main-only root tracks the published branch, so both boundaries coincide |
| the published ref, `<PUB>` | `origin/HEAD`, which resolves to `origin/main` |
| the green gate at HEAD | the battery, green at every commit under the maintainer loop's tier 0 and enforced at push. Tier 1 on the substantive commits is the owner's (maintainer loop step 3) |
| the `next` skill's REQ ids | none; the root has no PRD |
| the attribution trailer | the `Co-Authored-By` line the root commit convention requires |
| the whole-feature review | `/audit-harness <B>..HEAD`, tier 1 over the range; `/audit-harness full <B>..HEAD` when the range retires, renames, or changes a default |

## Root Additions

- **The project history.** `docs/project-history.md` lines in the range are
  drafts: one line per shipped milestone, each dated by a surviving commit or
  by its ADR. A line for a folded-away state goes. Pushed lines are never
  re-dated or rolled up.
- **The milestone line.** `/update-history` runs over the range before the
  fold commit, so a missing milestone is proposed while the commits that
  carry its date still exist.
- **The handbook delta.** A fold that touches `docs/agentic-harness.md` also
  touches its installed copy, or the battery's handbook-delta step fails.
- **Judgment runs on Opus.** The fold and the grouping are delegated to one
  Opus subagent carrying the inventory and the core skill's rules; the
  mechanical steps run here.

## What Follows

A clean tree after `/prepare-ship` is the input `/release-version` expects,
and the release commit is pushed as cut. The order matters: a tag inside the
range stops the skill, so the fold runs before the cut.
