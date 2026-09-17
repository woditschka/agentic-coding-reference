---
name: code-quality-review
description: >-
  Java code quality checklist for Spring Boot applications, plus design
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

When an IDE semantic oracle is available, use it to raise review precision over grep-and-recall: (a) pre-filter deterministic inspections on changed files and fold them into findings — if `code-quality-gate` § IDE Static Analysis already ran them, confirm rather than re-litigate; and (b) ground `consistent-with-codebase` claims by resolving the referenced symbol instead of recalling it ("mirrors `ExampleRepository`" is a checkable claim). Part (b) is required, not optional: when the oracle is connected, a `consistent-with-codebase` finding (raised or cleared) **must cite the `search_symbol` / `get_symbol_info` call** that resolves the referenced symbol (see `intellij-idea` § Cite the call that backs a claim) — without the oracle, cite the grep and label it the weaker basis. The inspection pre-filter (a) stays an accelerator; a client without an oracle reviews on native tools alone. Tool mechanics: see the `intellij-idea` skill.

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
- [ ] Nothing is hand-written that the JDK or an approved source provides (`java.util` collections, `Comparator`, `PriorityQueue`, `ArrayDeque`, `java.util.concurrent`). An exception is recorded in the row's Form column with its ADR, because hand-written structures are where subtle bugs live; its case-table tests are the test-reviewer's.
- [ ] A performance claim names its measurement or says it is reasoned, in the row or an ADR; a code comment carries no bound. A benchmark harness is not a project dependency by default.
- [ ] An inefficiency outside the change set is a `recommendations` entry, never a finding on the slice (`spec-grounded`).
- [ ] An unbounded load is the security-reviewer's `secure-by-design` item; this section files nothing twice.

The free tier is the default on every path: where the better form costs nothing in clarity, it is taken without a row. The test is clarity, not the shape; a scan over a bounded literal list is the simplest form and stays. A neighbor's misselection is a convention only while the path stays bounded, because it starts to cost once the path grows. A miss is `blocked`, severity `fixable`, under `operationally-honest` where the better form is equally clear; otherwise a `recommendations` entry. Common shapes:

- `List.contains` or `indexOf` inside a loop over a collection that grows, where a `Set` or `Map` serves
- string built by `+=` in a loop instead of `StringBuilder` or `String.join`
- `LinkedList`, or `remove(0)` on an `ArrayList` in a loop, where `ArrayDeque` serves
- nested loop over two collections where one map lookup serves
- `HashMap` or `ArrayList` mutated from more than one thread; a `ConcurrentHashMap` where a request-private map serves
- `parallelStream()` on a bounded collection; boxing in a stream where a primitive stream serves
- N+1 query: a repository call inside a loop, or a lazy association walked per row, where a fetch join or `@EntityGraph` serves
- a transaction held open around I/O that does not need it

## Code Quality Checklist

### Naming
- [ ] Type names and suffixes follow `docs/architecture-principles.md` § Naming (value-object/service rules, prohibited-suffix list)
- [ ] Variables: descriptive, length proportional to scope
- [ ] No `get`/`set` prefixes on record accessors (records generate `name()` not `getName()`)
- [ ] No abbreviations unless universally understood
- [ ] Package names: lowercase, single word where possible
- [ ] No `util`/`common`/`misc` package names; a `Helper` class only as Bloch's utility class: pure static functions over one type the project does not own, statically imported
- [ ] No type name repetition in method names (`parser.parse()` not `parser.parseInput()`)

### Comments and Javadoc
- [ ] Comments explain WHY; none restate what the code already says (`legible-cold`)
- [ ] A comment a better name would make redundant is a rename, not a comment
- [ ] No requirement ids, edge-case numbers, or handoff vocabulary in code comments; the test that covers the case carries the citation
- [ ] Javadoc scope follows the brief; the default is public types and API only, one sentence of purpose. No `@param`/`@return` tags that restate the signature, no empty tags, no `@return` naming the wrong type
- [ ] No narration comments on test methods (the brief's § Tests Are Specifications)
- [ ] List every added comment block: `python3 scripts/grading.py conventions-map` (license headers excluded); each hit failing a bullet above is an `autofix` finding, severity `fixable`

### Records and Data Model
- [ ] Records realize the value-object rule (immutable, equality by value) in `docs/architecture-principles.md`; used for data transfer between pipeline steps
- [ ] Record fields are typed (no raw `Object` or `Map<String, Object>`)
- [ ] `LocalDate` for dates, `Instant` for timestamps, not `String`
- [ ] `Optional` used for nullable return values, not null
- [ ] Jackson annotations only where needed (records work with Jackson by default)
- [ ] Collections use defensive copies where appropriate

### Construction
The brief's Pattern Catalog row "Construction and update" binds as written; a project that adapts the row is reviewed against its own text.
- [ ] A type has one entry point, its canonical constructor or one static creator (`Address.of(...)`), taking every mandatory parameter; a record's compact constructor validates
- [ ] `with{Attribute}(...)` methods return a copy built through that entry point; none assigns a field directly
- [ ] No builder on a domain type and no test-only construction path; a change a rule governs is a named method, never a wither
- [ ] A static creator normalizes before validating and is the only public creation path beside the constructor, never a second one

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

### Logging
- [ ] SLF4J with `{}` placeholders, not string concatenation
- [ ] Levels: INFO for progress, WARN for skipped items, ERROR for failures, DEBUG for detail
- [ ] No `System.out.println` or `System.err.println`
- [ ] Log messages include relevant context

### Functions and Methods
- [ ] A function reads at one level of abstraction and calls one level down or sideways, never up (Single Level of Abstraction Principle)
- [ ] Single responsibility
- [ ] Early returns for error/edge cases
- [ ] Methods under ~30 lines (extract helpers if longer)
- [ ] No side effects in methods named as queries

### Control Flow
- [ ] Happy path unindented; error paths handled early
- [ ] No deeply nested if/else chains
- [ ] Modern Java idioms where they read better: pattern matching (`instanceof` with pattern variables), `var`, text blocks
- [ ] Enhanced for-each or stream pipelines over indexed loops
- [ ] A conditional repeated across sibling sites (code, template elements, links) is duplication: compute it once (`th:with` or a fragment) and reference it

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
