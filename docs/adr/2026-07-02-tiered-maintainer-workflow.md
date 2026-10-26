# The Maintainer Workflow Is Tiered: a Deterministic Battery Under One Judgment Skill

**Status:** Accepted

## Context

The root authors the harness; the samples and consumers execute it, so a defect in shipped code runs on other people's machines. The maintainer loop is edit, verify, judge, commit, ship. Before this decision four audit and release skills restated the loop in four orders, every substantive change paid a three-sample audit, and the root skill tables had no gate. Each agent exists once per tool: a `.claude/agents/` base plus a Copilot and an OpenCode mirror whose bodies must match byte for byte. The stacks also carry hand-owned parallel files (the IDE skill pair, the per-stack review checklists) whose rosters and vocabularies are contract-bearing while their prose legitimately diverges. The battery is a local tool with four optional static checkers; a rostered scanner once skipped silently for weeks because it was uninstalled. A passing audit shipped a terminal escape-injection hole, because no reviewer carried a security mandate. Nothing proved the glue reaches no network or writes only where it should. On the marketplace channel the project holds no `.claude/skills/`, so an agent body saying "load skill X" had no target.

## Options Considered

1. **Four skills with cross-references.** Rejected: restatements are the drift source.
2. **Separate `audit-lite` and `audit-full` skills.** Rejected: two rosters for one three-layer process.
3. **Hand-authored mirrors behind the parity gate.** Rejected: the gate detects a miss but never removes the four-fold edit cost.
4. **Generate whole mirror files, frontmatter included.** Rejected: frontmatter encodes per-tool policy a sidecar would only re-encode.
5. **Fix the one security finding; a linter only; a judgment lens only.** Rejected: a finding without a standing check returns. Bandit cannot reason about trust boundaries, and a reviewer is not a regression gate.
6. **Whole-document render, strict text equality, or no gate for hand-owned parallels.** Rejected: every genuine divergence becomes an overlay exception, and equality forces a growing whitelist. A drifted feedback tag breaks review silently. A core-plus-overlay split clears the bar only for a contiguous byte-identical block.
7. **Local-only discipline, a hook only, or CI only.** Rejected: discipline skipped silently; a hook is bypassable and attests nothing; CI alone loses the fast local net.
8. **CVE scanning as a battery step, CodeQL advanced setup, Dependabot pull requests.** Rejected: a daily-changing database makes an unchanged commit fail. A pinned query bundle catches less than default setup, and this repo commits to `main`.
9. **Keep the name `check-sync`, or `verify.py`, or `verify-reference`.** Rejected: the name described one step of about 25; a bare importable name reopens the duplicate-module caveat; the `-harness` family symmetry wins.
10. **A runtime audit hook, or linter configuration, for confinement.** Rejected: suites run as child processes the hook never sees; linters cannot express per-file argv allowlists or egress pairs.
11. **Preload every cited skill, grant the Skill tool, or a path formula from the preload directory.** Rejected: about 8,400 words per dispatch. A wider tool surface OpenCode cannot match, and an undocumented inference.
12. **Three tiers under one judgment skill, rendered mirrors, gated parallels, two push gates, advisory scanners beside the battery, confinement gates, and skills reached by preload or path** (chosen).

## Decision

**The maintainer loop runs in three tiers: the battery after every edit, one diff-scoped judgment skill before a substantive commit, its `full` mode before a release.**

**The tiers.** The root `CLAUDE.md` states them once. Tier 0 is `harness/verify-harness.py`; after a `/harness` edit, `harness/propagate-harness.sh` renders the mirrors, materializes the samples, packages the marketplace, then runs the battery. `--quick` serves an edit outside the derived trees and refuses while any is dirty. Tier 1 is `/audit-harness`, three layers: the battery, the six-check consistency audit with agent depth delegated to `/audit-agents`, and an adversarial review of the diff. Tier 2 is `/audit-harness full`; `/audit-agents` then runs fully in one sample plus stack deltas in the other two, since core-sourced bodies are byte-identical. Battery step 3c holds the `CLAUDE.md` and README root skill tables equal to `.claude/skills/` in both directions. Root skills declare `compatibility: claude-code`.

**The battery's name and shape.** `verify-harness.py` completes the `verify`/`audit`/`review`-harness family; its docstring is the authoritative step list. The hyphen keeps the launcher from clashing with the `verify_harness/` package.

**Rendered mirrors.** The `.claude/agents/` copy is the authored base and the roster's source of truth. `harness/render-agent-mirrors.py` keeps each mirror's hand-owned frontmatter and replaces the body below the fence, rewriting skill links per tool. It never creates a file: a new agent's mirror frontmatters are authored once, as a reviewed per-tool decision. It prunes a mirror whose base is gone, never a layer with failures, so a rename keeps its authored frontmatter. A base carrying `variant-of:` has its own body rendered from its target. Step 2b gates a forgotten render; step 2c runs the renderer's fixture self-test.

**Gated parallels.** Hand-owned parallel files are gated at the level a contract forces identical, never prose (step 3i). The gate covers the IDE skill pair's `##` roster with pinned divergence pairs, the stack-parallel rosters, feedback tags against the `review-workflow` set, and the severity headings across the `security-checks` copies. A contiguous byte-identical tail ships once as a core companion (`doc-sync/maintenance.md`, `document-writing/autofix-protocol.md`, `design-validation/pipeline-contract.md`, `handoff-append/scratch-contract.md`); interleaved deltas stay hand-owned and gated.

