# Product Workspace

**Status:** Design, partly built. The change set and the review plan fan out over members today; § Implementation Status lists the rest. [ADR 2026-09-13](adr/2026-09-13-product-workspace-with-member-modules.md) records the decision and its implementation order. This document states what a workspace is and how it operates, so every other surface can point here.

A product workspace is how the harness serves a product whose modules live in separate repositories. Typical splits: a frontend and a backend, a contract library and its two sides, one service per team. One repository, the **umbrella**, owns the product truth and declares the modules. Each module repository is a **member**. Members sit beside the umbrella as sibling directories, never inside it, and are checked out only when a slice needs them.

## Roles

| Role | Repository | Owns | Runs |
|---|---|---|---|
| Product | The umbrella | The PRD, the product design, cross-module decisions, the shared vocabulary, the member list, the dependency graph | The harness, on any distribution channel. Every harness session starts here |
| Module | A member | Its module design, module decisions, an extension brief only where it deviates, its code and build | Its own build. No harness session starts here |

A member carries no harness runtime and no rules file beyond one line that names the umbrella. Claude Code loads a granted directory's rules file once a file under it is read, and Copilot CLI loads a granted directory's agents and skills. A member with a runtime of its own would therefore load two harnesses into one session.

## Operating Modes

Two ways of working share one mechanism. They differ only in which members sit beside the umbrella on a machine.

- **One team, one member.** The backend team checks out the umbrella and the backend. The frontend is a name in the member list and a contract in the product design. The team knows the frontend exists and never reads its code.
- **One developer across all.** The developer checks out the umbrella and every member the current slice touches. A contract change checks out both sides.

Three constraints hold in both modes:

1. **Harness sessions start in the umbrella.** The product truth is the working directory, so no agent can skip it. An IDE session on a member is unaffected. A session started in a member reads the one-line rules file and moves to the umbrella.
2. **A member checked out alone is not a harness consumer.** Its build, tests, and IDE work as in any repository. The harness never runs there, by design.
3. **The umbrella is always checked out.** Members are on demand. A declared member that is absent is reported, never failed: absence is the mechanism that keeps each contract sufficient on its own.

## Two Tiers of Truth

The routing rule between the tiers is mechanical: whatever another team would need to know goes up. A module design refers up to the contracts it implements and never defines one. The product design links each module design.

A second rule places the briefs. The umbrella states every principle once, with one realization section per stack its members use. A member carries a brief of the same name only where its module deviates, holding nothing but the deviation.

| Brief | Umbrella | Member | Reason |
|---|---|---|---|
| `prd.md` | yes | no | Product truth has one owner |
| `system-design.md` | yes | yes | Product: the module map, each module's responsibility, the contracts between modules (APIs, events, data ownership), the cross-cutting concerns. Module: internal structure, aggregates, data model, local terms |
| `adr/` | yes | yes | Cross-module decisions up, module decisions local. Deployment topology is a product design statement and an ADR, never a layout fact |
| `ubiquitous-language.md` | yes | no | One glossary. A module's local terms live in its design doc |
| `testing-principles.md` | yes | extension only | The product states the bar, with the framework floor per stack in its own section; the cross-module rule, consumer-driven contract tests, is one paragraph in the product design's Contracts section. A member that deviates states the deviation, nothing more |
| `architecture-principles.md` | yes | extension only | The pattern catalog and naming rules are stated once per stack; boundaries between members and the dependency direction are the product design's job |
| `security-principles.md` | yes | extension only | Trust boundaries run between members, so the product states them; a member adds a boundary of its own only when it has one |
| `CLAUDE.md` | yes | one line | The umbrella's rules file is authoritative |
| `scripts/layout.toml` | yes | no | One layout classifies every member |

The doctor therefore runs two rosters. Product: every brief of a single repository. Module: the module design and its ADRs, plus any extension brief present, held to the same section shape. Every requirement id a module design cites resolves against the umbrella's PRD.

## Layout

The umbrella's `scripts/layout.toml` declares the members. Each key names the member in the review plan and the gate. Each path is relative to the umbrella and is the prefix every change-set path carries. Each stack names the shipped defaults the engine merges for that member's paths.

