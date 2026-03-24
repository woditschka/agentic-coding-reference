# Test Refactoring Philosophy for Agentic Programming

A guide for AI agents to write clean, maintainable, self-documenting tests. The goal: every test should be so clear that it doubles as a specification.

---

## Core Principle: Tests Are Specifications

A well-written test answers three questions instantly:

1. **What world does this test live in?** (Setup)
2. **What action triggers the behavior?** (Exercise)
3. **What should the world look like afterward?** (Verification)

If a reader needs more than a few seconds to answer all three, the test is too complex. Strive for tests where the causal chain from inputs to expected outputs is self-evident.

---

## The Four-Phase Structure

Organize every test into four distinct phases:

1. **Arrange** — build the world the test needs
2. **Act** — trigger the behavior under test
3. **Assert** — check that reality matches expectations
4. **Cleanup** — restore the world (ideally automatic)

Separate phases with blank lines. When the test is clean — short, well-named, with clear intent — the structure is self-evident from the code. Phase comments like `// Arrange` become redundant noise. This applies broadly: never add prose that restates what the code already says. That includes phase comments, `.as("descriptive message")` annotations on assertions whose chain is already readable, and inline comments narrating obvious logic. If you feel the need to explain a test, the test is too long or too obscure and should be refactored instead.

Keep each phase minimal. If any single phase overwhelms the test, treat it as a signal to refactor.

---

## Refactoring Playbook

### 1. Sharpen the Assertions

Assertions are the point of the test. Start refactoring here.

**Prefer fluent assertions (AssertJ).** Fluent assertion libraries like AssertJ let you chain assertions that read like natural language specifications. They produce richer failure messages, eliminate argument-order confusion, and often replace multi-step verification logic with a single expressive chain. Prefer AssertJ over JUnit's classic `assertEquals`/`assertTrue` in all new tests.

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

#### 1.1 Use the Most Direct Assertion Available

**Smell:** Roundabout ways to express failure or expectation — e.g., wrapping a boolean `false` inside a generic truth check.

**Fix:** Pick the assertion that says exactly what you mean. AssertJ's type-aware API offers precise methods for every situation.

```java
// BAD: Indirect — reader must mentally evaluate assertTrue(false)
assertTrue("Expected at least one result", results.size() > 0);

// BETTER (JUnit): More specific
assertFalse("Results should not be empty", results.isEmpty());

// BEST (AssertJ): Reads like a specification, rich failure message
assertThat(results).isNotEmpty();
// Failure: "Expecting actual not to be empty" — no manual message needed

// BAD: Generic boolean when equality is what you mean
assertTrue(order.getStatus().equals("shipped"));

// BEST (AssertJ): Fluent, type-safe, clear failure output
assertThat(order.getStatus()).isEqualTo("shipped");
// Failure: "expected: 'shipped' but was: 'pending'" — auto-generated diff
```

**Rule:** Always choose the most semantically precise assertion. AssertJ's fluent chains are the default choice — they're self-documenting and produce failure messages that diagnose problems without re-running the test in a debugger.

#### 1.2 Stop Re-Testing Other Units

**Smell:** A test for component A also asserts on internal fields that are the responsibility of component B (which has its own tests).

**Fix:** Assert only on the behavior you're actually testing. Trust that B's own tests cover B.

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

When full object equality isn't practical (e.g., generated IDs, timestamps), AssertJ lets you compare specific fields without falling back to field-by-field assertions:

```java
// Compare only the fields that matter, ignoring generated/volatile ones
assertThat(reservation)
    .usingRecursiveComparison()
    .ignoringFields("id", "createdAt")
    .isEqualTo(expected);
```

**Rule:** Construct the expected result as a complete object and compare with a single assertion. Use `usingRecursiveComparison().ignoringFields(...)` when some fields are irrelevant or non-deterministic.

#### 1.3 Flatten All Branching Out of Tests

**Smell:** `if/else` blocks, `switch` statements, or loops inside a test body. When a test has multiple execution paths, you lose confidence about which path actually ran.

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

#### 1.4 Name Your Verification Patterns

**Smell:** The same multi-step verification sequence appears in several tests.

**Fix:** First, check whether AssertJ's built-in vocabulary already expresses the pattern. If it does, a custom helper is unnecessary. If it doesn't, you have two options: a simple helper method, or a full AssertJ custom assertion class.

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

When a domain object is asserted on frequently across many tests, create a dedicated assertion class that plugs into AssertJ's fluent style:

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

