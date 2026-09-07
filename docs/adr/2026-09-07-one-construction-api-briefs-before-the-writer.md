# One Construction API per Domain Type, and the Principle Briefs in Front of the Writer

**Status:** Accepted

## Context

The v0.3.9 sweep's 36 blind-judge samples never score test-quality at 5 and score maintainability at 5 once. The deductions fall into classes the fixture's testing brief already rules on:

| Class | Samples of 36 |
|---|---|
| Comment or doc comment restating the code | 24 |
| Raw domain constructor in a test | 19 |
| Framework stub or interaction assertion without a recorded exception | 19 |
| Bare literal in a test | 15 |
| Copy-paste twin tests | 9 |
| Naming-school breach | 8 |

The retained transcripts show why the rules do not reach the code. The implementer saw the testing brief's text in 8 of 27 dispatches and the architecture brief's in 1 of 32. The test reviewer saw the testing brief in 10 of 18. Three harness rules produced that. The Scoping Pre-Check named the design and architecture briefs as the implementer's durable memory and omitted the testing brief. The read discipline biased every dispatch toward fewer reads. The Test-Conventions Walk told the implementer to match the host file's idiom, which in a suite that predates the brief means copying the debt the brief names.

The construction rule itself, "never call a constructor; wrap it in a test-owned factory", hid the varied value inside a factory call. It also put a second construction path in the test tree.

## Options Considered

1. **Keep test-owned factories** (status quo). Rejected: a second construction API per type, and `createShipment(a, b, c, d)` hides which argument the test is about.
2. **Test data builders** in the test tree (`anOrder().withLine(...).build()`). Rejected: the same second API, now a type per aggregate, with withers that exist only for tests.
3. **A builder on the production type.** Rejected: a half-built mutable stage, and the mandatory parameters vanish from any signature.
4. **One construction API on the type, with copies for optional attributes** (chosen).

## Decision

**A domain type has one construction entry point, taking every mandatory parameter, and tests use exactly the API production uses.** The entry point is the constructor or one named creator such as `Address.of(...)`, and it enforces the invariants. The named creator earns its place where the name adds meaning or input is normalized first. Optional attributes are set through `with` copies routed through that entry point. Attributes that belong together form a value object with one wither. Where the group is small and its order reads itself, the wither may take the parts directly as a thin overload. A change a business rule governs is a named operation, never a wither. In tests, an irrelevant instance hides behind a one-line named default such as `anOwner()`, a name for values rather than a second API. A value object with all-named arguments may be constructed directly. The model is a Pattern Catalog entry, open to a project's brief; the kernel keeps only invariants at construction.

**The two principle briefs are mandatory full reads for the implementer, and the brief binds where it speaks.** `docs/architecture-principles.md` and `docs/testing-principles.md` join the Scoping Pre-Check's durable memory and sit outside the fewer-reads bias. Host-file idiom governs only where the brief is silent. A host file that predates the brief is debt to leave.

**Code is self-documenting first.** A comment a better name would make redundant is a rename. A requirement or edge case is cited in the test that covers it, never in a code comment. A doc comment on a public type states its purpose in one sentence. None restates a signature, sits on a private member, or sits on a test. The code-quality checklists list every added comment line, as the test checklists list raw constructions.

The document-writing standards gain two rules that had lived only in operator memory. Prose describes the current state. Unusual inputs are named by their shape rather than by attack metaphor.

## Consequences

**Positive:** the varied value is visible at the call site. Validation has one home. Production, persistence mapping, and tests share one API. The writer holds the same text the reviewers and the judge hold.

**Negative:** one short method per free optional attribute on the type. Two more reads per implementer dispatch, about ten thousand cached tokens. The eval fixture's brief keeps the old rule until its next epoch, so the judge series moves only after that dated condition change. Reading is not following: `grading.py conventions-map` lists added comment blocks, raw test constructions, and literal-bearing test lines per file, and the walk and both reviewer checklists work from it; whether a listed row is a finding stays judgment.

## Implementation

The doctor templates for both briefs and the three samples' copies. `tdd-workflow` (pre-check, walk) and `tdd-principles.md` (`legible-cold`). The three stacks' `test-review` and `code-quality-review` checklists, with a Go construction section. The three `feature-implementer` agents' read discipline. `document-writing/documentation-standards.md`.

## References

- [2026-09-03 coverage-map-joins-the-walk](2026-09-03-coverage-map-joins-the-walk.md): the walk this decision extends.
- [2026-06-12 docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md): the briefs are project-owned, which is why the template changes now and the fixture's copy changes on its own epoch.
- [2026-09-01 evidence-gated-dynamic-tiering](2026-09-01-evidence-gated-dynamic-tiering.md), sixth amendment: design placement of tests, the precedence rule's sibling.
