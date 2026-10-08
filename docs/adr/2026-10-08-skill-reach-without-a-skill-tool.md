# An Agent Reaches a Skill by Preload or by Path, Never by Search

**Status:** Accepted

## Context

Every harness agent lists its tools explicitly, and none lists the Skill tool. An agent reaches a skill two ways: the `skills:` preload injects a skill's content at dispatch, and the body names further skills to consult. On the copy and manifest channels the named skills sit in the project under `.claude/skills/`, so a body that says "load the X skill" is honored by reading the file. On the marketplace channel the skills sit in the plugin cache and the project holds no `.claude/skills/`, so the same instruction has no target.

A marketplace consumer's product-requirements expert reported that it could not load its skills. Its preloaded skills were in context. The skill it could not reach was one it cites and executes on every dispatch, the Scoping Pre-Check in the `tdd-workflow` skill, which it did not preload. Probes with the shipped plugin, the agent pinned to Haiku, showed the preload resolving plugin skills on every run. A cited but unpreloaded skill was reached once, by guessing a cache path from the preload's base directory, and missed once. Claude Code's documentation states that `${CLAUDE_PLUGIN_ROOT}` is substituted in a plugin agent's body; a probe confirmed the absolute cache path arrives expanded.

The body links in question also used the agents-directory-relative form `../skills/<name>/<file>`, which never resolved from a subagent's working directory on any channel.

Root is different. It holds the Skill tool, and an invocation names the skill's directory, so root reaches a skill's supporting files through the invocation. The agents do not, which is why their path has to be stated.

## Options Considered

1. **Preload every cited skill.** Reliable on every model and channel. Rejected as the default: the product expert's four cited skills add about 8,400 words to every dispatch, and the largest is consulted for one section.
2. **Grant the Skill tool.** Rejected: it widens every agent's tool surface and its call budget for a lookup the body already names, and OpenCode has no equivalent.
3. **A path formula from the preload's base directory.** Rejected: the base-directory line is observed behavior, not documented, and a formula is one more inference for a weaker model.
4. **Preload what every dispatch executes; state every other reference as a project path the packager rewrites per channel** (chosen).

## Decision

**On Claude Code, a skill an agent executes on every dispatch is in context at dispatch.** The two experts' scope and length checks are restated in their bodies as the role's statement of the contract. `tdd-workflow` is named as its canonical home, and no load of it is needed. The reviewer statement in `review-workflow` already follows that pattern. The restatements are role-specific where the canonical text is not: an expert's overrun ends in a consultation request, never a partial artifact. OpenCode and Copilot preload nothing, so there the restatement is what holds and every other skill is an on-demand read. The writing standards in `document-writing` stay on demand for the experts: the `prd-authoring` skill they preload carries the pre-handoff self-check, and the doc-reviewer, which preloads the standards, gates the result.

**Every other skill reference is an on-demand read by path.** Each agent's Skills section carries one rule: a skill not preloaded is read on demand, never searched for, under `.claude/skills/<name>/`. Body links use that project-relative form. The marketplace packager rewrites the prefix to `${CLAUDE_PLUGIN_ROOT}/skills/` in the Claude plugin's agent bodies, so the path a subagent reads is absolute after substitution. Copilot has no such variable, so its render names the installed plugin's `skills/<name>/` and drops the no-search clause; locating the install is that tool's own step.

**The battery gates the contract.** Every base agent carries the rule in its Skills section, no base body links `../skills/`, and every `skills:` preload name is a shipped skill. No rendered plugin agent carries the project form, and only Claude's carry the plugin-root variable. An empty scan fails rather than passes.

The doctrine pointers a body does not execute, the loop model and the conversations-stay-in-root rule, keep the skill name and drop the link. The implementer's gate-failure sentence names the record it appends and leaves recovery to `route`, which owns it.

## Consequences

- The product expert's step 1 grows by 75 words and the design expert's by 65. Every agent gains the 19-word rule; the experts, the implementers, and the doc-reviewer lose a link or a citation.
- A lazy read is a mechanical step on every model. Whether a model performs it when it should remains prompt-side discipline, confined to skills consulted on occasion.
- A new on-demand reference in a body uses the project form; the packager and the gate carry it to the plugin.
- A Copilot marketplace consumer's on-demand read names the installed plugin's `skills/<name>/`; whether a Copilot subagent locates the install is unverified here.
- A re-split reaches the pipeline only through the human. The design expert's `conflicting` verdict halts the run with the split named, and a fresh scoping produces entries that pass Gate 1. An in-pipeline split that passes Gate 1 without that halt is a routing design change, left open.
- The pre-check doctrine has one canonical statement and five restatements: the reviewer's in `review-workflow`, the product expert's, and the design expert's in each of three stacks. The battery pins all six in `harness/scoping-pre-check.expected`; a change to any one fails until every restatement is reviewed and the pin regenerated.

## Implementation

`harness/package-marketplace.py` carries the per-tool rewrite table; `harness/verify_harness/checks/sync.py` carries the gate, with its unit test in `harness/tests/test_verify_harness.py`; the on-demand rule sits in every base agent under `harness/core` and `harness/stacks`.

## References

- [2026-06-24 CLAUDE.md managed chapters](2026-06-24-claude-md-managed-chapters.md) — the chapters that name skills by unit on every channel; this ADR extends the same rule to the agent bodies.
- [2026-08-02 plugin-shipped init](2026-08-02-plugin-shipped-init.md) — the marketplace channel whose project side holds no skills, the condition this ADR exists for.
- [2026-08-01 shared plugin namespace](2026-08-01-shared-plugin-namespace.md) — the Copilot plugin this ADR leaves with a residual.