```toml
[workspace.members]
api     = { path = "../bookstore-api",     stack = "java-spring-boot", contracts = ["src/main/proto/**"] }
backend = { path = "../bookstore-backend", stack = "java-spring-boot", depends_on = ["api"] }
web     = { path = "../bookstore-web",     stack = "java-spring-boot", depends_on = ["api"] }
```

Two more facts live in the same table: each provider's contract paths, and each member's dependencies. They live in the umbrella because the harness needs them exactly when a member is absent, and an absent repository's own declaration is unreadable. The product design states both in prose and stays the human-readable truth. The layout is the machine-readable copy, and the doctor holds the two to each other as it holds requirement ids between the PRD and the design doc. Dependencies are declared, not derived from build files: one line, any stack.

The umbrella detects as the generic stack, because it holds no build marker. Stack knowledge reaches every reviewer through the declared stack: the engine composes each member's security-surface probe and conventions from that stack's shipped defaults, the same files the stack's own consumers ship. Until that composition lands, the umbrella's own layout carries the probe, as the bookstore's does. A project override in the umbrella's layout applies key by key, as it does for a single repository.

Change-set paths are real relative paths from the umbrella, so every consumer opens a file by the path it is given. The layout's globs are written the same way: `../bookstore-backend/src/main/` is a production root, `../bookstore-web/src/test/**` a test glob. A single repository is the degenerate case with no members and no prefixes.

## Placement and Access

A member is a clone by default. A worktree is an option for a team that wants the shared object store. Its absolute link into the main repository must then be reachable wherever the session runs, the claude-dev container included.

Reading a sibling needs no grant in Claude Code; the grants gate writes. The session reaches a member through each tool's own grant, never through nesting:

| Tool | Grant | Where it lives |
|---|---|---|
| Claude Code | `permissions.additionalDirectories` plus the native sandbox's write allow-list | The umbrella's `.claude/settings.json`, committed; `init` writes it from the member list |
| OpenCode | The `external_directory` allow rule | The umbrella's project config, committed; `init` writes it |
| Copilot CLI | The per-location `allowed_directories` list | The user's config directory; no launch flag replaces it |
| claude-dev | A read-write mount | The operator's launch policy |

The doctor holds the two committed grants to the member list and reports a Copilot grant it cannot find. Nesting a member inside the umbrella is rejected for three reasons. The member enters the umbrella's snapshot as an embedded-repository link. Ignoring it hides it from the file tools' search. Its rules file loads on access.

## Partial Checkout and Pushback

A slice runs over the members that are present. The change set, the gate, and the reviewers read those and no others. An absent member is recorded in the review plan as absent, never as unchanged, so its silence is never read as evidence. The grader's verdict names the members that did not take part.

The harness pushes back when what is absent matters, at two levels:

- **Block.** A change under a member's contract paths while any member that depends on it is absent. The design owner refuses the slice at triage with a `consultation-request` naming the members to check out. The engine repeats the check at review-plan time as a safety net: the triage is judgment, the diff is fact.
- **Warn.** A change to a member that others depend on, with no contract path touched, while a dependent is absent. The slice proceeds. The review plan and the grader say which consumers' contract tests did not run, and the human reads that before merging.

A block is overridable through the consultation path, with the human's decision recorded in the ledger. "The frontend is unaffected" stays possible and never silent.

What no mechanism catches: a behavior change inside an unchanged contract while the consumer is absent. Only the consumer's contract tests would see it, and they run only where the consumer is present. That is the warn level, and the reason to check out both sides when in doubt.

## The Change Set and the Review

One review reads one change set across repositories. The git gateway runs each command per present member and joins every path git reports to that member's relative path. A snapshot is the umbrella's tree plus one tree per present member. The review plan records that map beside its own tree, and a fix pass diffs each member against that member's previous tree. Reviewers, the risk ladder, the security-surface probe, and the change grader all read the prefixed set.

The gate iterates present members before its own verbs: each verb runs inside the member with the member key exported, so one `stack.sh` binds every member's technology. Until the dispatcher carries that loop, the bookstore's `stack.sh` writes it by hand.

Design triage refuses a slice whose design touches an absent member: the design owner records a `consultation-request` naming the member, and the run pauses until the member is checked out.

The handoff ledger lives in the umbrella. Replaying a review across repositories needs the umbrella plus each named member at its recorded tree, where a single repository needs only itself.

