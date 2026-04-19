# Testing Principles for Agentic Projects

This document defines how to write, structure, and organize tests in agentic projects. These are language-agnostic principles. Each project applies them with language-specific conventions.

## Tests Are Specifications

A well-written test answers three questions instantly:

1. **What world does this test live in?** (Setup)
2. **What action triggers the behavior?** (Exercise)
3. **What should the world look like afterward?** (Verification)

If a reader needs more than a few seconds to answer all three, the test is too complex.

## Four-Phase Test Structure

Organize every test into four distinct phases:

1. **Arrange** — build the world the test needs
2. **Act** — trigger the behavior under test
3. **Assert** — check that reality matches expectations
4. **Cleanup** — restore the world (ideally automatic)

Separate phases with blank lines. When the test is clean, phase comments (`// Arrange`) are redundant noise. Remove them.

This applies broadly: never add prose that restates what the code already says. Phase comments, descriptive assertion messages on self-evident chains, and inline comments narrating obvious logic all violate this rule.

## Test Pyramid

```text
         +----------+
         |   E2E    |  Full pipeline tests
         |  (~5%)   |
        +------------+
        | Integration |  Real I/O, real data
        |  (~15%)     |
       +--------------+
       |  Unit Tests   |  Pure functions, no I/O
       |  (~80%)       |
       +---------------+
```

| Layer | Scope | I/O | Count |
|-------|-------|-----|-------|
| **Unit** | Single function or class | None — pure logic | ~80% of tests |
| **Integration** | Multi-component with real I/O | Real filesystem, real data | ~15% of tests |
| **E2E** | Full pipeline | Real filesystem, real output | ~5% of tests |

## Mocking Policy

Prefer real implementations over mocks in all layers.

| Principle | Rule |
|-----------|------|
| **Real objects first** | Construct real value objects. They are immutable and cheap to create. |
| **Real I/O for integration** | Use real files, real filesystem, real test data. |
| **Mock only at system boundaries** | HTTP clients, WebSocket connections, external APIs — these are the only acceptable mock points. |
| **Never mock internal code** | Internal packages, domain objects, and services use real implementations. |
| **Hand-write mocks** | When mocking is necessary, hand-write simple implementations. No mock frameworks. |

If a test needs more lines of setup than assertion, that is a signal the production code needs a simpler interface — not that the test needs mocks.

## Test Naming

Tests describe behavior, not implementation. The name should read as a specification.

| Convention | Rule |
|------------|------|
| Test class/file names | Describe the scenario or action being tested |
| Test method/function names | Describe the expected outcome |
| Parameterized tests | Same method name, data-driven via table or CSV source |

## Three-Tier Data Naming Convention

Every value in a test falls into one of three tiers. The naming convention makes each tier explicit.

| Tier | Purpose | Naming Convention | Example |
|------|---------|-------------------|---------|
| **Meaningful** | Directly affects the expected outcome | Role-describing name | `QUANTITY`, `DISCOUNT_RATE`, `HOURLY_WAGE` |
| **Irrelevant** | Required by the API but has no bearing on outcome | `SOME_` / `ANY_` prefix, or anonymous factory | `SOME_EMAIL`, `ANY_ADDRESS`, `createAnEmployee()` |
| **Mystery** | Bare literal with no explanation | **Eliminate** | `42`, `"hello@x.com"` |

A test with zero Tier 3 values is self-documenting. The reader scans names alone and knows which data drives the test and which is scaffolding.

### Constants Placement

| Scope | When to Use |
|-------|-------------|
| Class/file level | Universally irrelevant fixtures (`ANY_ADDRESS`, `SOME_PRODUCT`) |
| Method level | Locally irrelevant values (`SOME_QUANTITY`) or scenario-specific meaningful values (`DISCOUNT_PCT`) |

## Test Data Construction

### Factory Methods

Tests never call production constructors directly. Wrap construction in factory methods owned by the test suite.

```text
BAD:  new Shipment("WH-01", "Seattle", "Portland", 12.5, "FastFreight", 2)
GOOD: createShipment("WH-01", "Seattle", "Portland", 12.5, "FastFreight", 2)
```

When the constructor signature changes, fix one factory method instead of every test.

### Anonymous Factories

When most fields are irrelevant, create factories that auto-generate irrelevant values and accept only the fields that matter:

```text
createATeacher("Math")    -- only department matters
createAProduct(price)     -- only price matters
createAnEmployee()        -- nothing about the employee matters
```

Behind the scenes, the anonymous factory fills in everything else with unique generated data (counter or UUID). Unique generation prevents data collisions when tests share a datastore or run in parallel.

### Collapse Irrelevant Dependencies

If the test outcome does not depend on an object, the reader should not see it:

