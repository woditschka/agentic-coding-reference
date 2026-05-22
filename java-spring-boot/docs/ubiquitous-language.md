# Ubiquitous Language

<!--
  The canonical domain vocabulary for this project — the "ubiquitous language"
  in the Domain-Driven Design sense (Eric Evans, Chapter 2). The same terms
  are used by stakeholders, the PRD, the system design, and the source code.

  This file is durable memory. Agents and developers across sessions read it
  to keep the same vocabulary; drift here ripples into variable, class,
  method, and file names across the codebase.

  ENTRY FORMAT

    **TermName**: One-sentence definition. Define what it IS, not what it does.
    Relationships: (optional) one line naming the related concepts and the
      cardinality where obvious.
    Avoid: (optional) other words used in the wild for the same concept that
      this project rejects. Listing them is how we head off drift.

  Example:

    **Order**: A customer-placed request for one or more line items, accepted
      for fulfillment but not yet shipped.
    Relationships: An Order contains one or more LineItems and references one
      Customer.
    Avoid: Purchase, Transaction (those are billing-context terms).

  WHEN TO ADD A TERM

  - The moment a term resolves during a requirements interview or a design
    discussion. Do not batch. Do not wait for a second use.
  - When you find recurring domain terms in existing docs or source code that
    aren't yet captured (adoption case — system-design-expert may write here
    during a foundational triage to seed the initial vocabulary).

  WHAT NOT TO PUT HERE

  - Methodology vocabulary (slice, loop, inner-loop callback, triage verdict,
    etc.) — that lives in docs/agentic-harness.md and docs/tdd-principles.md.
    This file holds project-domain terms only.
  - Implementation details. Definitions describe domain concepts, not code
    shape.

  CONSUMERS

  - The product-requirements-expert resolves and writes PRD terms.
  - The system-design-expert resolves design terms; it writes here only
    during the foundational triage path on adoption.
  - The doc-reviewer lints cross-document term consistency.

  CADENCE

  Slow. The ubiquitous language changes less often than the PRD or system-
  design. Treat updates here as load-bearing — they ripple into variable,
  class, method, and file names across the codebase.
-->

## Domain Terms

_(empty — populated as the PRD develops)_

## Example Dialogue

_(placeholder — once several terms are in place, write a short worked exchange
between a developer and a domain expert that uses the canonical terms in
context. The dialogue shows readers how the terms interact and clarifies the
boundaries between related concepts.)_
