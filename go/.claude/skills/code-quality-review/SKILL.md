---
name: code-quality-review
description: >-
  Go code quality checklist based on Google Go Style Guide.
  Load when conducting code quality reviews.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

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
- [ ] Wrap with context: `fmt.Errorf("context: %w", err)`
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
