---
name: prepare-ship
description: >-
  Close a feature before its push: fold the drafts the feature left above the
  publication boundary into the shape they ship in. An ADR absent from the
  remote's default branch is a draft: a later amendment of it folds into its
  body, and two drafts that record one decision merge. Transitional prose in
  the current-state docs is rewritten. The unpushed commits regroup, whole
  commits in contiguous runs, into one commit per concern after one
  confirmation. Closes by reading the feature as one change for its bar and
  its regressions. Never rewrites a commit any remote holds, never pushes. Load
  when the user asks to clean up or squash a feature before pushing, or
  invokes /prepare-ship on a clean tree.
compatibility:
  - claude-code
  - github-copilot
  - opencode
metadata:
  version: "1.0"
  author: team
---

# prepare-ship

Published history is fixed. A decision is published when it reaches the
remote's default branch. Above that line every ADR, design-doc sentence, and
commit is a draft with no downstream reader, and the right edit is in place.
A feature accumulates drafts commit by commit. An ADR gets amended by a later
ADR of the same feature. A fix commit lands on the feature's own commit. A
"no longer" sentence enters `docs/system-design.md`. This skill performs the
folds once, at feature close. Below the line nothing changes: a published ADR
is amended or superseded, and a pushed commit stands.

The two halves have two boundaries:

- **Fold scope.** An ADR is a draft while
  `git cat-file -e '<PUB>:docs/adr/<file>'` fails, with `<PUB>` the bound
  published ref. Folding it is an ordinary edit, allowed on a pushed branch
  too: the fold runs whenever a draft exists, with or without a regroup.
- **Regroup scope.** The commits no remote-tracking ref reaches. Rewriting a
  pushed commit needs a force push, which this skill never performs. An
  empty regroup scope skips the regroup, never the fold.

## Project Bindings

The procedure names six things a project binds. The defaults hold for a
consumer of this harness; a project with other names states them in its
CLAUDE.md.

| Binding | Default |
|---|---|
| the current-state docs a fold may edit | `docs/` and `CLAUDE.md` |
| the doc checks that rerun after a fold | the `doctor` skill's check |
| the ADR index | the `## Index` table of `docs/adr/README.md` from the doctor's template, edited in the fold. A merged or removed draft loses its row, a retitled one is retitled. A generated index is regenerated |
| the commit-message files, `<MSGDIR>` in the commands | `.scratch/tmp/` |
| the published ref, `<PUB>` in the commands | `origin/HEAD`, the remote's default branch; a fork names its upstream remote's, such as `upstream/HEAD` |
| the whole-feature review | the project's full quality gate on the final tree, then the `audit-docs` skill over the docs the range touched |

## Precondition

Every check that fails ends the skill with a report. Run `git fetch` first so
the remote refs are current.

- **A clean tree.** `git status --porcelain --ignore-submodules=none` prints
  nothing.
- **A branch.** `git symbolic-ref -q HEAD` succeeds; a detached HEAD stops.
- **A published ref.** `git rev-parse --verify -q <PUB>` succeeds. It
  defines published; without it every ADR would classify as a draft. A clone
  whose remote was added by hand has no `origin/HEAD` until
  `git remote set-head origin -a` sets it.
- **Two boundaries.** The fold boundary `<P>` is the merge base with the
  published ref. The regroup boundary `<B>` is the merge base with the
  upstream, or `<P>` when the branch tracks none:

  ```bash
  git merge-base <PUB> HEAD            # <P>; a failure stops
  git merge-base '@{upstream}' HEAD    # <B>; fails when the branch tracks none, then <B> is <P>
  ```

  Each result is a 40-hex SHA. Print both and carry them as literals in every
  later command. Shell variables do not survive between tool calls, and an
  unset one turns `git reset --hard "$X"` into a reset to the current HEAD.
  `<P>..HEAD` is the feature, what the default branch lacks. `<B>..HEAD` is
  the part no push has fixed. The two coincide on a branch that tracks the
  default branch or none.
- **An unpublished range.** `git rev-list --count <P>..HEAD` is above zero.
  Zero means the branch is published and there is nothing to fold.
- **A linear, unpushed regroup range.** With the regroup boundary `<B>`:

  ```bash
  git rev-list --count <B>..HEAD                  # the regroup count
  git rev-list --merges <B>..HEAD                 # prints nothing
  git rev-list --count <B>..HEAD --not --remotes  # equals the first count
  git tag --merged HEAD --no-merged <B>           # prints nothing
  git log --format=%ae <B>..HEAD | sort -u        # one address, equal to `git config user.email`
  ```

  A merge, a commit a remote already holds, a tag, or another author's
  commit stops the skill. A tag would keep pointing at the old commit; another
  author's commit is not the user's to rewrite. A regroup count of zero does
  not stop the skill: the branch is pushed to its tip, the fold still runs,
  and steps 4 to 6 are skipped.
