#!/usr/bin/env bash
# Project-owned backlog connector — how `/next` reaches the team's tracker.
#
# The harness-owned engine (scripts/backlog.py) sources this file and calls
# the two functions below. Nothing else in the harness names the tracker.
# Solo work needs no edit: both functions ship as no-ops, and /next ranks
# from the PRD and git history alone. A team binds them to its tracker —
# Jira, Linear, GitHub Projects, any tool with a CLI — so every person's
# /next sees the same order and the same claims.
#
# Contract:
#   - backlog_items: print one line per OPEN board item, in the team's rank
#     order (line 1 is the top pick). Three tab-separated columns:
#         <REQ-ID>  <owner>  <title>
#     REQ-ID is the requirement the item delivers (REQ-XX-NNN, the id in
#     docs/prd.md); leave it empty for an item the PRD does not carry yet —
#     /next lists it as intake work. owner is who holds the item; leave it
#     empty when unclaimed. Print nothing when the board is empty.
#     Return non-zero when the tracker cannot be read: /next then stops
#     instead of offering work someone may already hold.
#   - backlog_claim <REQ-ID>: move the requirement's item to in-progress for
#     the current user. Called once, after the human confirms the pick.
#     Return non-zero when the move fails; /next reports it and the human
#     claims by hand. The pick itself is already recorded.
#   - Define functions only. Do not run commands at the top level of this
#     file; backlog.py sources it.
#
# Example bindings (illustrative — replace with the team's real commands):
#   backlog_items() {
#     jira issue list --plain --no-headers --columns key,assignee,summary \
#       -s"To Do" -s"In Progress" --order-by rank \
#     | awk -F'\t' '{ match($3, /REQ-[A-Z]+-[0-9]{3}/);
#                    print substr($3, RSTART, RLENGTH) "\t" $2 "\t" $3 }'
#   }
#   backlog_claim() {
#     key="$(jira issue list --plain --no-headers --columns key -q "summary ~ \"$1\"" | head -1)"
#     jira issue assign "$key" "$(jira me)" && jira issue move "$key" "In Progress"
#   }

# Open board items, ranked, as `REQ-ID<TAB>owner<TAB>title` lines.
backlog_items() { return 0; }

# Mark the requirement's item as taken by the current user.
backlog_claim() { return 0; }
