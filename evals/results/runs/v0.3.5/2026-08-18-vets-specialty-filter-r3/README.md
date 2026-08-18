# vets-specialty-filter r3 — v0.3.5

Filter the vet list by specialty (feature) · started 2026-08-18T00:35:57+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: filter the vet list by specialty. Three product decisions
> come with it, made here as the product owner:
> 
> - Non-goal NG-9 is narrowed: free-text veterinarian search stays out of
>   scope, but filtering the directory by an attribute it already shows is in.
>   Record the narrowing the way the project records non-goal changes.
> - The JSON endpoint at /vets is reinstated as a supported surface — this
>   filter is its first requested capability. Mint a fresh requirement for it;
>   the withdrawn REQ-VET-002 stays withdrawn and its id is not reused.
> - The filter is a URL contract only. Neither surface gains a form, dropdown,
>   or other page control in this request; pagination links carry the
>   parameter so filtered pages stay navigable. A visible control may come as
>   a follow-up request.
> 
> Both vet list surfaces accept an optional  specialty  query parameter:
> 
> - /vets.html?specialty=<name> — the HTML page shows only vets holding that
>   specialty; pagination applies to the filtered list.
> - /vets?specialty=<name> — the JSON endpoint returns only those vets.
> 
> Matching is on the whole specialty name, case-insensitive — not a prefix. A
> specialty matching no vet yields the normal page or JSON document with an
> empty vet list (HTTP 200). An empty or whitespace-only value behaves as if
> the parameter were absent, like the empty owner search. Without the parameter
> both endpoints behave as today. Cover the new behavior with tests.
> 
> These are all the product decisions; no further product answer will come
> during the work. Where a choice still seems open, take the narrowest reading
> consistent with this request and record the open question rather than
> waiting.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 5/5 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 8/8 |
| review attention (pipeline grade) | — |

