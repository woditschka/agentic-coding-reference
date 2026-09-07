<!-- harness: 2026-06-26 -->
# Testing Principles

This document defines how this project writes, structures, and organizes tests. The first part lays out language-agnostic principles. The second part (["Java Spring Boot Application"](#java-spring-boot-application)) applies them with Java and AssertJ specifics.

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

This project goes further: **no mock libraries at all.** Do not use Mockito, EasyMock, or any mock/stub framework. Mocks are unnecessary here because:

- **Value objects are immutable records** — constructing a real instance is a one-line call
- **Services are stateless** — pass real inputs, assert real outputs
- **Repositories use real files** — real I/O is fast and catches real bugs
- **Test data exists** — no need to fabricate test doubles

## Test Naming

Tests describe behavior, not implementation. The name should read as a specification.

| Convention | Rule |
|------------|------|
| Test class/file names | Describe the scenario or action being tested |
| Test method/function names | Describe the expected outcome |
| Parameterized tests | Same method name, data-driven via table or CSV source |

This project names tests in BDD style — class names the scenario, method names the outcome, so a failure report reads as a broken specification:

| Test Type | Naming Convention |
|-----------|-------------------|
| Unit test class | `WhenYou{Action}` |
| Integration test class | `{Feature}IT` |
| Test method | `the{Subject}Should{Outcome}()` |
| Parameterized test method | `the{Subject}Should{Outcome}()` with `@CsvSource` |

The machine-checkable floor (the regex handoff validation applies to `test_names`) lives in `scripts/layout.toml` as `test_name_pattern`; this section carries the school the floor cannot express.

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

Prefer assertion libraries that produce chained, readable, self-documenting assertions with rich failure messages.

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

- All error scenarios documented in system-design.md have test coverage
- Corrupted data triggers recovery, not crashes
- I/O errors are caught and logged
- Unparseable input produces a warning, not an exception

### Concurrency Testing

- Shared mutable state has concurrent-access tests using real concurrency primitives
- Interleavings are choreographed deterministically, never with sleeps
- Blocking test operations carry timeouts so a deadlock fails fast

### Adversarial Input Testing

- Every decoder of untrusted input has adversarial tests: malformed, truncated, oversized
- Malformed input is rejected at the boundary, not propagated raw
- Where the project adopts the stack's fuzzer, fuzz targets cover the decoders; the floor is parameterized adversarial fixtures

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

---

# Java Spring Boot Application

This section applies the principles above with Java and AssertJ. It shows concrete refactorings, the Java-specific smell/fix catalog, and a full before/after transformation example. Read the principles section first — the guidance below presumes those rules.

## AssertJ Setup

Fluent assertion libraries like AssertJ produce chained assertions that read like natural-language specifications. They produce richer failure messages, eliminate argument-order confusion, and collapse multi-step verification logic into a single expressive chain. Prefer AssertJ over JUnit's classic `assertEquals`/`assertTrue` in all new tests.

```xml
<!-- Maven -->
<dependency>
    <groupId>org.assertj</groupId>
    <artifactId>assertj-core</artifactId>
    <scope>test</scope>
</dependency>
```

```java
import static org.assertj.core.api.Assertions.assertThat;
```

All tests use AssertJ fluent assertions. Do not use JUnit `assertEquals`, `assertTrue`, or `assertNotNull`:

| JUnit (do not use) | AssertJ (use this) |
|--------------------|--------------------|
| `assertEquals(expected, actual)` | `assertThat(actual).isEqualTo(expected)` |
| `assertTrue(condition)` | `assertThat(condition).isTrue()` |
| `assertNotNull(value)` | `assertThat(value).isNotNull()` |
| `assertEquals(3, list.size())` | `assertThat(list).hasSize(3)` |

## Assertion Refactoring Playbook

### Use the Most Direct Assertion Available

**Smell:** Roundabout ways to express failure or expectation — e.g., wrapping a boolean `false` inside a generic truth check.

**Fix:** Pick the assertion that states the intent exactly. AssertJ's type-aware API offers precise methods for every situation.

```java
// BAD: Indirect — reader must mentally evaluate assertTrue(false)
assertTrue("Expected at least one result", results.size() > 0);

// BETTER (JUnit): More specific
assertFalse("Results should not be empty", results.isEmpty());

// BEST (AssertJ): Reads like a specification, rich failure message
assertThat(results).isNotEmpty();
// Failure: "Expecting actual not to be empty" — no manual message needed

// BAD: Generic boolean when equality is the intent
assertTrue(order.getStatus().equals("shipped"));

// BEST (AssertJ): Fluent, type-safe, clear failure output
assertThat(order.getStatus()).isEqualTo("shipped");
// Failure: "expected: 'shipped' but was: 'pending'" — auto-generated diff
```

**Rule:** Always choose the most semantically precise assertion. AssertJ's fluent chains are the default choice — they're self-documenting and produce failure messages that diagnose problems without re-running the test in a debugger.

### Stop Re-Testing Other Units

**Smell:** A test for component A also asserts on internal fields that are the responsibility of component B (which has its own tests).

**Fix:** Assert only on the behavior under test. Trust that B's own tests cover B.

```java
// BAD: Testing that Reservation's constructor works inside a Booking test
assertThat(reservation.getHotelName()).isEqualTo("Grand Plaza");
assertThat(reservation.getGuestCount()).isEqualTo(2);
assertThat(reservation.getCheckIn()).isEqualTo(LocalDate.of(2025, 6, 1));
assertThat(reservation.getCheckOut()).isEqualTo(LocalDate.of(2025, 6, 5));
assertThat(reservation.getTotalCost()).isEqualByComparingTo("800.00");
assertThat(reservation.getNightlyRate()).isEqualByComparingTo("200.00");

// GOOD: Build the expected object and compare in one shot
Reservation expected = new Reservation(
    "Grand Plaza", 2,
    LocalDate.of(2025, 6, 1), LocalDate.of(2025, 6, 5),
    new BigDecimal("800.00"));
assertThat(reservation).isEqualTo(expected);
```

When full object equality isn't practical (e.g., generated IDs, timestamps), AssertJ can compare specific fields without falling back to field-by-field assertions:

```java
// Compare only the fields that matter, ignoring generated/volatile ones
assertThat(reservation)
    .usingRecursiveComparison()
    .ignoringFields("id", "createdAt")
    .isEqualTo(expected);
```

**Rule:** Construct the expected result as a complete object and compare with a single assertion. Use `usingRecursiveComparison().ignoringFields(...)` when some fields are irrelevant or non-deterministic.

### Flatten All Branching Out of Tests

**Smell:** `if/else` blocks, `switch` statements, or loops inside a test body. When a test has multiple execution paths, it becomes unclear which path actually ran.

**Fix:** Replace conditional checks with sequential guard assertions that halt on failure. AssertJ's collection assertions are particularly powerful here — they eliminate the size-check-then-index pattern entirely.

```java
// BAD: Conditional logic — did the "else" branch ever fire?
List<CartItem> items = cart.getItems();
if (items.size() == 2) {
    assertEquals("ABC-001", items.get(0).getSku());
    assertEquals("XYZ-999", items.get(1).getSku());
} else {
    fail("Cart should contain exactly 2 items");
}

// BETTER (JUnit): Linear guards — each assertion is a gate
List<CartItem> items = cart.getItems();
assertEquals(2, items.size());
assertEquals("ABC-001", items.get(0).getSku());
assertEquals("XYZ-999", items.get(1).getSku());

// BEST (AssertJ): One fluent chain replaces all of the above
assertThat(cart.getItems())
    .hasSize(2)
    .extracting(CartItem::getSku)
    .containsExactly("ABC-001", "XYZ-999");
```

AssertJ's collection assertions are one of its biggest advantages. They eliminate the need for index-based access, guard assertions on size, and manual loops:

```java
// Verify a collection contains exactly one element matching expectations
assertThat(invoice.getLineItems())
    .singleElement()
    .satisfies(item -> {
        assertThat(item.getQuantity()).isEqualTo(QUANTITY);
        assertThat(item.getExtendedPrice()).isEqualByComparingTo(EXPECTED_TOTAL);
    });

// Verify multiple elements by extracting fields into tuples
assertThat(cart.getItems())
    .extracting(CartItem::getSku, CartItem::getQuantity)
    .containsExactly(
        tuple("ABC-001", 2),
        tuple("XYZ-999", 3));

// Verify at least one element matches a condition
assertThat(notifications)
    .anyMatch(n -> n.getType().equals("ALERT") && n.isUrgent());

// Verify all elements satisfy a condition
assertThat(lineItems)
    .allSatisfy(item -> assertThat(item.getTotal()).isPositive());
```

**Rule:** Tests must be straight-line code. No `if`, no `else`, no loops. AssertJ's fluent collection assertions make branching and manual iteration unnecessary — use `extracting`, `containsExactly`, `singleElement`, `allSatisfy`, and `anyMatch` instead.

### Name Verification Patterns

**Smell:** The same multi-step verification sequence appears in three or more tests.

**Fix:** First, check whether AssertJ's built-in vocabulary already expresses the pattern. If it does, a custom helper is unnecessary. If it doesn't, there are two options: a simple helper method, or a full AssertJ custom assertion class.

**Option A: AssertJ already handles it — no helper needed.**

```java
// This pattern appeared in 12 tests:
List<CartItem> items = cart.getItems();
assertEquals(1, items.size());
assertEquals(expectedItem, items.get(0));

// AssertJ replaces it natively — no custom code required
assertThat(cart.getItems()).containsExactly(expectedItem);
```

**Option B: Simple helper for domain-specific checks.**

```java
private void assertCartContainsOnly(ShoppingCart cart, CartItem expected) {
    assertThat(cart.getItems()).containsExactly(expected);
}

// In the test:
assertCartContainsOnly(cart, expectedItem);
```

**Option C: Full AssertJ custom assertion class for rich, chainable domain assertions.**

When a domain object is asserted on in three or more tests, create a dedicated assertion class that plugs into AssertJ's fluent style:

```java
public class ShoppingCartAssert
        extends AbstractAssert<ShoppingCartAssert, ShoppingCart> {

    public ShoppingCartAssert(ShoppingCart actual) {
        super(actual, ShoppingCartAssert.class);
    }

    public static ShoppingCartAssert assertThat(ShoppingCart cart) {
        return new ShoppingCartAssert(cart);
    }

    public ShoppingCartAssert hasItemCount(int expected) {
        isNotNull();
        assertThat(actual.getItems()).hasSize(expected);
        return this;
    }

    public ShoppingCartAssert containsExactlyOneItemMatching(CartItem expected) {
        isNotNull();
        org.assertj.core.api.Assertions.assertThat(actual.getItems())
            .containsExactly(expected);
        return this;
    }

    public ShoppingCartAssert hasTotalCloseTo(BigDecimal expected) {
        isNotNull();
        org.assertj.core.api.Assertions.assertThat(actual.getTotal())
            .isEqualByComparingTo(expected);
        return this;
    }
}

// Usage in tests — reads like a specification:
ShoppingCartAssert.assertThat(cart)
    .hasItemCount(2)
    .hasTotalCloseTo(expectedTotal);
```

**Rule:** Exhaust AssertJ's built-in vocabulary first. For recurring domain patterns, graduate from simple helper methods to full custom assertion classes when the pattern is used widely enough to justify it. Custom assertion classes keep the fluent style consistent and composable across the test suite.

## Cleanup Patterns

### Automate Persistent Cleanup with Registration

**Smell:** A sequence of manual delete calls in a `finally` or `tearDown` block. If any single deletion throws, the rest are skipped, leaving behind orphaned state.

**Fix:** Register each persistent object at creation time. Let the test framework iterate and clean them all, catching errors individually.

```java
// BAD: If deleteRecord(order) throws, payment and account leak
@Override
protected void tearDown() {
    deleteRecord(order);
    deleteRecord(payment);
    deleteRecord(account);
}

// GOOD: Registration pattern — framework handles it safely
public abstract class DatabaseTestCase extends TestCase {
    private List<Object> trackedRecords;

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        trackedRecords = new ArrayList<>();
    }

    protected <T> T track(T record) {
        trackedRecords.add(record);
        return record;
    }

    @Override
    protected void tearDown() {
        for (int i = trackedRecords.size() - 1; i >= 0; i--) {
            try {
                deleteRecord(trackedRecords.get(i));
            } catch (RuntimeException e) {
                // Log if needed, but never skip remaining deletes
            }
        }
    }
}

// Usage in test:
Account account = track(anAccount());
Order order = track(anOrder().withAccount(account));
```

**Rule:** Never write per-test teardown logic. Build cleanup into the framework once, then forget about it.

### Drop Unnecessary Pre-Declarations

**Smell:** Variables declared and initialized to `null` at the top of a test, only to be assigned real values later.

This pattern exists to satisfy scoping rules of `try/finally` blocks. Once manual teardown is eliminated, the declarations become dead weight.

```java
// BAD: Leftover from try/finally era
Account account = null;
Order order = null;
try {
    account = anAccount();
    order = anOrder().withAccount(account);
    // ... test logic ...
} finally {
    if (order != null) deleteRecord(order);
    if (account != null) deleteRecord(account);
}

// GOOD: Declare at point of use
Account account = anAccount();
Order order = anOrder().withAccount(account);
// ... test logic ...
```

## Setup Patterns

### Construct Through the Type's Own API

**Smell:** Raw constructor calls with long parameter lists scattered across dozens of tests, or a test-only factory that takes the same list. Either way the reader cannot tell which argument the test is about, and a signature change touches every call.

**Fix:** The type has one entry point taking its mandatory parameters and `with` copies for the optional ones. Tests use that API and nothing else; the one place the test tree fills mandatory parameters it does not care about is a named default.

```java
// BAD: which of the six values does this test depend on?
Shipment s = createShipment("WH-01", "Seattle", "Portland",
    12.5, "FastFreight", 2);

// GOOD: the type's own API; the varied value is the only visible one
Shipment s = aShipment().withCarrier(FAST_FREIGHT);
```

The type carries the API production uses too:

```java
public record Shipment(Warehouse origin, City destination, Weight weight, Carrier carrier) {
    public Shipment {
        Objects.requireNonNull(origin); Objects.requireNonNull(destination); Objects.requireNonNull(weight);
    }
    public Shipment withCarrier(Carrier carrier) {
        return new Shipment(origin, destination, weight, carrier);
    }
}
```

### Hide Values That Don't Matter

**Smell:** Tests spell out every field of every object, even when most fields are irrelevant to the behavior under test.

**Fix:** A **named default** builds the instance with irrelevant values; the test applies a wither for the one attribute it cares about.

```java
// BAD: Which of these values actually affect the test?
Teacher teacher = new Teacher(442, "Maria", "Chen",
    "Math", "mchen@school.edu", true);
Course course = new Course(901, "Algebra II",
    4, "B-204", "Fall");

// GOOD: Only the relevant values are visible
Teacher teacher = aTeacher().withDepartment(MATH);
Course course = aCourse().withCredits(FOUR_CREDITS);
```

The named default is a name for values, not a second API. It calls the type's entry point with unique generated data and takes no parameters:

```java
private static int counter = 0;

private static Teacher aTeacher() {
    counter++;
    return new Teacher(
        counter,
        "Teacher" + counter,
        "Last" + counter,
        SOME_DEPARTMENT,
        "teacher" + counter + "@test.edu",
        false);
}
```

**Why unique generation matters for isolation:** When tests create persistent objects (e.g., database records), hard-coded values like `id=42` or `email="test@example.com"` collide. Two tests against the same datastore conflict, and a re-run without cleanup conflicts with itself. Generate unique values from a counter or UUID. Each run produces distinct records, eliminating flaky failures from data collisions and conflicts when parallel suites share a database.

### Signal Irrelevance with SOME_ / ANY_ Constants

The three-tier convention applied in Java: `SOME_`/`ANY_` constants for placeholders, role-based names for meaningful values, zero bare literals.

```java
// BAD: Are these addresses important? Does the name "Jane Doe" matter?
// Reader wastes time trying to figure out which values affect the outcome.
Employee emp = new Employee(55, "Jane", "Doe",
    "jane@acme.com", "Alexanderplatz 1", "Berlin");
Department dept = new Department(12, "Engineering",
    "Torstraße 1", "Berlin", "Building C");
PayrollRun run = new PayrollRun(dept, emp, new BigDecimal("40"),
    new BigDecimal("75.00"));

// GOOD: Irrelevant data is declared as such. Meaningful data stands out.
private static final String SOME_NAME = "AnyEmployee";
private static final String SOME_EMAIL = "any@test.com";
private static final Department ANY_DEPARTMENT = aDepartment();

// In the test:
final BigDecimal HOURS_WORKED = new BigDecimal("40");
final BigDecimal HOURLY_RATE = new BigDecimal("75.00");

Employee emp = anEmployee();
PayrollRun run = new PayrollRun(ANY_DEPARTMENT, emp,
    HOURS_WORKED, HOURLY_RATE);
```

Apply the pattern at every level:

```java
// Class-level constants for universally irrelevant fixtures
private static final Address ANY_ADDRESS = anAddress();
private static final Product SOME_PRODUCT = aProduct().withPrice(SOME_PRICE);

// Method-level for locally irrelevant values
final int SOME_QUANTITY = 3;   // "I need a quantity, but which one doesn't matter"

// Contrast with meaningful values in the same test
final BigDecimal DISCOUNT_PCT = new BigDecimal("15");  // THIS drives the outcome
```

### Collapse Irrelevant Object Graphs

**Smell:** Building a tree of prerequisite objects that the test doesn't actually care about — just to satisfy a constructor's dependency requirements.

**Fix:** The named default builds its own dependencies; the wither names the one input that matters.

```java
// BAD: Test shows engine and transmission, but only cares about fuelType
Engine engine = anEngine();
Transmission trans = aTransmission();
Vehicle vehicle = new Vehicle(engine, trans, FuelType.ELECTRIC);

// GOOD: Only the relevant input is visible
Vehicle vehicle = aVehicle().withFuel(FuelType.ELECTRIC);
```

### Name Meaningful Constants by Their Role

**Smell:** Bare literals whose purpose is unclear, especially when the same value appears in both setup and verification.

**Fix:** Assign role-revealing names to every value that influences the expected outcome.

```java
// BAD: What's 3? What's "15.00"? Why does "45.00" appear below?
cart.add(product, 3);
assertEquals(new BigDecimal("45.00"), cart.getSubtotal());

// GOOD: Names make the data flow visible
final int QUANTITY = 3;
final BigDecimal PRICE_EACH = new BigDecimal("15.00");

cart.add(product, QUANTITY);

assertThat(cart.getSubtotal())
    .isEqualByComparingTo(PRICE_EACH.multiply(new BigDecimal(QUANTITY)));
```

### Derive Expected Values from Inputs

**Smell:** A hard-coded expected value whose origin is a mystery.

**Fix:** Calculate the expected result from the test's own inputs so the reader can verify the logic.

```java
// BAD: Where did 142.50 come from? Is it even correct?
assertEquals(new BigDecimal("142.50"), payroll.getNetAmount());

// GOOD: Derivation is transparent — reader can verify the math
final BigDecimal HOURS = new BigDecimal("20");
final BigDecimal RATE = new BigDecimal("15.00");
final BigDecimal TAX_RATE = new BigDecimal("0.05");

BigDecimal gross = HOURS.multiply(RATE);
assertThat(payroll.getNetAmount())
    .isEqualByComparingTo(gross.subtract(gross.multiply(TAX_RATE)));
```

**Rule:** If an expected value is a function of the inputs, express that function explicitly. Inline single-use computations directly into the `assertThat` chain rather than assigning them to intermediate variables. A variable earns its name only when it represents a meaningful domain concept (like `gross` above) or is referenced more than once. Pass-through variables like `expectedNet` add lines without adding clarity.

### Assert the Derived Value, Never Rebuild the Object

**Smell:** The type computes a value internally, and the test wants an expected object carrying that value. The tempting fix is a test-only constructor that sets the computed field, which is a second construction path.

**Fix:** Assert the derived value against the explicit function of the inputs. Whole-object comparison stays for objects built through the type's own API; a computed field is compared on its own.

```java
// LineItem derives totalCost from its inputs; the test states that function once
LineItem item = new LineItem(product, QTY, DISCOUNT);

assertThat(item.totalCost())
    .isEqualTo(PRICE.multiply(new BigDecimal(QTY))
        .multiply(BigDecimal.ONE.subtract(DISCOUNT.movePointLeft(2))));
```

**Rule:** A computed value is asserted on its own, against the explicit function of the inputs. A test never adds a construction path production does not have; the type's one entry point is the only way an object comes into being.

## Duplication Elimination

### Promote Repeated Constants

**Smell:** The same magic values redefined in every test method.

**Fix:** Pull them up to class scope. Use the `SOME_`/`ANY_` convention for irrelevant ones and role-based names for meaningful ones.

```java
public class PayrollTest extends TestCase {
    // Meaningful constants — these drive different test scenarios
    private static final BigDecimal STANDARD_RATE = new BigDecimal("25.00");
    private static final BigDecimal OVERTIME_MULTIPLIER = new BigDecimal("1.5");
    private static final BigDecimal DEFAULT_TAX = new BigDecimal("0.10");
    private static final BigDecimal NO_TAX = BigDecimal.ZERO;

    // Irrelevant constants — shared plumbing that never affects outcomes
    private static final Employee ANY_EMPLOYEE = anEmployee();
    private static final Department ANY_DEPARTMENT = aDepartment();
}
```

### Compose Higher-Level Named Defaults

**Smell:** The same sequence of setup calls at the top of every test.

**Fix:** A scenario that recurs gets its own named default; the name carries what the scenario fixes.

```java
// BAD: Every test does this dance
Teacher teacher = aTeacher().withDepartment(SCIENCE);
Classroom room = aClassroom().withWing(NORTH);
Schedule schedule = new Schedule(teacher, room);

// GOOD: One name captures the whole scenario
Schedule schedule = aScienceTeachingSchedule();
```

### Build a Testing Vocabulary

All of these refactorings accumulate into a domain-specific testing vocabulary tailored to the application. Once the vocabulary exists, writing a new test becomes trivial:

```java
@Test
void enrollStudentIncreasesHeadcount() {
    Section section = anOpenSection();

    section.enroll(aStudent());

    assertThat(section.getHeadcount()).isEqualTo(1);
}
```

This test took seconds to write, is instantly understandable, and will survive refactors to the underlying domain model because the vocabulary absorbs the change.

### Share the Vocabulary Across Test Classes

**Smell:** Useful named defaults and custom assertions are trapped inside a single test class. Other test classes that need the same vocabulary end up duplicating them.

**Fix:** Extract shared test utilities into a **common test superclass** or a standalone utility class.

```java
// Shared base for all tests that touch the scheduling domain
public abstract class SchedulingTestCase extends DatabaseTestCase {
    protected static final int SOME_CAPACITY = 30;

    protected Section anOpenSection() { ... }
    protected Student aStudent() { ... }
    protected Schedule aScienceTeachingSchedule() { ... }

    protected void assertSectionContainsOnly(Section s, Student expected) { ... }
}

// Individual test classes inherit the full vocabulary
public class EnrollmentTest extends SchedulingTestCase { ... }
public class WaitlistTest extends SchedulingTestCase { ... }
```

**Rule:** When the same test utilities are needed by multiple test classes, extract them into a shared superclass (or utility module). The vocabulary should be a project-wide asset, not locked inside one file.

## The Investment Pays Compound Returns

Refactoring the first test in a domain is the most expensive step. The effort concentrates in discovering and building the testing vocabulary — the named defaults, custom assertions, named constants, and cleanup infrastructure.

Once that vocabulary exists, every subsequent test in the same domain is dramatically cheaper to write, read, and maintain:

- **Writing:** A new test reuses existing named defaults and assertions. What took 35+ statements now takes 6.
- **Reading:** The vocabulary gives tests a consistent, predictable shape. A developer seeing `aCustomer().withDiscount(DISCOUNT_PCT)` for the first time understands it instantly.
- **Maintaining:** When the production API changes (e.g., a constructor gains a new parameter), one named default changes instead of hundreds of tests.
- **Scaling:** As the vocabulary grows, the cost per new test approaches near-zero because the building blocks already exist.

## Smell / Fix Quick Reference

| Smell | Fix | Technique |
|-------|-----|-----------|
| JUnit `assertEquals`/`assertTrue` | `assertThat(x).isEqualTo(y)` fluent chain | AssertJ Fluent Assertions |
| `assertTrue(false)` for failure | Use `fail(msg)` or AssertJ's specific assertion | Direct Assertion |
| Phase comments, `.as()` restating the obvious | Remove; let code and naming communicate | No Narration |
| Single-use `expectedX` variables | Inline computation into `assertThat` chain | Inline Derivation |
| Field-by-field assertions | Compare whole objects; use `usingRecursiveComparison()` to ignore volatile fields | Whole Object Comparison |
| `if/else` or loops in tests | Flat guards, or AssertJ `extracting`/`containsExactly` | Guard Assertion |
| Index-based collection access | `singleElement()`, `extracting()`, `allSatisfy()` | Collection Assertions |
| Repeated multi-step verification | AssertJ built-in chains, helper method, or custom assertion class | Custom Assertion |
| Shared mutable fixture across tests | Fresh fixture per test via named defaults | Fresh Fixture |
| Manual `finally` / `tearDown` deletes | Register objects, automate cleanup | Registration Pattern |
| Variables pre-set to `null` | Declare at assignment point | Inline Declaration |
| Raw constructor calls with unnamed arguments | The type's entry point and `with` copies; named defaults for irrelevant instances | One Construction API |
| Irrelevant hard-coded values | `SOME_` / `ANY_` constants or named defaults | Declarative Irrelevance |
| Hard-coded IDs/emails causing collisions | Generate unique values from counter/UUID | Unique Test Data |
| Visible irrelevant dependencies | Collapse into the named default | Collapsed Default |
| Bare numeric/string literals | Named constants with role-based names | Symbolic Constants |
| Opaque expected values | Compute from test inputs | Derived Expectation |
| Expected object needs a computed field | Assert the derived value against the function of the inputs | Derived Expectation |
| Same setup in every test | Compose into higher-level named defaults | Testing Vocabulary |
| Duplicated constants across tests | Promote to class scope | Shared Constants |
| Test utilities trapped in one class | Extract to shared superclass or utility | Test Superclass |

## Transformation Example

### Before: Tangled, Hard to Maintain

```java
public void testApplyDiscountMultipleItems() {
    Warehouse warehouse = null;
    Catalog catalog = null;
    ShoppingCart cart = null;
    try {
        warehouse = new Warehouse(1, "Main", "Denver",
            "Mountain", 55);
        catalog = new Catalog(7, "Summer Sale",
            LocalDate.of(2025, 6, 1), LocalDate.of(2025, 8, 31));
        Product gadget = catalog.addProduct(new Product(101,
            "Gadget", new BigDecimal("40.00"), "Electronics", 0.5));
        Product widget = catalog.addProduct(new Product(102,
            "Widget", new BigDecimal("25.00"), "Electronics", 0.3));
        cart = new ShoppingCart(warehouse, catalog,
            new BigDecimal("10"));

        cart.add(gadget, 2);
        cart.add(widget, 3);

        List<LineItem> items = cart.getItems();
        if (items.size() == 2) {
            assertEquals(101, items.get(0).getProductId());
            assertEquals(2, items.get(0).getQuantity());
            assertEquals(new BigDecimal("72.00"), items.get(0).getLineTotal());
            assertEquals(102, items.get(1).getProductId());
            assertEquals(3, items.get(1).getQuantity());
            assertEquals(new BigDecimal("67.50"), items.get(1).getLineTotal());
            assertEquals(new BigDecimal("139.50"), cart.getTotal());
        } else {
            assertTrue("Expected exactly 2 line items", false);
        }
    } finally {
        if (cart != null) deleteRecord(cart);
        if (catalog != null) deleteRecord(catalog);
        if (warehouse != null) deleteRecord(warehouse);
    }
}
```

**Problems:** Mystery values everywhere (what's `55`? does `"Mountain"` matter?). Conditional logic in assertions. Manual teardown that breaks if any delete throws. Field-by-field assertions re-testing LineItem internals. Impossible to tell which data drives the discount calculation.

### After: Clean, Self-Documenting

```java
private static final BigDecimal DISCOUNT_PCT = new BigDecimal("10");
private static final BigDecimal SOME_PRICE_A = new BigDecimal("40.00");
private static final BigDecimal SOME_PRICE_B = new BigDecimal("25.00");

@Test
void applyDiscountMultipleItems() {
    final int SOME_QTY_A = 2;
    final int SOME_QTY_B = 3;

    ShoppingCart cart = createDiscountCart(DISCOUNT_PCT);
    Product productA = aProduct().withPrice(SOME_PRICE_A);
    Product productB = aProduct().withPrice(SOME_PRICE_B);

    cart.add(productA, SOME_QTY_A);
    cart.add(productB, SOME_QTY_B);

    BigDecimal grossTotal = SOME_PRICE_A.multiply(new BigDecimal(SOME_QTY_A))
        .add(SOME_PRICE_B.multiply(new BigDecimal(SOME_QTY_B)));

    assertThat(cart.getTotal())
        .isEqualByComparingTo(
            grossTotal.multiply(
                BigDecimal.ONE.subtract(DISCOUNT_PCT.movePointLeft(2))));
}
```

Warehouses, catalogs, product categories, date ranges — all gone. The test shows exactly and only the values that matter. `DISCOUNT_PCT` is the sole Tier 1 constant; everything else is declared irrelevant with `SOME_` prefixes or hidden behind named defaults. The expected total is derived inline from inputs. A reader instantly knows what's being tested and can verify correctness by reading the code alone.
