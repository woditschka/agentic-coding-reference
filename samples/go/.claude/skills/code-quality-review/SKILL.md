---
name: code-quality-review
description: >-
  Go code quality checklist based on Google Go Style Guide, plus design
  placement and workload fit against the project's recorded briefs. Load when conducting
  code quality reviews.
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

## IDE-Assisted Review (optional)

When an IDE semantic oracle is available, use it to raise review precision over grep-and-recall: (a) pre-filter deterministic inspections on changed files and fold them into findings — if `code-quality-gate` § IDE Static Analysis already ran them, confirm rather than re-litigate; and (b) ground `consistent-with-codebase` claims by resolving the referenced symbol instead of recalling it ("mirrors `exampleStore`" is a checkable claim). Part (b) is required, not optional: when the oracle is connected, a `consistent-with-codebase` finding (raised or cleared) **must cite the `search_symbol` / `get_symbol_info` call** that resolves the referenced symbol (see `goland` § Cite the call that backs a claim) — without the oracle, cite the grep and label it the weaker basis. The inspection pre-filter (a) stays an accelerator; a client without an oracle reviews on native tools alone. Tool mechanics: see the `goland` skill.

## Design Placement

The style guide is the floor; the project's recorded design is the wall. For every new or moved business rule in the diff — a conditional, a validation, a computation encoding a domain decision — check its landing layer against the owning component's row in `docs/system-design.md`, read under the project's `docs/architecture-principles.md` (the placement doctrine a project may adapt):

- [ ] A new business rule lives in the layer its catalog row assigns. A rule landing in a web controller, handler, or adapter when the catalog assigns a domain or service seam is a `blocked` finding, severity per impact — even when the code works and reads cleanly.
- [ ] A helper widened for test access (package-private, exported-for-tests) is a placement smell: the sanctioned seam usually makes the behavior testable without widening.
- [ ] Normalization, formatting, and value logic sit where the catalog places their kind; the same rule applies when such logic lands inline in a handler.
- [ ] When neither the catalog nor `docs/architecture-principles.md` assigns a home for the rule's kind, say so and route the finding `clarify` to the system-design-expert instead of guessing. The same routing applies when two briefs read against each other on it. A placement finding that asks for a design decision is a `clarify` by its own words, never `blocked`. `blocked` is for a home the catalog assigns unambiguously.

Judge placement against the recorded briefs, never personal architecture taste. Every placement finding cites the catalog row or principle it enforces.

## Scope and Vocabulary

The slice's contract is its acceptance bullets in `docs/prd.md`; its boundary is the non-goals there and the non-goal ADRs under `docs/adr/`. Read both before the checklist:

- [ ] The change delivers the slice's acceptance bullets and nothing past them. Behavior outside the requirement, or work a recorded non-goal rules out, is a `blocked` finding carrying `bar_clause: "spec-grounded"`; speculative generality carries `"fit-for-purpose"`. The rule reaches fix rounds. A fix delta that changed behavior on a route or flow those bullets do not name is the same finding, whichever reviewer asked for it.
- [ ] New domain-facing names — types, fields, operations, user-facing messages — use the terms `docs/ubiquitous-language.md` defines and none it lists as terms to avoid. A coined synonym for a defined term is a `blocked` finding, severity `fixable`, carrying `bar_clause: "consistent-with-codebase"` and citing the entry. An empty vocabulary doc clears the check; say so rather than guessing.

## Workload Fit

Resource use is judged against `docs/system-design.md` § Scale and Load, never against the reviewer's own estimate of the workload. The implementer selected against that section, and a review from a different basis is taste (`tdd-principles` § Fit for the Workload). For every new or changed code path that scales with data:

