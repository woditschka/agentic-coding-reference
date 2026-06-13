# Harness–Project API Specification

**Version:** 0.1.0 — pre-release. Breaking changes allowed until 1.0.
**Owner:** the harness. Consumers read this spec; they never edit it. It ships with the harness and versions with it.

## What This Spec Is

The harness is a team; the project's `docs/` folder is the brief it reads. This spec defines that contract: which files the brief contains, what each must hold, and what form all of them take.

A project satisfying this spec can run the harness pipeline. Two validators enforce it:

- **The doctor blocks.** A deterministic script checks the machine-checkable subset — marked `[doctor]` below. CI-runnable, model-free.
- **The brief review advises.** An agent judges the rest — marked `[review]` below. It uses the standard feedback tags; style-only findings surface as autofix offers.

## The Kernel — What No Brief Can Vary

| Discipline | Fixed by the kernel | The brief varies |
|---|---|---|
| TDD-first | Red-green-refactor, test-before-code, the eight-clause quality bar | Pyramid ratios, mocking policy, coverage targets, naming style |
| DDD-strategic | Four properties: ubiquitous language, bounded modules, isolated unit-testable domain core, state-vs-history split | Tactical patterns: repositories, services, anti-corruption layers, naming rules, modulith strictness |
| Spec-driven delivery | PRD before design before code; the append-only handoff ledger; record/tag/verdict vocabularies | All content: requirements, design, decisions |
| Form contract | Principles-over-rules; the writing standards | Natural-language localization of examples, never of principles |

A brief specializes its discipline; it never contradicts it. `[review]`

## File Roster

All six entries must exist. `[doctor]` An absent file is a doctor failure; the remedy is materializing its template — never an invisible fallback.

| File | Kind | Owning agent | Kernel discipline |
|---|---|---|---|
| `prd.md` | stub | product-requirements-expert | spec-driven delivery |
| `system-design.md` | stub | system-design-expert | state-vs-history (state side) |
| `adr/` | stub | system-design-expert; non-goal ADRs: product-requirements-expert | state-vs-history (history side) |
| `ubiquitous-language.md` | stub | system-design-expert, product-requirements-expert | ubiquitous language |
| `testing-principles.md` | default | test-reviewer | TDD |
| `architecture-principles.md` | default | system-design-expert | DDD-strategic |

**Kinds.** A *default* ships complete house-style content; the consumer may rewrite it within the kernel. A *stub* ships structure only; the consumer supplies all content.

**Ownership.** Every roster file is project-owned. The owning agent is the only harness role that edits it, always as a consented diff.

## Required Sections

The doctor checks exact `##` headings. `[doctor]` Consumers add sections freely; they never remove required ones. *Slots* are required data inside a section, checked by pattern. `[doctor]`

### `prd.md`

| Section | Content rule | ID format |
|---|---|---|
| `## Goals` | Outcome language; no implementation terms | — |
| `## Non-Goals` | Declined scope with reason; never silently dropped | `NG-[0-9]+` |
| `## Requirements` | Durable current state, never history; renumbering forbidden | `REQ-[A-Z]+-[0-9]+` |

ID formats are definitions, not fill slots: a fresh PRD is legitimately empty. The doctor enforces them where IDs are *cited* — every REQ-ID referenced from `system-design.md` must resolve to `prd.md`. `[doctor]` The brief review checks the sections carry IDs once content lands. `[review]`

The PRD states *what*, never *how* or *why*. Litmus: if it changes when the implementation language changes, it belongs in system-design. `[review]`

### `system-design.md`

| Section | Content rule |
|---|---|
| `## Package Structure` | Module map as it exists today |
| `## Dependency Policy` | Approved sources; what a new dependency must satisfy |
| `## Threat Model` | What is trusted, what crosses a boundary |

Current state only. Rationale prose belongs in ADRs; every imperative line carries an ADR back-link. `[review]` Every REQ-ID it references exists in `prd.md`. `[doctor]`

### `adr/`

`adr/README.md` exists. `[doctor]` Entries match `YYYY-MM-DD-<kebab>.md`; non-goal ADRs match `YYYY-MM-DD-non-goal-<slug>.md`. `[doctor]` ADRs record the path — options, trade-offs, rationale. The destination lives in `system-design.md`.

### `ubiquitous-language.md`

| Section | Content rule |
|---|---|
| `## Domain Terms` | One canonical entry per term; project-owned vocabulary |