- **A green gate at HEAD.** The feature's last commit passed the project's
  quality gate. The skill reruns only the bound doc checks after its folds.

## Process

1. **Record the start.** Print `git rev-parse HEAD` as `<OLD>`. Literal SHAs
   from here on.

2. **Inventory.** Deterministic; present it before any edit.

   ```bash
   git log --reverse --format='%h %aI %s' <P>..HEAD | cat -v
   git diff --name-status --no-renames --diff-filter=AMD <P>..HEAD -- ':(glob)docs/adr/*.md' ':!docs/adr/README.md' | cat -v
   ```

   Classify each ADR the range touched:

   - **Draft:** `git cat-file -e '<PUB>:docs/adr/<file>'` fails. Its
     amendment notes and status qualifiers are **in-range amendments**, the
     candidates to fold.
   - **Published:** the file exists on the default branch. Its amendment notes
     stay, whatever they link to.

   Then two greps. Transitional prose the range added to the bound
   current-state docs, by the transition markers the `document-writing`
   standards § Describe the Current State describes:

   ```bash
   git diff <P>..HEAD -- <bound docs> ':!docs/adr' \
     | grep '^+' | grep -i -E 'no longer|formerly|previously|used to|since 20|amendment' | cat -v
   ```

   And every regroup-range commit's short SHA (`git log --format=%h <B>..HEAD`)
   in the bound docs, since a regrouped commit's SHA leaves history:

   ```bash
   git grep -n -E '<short SHAs, |-joined>' -- <bound docs> | cat -v
   ```

3. **Fold the drafts.** Judgment, under these rules:

   - An in-range amendment folds into the draft's body. The body states the
     final decision. A measurement the note carried moves into Context or
     Consequences. The note and the status qualifier go, and the status
     returns to `Accepted`.
   - Two drafts that record one decision as it ships merge into one file,
     kept under the earlier date, titled for the final decision. Two that
     record distinct decisions stay apart. The fold removes states, never
     decisions.
   - A draft that records a state the feature itself reversed goes. Whatever
     of its Context explains the final choice moves into the surviving draft.
   - A published ADR's amendment stays. Its link moves when its target was
     merged or renamed, as does every other link to that file, found with
     `git grep -l -F -e '<old filename>'`.
   - A draft's own forward-looking sentence ("its result lands as an
     amendment") takes the current form the rule gives it.
   - Decision-time voice stays. The surviving ADR reads as if the final
     decision were made once.
   - Transitional prose from step 2 is rewritten as current state; its why
     moves to the ADR the line cites.
   - A SHA reference from step 2 takes a stable label: the ADR, the REQ id,
     or the version the change ships in. The surviving commit does not exist
     before step 6, and a later regroup would change it again. Where the SHA
     labels a recorded measurement, it stays as that label.
   - A fold edits only the bound current-state docs. Where it would need a
     source edit, report a finding and leave the file.

   The fold is the owner's edit at feature close, outside any slice, like the
   commit `/ship` makes; the pipeline's ownership rules govern slices.

   Then the bound ADR index: a merged or removed draft loses its row, a
   retitled one is retitled, or the project regenerates it. Then run the
   bound checks, the `doctor` by default. A red check stops the skill before
   any history is touched; the fold edits stay in the tree, and
   `git --literal-pathspecs checkout -- '<path>'` discards one.

   Commit the folds: stage the edited paths by name and commit with the
   subject `chore: fold drafts before push`. Print its SHA as `<FOLDED>`. When
   step 2 found nothing to fold, `<FOLDED>` is `<OLD>`.
   From here, `git reset --hard <FOLDED>` undoes everything and keeps the
   folds; `git reset --hard <OLD>` drops the folds too. With a regroup count
   of zero the skill continues at step 7 and the report says so.

