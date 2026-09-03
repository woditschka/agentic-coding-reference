---
name: code-quality-review
description: >-
  Java code quality checklist for Spring Boot applications, plus design
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

When an IDE semantic oracle is available, use it to raise review precision over grep-and-recall: (a) pre-filter deterministic inspections on changed files and fold them into findings — if `code-quality-gate` § IDE Static Analysis already ran them, confirm rather than re-litigate; and (b) ground `consistent-with-codebase` claims by resolving the referenced symbol instead of recalling it ("mirrors `ExampleRepository`" is a checkable claim). Part (b) is required, not optional: when the oracle is connected, a `consistent-with-codebase` finding (raised or cleared) **must cite the `search_symbol` / `get_symbol_info` call** that resolves the referenced symbol (see `intellij-idea` § Cite the call that backs a claim) — without the oracle, cite the grep and label it the weaker basis. The inspection pre-filter (a) stays an accelerator; a client without an oracle reviews on native tools alone. Tool mechanics: see the `intellij-idea` skill.

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

### Naming
- [ ] Type names and suffixes follow `docs/architecture-principles.md` § Naming (value-object/service rules, prohibited-suffix list)
- [ ] Variables: descriptive, length proportional to scope
- [ ] No `get`/`set` prefixes on record accessors (records generate `name()` not `getName()`)
- [ ] No abbreviations unless universally understood
- [ ] Package names: lowercase, single word where possible
- [ ] No `util`/`helper`/`common` package names
- [ ] No type name repetition in method names (`parser.parse()` not `parser.parseInput()`)

### Records and Data Model
- [ ] Records realize the value-object rule (immutable, equality by value) in `docs/architecture-principles.md`; used for data transfer between pipeline steps
- [ ] Record fields are typed (no raw `Object` or `Map<String, Object>`)
- [ ] `LocalDate` for dates, `Instant` for timestamps, not `String`
- [ ] `Optional` used for nullable return values, not null
- [ ] Jackson annotations only where needed (records work with Jackson by default)
- [ ] No mutable state in records
- [ ] Collections use defensive copies where appropriate

### Spring Boot Idioms
- [ ] `@Component` / `@Service` for stateless services
- [ ] Constructor injection (implicit with single constructor, no `@Autowired`)
- [ ] `@ConfigurationProperties` with records for typed config binding
- [ ] `@ConditionalOnProperty` for optional components
- [ ] `spring.main.web-application-type=none` (if CLI)
- [ ] `CommandLineRunner` for the entry point, not `main()` logic (if CLI)

### Error Handling
- [ ] Follows the error-handling policy the project's briefs declare (system-design.md or architecture-principles.md)
- [ ] Exceptions caught at appropriate granularity (not blanket `catch (Exception e)`)
- [ ] Exception chaining preserved (`throw new X(msg, cause)`); no `printStackTrace`
- [ ] Resources closed via try-with-resources
- [ ] Fatal errors log at ERROR and terminate with a non-zero exit
- [ ] Error messages include enough context to diagnose the failure
- [ ] No swallowed exceptions (every catch block logs or rethrows)
- [ ] `Optional.empty()` for expected absence, exceptions for unexpected failures

### Design Principles
- [ ] Immutable records, no mutable state in records
- [ ] Stream pipelines preferred over manual loops for transformations
- [ ] Modern Java idioms (`var`, pattern matching, text blocks)

### Logging
- [ ] SLF4J with `{}` placeholders, not string concatenation
- [ ] Levels: INFO for progress, WARN for skipped items, ERROR for failures, DEBUG for detail
- [ ] No `System.out.println` or `System.err.println`
- [ ] Log messages include relevant context

### Functions and Methods
- [ ] Single responsibility
- [ ] Early returns for error/edge cases
- [ ] Methods under ~30 lines (extract helpers if longer)
- [ ] No side effects in methods named as queries

### Control Flow
- [ ] Happy path unindented; error paths handled early
- [ ] No deeply nested if/else chains
- [ ] Pattern matching (`instanceof` with pattern variables) where appropriate
- [ ] Enhanced for-each or streams over indexed loops

### Package Structure
- [ ] Follows system-design.md package layout
- [ ] No circular dependencies between packages
- [ ] Each package has a clear single responsibility
- [ ] Packages hold only the responsibilities system-design.md assigns them (a declared `model/` package stays free of business logic)

### UTF-8 and Edge Cases
- [ ] All file I/O specifies `StandardCharsets.UTF_8`
- [ ] HTML output (if any) uses `<meta charset="UTF-8">`
- [ ] Special characters in input handled correctly
- [ ] No assumption that input is ASCII

### Testing

Test quality is the test-reviewer's dimension; the checklist lives in the `test-review` skill and `docs/testing-principles.md`. Flag a test here only when it blocks reading the production change.
