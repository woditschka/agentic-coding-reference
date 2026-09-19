<!-- harness: 2026-09-17 -->
# Ubiquitous Language

<!-- The canonical domain vocabulary for this project — the "ubiquitous language" in the Domain-Driven Design sense (Eric Evans, Chapter 2). The same terms are used by stakeholders, the PRD, the system design, and the source code.

  This file is durable memory. Agents and developers across sessions read it to keep the same vocabulary; drift here ripples into variable, function, and file names across the codebase.

  ENTRY FORMAT

    **TermName**: One-sentence definition. Define what it IS, not what it does. Relationships: (optional) one line naming the related concepts and the cardinality where obvious. Avoid: (optional) other words used in the wild for the same concept that this project rejects. Listing them heads off drift.

  Example:

    **Order**: A customer-placed request for one or more line items, accepted for fulfillment but not yet shipped. Relationships: An Order contains one or more LineItems and references one Customer. Avoid: Purchase, Transaction (those are billing-context terms).

  WHEN TO ADD A TERM

  - The moment a term resolves during a requirements interview or a design discussion. Do not batch. Do not wait for a second use.
  - When recurring domain terms in existing docs or source code aren't yet captured (adoption case — the system-design-expert may write here during a foundational triage to seed the initial vocabulary).

  WHAT NOT TO PUT HERE

  - Harness methodology vocabulary (slice, loop, triage verdict, etc.) — that is the team's method, not this project's domain. This file holds project-domain terms only.
  - Implementation details. Definitions describe domain concepts, not code shape.

  CONSUMERS

  - The product-requirements-expert resolves and writes PRD terms.
  - The system-design-expert resolves design terms; it writes here only during the foundational triage path on adoption.
  - The doc-reviewer lints cross-document term consistency.
  - The feature-implementer names new domain-facing code from the entries; the code-quality-reviewer checks those names against them.

  CADENCE

  Slow. The ubiquitous language changes less often than the PRD or system design. Treat updates here as load-bearing — they ripple into variable, function, and file names across the codebase. -->

## Domain Terms

**Book**: One stocked title the store lists, identified by its title. Relationships: a Book has one Title and at most one Subtitle. Avoid: Item, Product (billing-context terms this product does not use).

**Title**: The name of a Book as printed on its cover before the colon; never blank.

**Subtitle**: The descriptive line printed after the colon; may be absent.

**Catalog**: The whole stock as the backend serves it, in stock order. Relationships: a Catalog lists zero or more Books. Avoid: Inventory (implies counts, which the product does not track).

**Stock**: The backend's fixed set of Books; the source the Catalog is served from.

## Example Dialogue

> **Developer:** When the page loads, what do we show?
> **Owner:** The catalog: every book in stock, title first, subtitle underneath.
> **Developer:** And a book with no subtitle?
> **Owner:** Still a book. Show the title row alone.
