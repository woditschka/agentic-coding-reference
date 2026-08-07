---
name: code-quality-review
description: >-
  Code-quality checklist — language-agnostic principles plus the
  per-section slots a stack fills in. Load when conducting code
  quality reviews.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/architecture-principles.md
metadata:
  version: "1.0"
  author: team
---

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
- [ ] Concurrency-safety, ownership, and cleanup requirements are documented where they apply
- [ ] **Stack-specific rules:** {{FILL: doc-comment format, public-API doc rules}}

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
- [ ] **Stack-specific rules:** {{FILL}}

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
