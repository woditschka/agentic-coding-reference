---
name: audit-harness
description: >-
  Hold the agentic-coding-reference to a high bar after a change. Runs the local
  deterministic battery (harness/check-sync.sh — its header carries the step
  list), then /audit-consistency, then an adversarial multi-agent
  review of the working-tree diff for regressions, lost coverage, and incoherence —
  and ends with one verdict. Load after a substantive change to /harness, the root
  docs, agents, skills, or scripts, before committing. Root-only (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# audit-harness

The repeatable high-bar review of this reference — the root, the `/harness`
source, and the samples — run after a change to confirm it **raised the bar and
introduced no regression** before you commit. It composes the existing audit
skills; it does not duplicate them.

**Usage:** `/audit-harness` (reviews the current working-tree diff). Root-only —
this reference is maintained with Claude Code, so the skill ships nowhere else.

## When to run

- After editing `/harness` (`core/`, `stacks/<stack>/`, `init/`), the root `docs/`, a root skill, an agent, or a script — before committing.
- After a rename, retirement, or default change that fans out across many surfaces.
- Periodically, to catch slow drift.

## The three layers

A review is three passes, mechanical → structured → adversarial. Run them in order; each is cheaper to fix than the next.

| Layer | What it proves | Home |
|---|---|---|
| **1. Deterministic battery** | No regression: lint clean, per-tool agent bodies identical, every test green, samples == `materialize(/harness)`, doctors green | `harness/check-sync.sh` |
| **2. Consistency audit** | Samples faithful to source and to each other; per-agent thinness/parity; briefs sound | `/audit-consistency` (calls `/audit-agents`; runs each sample's doctor) |
| **3. Adversarial change review** | The *judgment* pass: did this diff raise the bar, or quietly regress / lose coverage / break coherence? | this skill (dispatches reviewers) |

## Process

1. **Run the deterministic battery.**
   ```bash
   harness/check-sync.sh
   ```
   It is the full mechanical gate — every check from shellcheck to the real plugin install. The authoritative step list lives in the script's header; docs do not re-enumerate it. Every step fails loud: a missing sample suite or build-binding file is a FAIL, never a skip. A non-zero exit is a hard stop — fix the source and re-run before going further.

   The agent-body-parity step closes what used to be this layer's blind spot: an edit that lands in `.claude/agents/<x>.md` but misses a `.junie/`, `.opencode/`, or `.github/` sibling. That miss bit `feature-implementer` and `system-design-expert` during the security-principles change. The step compares every agent's four per-tool copies — core and each stack — byte-for-byte after frontmatter. It asserts the location-correct skill-link form per directory. A missing copy, a sibling-only copy, a wrong file suffix, an empty body, or an empty roster fails. Copilot's copy is `.github/agents/<name>.agent.md`; the `.agent.md` suffix makes it the one a manual sync forgets. A per-tool body still ships through **two channels**: the copy channel (`samples/<stack>/…`, via `bootstrap.sh`) and the marketplace plugin (`plugins/<stack>-<tool>/agents/…`, via `package-marketplace.sh`). Re-render both; the faithfulness steps then confirm both caught up.

2. **Run the consistency audit.** Invoke **`/audit-consistency`**. It re-materializes the samples, checks source-vs-sample faithfulness and the stack-agnostic-core invariant, and delegates the per-agent depth audit to **`/audit-agents`** run inside each sample. Route every finding to `/harness` by its core-vs-stacks rule, fix at source, re-materialize.

   When the diff touches an agent or skill body, do not skip or shortcut this layer. Layer 1's parity step proves the four copies are *identical*; `/audit-agents` judges what the battery cannot — whether the shared body is *sound* (thin persona, correct skill references, no stack fact in core).

3. **Run the adversarial change review.** Dispatch parallel reviewers over the working-tree diff (`git diff` + `git status`). Slice the diff by area so each reviewer has a focused, adversarial mandate — *find what is wrong*, not confirm what is right. Cover at least:
   - **Shipped scripts/engines** (bash, python): correctness and **no behavior regression**; run the affected test suites; check idiom and safety (see the `document-writing` standards for prose, shellcheck/py-syntax for code).
   - **Docs and skills** — check five things:
     - **coherence**: do README, CLAUDE.md, the skills, and the ADRs agree?
     - **stale-reference sweep**: a renamed or retired term survives only as intentional history in `docs/adr/` or a dated README Project History line.
     - **lost coverage**: did slimming a check drop a guarantee, or did it migrate?
     - **links and anchors** resolve.
     - **writing standards**: ≤30 words per sentence, data over adjectives.
   - **Skill cross-tool reach** — byte parity is Layer 1's job; judge what identical bytes cannot show. Does a `compatibility:` frontmatter change narrow which tools load the skill? Does the marketplace channel still deliver it (OpenCode is not a plugin target)? Can all four tools actually follow an edited instruction, or only Claude Code?
   - **Producer/reviewer/design-stage symmetry** — when a change adds or moves a principle, a quality-bar clause, or a reference brief, check it reached every stage the peer dimensions reach. Those stages: the producer (feature-implementer), the design gate (system-design-expert / `design-validation`), the reviewer (`*-review` skill), and the self-review clause walk. A dimension wired into only some stages is the gap the security-principles change existed to close.
   - **The change as a whole**: does it raise the bar against the goal it set, or only move things around?

   Give each reviewer the relevant file list and the finding format `[SEVERITY] file:line — issue`. Prefer small, focused adversarial agents over one broad pass.

4. **Synthesize one verdict, then close the findings.** State plainly: *raises the bar? introduced any regression / lost coverage / incoherence?* List findings by severity. **Fix the worthwhile ones at the source**, re-materialize, and **re-run the affected layer** — a fix that touches a shipped engine re-runs layer 1. A latent issue a fix *exposes* (not just introduces) is still yours to close.

## Verdict format

```
## audit-harness: <date>

Layer 1 — deterministic battery: PASS | FAIL (<which checks>)
Layer 2 — consistency audit: PASS | <N issues, mapped to /harness>
Layer 3 — adversarial review: <verdict — raises the bar? regressions?>

Findings:
- [SEVERITY] file:line — issue → fixed | left (why)

Verdict: <one paragraph — bar raised, regression-free, or what blocks it>
```

## What it reuses, and does NOT do

- **Reuses** `harness/check-sync.sh`, `/audit-consistency`, `/audit-agents`, the sample doctors, and the `document-writing` standards. It is an orchestrator — it never re-implements their checks.
- **Does not commit or push.** It reports a verdict; committing is a separate, explicit step (local-only — never propose server-side CI; the deterministic battery is the local gate, see `harness/check-sync.sh`).
- **Does not edit project-owned sample files by hand.** Every fix goes to `/harness` (or root) and is re-materialized — never a sample's committed runtime.
