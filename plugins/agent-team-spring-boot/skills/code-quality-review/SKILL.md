---
name: code-quality-review
description: >-
  Java code quality checklist for Spring Boot applications.
  Load when conducting code quality reviews.
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

## IDE-Assisted Review (optional)

When an IDE semantic oracle is available, use it to raise review precision over grep-and-recall: (a) pre-filter deterministic inspections on changed files and fold them into findings — if `code-quality-gate` § IDE Static Analysis already ran them, confirm rather than re-litigate; and (b) ground `consistent-with-codebase` claims by resolving the referenced symbol instead of recalling it ("mirrors `ExampleRepository`" is a checkable claim). Part (b) is required, not optional: when the oracle is connected, a `consistent-with-codebase` finding (raised or cleared) **must cite the `search_symbol` / `get_symbol_info` call** that resolves the referenced symbol (see `intellij-idea` § Cite the call that backs a claim) — without the oracle, cite the grep and label it the weaker basis. The inspection pre-filter (a) stays an accelerator; a client without an oracle reviews on native tools alone. Tool mechanics: see the `intellij-idea` skill.

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
