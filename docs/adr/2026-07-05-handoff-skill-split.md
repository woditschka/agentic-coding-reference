# Split the Handoff Contract by Role; Guard the Log Mechanically

**Status:** Accepted (2026-07-05)

## Context

Every pipeline dispatch preloads its agent's skills. The `pipeline-handoff` skill (4,599 words) bundled three audiences: the coordinator's routing rules, the writers' append contract, and root's review-processing procedures. Four agents preloaded all of it — the coordinator (which never appends) and three Opus-tier writers (product-requirements-expert, system-design-expert, feature-implementer, which never route). Each writer dispatch paid ~6k tokens for routing prose it never used. `review-checklist` (2,761 words) similarly charged all four reviewers for root's stall check and autofix apply procedure. The First Tool Call stanza repeated a 90-word rationale in 17 agent bases (~68 rendered files).

Separately, "append only through `scripts/handoff.py`" was enforced by an allow-hook and prose, but nothing blocked a raw `Write`/`Edit` or shell redirect onto the log, and nothing re-checked log integrity after the fact.

## Options Considered

1. **Trim the two skills in place.** Rejected: the cost is the audience mix, not the prose. Any cut deep enough to matter removes contract, and the writers still preload every routing rule.
2. **Extract rarely-used procedures to on-demand companion files** (e.g. a `recovery.md` loaded via a body pointer). Saved ~1k further tokens on the Sonnet coordinator, but added a model-follows-pointer dependency for recovery correctness. Rejected.
3. **Split the contract by role and preload each part only where it is consumed.** Chosen.

## Decision

**Split the handoff contract along the read/write axis, rename by role, and harden the logic-layer boundary in both directions.**

- **`handoff-append`** (new): the writer contract — sanctioned heredoc append form, append-only discipline, fix-record-never-file, line-number receipt, `next-retry`, per-tool permission setup. Preloaded by every record-writing agent.
- **`handoff-routing`** (renamed from `pipeline-handoff`): the coordinator contract — selection, handoff conditions, gates, recovery, queries — plus the root-applied procedures (reviewer stall check, design-doc autofix) absorbed from the reviewer skill.
- **`review-workflow`** (renamed from `review-checklist`): purely the review-loop contract — roster, fresh-eyes read-set, output protocol, tags, bar clauses, checkpoint rules. The name `review-checklist` misnamed it: the checklists live in the per-stack `*-review` skills.

Writers swap `pipeline-handoff` → `handoff-append` in their skill lists; the coordinator alone loads `handoff-routing`. The First Tool Call stanza compresses to the imperative, the agent's `responding_to` hint, and the full sanctioned append command. It stays inline in every body: Sonnet-tier agents execute it first, and the inline form is exactly what the permission layer pre-approves. No on-demand companion files: routing correctness stays always-loaded (option 2's rejection).

The boundary hardens in both directions. A committed deny hook (`handoff-log-guard.sh`) blocks `Write`/`Edit` tool calls on `.scratch/handoff.jsonl` and unquoted shell redirection/`tee` onto it (Claude Code). The quality gate gains a required `python3 scripts/handoff.py validate` check — the deterministic backstop on every tool, since Copilot, OpenCode, and Junie support no committed deny.

## Consequences

- Implementer, system-design-expert, and product-requirements-expert dispatches each shed ~3,830 preloaded words (~5k tokens): the 4,599-word routing skill out, the 767-word writer contract in. Reviewers trade the moved root procedures (−455 words) for the preloaded writer contract (+767) — net +312 words, accepted to put the write contract inline at Sonnet tier. The coordinator's skill stays ~flat: writer content out, the absorbed root procedures in. No contract was removed — every relocation is preloaded for its actual consumer.
- The write discipline has one home; the never-wrap heredoc warning survives only in `handoff-append`, with pointers elsewhere.
- Raw writes to the log are denied on Claude Code and detected at the gate on every tool.
- The renames fan out across agents, skills, docs, samples, and plugins; the battery (mirror render, faithfulness diffs, doctor) gates the propagation. Prior ADRs keep the old names as history.

## References

- [2026-05-08 — Append-only JSONL handoffs](2026-05-08-append-only-jsonl-handoffs.md): the ledger this contract governs.
- [2026-06-11 — Handoff log access tool](2026-06-11-handoff-log-access-tool.md): established `scripts/handoff.py` as the logic layer the guard now encloses.
- [2026-06-20 — Handoff append pre-approval](2026-06-20-handoff-append-pre-approval.md): the allow-hook; the new deny-hook is its complement.