Terms used in `prd.md` and `system-design.md` match the canonical spellings here. `[review]`

### `testing-principles.md`

| Section | Content rule | Slot |
|---|---|---|
| `## Test Pyramid` | Distribution across test levels, with rationale | Numeric ratios present |
| `## Mocking Policy` | When test doubles are permitted, as an ordered preference | — |
| `## Test Naming` | The naming school, with examples | — |
| `## Coverage` | What is measured and why the target is sufficient | Numeric target present |

### `architecture-principles.md`

Each section states how the project realizes its kernel property. `[review]`

| Section | Realizes |
|---|---|
| `## Module Boundaries` | Bounded modules: how boundaries are drawn and enforced |
| `## Domain Core` | Isolated core: what the core may depend on; where business logic lives |
| `## Pattern Catalog` | The tactical patterns in force (e.g. repositories, thin services, anti-corruption layers) |
| `## Naming` | Naming rules; prohibited forms |

## Form Requirements

Apply to every roster file and everything the harness writes into one.

1. **Principles, not rules.** Each principle entry states the principle, why it holds, and how to apply it to an unseen case. A bare rule with no rationale is a finding. `[review]`
2. **Enforceable.** A reviewer reading the entry can decide pass or fail. Unmeasurable qualifiers are findings. `[review]`
3. **Writing standards.** Maximum 30 words per sentence. Data over adjectives. No filler. Violations are autofix offers, not lectures. `[review]`
4. **Consistent.** No entry contradicts another entry, in the same file or across the roster. `[review]`

## Reference Rules

1. **Machinery reads via declarations, never links.** Each mechanics skill declares what it reads in frontmatter: `reads:` listing roster paths such as `docs/testing-principles.md`. Declarations are audited against the expectations manifest, not resolved at runtime.
2. **Documents reference downward-to-governing only.** `system-design.md` cites the principles it realizes; principles docs reference nothing back; ADRs may cite principles; the PRD cites nothing. `[review]`
3. **No handbook paths or copies.** Roster files never reference harness-owned documents, and `docs/` never holds a handbook doc itself — its content ships with the harness, as installed skills or reference-only docs. The brief is self-sufficient. `[doctor]`

## The Channel Rule

Upgrades never write roster files. New expectations arrive as review feedback: a finding, a shipped default, and an offer to draft the consumer's stance. The owning agent edits its file only as a consented diff — form violations surfaced unprompted, content direction changed only on request. Write-backs record generalized principles with rationale, never bare case rulings.

## Briefs Feed Agents; Data Files Feed Engines

Anything enforced by judgment lives in a brief. Anything a deterministic engine consumes lives in project data (`layout.toml`): test file globs, the `test_name_pattern` regex, module derivation, the channel declaration. Where both need one fact, the data file carries the operational form and the brief carries the principle; the review checks they agree. `[review]`

The `[harness]` table in `layout.toml` declares the `channel` — `copy` (runtime committed), `manifest` (runtime materialized from a pinned source, gitignored and doctor-enforced untracked), or `marketplace` (runtime shipped as a plugin) — and the `spec_version` this project targets. `[doctor]` Both reference samples run on `manifest`.

Two optional keys let a project own part of the runtime tree. `tools` lists the AI tool surfaces installed — claude is always on; copilot, opencode, junie are optional — and `materialize` installs only these, never adding one on upgrade. `extensions` lists runtime-relative paths to skills or agents the project added that the harness does not own; `materialize` keeps them (never prunes them as orphans) and the doctor excludes them from the untracked-runtime check, so they stay tracked by design. `[doctor]`

## Optional Capabilities

A capability (e.g. an IDE semantic oracle) may extend the harness when three properties hold:

1. **Never roster-required.** Its absence fails nothing.
2. **Probed, not declared.** Availability is detected at runtime; nothing about it is committed.
3. **Never load-bearing.** The pipeline functions identically without it; when present, its claims require citations.

## Templates and Materialization

Every roster file has a template shipped with the harness. Materialization writes it into the project with a provenance first line:

```
<!-- materialized by harness@<version>, template <name>, spec 0.1.0 — this file is owned by the project -->
```

Everything below the provenance line is the consumer's. Re-materializing an existing file is forbidden; that is the channel rule.

## Versioning

This spec versions with the harness (semver). The manifest (`brief-expectations.toml`) carries the matching `spec_version`. Until 1.0, minor versions may break. From 1.0, a removed file, a removed section, or a tightened slot is a major version; additions with shipped defaults are minor.
