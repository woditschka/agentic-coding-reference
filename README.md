<a href="https://github.com/woditschka/agentic-coding-reference/actions/workflows/checks.yml?query=branch%3Amain+event%3Apush"><img align="right" src="https://github.com/woditschka/agentic-coding-reference/actions/workflows/checks.yml/badge.svg?branch=main&amp;event=push" alt="checks"></a>

# agent-team

*An engineering team behind one conversation.*

Describe a feature. Specialist agents carry it through requirements, design, TDD implementation, review, and grading, working from durable specs that remember what agents forget. You make the merge decision. This repository, the **Agentic Coding Reference**, builds, proves, and ships that team.

**Seen, not claimed:** [a real recorded run](docs/feature-walkthrough.md) takes a bug report to a reviewed, graded, merge-ready change in 17 agent-minutes for $8.21, catching one critical spec defect on the way.

> **TL;DR** — Coding agents forget and drift. Better prompts do not fix that; engineering discipline does. This reference turns TDD, DDD, ADRs, ubiquitous language, and durable specs into the memory and feedback substrate an agentic coding workflow runs on. Decisions survive across sessions. Nested feedback loops catch drift before it compounds. The pipeline is not the point; the disciplines are. Adopt it with `/materialize` or the `agent-team` marketplace plugins, and run it with Claude Code, Copilot CLI, or OpenCode.

## Quick Start

