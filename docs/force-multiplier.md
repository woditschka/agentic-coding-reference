# The Force Multiplier and the Engineer's Part in It

An agent multiplies whatever it is pointed at. Judgment is the scarce input. The engineer supplies the design and the standards; the harness supplies the memory, discipline, and execution that amplify them. The disciplines that keep the multiplier raising quality rather than noise (TDD, DDD, owned specs, ADRs) matter more at this speed, not less. This document states how the work divides between the engineer and the agent team, and at which levels that division repeats. The loop model the levels run on is in [`agentic-harness.md`](agentic-harness.md); how more than one person shares the levels is in [`human-teams.md`](human-teams.md).

## How the Work Divides

- **The engineer decides.** Requirements, design, and standards are theirs; the agent does not set them.
- **The agent researches and critiques.** It proves or disproves a direction, researches the ground, and surfaces options the engineer had not weighed, widening the choice space they decide within. It improves the inputs to a decision, not the decision.
- **Design is discovered in the dialogue,** and against real user feedback once a slice ships. The inner loop only settles interface shape. What the dialogue produces is captured as memory at three levels: **what** to build (`prd.md`), **how** it is structured (`system-design.md`), and **why** it won over the alternatives (`adr/`). That separation lets a decision outlast the session that made it.

## Three Flight Levels

The same collaboration runs at three flight levels, each writing the memory that keeps agents, sessions, and people pointed the same way:

| Flight level | Who decides | The agent's work | What holds the direction |
|---|---|---|---|
| Within a slice | the engineer | proposes, challenges, builds | tests · `system-design.md` |
| Across slices | the team | drives each slice; surfaces conflicts | `prd.md` · ubiquitous language |
| Whole codebase | the architect seat | sweeps for drift at machine speed | `adr/` · `system-design.md` |

The top level is the one teams skip under deadline: whole-codebase coherence review costs days of legwork. The agent does that legwork at machine speed; the architect seat brings the judgment. The multiplier makes the review affordable. It does not remove the seat.

## Range Is Rewarded, Not Required

The harness amplifies whatever judgment it is given. An engineer who reads the customer, the system, and the code at once catches drift at every level the agent moves through. A less experienced engineer gets the same scaffolding around their own decisions. What the harness will not do, at any level, is supply judgment that is not there.

## The Payoff

The payoff is a build-ship-watch loop measured in days, not weeks: short enough to keep pace with how user needs surface. The harness is the fixed cost that makes this repeatable. Paid once, it holds every feature to the team's standards across sessions, so speed never costs direction.
