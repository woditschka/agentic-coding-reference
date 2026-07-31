---
name: derive-briefs
description: >-
  Draft the project's docs/ briefs by surveying an existing codebase.
  Recovers requirements, design, vocabulary, and decisions from what the code
  demonstrably does, marking every statement with how it is known — derived,
  confirmed, or not recoverable. Load on a brownfield project whose briefs
  onboarding scaffolded but nobody has written, before the pipeline runs. Not
  for a greenfield project, where the owner writes them as the work proceeds.
  Observed behavior is not an intended requirement; this skill records the
  difference instead of erasing it.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/prd.md
  - docs/system-design.md
  - docs/adr/
  - docs/ubiquitous-language.md
  - docs/testing-principles.md
  - docs/architecture-principles.md
  - docs/security-principles.md
metadata:
  version: "1.0"
  author: team
---

## What this fills

Onboarding scaffolds the roster in two kinds: four structure-only stubs (`prd.md`, `system-design.md`, `ubiquitous-language.md`, `adr/`), and three principles briefs that arrive filled with the harness's default policy. On a greenfield project the owner writes the stubs as the work proceeds. On a **brownfield** project — a codebase adopted before the harness — that content already exists, encoded in the source rather than in prose. This skill reads it out.

It sits between two neighbors and duplicates neither. `doctor` checks the briefs are structurally present; `audit-docs` judges whether written briefs hold up. Both presuppose content. This skill produces the first draft that gives them something to check.

The output is a draft for the owner to correct, never a ratified brief. What it derives is what the code does. What the code *means* — whether a behavior is a deliberate requirement, an accident, or a shipped bug — the source cannot say, and this skill never guesses.

## The load-bearing rule

**Observed behavior is not an intended requirement.** A codebase records decisions without recording their reasons. Prose that presents a derived observation as a settled intention manufactures institutional memory, and a later reader cannot tell the invention from the record.

Every statement therefore carries one of three marks, stated in the document rather than implied:

| Mark | Means | Written as |
|---|---|---|
| **Derived** | Read off the code; true of the implementation, silent on intent | `> Provenance: derived — <what was surveyed>.` at the top of the section or document |
| **Confirmed** | A human answered a question about it | `(confirmed <YYYY-MM-DD>)` inline, after the statement |
| **Not recoverable** | The reasoning predates the repository or was never written | `> Provenance: not recoverable.` in place of a reconstruction |

The three forms are fixed tokens, never paraphrased: an editor, a reviewer, or a future gate recognizes a mark by searching for it. A section that records its reasoning as unrecoverable is a finished section. Filling it with a plausible reconstruction is the failure this skill exists to prevent. These marks describe how a statement is known; they are unrelated to the `<!-- harness: <date> -->` line every scaffolded brief already carries, which holds the harness release date.

## What a codebase cannot evidence

Two required sections have no answer in the source, and absence is not an answer either. A capability the code lacks may be unbuilt, unfinished, or deliberately excluded, and no amount of reading separates those.

- **Goals and Non-Goals** (`prd.md`). Derive a Goal only where the boundary surface states one — a published API, a documented promise. Otherwise both sections record that the intent is not recoverable, and the question goes to the owner.
- **ADR Context and Options Considered.** The reasoning behind an adopted codebase's structural choices predates the repository. Recording that is the finished state; inventing a rationale from the outcome is not.

## Survey order

Work outside in. The boundary surface carries intent; the internals carry mechanism.

1. **Boundary first.** The system's outward surfaces, in whatever form it exposes them: entry points, published interfaces, commands, scheduled work, persisted schemas. These are the capabilities somebody wanted, and they become candidate requirements.
2. **Rules next.** Validation, constraints, guards, error paths. These bound the capabilities and become acceptance bullets.
3. **Structure after.** Packages, layers, dependency direction, the shape persistence takes. This becomes the design brief.
4. **Vocabulary throughout.** Terms taken from persisted or serialized types, fixture data, and user-visible strings — the project's own words, never improved on the way in.
5. **Decisions last.** Only structural choices the code makes visible. Name each record with the survey's date, since the decision's own date is not recoverable, and add its row to the `docs/adr/README.md` index.

## What each brief receives

- **`prd.md`** — narrative requirements derived from the boundary surface only, in `prd-authoring`'s format. Mechanism stays out; it belongs in the design brief. Behavior that contradicts another requirement, or serves none, is recorded as a defect under a `## Known Defects` section rather than written up as intent. A whole-codebase survey can approach the doctor's PRD word budget (the `prd_max_words` override): requirements earn their space, restated mechanism does not.
- **`system-design.md`** — the architecture as it stands: structure, contracts and the requirements they serve, persistence, the security posture wherever the project declares it. A contract serving no requirement is recorded as serving none, never linked to a requirement invented to justify it. Absences are recorded as observations, never as approval.
- **`ubiquitous-language.md`** — the domain terms the code already uses, including collisions, recorded as found.
- **`adr/`** — one record per structural decision the code evidences. The Decision section is evidenced; Context and Options Considered follow the rule above.
- **The three principles briefs** — these arrive filled, and the survey does not rewrite them. Read the code against each and record every gap against the principle, never resolved by lowering it. Relief from a shipped principle is a human's to grant: record it as a confirmed, dated exception naming who granted it. A closed kernel property is not the project's to relax at all.

## Briefs that already carry content

Authored content is not the survey's to rewrite — that is the channel rule. It holds for the three filled principles briefs, and for any stub an owner has started. A prior survey draft counts as authored content on a re-run, and a *confirmed* statement is never re-derived. Derive against what is written, record each divergence as a gap or an open question, and propose every edit as a consented diff.

## Defects, gaps, and open questions

A survey finds three things the briefs must keep apart:

- **A known defect** — behavior that contradicts a requirement the survey derived, or that serves none. Record it in the PRD's `## Known Defects` section, name what it breaches, and leave it in the code. This skill documents; it does not fix.
- **A gap against a principle** — the code does not meet a brief's stated standard. Record it against the principle. Never edit the principle to match the code.
- **An open question** — the code cannot settle which reading is right. Record it as a question, so a human can close it into a requirement, a non-goal, or an ADR.

Each is cheap to record now and expensive to reconstruct later, once the survey's context is gone.

## Procedure

1. **Confirm the roster is present and valid.** Run `python3 scripts/doctor.py check`. It validates structure, not emptiness. Materializing a missing roster file is the `doctor` skill's remedy, or a re-run of `/materialize` — never this skill's.
2. **Read what each brief already says.** Anything authored governs, under § Briefs that already carry content.
3. **Survey in the order above**, reading the codebase directly. `scripts/layout.toml` names the production roots once the project has filled them; verify them against the tree. A survey that finds no production code stops here and says so.
4. **Draft each brief**, marking every statement as the table requires and following the `document-writing` standards. `prd-authoring` owns the PRD's format; `adr-template` owns each ADR's.
5. **Collect the open questions** into the PRD's `## Open Questions` section rather than scattering them.
6. **Put the open questions to the user.** Each answer that lands becomes a *confirmed* statement, dated; the rest stay open and stay marked.
7. **Run `/audit-docs`.** The doctor gates structure; the judgment pass reviews what was drafted. A survey draft is a first draft, and it is reviewed as one.

## Scope

This skill writes `docs/` and nothing else. It does not change source, schemas, or configuration — including defects it finds. A defect it records becomes a slice the pipeline runs later, against the requirement the survey wrote. The survey seeds the briefs before the pipeline owns them; from the first slice on, every edit to a roster file routes through its owning agent as a consented diff.
