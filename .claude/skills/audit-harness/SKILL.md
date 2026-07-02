---
name: audit-harness
description: >-
  Hold the agentic-coding-reference to a high bar after a change. Runs the local
  deterministic battery (lint, syntax, sample test suites, materialization
  faithfulness, doctors), then /audit-consistency, then an adversarial multi-agent
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
| **1. Deterministic battery** | No regression: lint clean, every test green, samples == `materialize(/harness)`, doctors green | `harness/check-sync.sh` |
| **2. Consistency audit** | Samples faithful to source and to each other; per-agent thinness/parity; briefs sound | `/audit-consistency` (calls `/audit-agents`; runs each sample's doctor) |
| **3. Adversarial change review** | The *judgment* pass: did this diff raise the bar, or quietly regress / lose coverage / break coherence? | this skill (dispatches reviewers) |

## Process

1. **Run the deterministic battery.**
   ```bash
   harness/check-sync.sh
   ```
   It runs shellcheck, python syntax, the sample test suites (doctor, handoff, score-change × each sample), materialization faithfulness (re-materialize in place; flag orphans and any change the re-materialize introduces), the doctors, and the materialize self-test. A non-zero exit is a hard stop — fix the source and re-run before going further.

   **Blind spot to carry into the next layers.** The battery proves `sample == materialize(/harness)`; it does **not** compare the source's own per-tool agent bodies to each other. An edit that lands in `.claude/agents/<x>.md` but not its `.junie/`, `.opencode/`, or `.github/` sibling sits identically in source and sample, so faithfulness passes. That divergence is Layer 2's catch (see step 2) — it bit `feature-implementer` and `system-design-expert` during the security-principles change.

2. **Run the consistency audit.** Invoke **`/audit-consistency`**. It re-materializes the samples, checks source-vs-sample faithfulness and the stack-agnostic-core invariant, and delegates the per-agent depth audit to **`/audit-agents`** run inside each sample. Route every finding to `/harness` by its core-vs-stacks rule, fix at source, re-materialize.

   When the diff touches an agent or skill body, do not skip or shortcut this layer. `/audit-agents` cross-tool parity is the only check that catches a per-tool source body drifting from its siblings (`.claude/`, `.junie/`, `.opencode/`, `.github/`). A `feature-implementer.md` whose `.claude/` body gains a reference line its `.opencode/` body lacks ships a weaker agent to OpenCode users, and Layer 1 cannot see it.

   **Run this fast source-side gate whenever the diff touches any agent body.** It catches the most common miss — a per-tool copy left behind — in seconds, before the full `/audit-agents` fan-out:

   ```bash
   strip_fm() { awk 'BEGIN{n=0} /^---[ \t]*$/{n++; next} n>=2{print}' "$1"; }
   for s in go java-spring-boot; do
     for base in harness/stacks/$s/.claude/agents/*.md; do
       a=$(basename "$base" .md); [ "$a" = "README" ] && continue
       for f in "harness/stacks/$s/.junie/agents/$a.md" \
                "harness/stacks/$s/.opencode/agents/$a.md" \
                "harness/stacks/$s/.github/agents/$a.agent.md"; do
         [ -f "$f" ] || { echo "MISSING $f"; continue; }
         diff -q <(strip_fm "$base") <(strip_fm "$f") >/dev/null || echo "DRIFT  $f"
       done
     done
   done
   echo "no DRIFT/MISSING above = all four tools body-identical"
   ```

   Two traps this closes. **Copilot's copy is `.github/agents/<name>.agent.md`** — the `.agent.md` suffix (not `.md`) makes it the one a manual sync forgets, exactly what happened to `feature-implementer` during the security-principles change. And a per-tool body ships through **two channels**: the copy channel (`samples/<stack>/.github/…`, via `bootstrap.sh`) and the marketplace plugin (`plugins/<tool>/agents/…`, via `package-marketplace.sh`). Re-render both; faithfulness then confirms the plugin caught up.

3. **Run the adversarial change review.** Dispatch parallel reviewers over the working-tree diff (`git diff` + `git status`). Slice the diff by area so each reviewer has a focused, adversarial mandate — *find what is wrong*, not confirm what is right. Cover at least:
   - **Shipped scripts/engines** (bash, python): correctness and **no behavior regression**; run the affected test suites; check idiom and safety (see the `document-writing` standards for prose, shellcheck/py-syntax for code).
   - **Docs and skills** — check five things:
     - **coherence**: do README, CLAUDE.md, the skills, and the ADRs agree?
     - **stale-reference sweep**: a renamed or retired term survives only as intentional history in `docs/adr/` or a dated README Project History line.
     - **lost coverage**: did slimming a check drop a guarantee, or did it migrate?
     - **links and anchors** resolve.
     - **writing standards**: ≤30 words per sentence, data over adjectives.
   - **Agent & skill cross-tool parity** — when the diff edits an agent or skill body, confirm the identical edit reached every per-tool source copy (`.claude/`, `.junie/`, `.opencode/`, `.github/`). Bodies differ only in frontmatter; a body that drifts in one tool ships a weaker agent there. This is the adversarial backstop to Layer 2's `/audit-agents`, since Layer 1 is blind to it.
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
