---
name: code-quality-review
description: >-
  Code-quality checklist — language-agnostic principles, design placement
  against the project's recorded briefs, and the per-section slots a stack
  fills in. Load when conducting code quality reviews.
compatibility:
  - claude-code
  - github-copilot
  - opencode
reads:
  - docs/architecture-principles.md
  - docs/system-design.md
  - docs/prd.md
  - docs/ubiquitous-language.md
  - docs/adr/
metadata:
  version: "1.0"
  author: team
---

## Design Placement

The style guide is the floor; the project's recorded design is the wall. For every new or moved business rule in the diff — a conditional, a validation, a computation encoding a domain decision — check its landing layer against the owning component's row in `docs/system-design.md`, read under the project's `docs/architecture-principles.md` (the placement doctrine a project may adapt):

- [ ] A new business rule lives in the layer its catalog row assigns. A rule landing in a web controller, handler, or adapter when the catalog assigns a domain or service seam is a `blocked` finding, severity per impact — even when the code works and reads cleanly.
- [ ] A helper widened for test access (package-private, exported-for-tests) is a placement smell: the sanctioned seam usually makes the behavior testable without widening.
- [ ] Normalization, formatting, and value logic sit where the catalog places their kind; the same rule applies when such logic lands inline in a handler.
- [ ] When neither the catalog nor `docs/architecture-principles.md` assigns a home for the rule's kind, say so and route the finding `clarify` to the system-design-expert instead of guessing. The same routing applies when two briefs read against each other on it. A placement finding that asks for a design decision is a `clarify` by its own words, never `blocked`. `blocked` is for a home the catalog assigns unambiguously.

Judge placement against the recorded briefs, never personal architecture taste. Every placement finding cites the catalog row or principle it enforces.

## Scope and Vocabulary

The slice's contract is its acceptance bullets in `docs/prd.md`; its boundary is the non-goals there and the non-goal ADRs under `docs/adr/`. Read both before the checklist:

- [ ] The change delivers the slice's acceptance bullets and nothing past them. Behavior outside the requirement, or work a recorded non-goal rules out, is a `blocked` finding carrying `bar_clause: "spec-grounded"`; speculative generality carries `"fit-for-purpose"`.
- [ ] New domain-facing names — types, fields, operations, user-facing messages — use the terms `docs/ubiquitous-language.md` defines and none it lists as terms to avoid. A coined synonym for a defined term is a `blocked` finding, severity `fixable`, carrying `bar_clause: "consistent-with-codebase"` and citing the entry. An empty vocabulary doc clears the check; say so rather than guessing.

## Code Quality Checklist

This checklist is structurally complete and language-agnostic. The principles below hold in any language; the **Stack-specific rules** slot under each heading is where this project records the conventions its language and tools impose, or points to `docs/architecture-principles.md` and `CLAUDE.md`. A reviewer decides pass or fail on the principles. An empty slot means the stack has not recorded its specifics yet — not that anything goes.

### Formatting
- [ ] Code passes the project's formatter (`scripts/gate.sh format` is clean)
- [ ] Long lines are refactored for clarity, not split arbitrarily
- [ ] Layout is tool-enforced — no hand-formatting the formatter would undo
- [ ] **Stack-specific rules:** {{FILL: formatter, line conventions}}

### Naming
- [ ] One consistent casing scheme per identifier kind
- [ ] Name length is proportional to scope; short names only in small scopes
- [ ] Names describe meaning, not type or implementation detail
- [ ] No context already implied by the enclosing module or type
- [ ] No dumping-ground names (util, helper, common, misc)
- [ ] **Stack-specific rules:** {{FILL: casing scheme, acronym and getter conventions}}

### Documentation
- [ ] Every public name carries a doc comment that starts with the name
- [ ] Comments explain non-obvious intent; they never restate the code
- [ ] A comment a better name would make redundant is a rename; no requirement ids or edge-case numbers in code comments, the covering test carries the citation (`legible-cold`). `python3 scripts/grading.py conventions-map` lists every added comment block
- [ ] Concurrency-safety, ownership, and cleanup requirements are documented where they apply
- [ ] **Stack-specific rules:** {{FILL: doc-comment format, public-API doc rules}}

### Construction
The brief's Pattern Catalog row "Construction and update" binds as written; a project that adapts the row is reviewed against its own text.
- [ ] A type has one entry point taking every mandatory parameter, and it validates
- [ ] Optional attributes are `with` copies routed through that entry point; a rule-governed change is a named operation, never a wither
- [ ] No builder on a domain type and no test-only construction path
- [ ] **Stack-specific rules:** {{FILL: the constructor or creator idiom, the copy idiom}}

### Imports and Dependencies
- [ ] Imports are grouped and ordered consistently
- [ ] No unused imports or dependencies (`scripts/gate.sh deps` is clean)
- [ ] New dependencies are justified against `docs/system-design.md` § Dependency Policy
- [ ] **Stack-specific rules:** {{FILL: import grouping, dependency conventions}}

### Error Handling
- [ ] Errors are surfaced, not swallowed; failures are explicit
- [ ] Error messages carry context inward without leaking internals outward
- [ ] The happy path stays unindented; failures exit early
- [ ] Programmatic error inspection uses typed or sentinel errors, not string matching
- [ ] **Stack-specific rules:** {{FILL: error idiom — return values, exceptions, result types}}

### Functions and Methods
- [ ] Single responsibility; one reason to change
- [ ] Small parameter lists; group related parameters into a type when they grow
- [ ] Names read as nouns for value-returning operations, verbs for actions
- [ ] Prefer synchronous, side-effect-free designs where practical
- [ ] **Stack-specific rules:** {{FILL: signature conventions, receiver/self rules}}

### Control Flow
- [ ] Conditions stay simple; complex booleans are extracted to named locals
- [ ] No dead branches or redundant control statements
- [ ] **Stack-specific rules:** {{FILL: the control-flow idioms this stack enforces, e.g. early return, guard clauses, no nested ternaries}}

### Concurrency
- [ ] Concurrent unit lifetimes are clear — start, ownership, and exit are explicit
- [ ] Shared state is synchronized or avoided; data races are designed out
- [ ] Cancellation and timeouts propagate through the call tree
- [ ] **Stack-specific rules:** {{FILL: concurrency primitives, cancellation idiom}}

### Module Structure
- [ ] Implementation details stay internal; only the intended API is public
- [ ] No circular dependencies between modules
- [ ] Interfaces are defined where consumed, not where implemented
- [ ] Conceptually distinct functionality lives in separate modules
- [ ] **Stack-specific rules:** {{FILL: visibility mechanism, module layout}}

### Failure and Invariants
- [ ] Hard failures (assertions, aborts) are reserved for impossible conditions, not normal errors
- [ ] Invariant violations fail loudly at the boundary, never silently
- [ ] **Stack-specific rules:** {{FILL: assertion/exception/abort policy}}

### Variables and Types
- [ ] Declarations sit close to use; scope is as narrow as possible
- [ ] Zero and empty values are used intentionally, documented when they carry meaning
- [ ] Collections are pre-sized when the final size is known
- [ ] **Stack-specific rules:** {{FILL: declaration idioms, preferred types}}
