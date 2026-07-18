---
name: audit-harness
description: >-
  Hold the agentic-coding-reference to a high bar after a change; three
  layers, one verdict. Layer 1 runs the deterministic battery
  (harness/verify-harness.py — its header carries the step list). Layer 2 runs the
  judgment-only consistency audit — six checks, agent depth delegated to
  /audit-agents. Layer 3 dispatches an adversarial multi-agent review of the
  working-tree diff. The default run scopes the judgment layers to the diff;
  "/audit-harness full" runs all six consistency checks across the samples.
  The root CLAUDE.md maintainer loop states when each tier runs. Root-only
  (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "2.1"
  author: team
---

# audit-harness

The repeatable high-bar review of this reference — the root, the `/harness`
source, and the samples — run after a change to confirm it **raised the bar and
introduced no regression** before you commit. Layer 1 reuses the deterministic
battery; layers 2 and 3 are this skill's judgment passes. When anything
disagrees with `/harness`, `/harness` wins: fix the source, re-materialize,
never a sample's committed runtime.

**Usage:** `/audit-harness` (default — judgment scoped to the working-tree
diff) or `/audit-harness full`. Root-only — this reference is maintained with
Claude Code, so the skill ships nowhere else.

## Tiers

The maintainer loop in the root `CLAUDE.md` is the canonical statement of when
each tier runs; this table maps only tier → invocation.

| Tier | What runs |
|---|---|
| **0** | The battery alone (§ Layer 1). Not an `/audit-harness` run. |
| **1** | `/audit-harness` — Layer 1, then layers 2 and 3 scoped to the working-tree diff |
| **2** | `/audit-harness full` — Layer 1, all six Layer 2 checks (agent depth: one full sample plus stack deltas), Layer 3 |

## The three layers

A review is three passes, mechanical → structured → adversarial. Run them in
order; each is cheaper to fix than the next.

| Layer | What it proves | Home |
|---|---|---|
| **1. Deterministic battery** | No regression: lint clean, per-tool agent bodies identical, every test green, samples == `materialize(/harness)`, doctors green | `harness/verify-harness.py` |
| **2. Consistency audit** | The judgment the battery cannot make: per-agent depth, semantic cross-tool parity, routing semantics, samples reflect the handbook | § Layer 2 (judgment-only; delegates depth to `/audit-agents`) |
| **3. Adversarial change review** | Did this diff raise the bar, or quietly regress / lose coverage / break coherence? | § Layer 3 (dispatches reviewers) |

## Layer 1 — the deterministic battery

```bash
harness/verify-harness.py
```

After a `/harness` edit, run `harness/propagate-harness.sh` instead — it renders
the agent mirror bodies, propagates to the samples and the marketplace, then
runs the same battery. The
battery is the full mechanical gate — every check from shellcheck to the real
plugin install. The authoritative step list lives in the script's header; docs
do not re-enumerate it. Every step fails loud: a missing sample suite or
build-binding file is a FAIL, never a skip. A non-zero exit is a hard stop —
fix the source and re-run before going further.

The agent-body-parity step guards the render contract. Mirror bodies
(`.junie/`, `.opencode/`, `.github/`) are rendered from the `.claude` base by
`harness/render-agent-mirrors.py` (propagate-harness runs it first), never edited by
hand; the render also prunes a mirror whose base is gone. The step compares
every agent's four per-tool copies — core and each stack — byte-for-byte after
frontmatter. It asserts the location-correct skill-link form per directory. A
missing copy, a sibling-only copy, a wrong file suffix, an empty body, or an
empty roster fails. Most parity failures mean a forgotten render or a
hand-edited mirror: fix the `.claude` base and re-run the render. A missing
mirror instead needs its frontmatter authored once — the renderer never
creates files. The manual four-way sync
it replaced once bit `feature-implementer` and `system-design-expert` during
the security-principles change. A per-tool body
still ships through **two channels**: the copy channel (`samples/<stack>/…`,
via `materialize-samples.sh`) and the marketplace plugin
(`plugins/<stack>-<tool>/agents/…`, via `package-marketplace.py`). Re-render
both; the faithfulness steps then confirm both caught up.

## Layer 2 — the consistency audit

Judgment-only: every mechanical consistency check (faithfulness, layout
invariants, rosters, placeholders, handbook delta, enums, links) runs in
Layer 1's battery. This layer never re-implements a battery check.

### What the battery already proves (do not re-check)

Steps are named descriptively here, never by number — the script's header owns
the numbering, and a renumbering must not invalidate this table.

| Retired section | Now proven by |
|---|---|
| Samples match source; skill parity between samples; orphans | the materialization-faithfulness step (extras count) |
| Cross-tool layout rules (no AGENTS.md, skills in `.claude/skills/` only, all surfaces present); copy-channel invariants (`channel="copy"`, `extensions=[]`, runtime tracked, `.gitignore` scope) | the layout-invariants step |
| Skills-table name rows (samples and root, both directions), agents README roster, init skeleton coverage, brief roster, sample `docs/adr/` holds only README.md | the roster step — row *descriptions* stay judgment (check 5) |
| Template placeholders confined to documented locations (per-file allowlist) | the placeholder step — token *placement* inside an allowed brief stays judgment |
| Root handbook vs installed copy (pinned delta); sample doc self-containment | the handbook-delta step — a change to `handbook-delta.expected` itself is reviewed as content drift |
| `design-block` / `review-feedback` verdict enums | the enum-sync step |
| Stack-agnostic core (no stack token in `harness/core/`) | the stack-agnostic-core step |
| Root markdown links resolve, including `#fragment` anchors against heading slugs and `<a id>` anchors | the link-integrity step — bare path tokens outside link syntax stay judgment (check 5) |
| Byte-level agent body parity across the four tool copies | the agent-body-parity step |

### Scoping (default run)

Map the diff to checks; run only the checks the diff touches and name the
skipped ones in the verdict. `full` runs all six. Every check is a comparison —
a diff on **either side** of the comparison triggers it.

| Diff touches | Run |
|---|---|
| agent or skill bodies shipped from `/harness` | checks 1–2 (`/audit-agents` sections scoped to the changed agents; root skills ship in no sample — check 5 and Layer 3 cover them) |
| consultation or routing content (coordinator, `system-design-expert`, `handoff-routing`, `tdd-workflow`, `design-validation`, the consultation schemas) | checks 3–4 |
| root docs, `CLAUDE.md`, `README.md`, a quality-gate home, a `harness/init/` skeleton | check 5 |
| `docs/agentic-harness.md` or its installed copy | checks 4–6 (check 4 guards the handbook's own verdict prose) |
| a canonical comparison home: `schemas/scratch/`, the `handoff-routing` skill, a roster or the `TOOLS` registry in `harness/registry.py` (`registry.sh` mirrors the rosters) | checks 5–6; check 2 for a tool-roster change |

When the diff touches an agent or skill body, never skip or shortcut check 1.
Layer 1's parity step proves the four copies are *identical*; `/audit-agents`
judges what the battery cannot — whether the shared body is *sound* (thin
persona, correct skill references, no stack fact in core).

### The six checks

**1. Agent config depth — delegated to `/audit-agents`.** The per-agent rules
are owned by the `audit-agents` skill that ships inside every sample. It covers
thinness, write scope, reference integrity, reviewer conduct, state/enum
checks, and the four-tool comparison with the model-mapping table. On a `full` run, use the
identity the battery proves: core-sourced bodies are byte-identical in all
three samples. Run `/audit-agents` fully in one sample; in the other two, audit
only the stack-sourced files (`harness/stacks/<stack>/…`) and the frontmatter
the stack varies. One full pass plus two stack deltas covers every rule it owns
at well under the cost of three full passes. On a default run, audit only the
changed agents: run the relevant sections in any one sample — the battery
proves the bodies identical. Map every finding back to source:

- A finding in **every** sample, on a file sourced from `core/` → fix in `harness/core/…`.
- A finding confined to **one stack** → fix in `harness/stacks/<stack>/…`.
- A finding on a project-owned committed file (`CLAUDE.md`, `scripts/layout.toml`, `docs/` briefs) → fix the skeleton in `harness/init/…` or the doctor template.

Then re-materialize and re-run to confirm the finding clears.

**2. Semantic cross-tool parity.** The battery's parity step proves the four
per-tool bodies are *identical*; judge what identical bytes cannot show. Does the model mapping fit
each tool? Do tool permissions in the frontmatter match the body's needs? Can
all four tools actually follow the instructions, or only Claude Code?

**3. Consultation routing semantics.** Verify the roundtrip is described
consistently across the samples:

- [ ] `handoff-routing`: after a `consultation-response`, Gate 2b routes **back to the requesting specialist**, never forward.
- [ ] `pipeline-coordinator` agent: never re-decides a transition `route` owns — the consultation back-route is Gate 2b's; the coordinator handles only `escalate` and fresh intake.
- [ ] `tdd-workflow`: the design-check tree appends a `consultation-request` rather than blocking; the inner loop resumes on the matching response.
- [ ] `design-validation`: describes triage mode (six `design-block` verdicts) and consultation mode; the agent branches on the input record type.
- [ ] `system-design-expert`: write scope allows appending `consultation-response`; `docs/ubiquitous-language.md` is in scope only during the `foundational` triage path.
- [ ] Both consultation schemas exist with fields matching the skill/agent descriptions.

**4. SDE triage verdicts.** The schema enum is pinned by the battery; judge the
*descriptions*. The SDE agent, `design-validation`, and `docs/agentic-harness.md`
must name the same six verdicts with compatible guidance. The `foundational`
path covers both greenfield and adoption the same way in all three. Flag the
retired verdict values (`needs_changes`, `revised`, `escalated`) anywhere in a
design-block context; `approved`/`blocked` stay valid for `review-feedback`.

**5. Root doc and quality-gate alignment.**

- Scratch-state names, record types, and agent names in root docs agree with the canonical homes: the `handoff-routing` skill and `schemas/scratch/`. The `review-feedback` `author` enum is the canonical reviewer identity — there are no per-reviewer markdown files.
- Skills-table row *descriptions* match what the skill actually does — in each sample's `CLAUDE.md` and in the root `CLAUDE.md` table (the README carries no skills table; it links out); the battery gates only the name rosters.
- Per sample, the quality gate agrees across its three homes: the `CLAUDE.md` Quality Gate chapter, the `code-quality-gate` skill, and the code-quality-reviewer's permitted commands. Java additionally carries `formatJava` and `checkJavaFormat` where each applies, including `.claude/settings.local.json`.
- Bare path-shaped tokens outside markdown-link syntax (backticked paths in prose, fenced usage lines) resolve — the battery's link step checks markdown-link targets only.

**6. Samples reflect `docs/agentic-harness.md`.** The doc is the bar for what
the deployed harness looks like and how it behaves. Read it end-to-end; for
each checkable claim — write-scope tables, record-type lists, do/don't pairs,
named contracts — verify the samples reflect it. Claims with explicit examples
turn into greps; structural claims check against the filesystem. Two worked
examples of the shape:

- *Self-containment:* agent prompts, skills, and schema descriptions cite no specific ADR file or REQ identifier (write-scope mentions of `docs/adr/` are exempt).
- *Tool-agnostic prose:* concrete numeric budgets live in agent frontmatter; skill prose names `toolCallBudget` without a value; harness-level structural constants (retry count, reviewer count) are fine.

## Layer 3 — the adversarial change review

Dispatch parallel reviewers over the working-tree diff (`git diff` +
`git status`). On a `full` run over a clean tree (the periodic drift check),
there is no diff — record Layer 3 as "no diff" in the verdict; Layer 2 carries
the run. Each reviewer gets a focused, adversarial mandate — *find what is
wrong*, not confirm what is right.

### Lane scoping

Dispatch only the lanes the diff reaches (the table below); record every
skipped lane in the verdict as `n/a` with the reason. A skipped lane is a
visible, vetoable decision — never a silent omission. Every row keys on the
file list except the symmetry row, which keys on the diff's content. Scoping
applies to the default run; a `full` run over a dirty tree dispatches every
lane. Two rules are non-negotiable:

- **Whole-change always runs.** It owns what no area lane does.
- **Security is sticky.** Any script, hook, hook registration, or schema in
  the diff dispatches the security lane — no exceptions. So does a widened
  agent tool grant, and prose that directs shell command construction or
  changes an agent's permitted commands.

| Diff touches | Dispatch lanes |
|---|---|
| any script (shipped or maintainer — `harness/`, `tools/`, engines), a hook, a hook registration (`hooks.json`, hook entries in `settings.json`), or a schema | scripts correctness **and** security |
| agent or skill bodies or frontmatter, marketplace assets | docs-and-skills, cross-tool reach (a widened `tools:` grant also trips sticky security) |
| root docs (incl. `docs/images`), `CLAUDE.md`, `README.md`, ADRs, root skills, `handbook-delta.expected` | docs-and-skills |
| a rename or retirement of a skill, agent, term, or path (content-keyed: judge the hunks, not the paths) | docs-and-skills (stale-reference sweep) |
| a principle, quality-bar clause, or reference brief added or moved (content-keyed: judge the hunks, not the paths) | symmetry |
| anything (every run with a diff) | whole-change |

When unsure whether a lane is reached, dispatch it — the mapping trims clear
misses, not close calls.

### The lanes

- **Scripts/engines** (bash, python — shipped or maintainer): correctness and **no behavior regression**; run the affected test suites; check idiom (see the `document-writing` standards for prose, shellcheck/py-syntax for code). Security is the next lane's job, not this one's.
- **Security** — a security lens over the diff's untrusted-input surfaces: scripts, hooks, and prose that directs shell command construction. Cover four: log or record content rendered to a terminal (escape injection), shell command construction, path handling, and the `PreToolUse` hooks' auto-approve or deny scope. Hook scripts and their registration both count. The deterministic linters (shellcheck, bandit) run in the battery and gate the mechanical findings; this lens hunts what they cannot — trust-boundary reasoning. The handoff log is agent-authored: treat every field of it as untrusted input.
- **Docs and skills** — check five things:
  - **coherence**: do README, CLAUDE.md, the skills, and the ADRs agree?
  - **stale-reference sweep**: a renamed or retired term survives only as intentional history in `docs/adr/` or a dated README Project History line.
  - **lost coverage**: did slimming a check drop a guarantee, or did it migrate? A diff touching `harness/handbook-delta.expected` is a re-pin of the handbook delta — review it as content drift, not as a mechanical update.
  - **links and anchors** the diff adds or moves resolve. Repo-wide sweeps are owned elsewhere — file links by the battery's link step, anchors by check 5 — never re-run here.
  - **writing standards**: ≤30 words per sentence, data over adjectives.
- **Skill cross-tool reach** — byte parity is Layer 1's job, and whether all four tools can follow a changed body is check 2's — re-ask neither here. Judge only the delivery surface the diff touched: does a `compatibility:` frontmatter change narrow which tools load the skill? Does the marketplace channel still deliver it (OpenCode is not a plugin target)?
- **Producer/reviewer/design-stage symmetry** — when a change adds or moves a principle, a quality-bar clause, or a reference brief, check it reached every stage the peer dimensions reach. Those stages: the producer (feature-implementer), the design gate (system-design-expert / `design-validation`), the reviewer (`*-review` skill), and the self-review clause walk. A dimension wired into only some stages is the gap the security-principles change existed to close.
- **The change as a whole**: does it raise the bar against the goal it set, or only move things around?

Give each reviewer the relevant file list and the finding format
`[SEVERITY] file:line — issue`. Prefer small, focused adversarial agents over
one broad pass.

## Synthesize one verdict, then close the findings

State plainly: *raises the bar? introduced any regression / lost coverage /
incoherence?* List findings by severity. **Fix the worthwhile ones at the
source**, re-materialize, and **re-run the affected layer** — a fix that
touches a shipped engine re-runs layer 1. A latent issue a fix *exposes* (not
just introduces) is still yours to close.

## Verdict format

```
## audit-harness: <date> — default | full

Layer 1 — deterministic battery: PASS | FAIL (<which steps>)
Layer 2 — consistency audit: PASS | <N issues, mapped to a /harness (or root) path> (checks run: <…>; skipped: <…>)
Layer 3 — adversarial review: <verdict — raises the bar? regressions?> (lanes run: <…>; skipped: <lane — n/a reason>) | no diff (clean tree)

Findings:
- [SEVERITY] file:line — issue → fixed | left (why)

Verdict: <one paragraph — bar raised, regression-free, or what blocks it>
```

## What it reuses, and does NOT do

- **Reuses** `harness/verify-harness.py`, `/audit-agents`, the sample doctors, and the `document-writing` standards. It never re-implements their checks.
- **Does not commit or push.** It reports a verdict; committing is a separate, explicit step. The deterministic battery (`harness/verify-harness.py`) is enforced at push by two gates — the `.githooks/pre-push` hook and the `.github/workflows/checks.yml` CI workflow (see the [enforcement ADR](../../../docs/adr/2026-07-13-server-side-battery-enforcement.md)).
- **Does not edit project-owned sample files by hand.** Every fix goes to `/harness` (or root) and is re-materialized — never a sample's committed runtime.