**New to agentic coding?** The [primer](docs/agentic-coding-primer.md) defines the terms this page uses: agent, skill, subagent, hook, MCP, context window, TDD, DDD, ADR. **The idea in 40 minutes:** [the conference deck](https://woditschka.github.io/agentic-coding-reference/deck/) runs in the browser, with a lightning version and recorded eval runs (or [offline from a clone](docs/deck/)). **The idea in one run:** the [feature walkthrough](docs/feature-walkthrough.md) narrates a committed run record by record.

### Try a reference implementation

Needed once: one agent tool installed ([Claude Code](https://code.claude.com/docs/en/overview), [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli), or [OpenCode](https://opencode.ai/docs/)) and a clone of this repository. Two self-contained samples follow, explicit Go versus convention-driven Spring Boot; each sample's `CLAUDE.md` is its authoritative guide.

```bash
git clone https://github.com/woditschka/agentic-coding-reference.git
cd agentic-coding-reference

# Go — samples/go/CLAUDE.md
cd samples/go/
make ci                      # the full quality gate

# Java Spring Boot — samples/java-spring-boot/CLAUDE.md
cd samples/java-spring-boot/
./gradlew build              # compile, format check, test, package
```

Two more samples: [`samples/generic/`](samples/generic/) carries no build toolchain, and [`samples/product-workspace/`](samples/product-workspace/) runs one product across four repositories (partly built).

### Use with an agent tool

Open any sample directory. Configuration loads automatically; one `CLAUDE.md` and one `.claude/skills/` tree serve all three tools.

```bash
cd samples/go/                     # or samples/java-spring-boot/, samples/generic/
claude                             # or copilot, opencode
> Let's discuss the feature for rate-limiting the public API
```

The session interviews you, then the specialists take over; every hop is appended to `.scratch/handoff.jsonl`. Watch it from a second terminal with `python3 scripts/handoff.py view`.

### Adopt in your own project

One command onboards a new project and upgrades an existing one.

```bash
cd agentic-coding-reference
claude
> /materialize ../my-service       # installs the runtime; project files are kept
```

The harness ships opinionated defaults and is open-closed. Closed is the way of working: specialist agents, TDD-first, strategic DDD, XP-style nested loops, and spec-driven delivery through a PRD, a system design, and ADRs. That [kernel](docs/harness-project-api.md#the-kernel--what-no-brief-can-vary) and the runtime that carries it (`.claude/` skills, agents, hooks, schemas) are replaced whole on every upgrade. Open is what the specialists hold as opinion: what to test, how to layer, where the security bar sits. Each house-style brief below is one specialist's working opinion, shipped as a default and rewritten by the project within the kernel; project-owned files are kept on every upgrade.

```text
my-service/
├── CLAUDE.md                      # project rules; only the harness-managed chapters inside are replaced
├── scripts/layout.toml            # stack binding, distribution channel, workspace members
├── scripts/backlog.sh             # the /next tracker connector, unbound until a team binds it
└── docs/
    ├── testing-principles.md      # the test reviewer's opinion: what to test, doubles, naming
    ├── architecture-principles.md # the system-design expert's opinion: layering, DDD tactics, boundaries
    ├── security-principles.md     # the security reviewer's opinion: the security bar
    ├── prd.md                     # stubs the specialists fill as the work proceeds; on existing code,
    ├── system-design.md           #   /derive-briefs fills them from the code first
    ├── ubiquitous-language.md
    └── adr/
```

Then work from the project itself.

```bash
cd ../my-service
claude                             # or copilot, opencode
> Let's discuss the feature for rate-limiting the public API
```

The steps, the three distribution channels, and the no-clone plugin install are in the [Adoption Guide](docs/adoption-guide.md).

### Go further

- **Make it your own.** [Customize after onboarding](docs/adoption-guide.md#customize-after-onboarding) lists the options a project controls and the extensions it keeps. [`harness-project-api.md`](docs/harness-project-api.md) names the seven briefs a project owns and the kernel it cannot vary.
- **Choose or configure an agent tool.** [`cross-tool-strategy.md`](docs/cross-tool-strategy.md) holds the rules-file, skill, and agent matrices, the IDE paths, and the tool-choice framework.
- **Run it on open-weight models.** [`open-weight-models.md`](docs/open-weight-models.md) maps the two pinned tiers to a provider, per tool.
- **Run it with more than one person.** [`human-teams.md`](docs/human-teams.md): one checkout and one slice per person; claims live in the team's tracker.
- **Run one product across more than one repository.** [`product-workspace.md`](docs/product-workspace.md), partly built: the umbrella and its members, the tiers of truth, the cross-repository change set.

## Why This Exists

To build software that lives for years, and hold it to a high bar on quality and maintainability the whole way. Agents make the building fast. Documentation, tests, and recorded decisions keep a codebase coherent long after any single session, and those are exactly what agent work erodes by default. An agent forgets between one message and the next, the way a human forgets between Friday and Monday. Within days, a project that skips the compensating disciplines drifts: inconsistent terms, re-litigated decisions, this week's architecture contradicting last week's.

The harness answers with the disciplines human teams already built: documentation standards, DDD, TDD, ADRs, ubiquitous language, XP-style nested loops. They become the **memory and feedback substrate** every agent, session, and person reads and writes. **Long-term memory** lives in `docs/`, the durable specs that evolve across features. **Working memory** lives in `.scratch/`, the per-feature handoff log, cleared after merge. A specialist agent team operates it through a file-based pipeline, building one vertical slice at a time. The loop model, the artifact roster, and the handoff contract are in [`agentic-harness.md`](docs/agentic-harness.md).

<p align="center">
  <img src="docs/images/pipeline-flow.drawio.png" width="640" alt="The agentic harness pipeline in three layers: a long-term memory band of durable specs (prd.md, system-design.md, adr/, ubiquitous-language) on top; a vertical specialist flow — product-requirements, system-design, feature-implementer, reviewer roster, change-grader, human — inside four nested loop bands, with requested-flow arrows for consultation, rework, and next-slice; and a short-term memory band of the append-only handoff.jsonl record stream on the bottom. A slim routing layer (route script plus coordinator) sits between the flow and the log it reads.">
</p>

It is for anyone who runs an agentic coding workflow over more than a few sessions. A solo developer driving an agent team past what fits in one conversation. A team where each developer drives their own agent team on a shared codebase. A human-only team that wants the same discipline against the slower drift humans face. The failure modes are the same; only the speed differs.

## Your Part in It

An agent multiplies whatever it is pointed at. Judgment is the scarce input. You supply the design and the standards; the harness supplies the memory, discipline, and execution that amplify them.

- **You decide.** Requirements, design, and standards are yours; the agent does not set them.
- **The agent researches and critiques.** It proves or disproves a direction and surfaces options you had not weighed. It improves the inputs to a decision, not the decision.
- **Design is discovered in the dialogue,** and against real user feedback once a slice ships. What the dialogue produces is captured as memory: **what** to build (`prd.md`), **how** it is structured (`system-design.md`), and **why** it won (`adr/`).

The same collaboration repeats at three flight levels: within a slice, across slices, and over the whole codebase. The whole-codebase level is the review teams skip under deadline; the agent makes it affordable without removing the architect seat. Range is rewarded, not required: a less experienced engineer gets the same scaffolding around their own decisions. The harness amplifies whatever judgment it is given and supplies none that is not there. The levels, the division of work, and the payoff are in [`force-multiplier.md`](docs/force-multiplier.md).

## What It Looks Like in Practice

You type one sentence. The router dispatches each hop: a script for decided transitions, a coordinator for untriaged intake and escalations. Agents read and update long-term memory as they go.

```text
You: "Let's discuss the feature for rate-limiting the public API"

→ root interviews you directly (goals, constraints, non-goals)
  └─ you confirm the exit; your decisions are recorded verbatim (intake-decision)
→ product-requirements-expert judges the quoted intake cold
  └─ writes docs/prd.md + ubiquitous language · appends prd-entry (schema-validated)
→ system-design-expert triages the slice against durable memory
  └─ verdict "new" · writes docs/system-design.md + an ADR · appends design-block
→ feature-implementer runs the TDD inner loop (red → green → refactor)
  ├─ a question the triage missed? consultation-request → answer → control
  │  returns to the implementer, never forward
  └─ appends build-pass (quality gate: build, test, lint, deps-check)
→ reviewer roster in parallel: security · code-quality · tests · docs
→ change-grader (advisory): how much human attention the passing change
  deserves — nothing auto-merges; you make the merge decision
```

The trace above is schematic. The [feature walkthrough](docs/feature-walkthrough.md) narrates a committed run record by record: ledger, review findings, fix routing, escalation, grade, and cost included. Each step either updates a durable spec in `docs/` or appends to the schema-validated log in `.scratch/`. The filesystem is the coordination layer: auditable, interruptible, tool-agnostic.

## The Eval Bench

Claims about agent harnesses are cheap; measurements are not. **The series is public:** [`TREND.md`](evals/results/TREND.md) prices every released harness version against one fixed subject project, reporting cost per pass, waste, and wall, straight down the versions. Every figure is regenerated from the committed run folders, never hand-edited. The [eval bench](evals/README.md) holds the method: frozen prompts, a machine-verified bar, and an advisory blind judge that keeps quality drift visible. The bench caught its first cost regression in this repository; the fix landed as [ADR 2026-08-07](docs/adr/2026-08-07-review-cycle-survives-mid-slice-design-records.md) with engine tests pinning it.

<p align="center">
  <img src="docs/images/eval-trend.drawio.png" width="720" alt="Five aligned panels across every measured harness version: cost of a clearing rep with rolling-mean trends per feature task and a flat one-dollar refusal line, each task's median delivery wall in the same encoding, burn rate in dollars per minute holding a flat band across every version, reliability at 100 percent apart from one early-version dip with the known-defect clear rate dashed beneath it between zero and a third across every version, and blind-judge quality as one line per rubric facet: doc-fit near 5 throughout, design-fit stepping from 3 to 4 at the model change and holding, test-quality and maintainability rising from about 3.4 toward 4 across the series; a dashed rule marks where the models change">
</p>

> The figure is a dated snapshot; its subtitle carries the stamp. [`TREND.md`](evals/results/TREND.md) is the live series it summarizes, with per-rep links and the dated operator notes.

## Under the Hood

- **Understand the machinery in depth.** [`agentic-harness.md`](docs/agentic-harness.md): the four-loop model, slice definition, agent roster, handoff contract, grading, recovery.
- **Study the architecture or migrate stepwise.** [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md): design principles, capability progression, canonical layout, migration playbook.
- **Look up a harness term.** The [glossary](docs/glossary.md) holds the working vocabulary, each entry linking its canonical home.
- **Measure a harness version.** [`evals/README.md`](evals/README.md) prices cost per pass against a fixed SUT; the results are in [`TREND.md`](evals/results/TREND.md).
- **Understand why the harness evolved this way.** [`docs/adr/`](docs/adr/) is the decision log; it pairs with the [project history](docs/project-history.md), the pre-launch narrative and the dated milestone timeline.
- **Maintain this reference.** [`CLAUDE.md`](CLAUDE.md) holds the maintainer loop and root skills; [`harness/README.md`](harness/README.md) holds the source tree, scripts, and battery.

## Disclaimer

This is a personal learning project. It documents patterns and ideas the author explored while experimenting with AI coding agents.

Use anything here freely under the [MIT License](LICENSE), but at your own risk. Evaluate everything yourself before applying it to your own work.

This project is not affiliated with, endorsed by, or sponsored by Anthropic, GitHub, or any other tool vendor mentioned in this repository. All product names, trademarks, and registered trademarks are the property of their respective owners and are used here solely for identification and descriptive purposes.

## License

[MIT License](LICENSE)
