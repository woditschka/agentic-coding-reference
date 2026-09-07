<!-- harness: {{HARNESS_DATE}} -->
# Testing Principles

This document defines how this project writes, structures, and organizes tests. The principles are language-agnostic; language-specific conventions live in the project's `CLAUDE.md`.

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

The pyramid's question — could this rule have been tested without the framework? — applies to rules the design doc assigns below the boundary. A rule the design assigns to the boundary layer (request binding, normalization, response shaping) is tested at that layer. Extracting it for a unit test is placement drift, not pyramid progress.

## Coverage

| Target | Scope |
|--------|-------|
| 80% line coverage | Domain and core packages |

Coverage is judged by behavior exercised, not lines touched. The number is a tripwire, not a goal: a drop below the target signals untested behavior slipped in; reaching it proves nothing by itself. Raising coverage with assertion-free tests is a defect, not progress.

## Mocking Policy

Prefer real implementations over mocks in all layers.

| Principle | Rule |
|-----------|------|
| **Real objects first** | Construct real value objects. They are immutable and cheap to create. |
| **Real I/O for integration** | Use real files, real filesystem, real test data. |
| **Mock only at system boundaries** | HTTP clients, WebSocket connections, external APIs — these are the only acceptable mock points. |
| **Never mock internal code** | Internal packages, domain objects, and services use real implementations. |
| **Hand-write mocks** | When mocking is necessary, hand-write simple implementations. No mock frameworks. The slice's design record names the double per boundary. |

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
| **Irrelevant** | Required by the API but has no bearing on outcome | `SOME_` / `ANY_` prefix, or a named default | `SOME_EMAIL`, `ANY_ADDRESS`, `anEmployee()` |
| **Mystery** | Bare literal with no explanation | **Eliminate** | `42`, `"hello@x.com"` |

A test with zero Tier 3 values is self-documenting. The reader scans names alone and knows which data drives the test and which is scaffolding.

### Constants Placement

| Scope | When to Use |
|-------|-------------|
| Class/file level | Universally irrelevant fixtures (`ANY_ADDRESS`, `SOME_PRODUCT`) |
| Method level | Locally irrelevant values (`SOME_QUANTITY`) or scenario-specific meaningful values (`DISCOUNT_PCT`) |

## Test Data Construction

### One Construction API

A domain type has one public way to come into being: its constructor, or one named creator such as `Address.of(...)`. The named creator earns its place where the name adds meaning or input is normalized before validation. That entry point takes every mandatory parameter and enforces the type's invariants, so no instance exists in an invalid state. Attributes the domain lets vary after creation, the optional ones first, are set through `with` copies on the type, `owner.withAddress(address)`, each routed through the same entry point. A test varies a mandatory component the same way, since the copy re-enters the entry point. Attributes that belong together form a value object with one wither. Where the group is small and its order reads itself, the wither may take the parts directly, `withAddress("Alexanderplatz 1", "10178 Berlin")`, as a thin overload that builds the value object. A change a business rule governs is a named operation, never a wither.

Tests call exactly that API. Production, persistence mapping, and tests construct the same way; there is no test-only builder, factory class, or second construction path.

```text
BAD:  createShipment("WH-01", "Seattle", "Portland", 12.5, "FastFreight", 2)   -- a test-only factory; which value matters is invisible
GOOD: aShipment().withCarrier(FAST_FREIGHT).withWeight(OVERWEIGHT_KG)           -- the type's own API; the varied values are visible
GOOD: new Money(TEN, EUR)                                                       -- a value object with all-named arguments
```

When the mandatory signature changes, the named defaults are the only test code that changes.

### Named Defaults

An instance whose values do not matter to the test hides behind a one-line named default that calls the type's entry point with irrelevant values:

```text
aShipment()      -- every mandatory parameter filled with SOME_/ANY_ values
anOwner()        -- nothing about the owner matters
```

A named default is a name for values, not a second API. It holds no logic and takes no parameters. It is the only place the test tree fills a mandatory parameter it does not care about. A test that cares about one attribute starts from the default and applies one wither. Where instances share a datastore or run in parallel, the default generates unique values (counter or UUID) so tests never collide.

### Collapse Irrelevant Dependencies

If the test outcome does not depend on an object, the reader should not see it:

```text
BAD:  engine = anEngine(); trans = aTransmission(); vehicle = new Vehicle(engine, trans, ELECTRIC)
GOOD: vehicle = aVehicle().withDrive(ELECTRIC)
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

Prefer assertion styles that produce chained, readable, self-documenting assertions with rich failure messages.

| Principle | Rule |
|-----------|------|
| Use the most direct assertion available | Pick the assertion that states the intent exactly |
| One assertion per concern | Multiple assertions on the same result are fine; testing unrelated concerns is not |
| No branching in assertions | No `if/else`, `switch`, or loops. Use collection-aware assertions instead |
| Whole-object comparison | Compare complete expected objects rather than picking apart fields |

### Stop Re-Testing Other Units

Assert only on the behavior the test owns. Trust that other components' own tests cover them. Build the expected object and compare in one shot rather than asserting on individual fields that belong to another unit.

## Cleanup

### Default to Ephemeral Fixtures

If no persistent side effect occurs (no database writes, no file creation), cleanup should be empty. Use in-memory objects that vanish when the test ends.

### Never Share Mutable Fixtures

Shared mutable state causes unrepeatable tests, interacting tests, and mystery guests. Each test builds exactly the state it needs through the type's entry point and the suite's named defaults.

Shared fixtures are acceptable only when immutable — static reference data that no test modifies.

### Automate Persistent Cleanup

Register each persistent object at creation time. Let the test framework iterate and clean them all, catching errors individually. Never write per-test teardown logic.

## Testing Vocabulary

All patterns accumulate into a domain-specific testing vocabulary: named defaults, custom assertions, named constants, and `SOME_`/`ANY_` placeholders.

Once the vocabulary exists:
- Writing a new test reuses existing named defaults and assertions
- Reading is consistent — developers see `aCustomer().withDiscount(DISCOUNT_PCT)` and understand instantly
- Maintenance is cheap — a signature change updates one named default, not every test
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

- All error scenarios documented in the system design have test coverage
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
10. **One construction API:** Every object built through the type's entry point and its `with` copies, irrelevant ones behind a named default; no test-only builder or factory?
11. **No mystery values:** Every literal is named or declared irrelevant?
12. **Signal vs. noise:** Reader can tell at a glance which values matter?
13. **Transparent expectations:** Expected values derived from inputs?
14. **Zero duplication:** Reusable patterns in the shared vocabulary?