## Contracts

A contract has two homes. Its description, the module map, and its ownership live in the product design. Its artifact, a proto file or an API schema, lives in the member that publishes it. A contract change is therefore a slice across the umbrella's docs and both sides of the contract, and both sides are checked out for it. The contract artifact is that slice's primary deliverable surface; the product design and the consumer's contract test are the other layers it cuts through.

Cross-module integration is consumer-driven contract tests, defined with the contract and living in the consumer. No shared checkout stands in for them.

A slice lands as one commit per member the umbrella's ship step makes. The team owns merge order and the deploy tolerance for one side landing first.

## Unintrusive by Construction

A single repository must not load, run, or emit a single thing about workspaces, and the rule is checked, not promised.

- **No setting.** A layout without a `[workspace]` table is a single repository. The reader returns no members, every fan-out loop runs once over the project itself, and no template, init skeleton, or doctor key mentions the table.
- **No shipped prose, with one exception.** The tiers, the session home, and the pushback rules are one managed `CLAUDE.md` chapter rendered only for the product role. Subagents receive it with the rest of the rules file. Two clauses ship to every consumer, because no chapter can carry them: the review planner keeps `basis.members` on the plan it authors, and the review workflow names the per-member tree override. Agent bodies and skills gain nothing else.
- **No new fields.** The review plan carries its member map only when members exist. The `changeset` and doctor outputs print no workspace line for a project without the table. Records stay byte-identical.
- **No extra work.** The single iteration runs the same git commands as today, and the member reader parses the layout once more and finds no table. No grant, sandbox path, or mount is written.
- **No plugin growth.** The fan-out lives in the shared engine and executes only with members. The umbrella consumes the same marketplace plugin as any generic-stack consumer, and its product-owned files come from init.

The nets: the grading fuzzer, the ledger replay, and the handoff fuzzer against a worktree at the last commit print no difference for the single-repository path. The replay also proves every recorded ledger validates under the review-plan schema with its optional `members` object. The eval bench's dev sweep prices the candidate on the single-repository system under test before the release. A move in cost per pass there is a regression the release does not cut.

## Implementation Status

The sections above describe the design in the present tense. This table says which mechanism runs today; the ADR's Implementation section orders the rest.

| Mechanism | Status |
|---|---|
| The `[workspace.members]` reader with path, stack, contract, and dependency validation | built |
| The change set, the grading features, and the conventions map over every present member | built |
| The review plan's `members` map and the fix delta per member | built |
| The `--base-tree <key>=<sha>` override, refused for an undeclared member | built |
| The grading fuzzer building workspace projects | built |
| The doctor's presence report and grant-drift check | pending, change 2 |
| The gate dispatcher's member loop | pending, change 2; the bookstore's `stack.sh` hand-writes it |
| Pushback: triage refusal, the review-plan-time safety net, the grader naming absent members | pending, change 2 |
| The doctor holding `contracts` and `depends_on` to the product design's module map | pending, change 2 |
| Per-member probe and conventions composed from the declared stack | pending, change 3 |
| The doctor's two rosters and the module role in init and materialize | pending, change 3 |
| `init` writing the Claude Code, sandbox, and OpenCode grants | pending, change 3; the bookstore carries them by hand |
| The product-role managed chapter and the adoption-guide section | pending, change 3 |

## Worked Example

The bookstore under [`samples/product-workspace/`](../samples/product-workspace/) is the reference shape: the `bookstore` umbrella, the `bookstore-api` contract member with the catalog proto, the `bookstore-backend` gRPC server, and the `bookstore-web` page. The sample builds and runs, the umbrella carries the runtime and every brief, and each member carries its module design and decisions. Everything the table above marks pending is written by hand in the sample where the sample needs it.

## References

- [ADR 2026-09-13](adr/2026-09-13-product-workspace-with-member-modules.md): the decision, the rejected options, the implementation order.
- [`ddd-principles.md`](ddd-principles.md): the context map is the product tier; a bounded context's design is the module tier.
- [`harness-project-api.md`](harness-project-api.md): the single-repository roster this design splits into two.
- [`adoption-guide.md`](adoption-guide.md): the consumer surface that gains the workspace section with the implementation.
