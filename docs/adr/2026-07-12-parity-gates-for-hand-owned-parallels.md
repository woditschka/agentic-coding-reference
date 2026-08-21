# Roster and Vocabulary Gates for Hand-Owned Parallel Files

**Status:** Accepted (doc-sync split carve-out added 2026-08-06; three further carve-outs added 2026-08-21)

> 2026-08-21: three more contiguous byte-identical blocks cleared the 2026-08-06 bar and moved to core companions — the agents-README stack-agnostic tail (`README-cross-tool.md`; it had shipped one-sided edits twice, the revisit trigger recorded below), the review-checks autofix sections (`autofix-protocol.md`; the contract `handoff.py audit-autofix` enforces), and design-validation's Pipeline Position + Input Contract head (`pipeline-contract.md`; the reduced cut — § Triage Mode's interleaved half stays gated per the option-5 rejection). Option 6's whole-README rejection is narrowed the same way the option-5 rejection was: the stack heads stay hand-owned and gated; only the byte-identical tails render from core. The remaining ×3 residue is one pointer sentence per file, discipline-covered.

> 2026-08-06: the option-5 rejection is premise-specific, not blanket. `doc-sync/SKILL.md` carried a 47-line tail (Maintenance Rules, Compaction, Format Migration) byte-identical go↔generic and one noun-list token off in java — contiguous, zero interleaving, so the overlay-exception cost that sank option 5 for design-validation never arises. That tail now ships once as core `doc-sync/maintenance.md`; the stack `SKILL.md` keeps the exploration phases, the Output contract, its Contracts-table vocabulary, and a pointer. Everything else in this ADR holds; design-validation and the agent bases stay gated, not rendered.

## Context

The stacks carry hand-owned parallel files that legitimately diverge: the GoLand/IntelliJ skill trio and the three per-stack review checklists. Measured deltas are product tokens interleaved inside doctrine sentences, plus deliberate stack adaptations. Their contract-bearing parts — section rosters, feedback tags, severity levels — must not drift, yet no battery step gates them.

## Options Considered

1. **Whole-document render**, per the mirror-bodies precedent. Rejected: the similarity is ancestry, not contract; every genuine divergence becomes an overlay exception, coupling what evolves apart.
2. **Strict text-equality gates on shared sections.** Rejected: verification found product tokens inside doctrine sentences and legitimate content divergence; equality forces false parallels or a growing whitelist.
3. **No gate.** Rejected: discipline has held (one shared edit since both IDE skills exist), but the shared tokens are contract-bearing — a drifted feedback tag breaks review processing silently.
4. **Roster and vocabulary parity gates** (chosen).
5. **Core-plus-overlay file split for near-identical stack skills** (2026-08-02 review, rejected for design-validation; 2026-08-06, accepted for doc-sync's tail — see the status note). Proposed for `design-validation/SKILL.md` (~94% three-way identical) on the document-writing precedent. Verification refuted the premise there: the delta interleaves stack wording inside shared checklist sections, and one paragraph exists in only two of three stacks. Option 1's rejection reason — every genuine divergence becomes an overlay exception — applies to the split mechanism wherever deltas interleave; a contiguous byte-identical block clears it.
6. **Template render of `agents/README.md`** (2026-08-02 review, rejected). The go↔java delta is near-pure fact tokens, but generic diverges in prose and structure; the pinned-heading gate already covers the roster risk. Machine contracts are different: the three-way build schemas fall under the mirror-bodies render precedent this option list never governed — see the References note.

## Decision

**Hand-owned parallel files are gated at the level a contract forces identical — section rosters and shared vocabularies, never prose.** Three checks join the battery:

- The GoLand and IntelliJ IDE skills carry the same `##` section roster. A product-prose heading pair may be pinned as expected divergence, scoped to its file pair. Editing either heading fails the gate until the pin is updated — an edit-reviewed decision, not a growing whitelist.
- Feedback tags used in any stack skill belong to the canonical set in core `review-workflow` § Feedback Tags.
- The severity-level headings match across the three `security-review` copies.

## Consequences

- A doctrine section added to one IDE skill without its twin fails the battery.
- Prose stays free to diverge per stack; a legitimate divergence never fights a template.
- Sentence-level drift inside shared doctrine stays discipline-covered; revisit gating there if an edit ever ships one-sided.

## Implementation

The checks join `harness/check-sync.py`'s parity family.

## References

- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — this decision applies its identity test: gate rosters and vocabularies where prose legitimately diverges.
- [Rendered Agent Mirror Bodies](2026-07-03-rendered-agent-mirror-bodies.md) — the render precedent; it covers contract-identical copies, which these files are not. The stack build schemas were later found contract-identical modulo two data slots and route to that precedent, not this gate.