- ✔ `theSpecialtyFilterShouldMatchCaseInsensitively` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheHtmlVetList` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheJsonVetList` — passed
- ✔ `theUnknownSpecialtyShouldYieldAnEmptyVetList` — passed
- ✔ `theVetListShouldShowTheFirstPageWithoutAFilter` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theSpecialtyFilterShouldMatchCaseInsensitively`
- ✔ `theSpecialtyFilterShouldNarrowTheHtmlVetList`
- ✔ `theSpecialtyFilterShouldNarrowTheJsonVetList`
- ✔ `theUnknownSpecialtyShouldYieldAnEmptyVetList`
- ✔ `theVetListShouldShowTheFirstPageWithoutAFilter`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.05. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching is pushed into a derived repository query ( findDistinctBySpecialtiesNameIgnoreCase ), keeping the controller a thin adapter, but  narrowingSpecialty  in VetController adds a blank-equals-absent rule to a controller — the catalog's *Web controller* row bars new rules there, and no ADR names the departure. Tests are behavior-named ( theVetDirectoryShouldIgnoreABlankSpecialty ), phase-separated, and use tiered constants ( ONE_VET_PER_PAGE ,  SPECIALTY_HELD_BY_NO_VET ); they still lean on Mockito stubs and bare expected literals ( "Leary" ,  .value(2) ) without factories. Maintainability is good — javadoc records why the narrowed reads are uncached — though the template now carries five duplicated two-form links. Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, superseded note, known-defect row removed, threat-model and open-question rows added, three ADRs indexed.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in the repository as derived queries (VetRepository.findDistinctBySpecialtiesNameIgnoreCase), the cache decision is deliberate and documented, and the controller only binds and delegates — though narrowingSpecialty() puts the blank-equals-absent rule in the controller rather than a unit-testable seam, and the template now carries every page link twice through the narrowed ternary. Tests are behavior-named (theVetDirectoryShouldIgnoreABlankSpecialty), use collection assertions and named constants such as SPECIALTY_CARRYING_URL_SYNTAX, and cover blank, no-match, case, prefix, encoding and pagination; mystery literals survive (is("Leary"), jsonPath id .value(2)) and the not(containsString("specialty=")) whole-page assertion is brittle. Docs are exemplary: NG-9 narrowed, REQ-VET-003/004 minted, the withdrawn-route defect row removed, threat model and open questions updated.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository derived queries ( findDistinctBySpecialtiesNameIgnoreCase ) keep matching and the caching decision at the persistence seam, and the controller stays a thin adapter; the private  narrowingSpecialty  normalization is request-level, but being controller-private it can only be exercised by booting MVC, widening the pyramid gap the principles flag. The template's five duplicated ternary link forms are real, if ADR-acknowledged, debt. New tests are BDD-named ( theVetDirectoryShouldIgnoreABlankSpecialty ), phase-separated, use existing  helen() / james()  factories and named constants ( ONE_VET_PER_PAGE ,  BLANK_SPECIALTY ), and cover blank, no-match, case, prefix, dedup, and URL encoding; residual mystery literals remain ( jsonPath("$.vetList[0].id").value(2) , bare "Leary"/"Douglas"). Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, superseded entry, known-defect row removed, threat-model row, three ADRs indexed.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.90 | 39m | 27 | 94% | 11 file(s) +400/−33 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VETSSPECIALTYFILTER-001 — Veterinarian directory can be narrowed to one specialty

0 review rounds · 0 build-passes · **1 build-failure** · no grade yet

- • intake-decision (human)
- ◇ **prd-entry** Veterinarian directory can be narrowed to one specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 8m***
- ↳ consult **design** → **prd-expert** · Does docs/prd.md record REQ-VETSSPECIALTYFILTER-001 — for instance as a traceability line naming it the slice that delivered REQ-VET-003 and REQ-VET-004, without minting it as a requirement or reusing the withdrawn REQ-VET-002? If you record it in some such form, say which, and I will mirror exactly that form in the Contracts prose of docs/system-design.md so both halves of the gate close consistently. If you judge that a scratch-log id must not enter the PRD at all, say so: then the gate failure is a defect in the seeded slice id rather than in either document, and it needs a human waiver rather than a documentation edit.
- ↲ consult **prd-expert** → **design** · No. docs/prd.md does not record REQ-VETSSPECIALTYFILTER-001, and I will not add it in any form. Your half is decided correctly: do not mirror it into docs/system-design.md either. Three reasons. First, the id names no requirement. The PRD's ids name capability areas (OWN, PET, VIS, VET, LANG, SYS); VETSSPECIALTYFILTER is a slice label seeded by headless intake, and it would sit beside REQ-VET-001 looking exactly like a peer requirement. Second, the behavior is already recorded, twice over, under REQ-VET-003 and REQ-VET-004. A third id for the same capability is a duplicate identity, and the owner's intake decision points the other way: 'Mint a fresh requirement for it; the withdrawn REQ-VET-002 stays withdrawn and its id is not reused.' The owner is reasoning in the REQ-VET namespace. Nothing in the intake authorizes a third id. Third, a traceability line would not stay inert. The doctor's req-acceptance check requires every REQ-ID token in docs/prd.md to appear in a list item, so the id would have to be dressed as an acceptance bullet to pass. That is minting a requirement nobody asked for, in order to satisfy a mechanical check. A git-ignored scratch identifier in a durable brief also serves no reader of the PRD. The substance the gate exists to enforce is already satisfied. Both documents are in sync under the real ids: the Contracts rows for Vet, Specialty, Vets, VetRepository, and VetController cite REQ-VET-003 and REQ-VET-004, and both ids carry Done-when bullets under Veterinarian directory in docs/prd.md. I verified this by running the check under each requirement id: 'contracts-sync --feature REQ-VET-003' and '--feature REQ-VET-004' both exit 0 today, with no edit to either document. So the failure is not a documentation gap. It is the slice id itself. The gate assumes the slice req_id is a requirement id, and headless intake seeded one that is not. Correcting that is not a product decision and is outside my write scope: it means either waiving contracts-sync for this slice on the evidence that it passes under REQ-VET-003 and REQ-VET-004, or re-keying the slice to a requirement id, which forks an append-only chain whose intake-decision, design-blocks, and build-failure all carry the seeded id. That choice is the human's alone. I am recording it here as a pause rather than editing a durable brief to make a mechanical check green.
- ↳ consult **design** → **human** · How should this slice clear contracts-sync, given that its req_id names no requirement? Two remedies are available and both are yours to choose; neither is within any agent's write scope. (A) Waive contracts-sync for this slice, on the recorded evidence that it exits 0 under REQ-VET-003 and REQ-VET-004 against this same working tree — the implementer then records the check as run under the real requirement ids and proceeds to review. (B) Re-key the slice to a requirement id, which forks the append-only chain: the intake-decision, prd-entry, both design-blocks, the build-failure, and the consultation pair all carry the seeded id, so re-keying means re-establishing the slice under REQ-VET-004 and losing the continuity of this trail. My recommendation is (A): the gate's purpose is already satisfied and verifiable, whereas (B) pays real audit-trail cost to satisfy a string match. Separately, and not blocking this slice, the underlying defect is that headless intake seeded a slice-label id in requirement-id shape; a fresh slice against the harness would fix that so this cannot recur.

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:system-design-expert` | 3 | opus-5 | $8.24 | 15m 47s | 93% |
| `agent-team:feature-implementer` | 1 | opus-5 | $6.36 | 13m 5s | 97% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $4.97 | 7m 14s | 92% |
| `(parent)` | 1 | opus-5 | $3.22 | 39m 16s | 95% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $6.36 | 13m 5s | 97% |
| `agent-team:system-design-expert` | opus-5 | $4.02 | 9m 22s | 94% |
| `(parent)` | opus-5 | $3.22 | 39m 16s | 95% |
| `agent-team:product-requirements-expert` | opus-5 | $2.90 | 4m 21s | 92% |
| `agent-team:system-design-expert` | opus-5 | $2.79 | 4m 40s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $2.07 | 2m 52s | 91% |
| `agent-team:system-design-expert` | opus-5 | $1.43 | 1m 44s | 89% |

</details>

## Artifacts

- [`change.patch`](change.patch) — the agent's diff against the baseline commit
- [`handoff.jsonl`](handoff.jsonl) — the pipeline's handoff ledger, one record per line
- [`agent-costs.json`](agent-costs.json) — per-agent and per-stage token and dollar figures
- [`run.log`](run.log) — prep, gradle, and diagnostic tails
- [`egress.log`](egress.log) — the confinement proxy's per-request access records
- [`manifest.json`](manifest.json) — pre-run coordinates: prompt, fingerprint, prep steps
- [`result.json`](result.json) — the raw measurement record this page derives from

## Provenance

- plugin `agent-team-spring-boot` at `v0.3.5` (tag)
- model requested `claude-opus-5`; models used: opus-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.233 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