---

### 2. Simplify Cleanup

#### 2.1 Default to Ephemeral Fixtures

**Smell:** Explicit teardown code deleting objects, closing connections, or resetting state after every test.

**Fix:** Use in-memory objects that vanish when the test ends. Most unit tests need no cleanup at all.

**Rule:** If no persistent side effect occurs (no database writes, no file creation, no external calls), your teardown should be empty.

#### 2.2 Never Share Mutable Fixtures Across Tests

**Smell:** To avoid writing teardown code, a shared fixture (created once, reused by many tests) is left in place between test runs.

**Fix:** Don't do it. Shared mutable fixtures cause three interrelated problems:

- **Unrepeatable Tests:** A test passes on the first run but fails on the second because a previous test modified the shared data.
- **Interacting Tests:** Test A and Test B both pass in isolation, but fail when run together because they mutate the same fixture in conflicting ways.
- **Mystery Guests:** The test references objects it didn't create, so the reader cannot see the fixture and must hunt elsewhere to understand the test.

The correct solution is a **fresh fixture per test** — each test builds exactly the state it needs. Use factory methods and anonymous creators (see Section 3) to make fresh fixture creation cheap, and automated cleanup (see Section 2.3) to make disposal free.

**Rule:** Shared fixtures are acceptable only when immutable (e.g., static reference data that no test ever modifies). If any test writes to it, create a fresh copy instead.

#### 2.3 Automate Persistent Cleanup with Registration

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
Account account = track(createAccount("Test Corp"));
Order order = track(createOrder(account));
```

**Rule:** Never write per-test teardown logic. Build cleanup into the framework once, then forget about it.

#### 2.4 Drop Unnecessary Pre-Declarations

**Smell:** Variables declared and initialized to `null` at the top of a test, only to be assigned real values later.

This pattern exists to satisfy scoping rules of `try/finally` blocks. Once you eliminate manual teardown, the declarations become dead weight.

```java
// BAD: Leftover from try/finally era
Account account = null;
Order order = null;
try {
    account = createAccount(...);
    order = createOrder(account, ...);
    // ... test logic ...
} finally {
    if (order != null) deleteRecord(order);
    if (account != null) deleteRecord(account);
}

// GOOD: Declare at point of use
Account account = createAccount(...);
Order order = createOrder(account, ...);
// ... test logic ...
```

---

### 3. Streamline the Setup

#### 3.1 Wrap Construction in Factory Methods

**Smell:** Raw constructor calls with long parameter lists scattered across dozens of tests. A single constructor signature change forces edits everywhere.

**Fix:** Wrap each constructor in a **factory method** owned by the test suite. When the API changes, fix one method.

```java
// BAD: If Shipment's constructor adds a parameter, 40 tests break
Shipment s = new Shipment("WH-01", "Seattle", "Portland",
    12.5, "FastFreight", 2);

// GOOD: Encapsulated — one place to update
Shipment s = createShipment("WH-01", "Seattle", "Portland",
    12.5, "FastFreight", 2);
```

**Rule:** Tests should never call production constructors directly. Factory methods are the single point of contact.

#### 3.2 Hide Values That Don't Matter

**Smell:** Tests spell out every field of every object, even when most fields are irrelevant to the behavior under test. This is the "hard-coded data" problem — the reader can't distinguish signal from noise.

**Fix:** Create **anonymous factory methods** that auto-generate irrelevant values. Only accept parameters for fields that actually influence the test outcome.

```java
// BAD: Which of these values actually affect the test?
Teacher teacher = createTeacher(442, "Maria", "Chen",
    "Math", "mchen@school.edu", true);
Course course = createCourse(901, "Algebra II",
    4, "B-204", "Fall");

// GOOD: Only the relevant values are visible
Teacher teacher = createATeacher("Math");
Course course = createACourse(4);
```

Behind the scenes, the anonymous factory fills in everything else with unique generated data:

```java
private static int counter = 0;

