---
name: code-quality-review
description: >-
  Go code quality checklist based on Google Go Style Guide, plus design
  placement against the project's recorded briefs. Load when conducting
  code quality reviews.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
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

## IDE-Assisted Review (optional)

When an IDE semantic oracle is available, use it to raise review precision over grep-and-recall: (a) pre-filter deterministic inspections on changed files and fold them into findings — if `code-quality-gate` § IDE Static Analysis already ran them, confirm rather than re-litigate; and (b) ground `consistent-with-codebase` claims by resolving the referenced symbol instead of recalling it ("mirrors `exampleStore`" is a checkable claim). Part (b) is required, not optional: when the oracle is connected, a `consistent-with-codebase` finding (raised or cleared) **must cite the `search_symbol` / `get_symbol_info` call** that resolves the referenced symbol (see `goland` § Cite the call that backs a claim) — without the oracle, cite the grep and label it the weaker basis. The inspection pre-filter (a) stays an accelerator; a client without an oracle reviews on native tools alone. Tool mechanics: see the `goland` skill.

## Design Placement

The style guide is the floor; the project's recorded design is the wall. For every new or moved business rule in the diff — a conditional, a validation, a computation encoding a domain decision — check its landing layer against the owning component's row in `docs/system-design.md`, read under the project's `docs/architecture-principles.md` (the placement doctrine a project may adapt):

- [ ] A new business rule lives in the layer its catalog row assigns. A rule landing in a web controller, handler, or adapter when the catalog assigns a domain or service seam is a `blocked` finding, severity per impact — even when the code works and reads cleanly.
- [ ] A helper widened for test access (package-private, exported-for-tests) is a placement smell: the sanctioned seam usually makes the behavior testable without widening.
- [ ] Normalization, formatting, and value logic sit where the catalog places their kind; the same rule applies when such logic lands inline in a handler.
- [ ] When neither the catalog nor `docs/architecture-principles.md` assigns a home for the rule's kind, say so and route the finding `clarify` to the system-design-expert instead of guessing.

Judge placement against the recorded briefs, never personal architecture taste. Every placement finding cites the catalog row or principle it enforces.

## Scope and Vocabulary

The slice's contract is its acceptance bullets in `docs/prd.md`; its boundary is the non-goals there and the non-goal ADRs under `docs/adr/`. Read both before the checklist:

- [ ] The change delivers the slice's acceptance bullets and nothing past them. Behavior outside the requirement, or work a recorded non-goal rules out, is a `blocked` finding carrying `bar_clause: "spec-grounded"`; speculative generality carries `"fit-for-purpose"`.
- [ ] New domain-facing names — types, fields, operations, user-facing messages — use the terms `docs/ubiquitous-language.md` defines and none it lists as terms to avoid. A coined synonym for a defined term is a `blocked` finding, severity `fixable`, carrying `bar_clause: "consistent-with-codebase"` and citing the entry. An empty vocabulary doc clears the check; say so rather than guessing.

## Code Quality Checklist

### Formatting
- [ ] Code passes `gofmt`
- [ ] No fixed line length, but refactor overly long lines rather than splitting arbitrarily
- [ ] Closing braces align with opening brace indentation
- [ ] Function signatures on single lines where possible

### Naming (MixedCaps)
- [ ] Exported names: `MixedCaps`
- [ ] Unexported names: `mixedCaps`
- [ ] No underscores in names (except test files, generated code, OS interop)
- [ ] Acronyms consistent casing: `URL`, `HTTP`, `ID` (all caps) or `url`, `http`, `id` (all lower)
- [ ] Receiver names: short (1-2 letters), abbreviation of type, consistent across methods
- [ ] Variable name length proportional to scope size
- [ ] No `Get` prefix on getters (use `Counts` not `GetCounts`)
- [ ] No repetition: avoid redundant package/type/context info in names
- [ ] Constants describe meaning, not content (`MaxRetries` not `Three`)
- [ ] Avoid shadowing standard package names (`context`, `errors`, `fmt`)
- [ ] No util/helper/common package names

### Documentation
- [ ] All exported names have doc comments starting with the name
- [ ] Package comments immediately above package clause (no blank line)
- [ ] Doc comment sentences capitalized and punctuated; fragments need not be
- [ ] Target 80 characters for comment line length
- [ ] Runnable examples in test files, not production source
- [ ] Document error-prone or non-obvious fields; skip obvious ones
- [ ] Document when operations are NOT safe for concurrent use
- [ ] Document cleanup requirements to prevent resource leaks
- [ ] Document significant sentinel errors and error types returned

### Imports
- [ ] Four groups: standard library, project packages, third-party, side-effect imports
- [ ] Rename most local/project-specific import on collision
- [ ] No dot imports (makes functionality source unclear)
- [ ] Blank imports only in main packages or tests

### Error Handling
- [ ] `error` as final return parameter
- [ ] Return `nil` for successful operations
- [ ] Error strings lowercase (except proper nouns), no ending punctuation
- [ ] Wrap with context per `docs/architecture-principles.md` error-flow rule: `fmt.Errorf("context: %w", err)`
- [ ] Place `%w` at end of error string
- [ ] Handle errors before proceeding (early return, not else clauses)
- [ ] No in-band errors (special values like -1); use multiple returns
- [ ] Use sentinel values or custom types for programmatic error inspection
- [ ] Use `errors.Is` for wrapped errors, not string matching
- [ ] Don't duplicate error info already in underlying error
- [ ] Let callers decide whether to log errors

### Functions and Methods
- [ ] Single responsibility
- [ ] Early returns for error cases
- [ ] 4 or fewer parameters; use option structs for more
- [ ] Omit types/receiver names from function names
- [ ] Noun-like names for value-returning functions; verb-like for actions
- [ ] `context.Context` always first parameter (except HTTP handlers)
- [ ] Prefer synchronous over asynchronous functions
- [ ] Don't pass pointers just to save bytes (except large structs, protobufs)
- [ ] Receiver type: use pointer when uncertain; correctness is primary criterion

### Control Flow
- [ ] Don't line-break if statements; extract boolean operands as local variables
- [ ] Omit redundant break statements in switch
- [ ] Use comments for empty switch clauses
- [ ] Handle errors in indent; keep happy path unindented

### Concurrency
- [ ] Goroutine lifetimes clear: document when/whether they exit
- [ ] Never create custom context types; use `context.Context`
- [ ] Specify channel direction (`<-chan`, `chan<-`) where possible
- [ ] Don't copy structs with sync primitives or pointer-type methods

### Package Structure
- [ ] Internal packages for implementation details
- [ ] No circular imports
- [ ] Interfaces in consumer package, not implementer package
- [ ] Tightly coupled unexported types together in one package
- [ ] Split conceptually distinct functionality into separate packages

### Panics
- [ ] Reserved for impossible conditions, not normal error handling
- [ ] `MustXYZ` naming for helpers that panic; use only at program startup
- [ ] Never let panics escape package boundaries; translate to returned errors
- [ ] Use `log.Fatal` for invariant failures, not `panic`

### Variables
- [ ] Prefer `:=` over `var` when initializing with non-zero values
- [ ] Use `var` for zero values conveying "empty and ready for later use"
- [ ] Preallocate slices/maps when final size is known
- [ ] Prefer `nil` slices over empty slices for local variables
- [ ] Prefer `any` over `interface{}` (Go 1.18+)
- [ ] Prefer `%q` for readable string output with quotation marks

### Generics
- [ ] Use only when fulfilling business requirements
- [ ] Avoid premature polymorphism without multiple instantiations
