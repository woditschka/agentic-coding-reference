<!-- harness: 2026-09-17 -->
# Product Requirements Document: bookstore

<!-- AGENT: This PRD is narrative prose. State WHAT the system does and WHY it matters. Never HOW — mechanism (flags, exit codes, file layouts, algorithms) lives in system-design.md. Never the decision trail — alternatives and trade-offs live in adr/. -->
<!-- AGENT: Annotate each requirement inline with its [REQ-XX-NNN] tag where the prose expresses it, and give it one "Done when" acceptance bullet carrying the same tag. The prose is the intent; the tagged bullet is the bounded, testable contract. Drop an <a id="req-xx-nnn"></a> anchor at first mention so other docs deep-link to it. -->
<!-- AGENT: A requirement is active by being in the narrative — there is no per-requirement Status field. Retire one by moving it to the Superseded list; never renumber an ID. -->

## Context

A small bookstore wants one page that lists what it stocks. The stock lives in a backend service that other channels will read later. The page and the backend are therefore separate modules in separate repositories, joined by one contract. This product is the reference's worked example of a product workspace. The umbrella here owns the requirements, the module map, and the contract; each module repository owns its own design.

## Goals

| ID | Goal | Success Metric |
|----|------|----------------|
| G-1 | A visitor sees every stocked book on one page | The page lists each book's title and subtitle exactly as the backend serves them |
| G-2 | The page stays up when the backend is down | A backend outage yields a notice on the page, never an error page |

## Non-Goals

<!-- Declined scope with the reason it was declined; never silently dropped. A non-goal ADR records the path to each decision. The first REQ id on a row is the declined one; a later id names a successor, which stays open. -->

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG-1 | Purchasing, carts, or accounts | The product shows the catalog; selling it is a later product ([non-goal ADR](adr/2026-09-19-non-goal-purchasing.md)) |
| NG-2 | Transport security between the modules | The sample runs both modules on one machine over plaintext gRPC; production hardening is a deployment decision outside this product |

## Requirements

<!-- Narrative prose, grouped by capability area. Weave each requirement into the prose and tag it inline with [REQ-XX-NNN]. After each group, a "Done when:" list gives every requirement in that group its bounded acceptance bullet, tagged with the same ID. A capability with edge cases adds a numbered "Edge cases:" list — stable numbering that tests and reviews cite. Mechanism stays out — link to system-design.md for the how. -->

### The catalog page

<a id="req-book-001"></a>
The page lists every stocked book, each with its title and its subtitle, in the order the catalog serves them `[REQ-BOOK-001]`. <a id="req-book-002"></a>When the catalog cannot be reached within the page's budget, the page still renders and says the catalog is unavailable `[REQ-BOOK-002]`.

**Done when:**
- `[REQ-BOOK-001]` given the catalog serves three books, when the page is requested, then it shows three entries, each a title row and a subtitle row, in the served order;
- `[REQ-BOOK-002]` given the catalog does not answer, when the page is requested, then the response is a rendered page with an unavailability notice and no book entries.

Edge cases:
1. A book without a subtitle shows its title row only.
2. A served book without a title is dropped from the page.

**ADR:** [ADR: The contract is its own member](adr/2026-09-19-the-contract-is-its-own-member.md)  ·  **Design:** [system-design.md#contracts](system-design.md#contracts)

## Superseded

<!-- Retired requirements: each ID maps to its successor (or to the reason it was withdrawn) so existing links still resolve. Keep this a list, so every retired ID stays in a list item. -->

- (none yet)

## Open Questions

<!-- Unresolved product questions. Each resolves into a requirement, a non-goal, or an ADR. -->

- (none yet)