private Teacher createATeacher(String department) {
    counter++;
    return new Teacher(
        counter,
        "Teacher" + counter,
        "Last" + counter,
        department,
        "teacher" + counter + "@test.edu",
        false);
}
```

**Rule:** If a value doesn't change the expected outcome, hide it. The test should only show what matters. This makes causal relationships between inputs and outputs unmistakable.

**Why unique generation matters for isolation:** When tests create persistent objects (e.g., database records), hard-coded values like `id=42` or `email="test@example.com"` will collide if two tests run against the same datastore — or if the same test runs twice without cleanup. Generating unique values from a counter or UUID ensures every test run produces distinct records, preventing flaky failures from data collisions and eliminating conflicts when parallel test suites share a database.

#### 3.3 Signal Irrelevance with SOME_ / ANY_ Constants

There are three categories of data in a test:

| Category | Purpose | Naming Convention | Example |
|----------|---------|-------------------|---------|
| **Meaningful** | Directly affects the expected outcome | Role-describing name | `DISCOUNT_RATE`, `QUANTITY` |
| **Irrelevant** | Required by the API but has no bearing on outcome | `SOME_` or `ANY_` prefix | `SOME_EMAIL`, `ANY_ADDRESS` |
| **Mystery** | Bare literal with no explanation | Avoid entirely | `"hello@x.com"`, `42` |

The critical insight: when a test uses a named constant like `SOME_ADDRESS` or `ANY_WAREHOUSE`, it is **actively communicating** that this value is a placeholder — its specific content does not matter. This is fundamentally different from a meaningful constant like `EXPECTED_TOTAL` and also different from a mystery literal like `"1222 1st St"` that leaves the reader guessing.

```java
// BAD: Are these addresses important? Does the name "Jane Doe" matter?
// Reader wastes time trying to figure out which values affect the outcome.
Employee emp = createEmployee(55, "Jane", "Doe",
    "jane@acme.com", "100 Oak Ave", "Denver");
Department dept = createDepartment(12, "Engineering",
    "500 Elm St", "Portland", "Building C");
PayrollRun run = new PayrollRun(dept, emp, new BigDecimal("40"),
    new BigDecimal("75.00"));

// GOOD: Irrelevant data is declared as such. Meaningful data stands out.
private static final String SOME_NAME = "AnyEmployee";
private static final String SOME_EMAIL = "any@test.com";
private static final Department ANY_DEPARTMENT = createADepartment();

// In the test:
final BigDecimal HOURS_WORKED = new BigDecimal("40");
final BigDecimal HOURLY_RATE = new BigDecimal("75.00");

Employee emp = createAnEmployee();  // everything about the employee is irrelevant
PayrollRun run = new PayrollRun(ANY_DEPARTMENT, emp,
    HOURS_WORKED, HOURLY_RATE);
```

Now the reader instantly sees: only `HOURS_WORKED` and `HOURLY_RATE` matter here. The department and employee details are noise — and the test says so explicitly.

**Use this pattern at every level:**

```java
// Class-level constants for universally irrelevant fixtures
private static final Address ANY_ADDRESS = createAnAddress();
private static final Product SOME_PRODUCT = createAProduct(SOME_PRICE);

// Method-level for locally irrelevant values
final int SOME_QUANTITY = 3;   // "I need a quantity, but which one doesn't matter"

// Contrast with meaningful values in the same test
final BigDecimal DISCOUNT_PCT = new BigDecimal("15");  // THIS drives the outcome
```

**Rule:** Every value in a test should declare whether it matters. Use `SOME_`/`ANY_` prefixes or anonymous factory methods (`createAnX()`, `createAnyX()`) for irrelevant data. Use descriptive role-based names for meaningful data. Never leave the reader guessing which category a value belongs to.

#### 3.4 Collapse Irrelevant Object Graphs

**Smell:** Building a tree of prerequisite objects that the test doesn't actually care about — just to satisfy a constructor's dependency requirements.

**Fix:** Let the factory method build its own dependencies internally.

```java
// BAD: Test shows engine and transmission, but only cares about fuelType
Engine engine = createAnEngine();
Transmission trans = createATransmission();
Vehicle vehicle = createVehicle(engine, trans, FuelType.ELECTRIC);

// GOOD: Only the relevant input is visible
Vehicle vehicle = createAVehicle(FuelType.ELECTRIC);
// createAVehicle internally builds an engine and transmission
```

**Rule:** If the test outcome doesn't depend on an object, the test reader shouldn't see that object.

#### 3.5 Name Meaningful Constants by Their Role

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

#### 3.6 Derive Expected Values from Inputs

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

**Rule:** If an expected value is a function of the inputs, express that function explicitly. The test becomes self-verifying documentation. Inline single-use computations directly into the `assertThat` chain rather than assigning them to intermediate variables — a variable only earns its name if it represents a meaningful domain concept (like `gross` above) or is referenced more than once. Pass-through variables like `expectedNet` just add lines without adding clarity.

#### 3.7 Create Test-Only Construction Paths for Expected Objects

**Smell:** The production code doesn't offer a constructor or factory that lets you build an expected result with pre-calculated values (because in production, the object calculates those values internally).

**Fix:** Create a **test-only factory method** in the test harness that constructs expected objects with all fields explicitly set — including computed ones that the SUT would normally derive.

```java
// The SUT's LineItem normally calculates totalCost internally.
// But in the test, we need an expected LineItem with a known totalCost
// so we can compare it against what the SUT produced.

