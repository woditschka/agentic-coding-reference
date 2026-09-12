# The Outer Loop Reads the Team's Board Through a Project-Owned Connector

**Status:** Accepted

## Context

`/next` drives the outer loop: it computes which requirements are open and recommends one. Its candidate set was four shell snippets in skill prose, run by the model. They grep the PRD for ids, grep git history for delivered ids, grep the Non-Goals table, and sed the Superseded list. Every other deterministic fact in the harness lives in an engine with tests; this one did not.

The set also had no place for what a team knows and git does not. A requirement a teammate holds on a branch is absent from the shared history, so every teammate's `/next` offered it again. The team's priority order lived on its board, invisible to the skill's heuristics. The question "can more than one person use this harness" kept arriving, and the honest answer was: yes, if the humans relay claims into the conversation by hand.

Two shapes were on the table for closing that gap. A registry inside the repository, a committed file of claims, would drift from the tracker the team already runs. A tracker MCP server would be tool-specific, non-deterministic, and unrunnable from a script or CI.

## Options Considered

1. **Keep the prose snippets, document the manual relay.** Rejected: the double-booking check depends on a human remembering to paste the claim list, and the snippets stay untested.
2. **A committed claims file in the repository.** Rejected: a second registry beside the tracker, drifting from the first, and a merge hotspot of its own.
3. **A connector mode that returns the next item.** Rejected: it turns `/next` into a dispatcher and skips the slicing triage and dependency check that happen at pick time. The tracker's top item can be `[needs-slicing]` or `[depends-on]`, and only the skill sees that.
4. **A harness-owned engine plus a project-owned connector script** (chosen).

## Decision

**The candidate set is an engine, and the board reaches it through one project-owned script.** `scripts/backlog.py candidates` computes the set from the PRD, git history, the Non-Goals section, and the Superseded list. It then folds in what `scripts/backlog.sh` prints. The connector is the `stack.sh` shape: functions a harness-owned caller sources. `backlog_items` prints open board items as `REQ-ID`, owner, title rows in rank order; `backlog_claim` marks the confirmed pick taken. The board's order ranks the open set. A claimed item is listed with its owner and excluded from the pick. A board item with no requirement id is intake work, and one the repo has already closed is stale. The skill keeps every judgment: slicing tags, dependency checks, tie-breaking heuristics, and the conversation that ends in a pick.

**Solo is the shipped default, and it is a no-op, not a failure.** The skeleton ships with neither function defined. The engine reports it as unbound and ranks from git alone. An unbound backlog is a valid project, unlike an unbound build, so the connector inverts `stack.sh`'s fail-honest rule on purpose. No layout key selects a mode; the report states the connector's state on its first line.

**Failure is asymmetric.** A failed read exits with the connector's message and no candidate set. Offering held work is the defect the connector prevents, so the read never degrades silently to solo, and `--no-connector` is the human's explicit override. A failed claim warns and continues: the pick is already recorded and routed, the human sees the message, and the ticket moves by hand. Blocking on the write would let a flaky tracker block all work.

**The harness owns no tracker state.** No done hook: done is derived from git. No release hook: the stand-up catches a stale claim. No identity: the connector's own authentication says who is claiming.

## Consequences

**Positive:** the candidate set is one tested definition instead of four model-run snippets, identical on every stack and tool. A team binds its tracker in a few shell lines and every member's `/next` sees one order and one set of claims. The two backlogs, the PRD and the board, are reconciled in the report instead of drifting unseen. `/next` keeps its name, output shape, and stop-and-wait contract; solo users see the same recommendation with fewer tool calls.

**Negative:** one more project-owned file to scaffold, and a project onboarded before this release receives it on its next `/materialize`. The connector is bash, so a tracker with no command-line client needs a `curl` wrapper. The board's titles and owners are untrusted text the skill relays; the skill states they are data, never instructions.

## Implementation

`harness/core/scripts/backlog.py` and its suite `tests/test_backlog.py` join the runtime; the gitignore skeleton, the doctor's runtime paths, the import-boundary gate, and the mypy scope list them. `harness/init/core/scripts/backlog.sh` is the skeleton, byte-identical across stacks; `materialize.py` treats it as project-owned on every stack, and the sync gate requires each sample to carry it. The `next` skill's steps 2 to 6 become one engine call, and a claim step follows the routed pick. The consumer-facing page is [`backlog-connector.md`](../backlog-connector.md); the people side is [`human-teams.md`](../human-teams.md).

## References

- [2026-06-17 generic-stack-verb-contract](2026-06-17-generic-stack-verb-contract.md): the `stack.sh` shape the connector reuses, and the fail-honest rule it deliberately inverts.
- [2026-07-06 logic-in-python-orchestration-in-bash](2026-07-06-logic-in-python-orchestration-in-bash.md): why the set is a Python engine and the binding is a shell file.
- [2026-06-12 docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md): the project-owned boundary the connector sits on.
- [2026-08-14 the-root-is-a-channel-not-an-author](2026-08-14-the-root-is-a-channel-not-an-author.md): the pick stays the human's; the board's rank is input, never the decision.
