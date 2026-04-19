---
name: code-quality-review
description: >-
  Java code quality checklist for Spring Boot applications.
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

### Naming
- [ ] Classes follow meaningful naming (value objects as nouns, services as `{Subject}{Verb}er`)
- [ ] No prohibited suffixes (`Manager`, `Helper`, `Utility`, `Handler`, `Processor`, `Base`, `Info`, `Data`)
- [ ] Variables: descriptive, length proportional to scope
- [ ] No `get`/`set` prefixes on record accessors (records generate `name()` not `getName()`)
- [ ] No abbreviations unless universally understood
- [ ] Package names: lowercase, single word where possible
- [ ] No `util`/`helper`/`common` package names
- [ ] No type name repetition in method names (`parser.parse()` not `parser.parseInput()`)

### Records and Data Model
- [ ] Records used for immutable data transfer between pipeline steps
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
- [ ] `CommandLineRunner` for the entry point, not `main()` logic

### Error Handling
- [ ] Follows error handling table in system-design.md
- [ ] Per-item errors: log at WARN, continue to next item
- [ ] Per-batch errors: log at ERROR, continue to next batch
- [ ] Fatal errors: log at ERROR, exit with non-zero code
- [ ] Exceptions caught at appropriate granularity (not blanket `catch (Exception e)`)
- [ ] Error messages include context (which item, which batch)
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
- [ ] `model/` package contains only records, no business logic

### UTF-8 and Edge Cases
- [ ] All file I/O specifies `StandardCharsets.UTF_8`
- [ ] HTML output uses `<meta charset="UTF-8">`
- [ ] Special characters in input handled correctly
- [ ] No assumption that input is ASCII

### Testing (see testing-principles.md)
- [ ] No mocks — real value objects and real I/O
- [ ] AssertJ fluent assertions (not JUnit `assertEquals`)
- [ ] Chained assertions on same object preferred over separate `assertThat()` calls
- [ ] Four-phase structure (Arrange/Act/Assert) separated by blank lines, no phase comments
- [ ] Three-tier data naming: meaningful (`QUANTITY`), irrelevant (`SOME_`/`ANY_`), no mystery literals
- [ ] Object construction behind factory methods, expected values derived from inputs