// Test-only factory — lives in the test class, not in production code
private LineItem createExpectedLineItem(Product product, int quantity,
        BigDecimal discount, BigDecimal totalCost) {
    return new LineItem(product, quantity, discount, totalCost);
}

// In the test:
BigDecimal expectedCost = PRICE.multiply(new BigDecimal(QTY))
    .multiply(BigDecimal.ONE.subtract(DISCOUNT.movePointLeft(2)));
LineItem expected = createExpectedLineItem(product, QTY, DISCOUNT, expectedCost);
```

**Rule:** When the expected object needs a construction path that doesn't exist in production, build it in the test harness. Never twist production APIs to serve test needs — keep the test-only code clearly separated.

---

### 4. Eliminate Duplication Across Tests

#### 4.1 Promote Repeated Constants

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
    private static final Employee ANY_EMPLOYEE = createAnEmployee();
    private static final Department ANY_DEPARTMENT = createADepartment();
}
```

#### 4.2 Compose Higher-Level Factories

**Smell:** The same sequence of factory calls at the top of every test.

**Fix:** Combine them into a single, more powerful factory.

```java
// BAD: Every test does this dance
Teacher teacher = createATeacher("Science");
Classroom room = createAClassroom("North");
Schedule schedule = createSchedule(teacher, room);

// GOOD: One call captures the whole scenario
Schedule schedule = createTeachingSchedule("Science");
```

#### 4.3 Build a Testing Vocabulary

All of these refactorings accumulate into a **domain-specific testing vocabulary** — a library of factory methods, custom assertions, named constants, and `SOME_`/`ANY_` placeholders tailored to your application.

Once the vocabulary exists, writing a new test becomes trivial:

```java
@Test
void enrollStudentIncreasesHeadcount() {
    Section section = createOpenSection(SOME_CAPACITY);

    section.enroll(createAStudent());

    assertThat(section.getHeadcount()).isEqualTo(1);
}
```

This test took seconds to write, is instantly understandable, and will survive refactors to the underlying domain model because the vocabulary absorbs the change.

#### 4.4 Share the Vocabulary Across Test Classes

**Smell:** Useful factory methods and custom assertions are trapped inside a single test class. Other test classes that need the same vocabulary end up duplicating them.

**Fix:** Extract shared test utilities into a **common test superclass** or a standalone utility class. Pull factory methods, custom assertions, and the registration/cleanup infrastructure into this shared base so any test class in the suite can inherit them.

```java
// Shared base for all tests that touch the scheduling domain
public abstract class SchedulingTestCase extends DatabaseTestCase {
    protected static final int SOME_CAPACITY = 30;

    protected Section createOpenSection(int capacity) { ... }
    protected Student createAStudent() { ... }
    protected Schedule createTeachingSchedule(String dept) { ... }

    protected void assertSectionContainsOnly(Section s, Student expected) { ... }
}

// Individual test classes inherit the full vocabulary
public class EnrollmentTest extends SchedulingTestCase { ... }
public class WaitlistTest extends SchedulingTestCase { ... }
```

**Rule:** When the same test utilities are needed by multiple test classes, extract them into a shared superclass (or utility module). The vocabulary should be a project-wide asset, not locked inside one file.

---

### 5. The Investment Pays Compound Returns

Refactoring the first test in a domain is the most expensive step. Most of the effort goes into **discovering and building the testing vocabulary** — the factory methods, custom assertions, named constants, and cleanup infrastructure.

Once that vocabulary exists, every subsequent test in the same domain is dramatically cheaper to write, read, and maintain:

- **Writing:** A new test reuses existing factories and assertions. What took 35+ statements now takes 6.
- **Reading:** The vocabulary gives tests a consistent, predictable shape. A developer seeing `createACustomer(DISCOUNT_PCT)` for the first time understands it instantly.
- **Maintaining:** When the production API changes (e.g., a constructor gains a new parameter), you update one factory method instead of hundreds of tests.
- **Scaling:** As the vocabulary grows, the cost per new test approaches near-zero because the building blocks already exist.

