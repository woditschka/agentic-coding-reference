# A Product Workspace Holds the Product Truth; Module Repositories Are Members Checked Out on Demand

**Status:** Accepted (implementation pending; see Implementation)

## Context

Some products split their modules, a frontend and a backend for instance, across repositories. The harness binds one consumer to one directory: one repository, one docs roster, one gate, one working tree. Three questions arrive tangled when such a product adopts it: where the product truth lives (PRD, system design, ADRs, ubiquitous language), how the product deploys (one unit, or services scaling apart), and who works on what (one team on everything, or teams per module behind an agreed API). A layout that fits one team shape should not be rebuilt for the next.

Two facts shape the decision. The change set under review has one definition, `git diff` in one repository through one gateway (`scripts/changeset/git_facts.py`); the reviewers, the review plan, the security-surface probe, and the change-grader all read it. And Conway's law holds for agents as for teams: what an agent can read, it couples to.

## Options Considered

1. **Git submodules under an umbrella repository.** Rejected: the superproject diff renders an edit inside a submodule as one pointer line, so the reviewers, the risk ladder, and the tree snapshots go blind while the pipeline runs green. Each module also sits on a detached HEAD.
2. **Git subtree.** Every git call works unchanged; syncing to the upstream repositories is a human step at commit time. Kept as the zero-change prototype path; rejected as the design because history noise and the sync burden grow with every member.
3. **Nested worktrees and a workspace-aware change set** (chosen).
4. **Model the deployment topology in the layout.** Rejected: the gate builds and tests, it never deploys, and repositories per module neither force nor forbid separate deployables.

## Decision

**A product workspace is an umbrella repository that owns the product truth and declares its member modules; members are worktrees checked out beside it only when a slice needs them.**

- **Product tier.** The umbrella's `docs/` holds the PRD, the product system design, and cross-module ADRs. The product design owns the module map, each module's responsibility, the contracts between modules (APIs, events, data ownership), the cross-cutting concerns, and the shared terms. Deployment topology is a statement in that design and an ADR, never a layout fact.
- **Module tier.** A member repository is a harness consumer in a new *module* role. Its `docs/` holds the module system design (internal structure, aggregates, data model, local terms) and module ADRs; it carries no PRD. References run one way: the product design links each module design; a module design refers up to the contracts it implements and never defines one. The routing rule is mechanical: whatever another team would need to know goes up.
- **Workspace.** A `[workspace]` table in `scripts/layout.toml` lists the members. The git gateway runs each command per present member and prefixes paths; a snapshot becomes a member-to-tree-sha map; the gate dispatcher iterates the present members before calling the stack verbs; the doctor reports an absent member without failing; design triage refuses a slice that needs an absent member. A single repository is the degenerate case with no members.
- **Checkout policy.** The umbrella always; members on demand. Not having the neighbor on disk is the mechanism that keeps the contract sufficient. A contract change checks out both sides, which is the whole-product shape for that one slice. Cross-module integration is consumer-driven contract tests defined with the contract, never a shared checkout.
- **One layout.** Prefixed globs classify every member; the security-surface probe is the union of the member languages. A member repository carries no `CLAUDE.md` of its own, or one line deferring to the umbrella; a team runs one harness level, never both.

## Consequences

**Positive:** one mechanism covers the one-team, per-module-team, and agreed-API shapes; they differ only in which worktrees sit beside the umbrella on a machine. Each tier has one decision log and a mechanical routing rule between them. Two teams editing the product design conflict at merge in the umbrella, which is the design conversation the split intends.

**Negative:** the umbrella detects as the generic stack, so stack-specific reviewer bodies and probes bind by hand. Two consumer roles mean two doctor rosters, and 37 agent and skill files per stack set (23 in core, 14 per stack) that name the PRD or the system design learn the two tiers; that fan-out warrants a tier-2 audit. The member-to-sha snapshot changes the review-plan record shape, so its version bumps. A slice lands as one commit per member; the feature-complete record lists each member's branch and head, and the team owns merge order and the deploy tolerance for one side landing first.

## Implementation

Not landed. Three changes, in order, each battery-gated: (1) the workspace fan-out in the git gateway, the emit module, the grading features, and `schemas/scratch/review-plan.schema.json`, proven unchanged for a single repository by the differential oracle; (2) member presence in the layout, the doctor, and `scripts/gate.sh`; (3) the module consumer role: its roster in `doctor-expectations.toml`, role detection in the stack registry, `init` and `materialize` scaffolding, the two-tier prose in the agents and skills, and a workspace section in `docs/adoption-guide.md`.

## References

- [2026-06-17-generic-stack-verb-contract](2026-06-17-generic-stack-verb-contract.md): the verb surface the umbrella's `stack.sh` binds per member.
- [2026-06-12-docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md): the single roster this decision splits into a product role and a module role.
- [2026-06-18-additive-reviewer-roster](2026-06-18-additive-reviewer-roster.md): the roster floor that stays fixed while the probes become a union.
- [`../ddd-principles.md`](../ddd-principles.md): the context map is the product tier; a bounded context's design is the module tier.
- [`../adoption-guide.md`](../adoption-guide.md): the consumer surface that gains the workspace section once the implementation lands.