```text
BAD:  engine = createAnEngine(); trans = createATransmission(); vehicle = createVehicle(engine, trans, ELECTRIC)
GOOD: vehicle = createAVehicle(ELECTRIC)
```

## Derived Expectations

Expected values should be derived from test inputs so the reader can verify correctness by reading the code alone.

```text
BAD:  assertEquals(142.50, payroll.getNetAmount())   -- where did 142.50 come from?
GOOD: gross = HOURS * RATE; assertThat(payroll.getNetAmount()).isEqualTo(gross - (gross * TAX_RATE))
```

If an expected value is a function of the inputs, express that function explicitly. The test becomes self-verifying documentation.

## Assertions

### Fluent Assertions

Prefer assertion libraries that produce chained, readable, self-documenting assertions with rich failure messages.

| Principle | Rule |
|-----------|------|
| Use the most direct assertion available | Pick the assertion that says exactly what you mean |
| One assertion per concern | Multiple assertions on the same result are fine; testing unrelated concerns is not |
| No branching in assertions | No `if/else`, `switch`, or loops. Use collection-aware assertions instead |
| Whole-object comparison | Compare complete expected objects rather than picking apart fields |

### Stop Re-Testing Other Units

Assert only on the behavior the test owns. Trust that other components' own tests cover them. Build the expected object and compare in one shot rather than asserting on individual fields that belong to another unit.

## Cleanup

### Default to Ephemeral Fixtures

If no persistent side effect occurs (no database writes, no file creation), cleanup should be empty. Use in-memory objects that vanish when the test ends.

### Never Share Mutable Fixtures

Shared mutable state causes unrepeatable tests, interacting tests, and mystery guests. Each test builds exactly the state it needs via factory methods.

Shared fixtures are acceptable only when immutable — static reference data that no test modifies.

### Automate Persistent Cleanup

Register each persistent object at creation time. Let the test framework iterate and clean them all, catching errors individually. Never write per-test teardown logic.

## Testing Vocabulary

All patterns accumulate into a domain-specific testing vocabulary: factory methods, custom assertions, named constants, and `SOME_`/`ANY_` placeholders.

Once the vocabulary exists:
- Writing a new test reuses existing factories and assertions
- Reading is consistent — developers see `createACustomer(DISCOUNT_PCT)` and understand instantly
- Maintenance is cheap — API changes update one factory, not every test
- Scaling approaches zero cost per new test

Extract shared test utilities into a common base class or utility module. The vocabulary is a project-wide asset.

## Edge Case and Boundary Testing

### Boundary Testing

Every test suite should cover:
- Empty input
- Single item
- Missing state (first run scenario)
- Corrupted or invalid data
- Special characters and Unicode edge cases

### Error Path Testing

- All error scenarios documented in system-design.md have test coverage
- Corrupted data triggers recovery, not crashes
- I/O errors are caught and logged
- Unparseable input produces a warning, not an exception

### State and Idempotency Testing

- First run creates output
- Second run with no changes produces identical output
- New, changed, and removed items are detected
- State round-trips correctly through serialization

## Agent Decision Checklist

When an agent writes or refactors a test, it walks through these checks:

1. **Structure:** Four phases separated by blank lines alone?
2. **No narration:** Free of comments and messages that restate code?
3. **Fluent assertions:** Using the preferred assertion style?
4. **Linearity:** No branching or loops in the test body?
5. **Focus:** Only asserting on behavior this test owns?
6. **Whole objects:** Comparing complete expected objects?
7. **Collection assertions:** Using collection-aware assertions instead of index-based access?
8. **Named patterns:** Recurring verification sequences extracted?
9. **Automatic cleanup:** Framework handles teardown?
10. **Encapsulated construction:** All objects behind factory methods?
11. **No mystery values:** Every literal is named or declared irrelevant?
12. **Signal vs. noise:** Reader can tell at a glance which values matter?
13. **Transparent expectations:** Expected values derived from inputs?
14. **Zero duplication:** Reusable patterns in the shared vocabulary?

## How This Relates to Project-Level Docs

This document defines the principles. Each implementation applies them:

- **Go:** [`go/CLAUDE.md`](../go/CLAUDE.md) — table-driven tests, `t.Run()` subtests, `cmp.Diff` for struct comparison, `t.Helper()` for helpers, no assertion libraries, race detector, fuzz testing
- **Java Spring Boot:** [`java-spring-boot/docs/testing-principles.md#java-spring-boot-application`](../java-spring-boot/docs/testing-principles.md#java-spring-boot-application) — AssertJ fluent assertions, BDD naming (`WhenYou{Action}`, `the{Subject}Should{Outcome}`), custom assertion classes, parameterized tests with `@CsvSource`