This is the core economic argument: the initial refactoring investment is not a one-time cost — it is infrastructure that compounds in value with every test added afterward.

---

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
| Shared mutable fixture across tests | Fresh fixture per test via cheap factories | Fresh Fixture |
| Manual `finally` / `tearDown` deletes | Register objects, automate cleanup | Registration Pattern |
| Variables pre-set to `null` | Declare at assignment point | Inline Declaration |
| Raw constructor calls in tests | Wrap in test-owned factory methods | Creation Factory |
| Irrelevant hard-coded values | `SOME_` / `ANY_` constants or anonymous factories | Declarative Irrelevance |
| Hard-coded IDs/emails causing collisions | Generate unique values from counter/UUID | Unique Test Data |
| Visible irrelevant dependencies | Collapse into parent factory | Collapsed Factory |
| Bare numeric/string literals | Named constants with role-based names | Symbolic Constants |
| Opaque expected values | Compute from test inputs | Derived Expectation |
| No production constructor for expected objects | Test-only factory in the test harness | Test Construction Path |
| Same setup in every test | Compose into higher-level factories | Testing Vocabulary |
| Duplicated constants across tests | Promote to class scope | Shared Constants |
| Test utilities trapped in one class | Extract to shared superclass or utility | Test Superclass |

---

## The Three-Tier Data Naming Convention

This convention is the backbone of test readability. Every value in a test falls into one of three tiers:

```
+---------------------------------------------------------+
|  Tier 1: MEANINGFUL         — drives the outcome        |
|  Name by role: QUANTITY, DISCOUNT_RATE, HOURLY_WAGE     |
|  "The test depends on this specific value."             |
+---------------------------------------------------------+
|  Tier 2: IRRELEVANT         — required but inert        |
|  Name with SOME_/ANY_: SOME_EMAIL, ANY_ADDRESS          |
|  Or use anonymous factories: createAnEmployee()         |
|  "The test needs a value here, but any value works."    |
+---------------------------------------------------------+
|  Tier 3: MYSTERY            — bare literal              |
|  "hello@x.com", 42, "1222 1st St"                      |
|  ALWAYS ELIMINATE — reader cannot tell if it matters.   |
+---------------------------------------------------------+
```

A test with zero Tier 3 values is self-documenting. The reader can scan the names alone and immediately know which data drives the test and which is just scaffolding.

---

## Agent Decision Checklist

When writing or refactoring a test, walk through these checks in order:

1. **Structure:** Is the test clearly divided into Arrange / Act / Assert by blank lines alone?
2. **No narration:** Is the test free of comments, `.as()` messages, and other prose that restates what the code already says?
3. **Fluent assertions:** Am I using AssertJ's fluent API (`assertThat`) rather than JUnit's classic assertions?
4. **Linearity:** Is the test body completely free of branching and loops?
5. **Focus:** Am I only asserting on the behavior this test owns?
6. **Whole objects:** Am I comparing complete expected objects rather than picking apart fields?
7. **Collection assertions:** Am I using `extracting`, `containsExactly`, `singleElement` instead of index-based access?
8. **Named patterns:** Are recurring verification sequences extracted — first checking if AssertJ handles it natively, then escalating to helpers or custom assertion classes?
9. **Automatic cleanup:** Is teardown handled by the framework, not the test?
10. **Encapsulated construction:** Are all object instantiations behind factory methods?
11. **No mystery values:** Is every literal either a meaningful named constant or a declared-irrelevant `SOME_`/`ANY_` placeholder?
12. **Signal vs. noise:** Can a reader tell at a glance which values matter and which are scaffolding?
13. **Transparent expectations:** Are expected values derived from inputs and inlined into the assertion chain? Do intermediate variables earn their names by representing domain concepts or being reused?
14. **Zero duplication:** Is every reusable pattern extracted into the shared testing vocabulary?

---

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
    Product productA = createAProduct(SOME_PRICE_A);
    Product productB = createAProduct(SOME_PRICE_B);

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

Warehouses, catalogs, product categories, date ranges — all gone. The test shows exactly and only the values that matter: `DISCOUNT_PCT` is the sole Tier 1 constant; everything else is declared irrelevant with `SOME_` prefixes or hidden behind anonymous factories. The expected total is derived inline from inputs. A reader instantly knows what's being tested and can verify correctness by reading the code alone.