**Security in both arms.** Step 1b runs bandit at medium severity and above over `harness/`, `tools/`, and `evals/`, with `--ignore-nosec` so an in-tree suppression cannot disarm a finding. Layer 3 carries a standing security lane over four untrusted-input surfaces: log content rendered to a terminal, shell command construction, path handling, and the `PreToolUse` hooks' auto-approve or deny scope. Log content reaching a terminal is sanitized at one choke point.

**Two push gates.** `.githooks/pre-push` (installed per clone with `git config core.hooksPath .githooks`) and `.github/workflows/checks.yml` both run the battery under `--strict`. That flag makes a missing shellcheck, bandit, ruff, or mypy a failure. The workflow installs shellcheck and a pinned bandit; its actions are SHA-pinned and `/upgrade-deps` tracks them. CodeQL default setup on Python and Dependabot alerts run as repo settings, advisory only, so the battery stays deterministic and its README badge means "these steps passed". Step 1c enforces the stdlib-only contract that keeps the dependency exposure narrow.

**Confinement.** Step 1h proves no network egress across both tiers: no network-module import, no `os.system`/`exec`/`spawn`, and `subprocess` only in a sanctioned spawner with a list-literal argv on its allowlist. Bash is scanned for named network CLIs and git network subcommands. The producer tier allows one egress, git `ls-remote` to an https origin. Step 1i bans raw write primitives outside sanctioned writers, so the tree rewriters go through `harness/write_guard.py`, whose `write_scope(*roots)` rejects any resolved path outside the declared roots and writes atomically. Every exception lives with its reason in `harness/confinement-policy.toml`; an entry naming a missing, unscanned, or stale target fails the gate. A bash network use with no manifest kind edits the named-CLI sets in `checks/confinement_ast.py` by reviewed diff and amends this ADR. A change that moves the trust surface, a new destination, a new tier, or a shipped-runtime writer, amends this ADR as well. The static ceiling is accepted: reflection, computed paths, bash writes, and unlisted binaries stay review-owned.

**Skill reach.** No agent holds the Skill tool. A skill an agent executes on every dispatch is preloaded or restated in its body; every other reference is read on demand under `.claude/skills/<name>/`, never searched for. The packager rewrites that prefix to `${CLAUDE_PLUGIN_ROOT}/skills/` for the Claude plugin and to the installed plugin's `skills/<name>/` for Copilot. Step 2bb gates the rule, the link form, and the preload names; step 3q pins the scoping pre-check's six restatements.

## Consequences

### Positive

- The root roster shrank from 12 skills to 10; the audit is one skill with two modes, and a tier-1 run names the checks it skipped.
- An agent-body edit is one file instead of three; the render replaced 57 hand-copied mirror files.
- A bandit finding, a network import, a stray write, a drifted tag, a missing table row, or an unreachable skill link is a battery failure, not a review miss.
- A public green check attests every push; a missing scanner fails loud at both gates.

### Negative

- The pre-push hook is opt-in per clone and bypassable with `--no-verify`.
- The CI action and the pinned bandit are supply-chain inputs; a local bandit ruleset is unpinned, so two machines can disagree at the margin.
- CodeQL and Dependabot are invisible to a reader and disableable without a commit; this ADR is their only record.
- A new writer or spawner fails the battery until it routes through `write_guard` or earns a policy entry with a reason.
- The product expert's step 1 grew by 75 words and the design expert's by 65; every agent carries the 19-word on-demand rule.
- Cross-tool frontmatter drift and sentence-level drift inside shared doctrine stay judgment concerns.

## References

- [The Python Core](2026-07-06-the-python-core.md) — the typed, stdlib-only code the battery lints, type-checks, and import-gates, and the battery's own package shape.
- [Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — close a silent-failure gap before adding a feature; gate rosters where prose diverges.
- [Materialize](2026-06-11-materialize.md) — install-time verification of the runtime; the push gates cover the source it installs from.
- [Distribution Channels](2026-06-14-distribution-channels.md) — the marketplace channel whose project side holds no skills, the condition the skill-reach rule exists for.
- [Confined Agent Tools](2026-07-16-confined-agent-tools.md) — the sibling boundary: that confines an agent's runtime egress, this confines the harness's own glue.
- [Model Tiering](2026-06-11-model-tiering.md) — the `variant-of:` bases whose bodies the renderer derives from their targets.
- [The Handoff Ledger](2026-05-08-the-handoff-ledger.md) — the agent-authored log whose `view` and `show` surfaces motivated the terminal-sanitization rule.
- [Docs as Harness Project API](2026-06-12-docs-as-harness-project-api.md) — root is the source; the samples are materialized instances the tiers verify.
- [The Decision Log](2026-06-07-the-decision-log.md) — history stays rewritable until published, the rule under which the tiers close a feature.
- Root `CLAUDE.md` (maintainer loop), `.claude/skills/audit-harness/SKILL.md`, `harness/README.md`, `docs/cross-tool-strategy.md` — where the tiers, the layers, the battery, and the mirror policy are stated.