- [ ] The structure's time and space complexity fits the row's operations, size, and access pattern. A mismatch is a `blocked` finding under `operationally-honest` citing the row, severity `fixable`. A form that fits the row but differs from its Form column is judged on fit; the column records, it does not bind. `critical` is for a hot-path or limit row only, because a misfit elsewhere ships without harm and a critical sustains dissent alone.
- [ ] A hot-path row states its form's time and space bound with its kind. The code's structure delivers that bound, because on a hot path the bound is the requirement.
- [ ] A row marked "unrecorded, treated as bounded" makes the simplest correct form the right one. The marker is not a finding, because the row is where the owner corrects the figure, never the code.
- [ ] When no row covers a path that plainly scales with user data, the finding is `clarify` to the system-design-expert on `changes_requested`, with no `bar_clause`, never `blocked`. Locate it at `docs/system-design.md`, so the owner is dispatched directly. The reviewer invents no size, as the implementer may not.
- [ ] A finding that asks for a more complex structure cites the row that demands it. Without one the simplest correct form stands, because clarity is paid on every read.
- [ ] Nothing is hand-written that the standard library or an approved source provides (`sort`, `slices`, `maps`, `container/heap`, `sync`). An exception is recorded in the row's Form column with its ADR, because hand-written structures are where subtle bugs live; its case-table tests are the test-reviewer's.
- [ ] A performance claim names its benchmark (`testing.B`) or says it is reasoned, in the row or an ADR; a code comment carries no bound.
- [ ] An inefficiency outside the change set is a `recommendations` entry, never a finding on the slice (`spec-grounded`).
- [ ] An unbounded load is the security-reviewer's `secure-by-design` item; this section files nothing twice.

The free tier is the default on every path: where the better form costs nothing in clarity, it is taken without a row. The test is clarity, not the shape; a scan over a bounded literal list is the simplest form and stays. A neighbor's misselection is a convention only while the path stays bounded, because it starts to cost once the path grows. A miss is `blocked`, severity `fixable`, under `operationally-honest` where the better form is equally clear; otherwise a `recommendations` entry. Common shapes:

- membership test by scanning a slice that grows, where a `map[T]struct{}` or `map[K]V` serves
- string built by `+=` in a loop instead of `strings.Builder`
- nested loop over two collections where one map lookup serves
- a plain `map` written from more than one goroutine; a mutex-guarded map where a request-private one serves
- `sync.Map` outside its two documented cases: keys written once and read many times, or disjoint key sets per goroutine

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
- [ ] No util/common/misc package names; a package of pure functions is named for its subject (`slug`, never `helpers`)

### Documentation
- [ ] All exported names have doc comments starting with the name
- [ ] Package comments immediately above package clause (no blank line)
- [ ] Doc comment sentences capitalized and punctuated; fragments need not be
- [ ] Target 80 characters for comment line length
- [ ] Comments explain WHY; a comment a better name would make redundant is a rename; no requirement ids or edge-case numbers in code comments, the covering test carries the citation (`legible-cold`). `python3 scripts/grading.py conventions-map` lists every added comment block
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
- [ ] A function reads at one level of abstraction and calls one level down or sideways, never up (Single Level of Abstraction Principle)
- [ ] Single responsibility
- [ ] Early returns for error cases
- [ ] 4 or fewer parameters; use option structs for more
- [ ] Omit types/receiver names from function names
- [ ] Noun-like names for value-returning functions; verb-like for actions
- [ ] `context.Context` always first parameter (except HTTP handlers)
- [ ] Prefer synchronous over asynchronous functions
- [ ] Don't pass pointers just to save bytes (except large structs, protobufs)
- [ ] Receiver type: use pointer when uncertain; correctness is primary criterion

### Construction
The brief's Pattern Catalog row "Construction and update" binds as written; a project that adapts the row is reviewed against its own text.
- [ ] A type with invariants hides its fields and has one constructor function, `NewOrder(customer, lines) (Order, error)`, taking every mandatory parameter; the error return is the invariant check
- [ ] A value type without invariants exposes its fields and is built with a keyed composite literal; positional literals are a finding
- [ ] Optional attributes are `With` methods on a value receiver returning a copy, the `context.WithTimeout` / `req.WithContext` shape, routed through the constructor where one exists
- [ ] Functional options (`NewServer(addr, WithTimeout(t))`) are an infrastructure-component idiom; a domain type follows the brief's § Test Data Construction: one entry point and `With` copies
- [ ] A change a rule governs is a named method, never a `With`

### Control Flow
- [ ] Don't line-break if statements; extract boolean operands as local variables
- [ ] Omit redundant break statements in switch
- [ ] Use comments for empty switch clauses
- [ ] Handle errors in indent; keep happy path unindented
- [ ] A conditional repeated across sibling sites (code, template elements, links) is duplication: compute it once (a template variable or a defined template) and reference it

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
