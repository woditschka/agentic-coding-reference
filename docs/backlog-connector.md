# Backlog Connector

`/next` picks the next requirement from a candidate set the engine `scripts/backlog.py` computes. The set is every requirement in the PRD, minus what git history records as delivered, minus what the PRD declines or retires. A project-owned script, `scripts/backlog.sh`, is the one hook into that computation. It tells the engine what git cannot know: the team's order and who holds what. Solo work never edits it. A team binds two shell functions to its tracker, and every person's `/next` reads the same board.

The people side of the same problem, who takes which slice and how the merges stay small, is [`human-teams.md`](human-teams.md). The skill itself is [`next`](../harness/core/.claude/skills/next/SKILL.md); the loop it drives is the outer loop in [`agentic-harness.md`](agentic-harness.md#nested-feedback-loops-drive-design-discovery).

## Two Halves, One Command

| Half | Owner | Holds |
|---|---|---|
| `scripts/backlog.py` | Harness; replaced on every upgrade | The candidate set: PRD ids, git-delivered ids, Non-Goals, the Superseded list, and the fold of the board into them |
| `scripts/backlog.sh` | Project; scaffolded once by `init`, never overwritten | Two functions: `backlog_items` (read the board) and `backlog_claim` (mark a pick taken) |
| The `next` skill | Harness | The judgment: slicing tags, dependency checks, the ranking heuristics, and the pick conversation |

The split follows the rule every engine in the harness follows. A deterministic fact lives in data or a script, and judgment lives in a skill ([`harness-project-api.md` § Briefs Feed Agents](harness-project-api.md#briefs-feed-agents-data-files-feed-engines)). The set is computed; the choice is made.

## The Contract

`backlog_items` prints one line per open board item, in the team's rank order, three tab-separated columns:

```text
REQ-ID<TAB>owner<TAB>title
```

- `REQ-ID` is the requirement the item delivers, the id in `docs/prd.md`. Empty means the board carries an item the PRD does not: intake work.
- `owner` is who holds the item. Empty means unclaimed.
- Line order is rank. Line 1 is the team's top pick.
- A line whose first character is `#` is a comment. A title keeps any further tabs. Two rows naming one id count once, the higher-ranked one. Control characters are stripped before the rows are read, so a title can never forge a row.
- In the PRD, the first id on a Non-Goals row is the declined one, and the first id on a Superseded line is the retired one. A later id on the same line names a successor, which stays a candidate. The report lists every excluded id.
- No output means an empty board. A non-zero exit means the board could not be read.

`backlog_claim REQ-ID` moves that requirement's item to in-progress for the current user. It runs once, after the human confirms the pick. A non-zero exit means the move failed.

The skeleton defines neither function. That is the solo mode, and it is a decision, not an omission. The report's first line says `unbound`, and the engine ranks from the PRD and git alone, exactly as with no connector at all. A bound connector whose board is empty prints `0 board items` instead, so the two states never read alike. This is the deliberate difference from `scripts/stack.sh`, where an unbound verb fails the gate by design. An unbound backlog is a valid project; an unbound build is not.

The engine calls the functions through `bash`, so any tracker with a command-line client binds in a few lines. The Jira CLI, the Linear CLI, `gh project`, or a `curl` against a REST endpoint all fit. The skeleton carries an illustrative Jira binding in its header comment.

## What the Report Says

`python3 scripts/backlog.py candidates` prints one report; `--json` gives the same content as data.

```text
connector: scripts/backlog.sh (5 board items)
open (3):
  1  REQ-WX-003  A widget is renamed. Done when: the name updates.
  4  REQ-WX-001  Widgets are listed so users see them. Done when: a list renders.
  -  REQ-WX-005  Widgets are archived. Done when: archived ones hide.  (not on the board)
claimed (1):
     REQ-WX-002  alice  A widget is created from a form. Done when: the form posts.
needs intake (1): board items with no REQ id
  3  Bulk import from CSV
stale on the board (1): the repo records these as closed or unknown
     REQ-WX-009  not in the PRD
excluded: done 0, non-goal 1 (REQ-WX-004), superseded 1 (REQ-WX-006)
```

Each section answers one question a team asks at pick time:

| Section | Question | What the human does |
|---|---|---|
| `open`, ranked | What does the team want next? | Picks from it. The rank is the board's; the skill's slicing tags say whether the top pick is ready. |
| `open`, unranked (`-`) | What is in the PRD but not on the board? | Plans it, or takes it when the board is empty. |
| `claimed` | What is someone already holding? | Leaves it alone. Taking it over is a stated decision with a reason. |
| `needs intake` | What is on the board but not in the PRD? | Runs `/intake` first. A ticket with no requirement cannot enter the pipeline. |
| `stale on the board` | What does the board still list that the repo has closed? | Fixes the board. The repo is the authority for done. |

The last two sections make the reconciliation between the two backlogs mechanical. The PRD as the harness sees it and the board as the team runs it drift, and the report shows the drift instead of hiding it.

Git history is the authority for delivered work. A requirement id in a commit subject or body counts as done, whatever the PRD says beside it. A squash merge that drops the id from the message re-opens the requirement on every teammate's next run. The `/ship` skill puts the id in the subject; a squash policy keeps it in the squashed message.

## Failure Is Asymmetric

A failed read blocks. When `backlog_items` exits non-zero, the engine prints the connector's message and no candidate set. Offering a requirement someone already holds is the defect the connector exists to prevent, so the board being unreadable never degrades silently to solo. The human re-runs with `--no-connector` to rank from git alone, and that flag is the explicit override, never the skill's own fallback.

A failed claim warns. When `backlog_claim` exits non-zero, the engine prints the connector's message and exits non-zero, and the skill continues. The pick is already recorded in the ledger and routed, so the human sees the warning at once and moves the ticket by hand. Blocking there would let a flaky tracker block all work; the ledger is the local truth, and the board is told from it.

A connector that fails to source, or a row whose first column is not a requirement id, is a binding error. It is reported, never treated as an empty board or as intake.

## What the Connector Does Not Do

- **No done hook.** Done is derived from git, and the team's merge flow already moves tickets.
- **No release hook.** A slice abandoned mid-way leaves a claim on the board; the stand-up catches it. The harness owns no tracker state.
- **No claim registry in the repo.** The board holds the claims. A second copy inside the repository would drift from the first.
- **No identity.** The engine never asks who is running it. The connector's own authentication answers that, and the owner column is display only.
- **No sandbox.** The connector is committed code that runs with the invoking user's environment and credentials; it is reviewed like any script under `scripts/`.

## Upgrading

The engine and the rewritten skill arrive with the runtime on every channel. The connector skeleton arrives through `init`, which fills gaps and never overwrites. A project without `scripts/backlog.sh` gets it on its next `/materialize`, which runs `init` for the missing project-owned files. A project on the marketplace channel gets it from the plugin's own `init`. Until the file exists, the engine reports `connector: none` and ranks from git alone, so nothing waits on the scaffold.

`/next` keeps its name, its output shape, and its stop-and-wait contract. The visible additions for a bound team are the `claimed`, `needs intake`, and `stale` lists, and one line after the pick relaying what the connector answered.