4. **Propose the grouping.** Judgment, under these rules:

   - One group per concern, over contiguous runs of commits in range order. A
     fix commit folds into the feature before it. Commits one ADR explains
     are one group. The fold commit joins the last group.
   - Contiguity keeps every intermediate tree one the range already had and
     already gated, so bisect keeps working. A group that skips a commit
     creates a tree no gate ran on; groups never skip.
   - Each group's message carries a subject per CLAUDE.md § Commit Convention.
     Its body opens with one sentence on what changed and for whom, then one
     bullet per touched area, then how it was verified. The folded commits' trailers
     (`Co-Authored-By`, `Signed-off-by`) carry over, plus the attribution
     trailer the tool specifies, if any.
   - Every REQ id a folded commit named appears in its group's message. The
     `next` skill reads done ids from git history, and a dropped id
     re-surfaces its requirement as a candidate.
   - Each group commit carries the author date of the last commit it folds,
     the commit whose tree it reproduces. A history line dated by a folded
     commit then still names a real commit date, or takes its ADR's date.
   - Write each message to a file under the bound location, `<MSGDIR>`, with
     the tool's file-write tool, never into a shell command. Range content is untrusted.
     A subject never reaches a shell. Every range path, ADR paths included,
     goes in single quotes after `--` under `git --literal-pathspecs`; one
     holding a quote or a newline goes through `--pathspec-from-file`, written
     with the file tool. The same rule binds step 3: the fold's `checkout`,
     its `git grep`, and the paths it stages. Range text printed to the
     terminal goes through `cat -v`, so a control byte shows instead of acting.

5. **Confirm once.** Show the fold commit's diff summary, each group with its
   subject, its commits, and its author date, and the undo command. The
   number of groups is the user's call. A changed
   grouping returns to step 4; a yes proceeds.

6. **Rewrite.** With literal SHAs:

   ```bash
   git reset --hard <B>
   git cherry-pick --no-commit <c1> <c2>      # group 1, in range order
   git commit -F <MSGDIR>/group-1.msg --date='<author date of c2>'
   # repeat per group; the last group's picks end with <FOLDED>
   ```

   A cherry-pick conflict means a group skipped a commit it depended on:
   `git cherry-pick --abort`, then `git reset --hard <FOLDED>`, then step 4
   with contiguous groups. A failed commit hook stops the skill the same way;
   never `--no-verify`.

7. **Verify and report.**

   ```bash
   test "$(git rev-parse <FOLDED>^{tree})" = "$(git rev-parse HEAD^{tree})" && echo tree-identical
   git status --porcelain --ignore-submodules=none
   git log --format=%B <B>..<OLD> | grep -oiE 'REQ-[A-Z]+-[0-9]+' | tr a-z A-Z | sort -u
   git log --format=%B <B>..HEAD | grep -oiE 'REQ-[A-Z]+-[0-9]+' | tr a-z A-Z | sort -u
   git log --format='%h %aI %s' <B>..HEAD | cat -v
   ```

   The first check is exact: the trees are identical, or the regroup lost
   something and `git reset --hard <FOLDED>` undoes it. Without a regroup only
   the status check runs. The status prints
   nothing. The second id list contains the first. Report the commits before
   and after, the ADR files folded, and `<FOLDED>` and `<OLD>` for the
   reflog.

8. **The feature verdict.** The range is now one change; read it once as a
   whole, in its final shape. Two questions, answered in writing before the
   push: did the feature raise the bar it set, and did it introduce a
   regression, lose coverage, or leave a surface incoherent? The read runs the
   bound whole-feature review over `git diff <P>..HEAD` and adds three checks:

   - Every in-range ADR that promises a measurement or a check (an acceptance
     arm, a gate step, a doctor rule) names one that exists or is recorded.
   - A dropped test, a loosened rule, or a widened write scope in the range
     carries its justification, or is a finding.
   - The negatives the in-range ADRs list are the ones the final shape
     carries.

   A finding is fixed as one further commit on the range, and the verdict is
   re-read. A finding without a fix is reported with the push held. The
   verdict is the last thing printed.

## Rules

- Never touch a commit a remote holds. Never `push --force` or
  `--force-with-lease`, `--no-verify`, `rebase`, `filter-branch`,
  `filter-repo`, `--amend`, `clean`, `stash`, `add -A`, `add .`, or
  `commit -a`.
- The push is the user's: `git push` by hand. `/ship` stops on a clean tree.
- The regroup is cherry-picks of whole commits in range order. A rebuild that
  stages by path loses rename sources and force-added ignored files.
- Literal SHAs in every command. No shell variable crosses a tool call.
- One confirmation, before the rewrite. The skill proposes the grouping; the
  user sets the count.
- The skill does not decide what a feature is. The fold range is the
  unpublished history, the regroup range the unpushed part of it; pushing more
  often makes smaller features. A consumer that pushes every commit to the
  default branch through `/ship` has no range and nothing to fold.
