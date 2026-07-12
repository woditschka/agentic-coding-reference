# Harness–Project API Specification

**Version:** 0.1.0 — pre-release. Breaking changes allowed until 1.0.
**Owner:** the harness. Consumers read this spec; they never edit it. It ships with the harness and versions with it.

## What This Spec Is

The harness is a team; the project's `docs/` folder is the brief it reads. This spec defines that contract: which files the brief contains, what each must hold, and what form all of them take.

A project satisfying this spec can run the harness pipeline. Two validators enforce it:

- **The doctor blocks.** A deterministic script checks the machine-checkable subset — marked `[doctor]` below. CI-runnable, model-free.
- **The `audit-docs` review advises.** An agent judges the rest — marked `[review]` below. It uses the standard feedback tags; style-only findings surface as autofix offers.

## The Kernel — What No Brief Can Vary

| Discipline | Fixed by the kernel | The brief varies |
|---|---|---|
| TDD-first | Red-green-refactor, test-before-code, the nine-clause quality bar | Pyramid ratios, mocking policy, coverage targets, naming style |
| DDD-strategic | Four properties: ubiquitous language, bounded modules, isolated unit-testable domain core, state-vs-history split | Tactical patterns: repositories, services, anti-corruption layers, naming rules, modulith strictness |
| Spec-driven delivery | PRD before design before code; the append-only handoff ledger; record/tag/verdict vocabularies | All content: requirements, design, decisions |
| Form contract | Principles-over-rules; the writing standards | Natural-language localization of examples, never of principles |

A brief specializes its discipline; it never contradicts it. `[review]`

The admission test: a discipline enters the kernel only when the machinery breaks without it, never by preference. The kernel closes *properties*; briefs carry *patterns* — the worked example lives in [`ddd-principles.md` § Properties Are Kernel](ddd-principles.md#properties-are-kernel-patterns-are-brief-variable).

## File Roster

All seven entries must exist. `[doctor]` An absent file is a doctor failure; the remedy is materializing its template — never an invisible fallback.

| File | Kind | Owning agent | Kernel discipline |
|---|---|---|---|
| `prd.md` | stub | product-requirements-expert | spec-driven delivery |
| `system-design.md` | stub | system-design-expert | state-vs-history (state side) |
| `adr/` | stub | system-design-expert; non-goal ADRs: product-requirements-expert | state-vs-history (history side) |
| `ubiquitous-language.md` | stub | product-requirements-expert; seeded once by system-design-expert under the `foundational` triage verdict | ubiquitous language |
| `testing-principles.md` | default | test-reviewer | TDD |
| `architecture-principles.md` | default | system-design-expert | DDD-strategic |
| `security-principles.md` | default | security-reviewer | secure-by-design (bar clause) |

**Kinds.** A *default* ships complete house-style content; the consumer may rewrite it within the kernel. A *stub* ships structure only; the consumer supplies all content.

**Ownership.** Every roster file is project-owned. The owning agent is the only harness role that edits it, always as a consented diff.

## Required Sections

The doctor checks exact `##` headings. `[doctor]` Consumers may add sections; they never remove required ones. *Slots* are required data inside a section, checked by pattern. `[doctor]`

### `prd.md`

| Section | Content rule | ID format |
|---|---|---|
| `## Goals` | Outcome language; no implementation terms | — |
| `## Non-Goals` | Declined scope with reason; never silently dropped | `NG-[0-9]+` |
| `## Requirements` | Durable current state, never history; renumbering forbidden | `REQ-[A-Z]+-[0-9]{3}` |

ID formats are definitions, not fill slots: a fresh PRD is legitimately empty. The doctor enforces them where IDs are *cited* — every REQ-ID referenced from `system-design.md` must resolve to `prd.md`. `[doctor]` The `audit-docs` review checks the sections carry IDs once content lands. `[review]`

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

### `security-principles.md`

Specializes the harness-owned security laws for the project; the `secure-by-design` bar clause walks it. The four laws stay harness-owned in `tdd-principles.md` § Secure by Design — the brief carries only the project's *how*. `[review]`

| Section | Content rule | Slot |
|---|---|---|
| `## Trust Boundaries` | Each point where control or data crosses into more trust, and the rule there | — |
| `## <stack> Realization` | The stack's high-bar defaults: each vulnerability class, the law it protects, the control | — |

## Form Requirements

Apply to every roster file and everything the harness writes into one.

1. **Principles, not rules.** Each principle entry states the principle, why it holds, and how to apply it to an unseen case. A bare rule with no rationale is a finding. `[review]`
2. **Enforceable.** A reviewer reading the entry can decide pass or fail. Unmeasurable qualifiers are findings. `[review]`
3. **Writing standards.** Maximum 30 words per sentence. Data over adjectives. No filler. Violations are autofix offers. `[review]`
4. **Consistent.** No entry contradicts another entry, in the same file or across the roster. `[review]`

## Reference Rules

1. **Machinery reads via declarations, never links.** Each mechanics skill declares what it reads in frontmatter: `reads:` listing roster paths such as `docs/testing-principles.md`. Declarations are audited against the expectations manifest, not resolved at runtime.
2. **Documents reference downward-to-governing only.** `system-design.md` cites the principles it realizes; principles docs reference nothing back; ADRs may cite principles; the PRD cites nothing. `[review]`
3. **No handbook paths or copies.** Roster files never reference harness-owned documents, and `docs/` never holds a handbook doc itself — its content ships with the harness, as installed skills or reference-only docs. The brief is self-sufficient. `[doctor]`

## The Channel Rule

Upgrades never write roster files. New expectations arrive as review feedback: a finding, a shipped default, and an offer to draft the consumer's stance. The owning agent edits its file only as a consented diff — form violations surfaced unprompted, content direction changed only on request. Write-backs record generalized principles with rationale, never bare case rulings.

## Briefs Feed Agents; Data Files Feed Engines

Anything enforced by judgment lives in a brief. Anything a deterministic engine consumes lives in project data (`layout.toml`): test file globs, the `test_name_pattern` regex, module derivation, the channel declaration. Where both need one fact, the data file carries the operational form and the brief carries the principle; the review checks they agree. `[review]`

The `[harness]` table in `layout.toml` declares the `channel` and the `spec_version` this project targets. `[doctor]` Three channels deliver the runtime — `copy`, `manifest`, `marketplace`; their semantics, defaults, and switching procedure are owned by the [Adoption Guide § Distribution channels](adoption-guide.md#distribution-channels). Two invariants are spec-level. On the off-copy channels the runtime is gitignored and doctor-enforced untracked. `[doctor]` The marketplace split keeps engine paths project-relative, so every tool resolves them identically — a Claude-specific plugin-root variable resolves only in Claude.

Two optional keys let a project own part of the runtime tree. `tools` lists the AI tool surfaces installed — claude is always on; copilot, opencode, junie are optional — and `materialize` installs only these, never adding one on upgrade. `extensions` lists runtime-relative paths to skills or agents the project added that the harness does not own. `materialize` keeps them and never prunes them as orphans. The doctor excludes them from the untracked-runtime check, so they stay tracked by design. `[doctor]`

A third optional key, `extra_reviewers`, extends the review roster. The four-reviewer floor — code-quality, test, security, doc — gates every change and cannot be dropped. `extra_reviewers` lists additional reviewer names (each `*-reviewer`) that join the gate. Each must have an agent body in every declared tool surface and be listed in `extensions` so `materialize` preserves it. Each body carries the dispatch-start First Tool Call stanza and the `review-workflow` output protocol — the dispatch-event contract binds every roster reviewer. The doctor enforces the floor's presence and the extras' naming, bodies, and extension listing. On the marketplace channel the floor bodies ship in the plugin, so their check is skipped; extras are project-owned — their checks and the undeclared-body drift scan still run. `[doctor]`

A fourth optional key, `auto_grade`, gates the terminal change-grader. It defaults to `true`: after the roster approves, `route` dispatches the advisory `change-grader` as the terminal hop. Setting it `false` makes the approved state terminal without the grader run — a project's opt-out when the per-change grade is not worth its cost. The gate is on the automatic dispatch only; the change-grader agent and `change-grading` skill stay runnable by hand, and a hand-run `grader-verdict` still routes to feature-complete. The router fails open on a non-boolean value (grading stays on); the doctor flags the type error. `[doctor]`

A separate optional `[review]` table configures risk-proportional review dispatch. It declares the review-surface globs (`docs`, `config`), the `size_threshold` line ceiling, and `mode` — `risk` *(default)* or `always-full`, which reproduces the unconditional full battery. An absent table uses the engine defaults; any unclassifiable input fails closed to the full roster. The table sizes when each reviewer runs, never roster membership — the four-reviewer floor is untouched. See [Risk-Proportional Review Dispatch](adr/2026-07-09-risk-proportional-review.md).

## The CLAUDE.md Managed Chapters

`CLAUDE.md` is project-owned, but it carries five harness-owned chapters — `## Agent Usage (Mandatory)`, `## Memory`, `## Writing Standards`, `## Scratch Directory`, `## Documentation Updates` — each identified by its heading rather than by marker comments. They hold stack-agnostic harness doctrine and are byte-identical across every stack. `materialize` refreshes each from a single source (`harness/claude-md/managed-chapters.md`) on every upgrade, rewriting from the heading to the next `## ` heading. These chapters are part of the upgrade's *deterministic* tier — refreshed in place, no judgment. The same tier ensures the `.gitignore` runtime paths and the `.claude/settings.json` harness keys are present (marker-free, in `materialize.py`, additive). A second *advisory* tier then diffs every template-seeded file against its shipped template and proposes the residual. The residual covers a dropped `.gitignore` line, `scripts/layout.toml` data, the `docs/` briefs, and this file's own *non-doctrine* chapters (see the `materialize` skill, steps 8–9). A non-doctrine chapter stays the project's, interleaved in its own order — but the diff-check may propose a skeleton improvement it lacks. The doctor's `required-chapter` check fails if any managed heading is missing or its chapter is empty. `[doctor]`

Stack-specific skills (for example an IDE oracle) live in their own project-owned `## Stack-specific skills` chapter — the core/extension split that keeps the managed chapters stack-identical and `## `-bounded. See [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](adr/2026-06-24-claude-md-managed-chapters.md).

The same refresh also stamps the harness release date as `CLAUDE.md`'s first line — `<!-- harness: <YYYY-MM-DD> -->`, single-sourced from `harness/VERSION-DATE`. Because `CLAUDE.md` is injected into every session, the token lands in every transcript. Downstream analysis attributes a session to the harness that produced it; the date maps one-to-one to the version. The doctor's `harness-stamp` check fails if the stamp is missing, duplicated, or malformed. `[doctor]` See [Stamp the Harness Release Date into Every Session via CLAUDE.md](adr/2026-06-27-harness-version-stamp.md).

## Optional Capabilities

A capability (e.g. an IDE semantic oracle) may extend the harness when three properties hold:

1. **Never roster-required.** Its absence fails nothing.
2. **Probed, not declared.** Availability is detected at runtime; nothing about it is committed.
3. **Never load-bearing.** The pipeline functions identically without it; when present, its claims require citations.

## Templates and Materialization

Every roster file has a template shipped with the harness. Materialization writes it into the project with a provenance first line:

```text
<!-- harness: <YYYY-MM-DD> -->
```

Everything below the provenance line is the consumer's. Re-materializing an existing file is forbidden; that is the channel rule. The date is the harness release date, single-sourced from `harness/VERSION-DATE` and filled by `init` at scaffold time. It is the same token `CLAUDE.md` carries, so every stamp a target receives is one orderable date. It records when the file was scaffolded and is independent of `spec_version`.

## Versioning

Two version axes describe a materialized project, decoupled. The **artifact version** (`harness/VERSION`, semver) names the release that produced the runtime. It is carried by the marketplace and each `plugin.json` — versioning lives where it is acted on, not stamped into the target. A target's files instead record that release as its **date** (`harness/VERSION-DATE`) — the orderable, neutral token. Stamped on every brief's provenance line and on `CLAUDE.md` line 1, it lets downstream analysis attribute a session to the harness that produced it. The second axis, **`spec_version`**, names the API contract revision; the expectations manifest (`brief-expectations.toml`) carries it and the doctor validates that a project's declared `spec_version` matches. The artifact version may advance on every release. `spec_version` advances only when this contract changes, so a marketplace plugin can ship upgrades without forcing an API-compat bump. Until 1.0, minor `spec_version` increments may break. From 1.0, a removed file, a removed section, or a tightened slot is a major version; additions with shipped defaults are minor.
