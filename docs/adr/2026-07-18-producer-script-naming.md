# Producer-Side Script Names Encode Scope: `-harness` for the Whole, the Tree for One

**Status:** Accepted

## Context

Renaming the deterministic battery to `verify-harness` ([verify-harness-rename](2026-07-18-verify-harness-rename.md)) fixed one name and exposed the rest. Four producer-side names muddle what they do, and no convention is written down, so the next script gets named ad hoc.

- `helpers.py` / `helpers.sh` is a junk-drawer name for the stacks/tools/channels registry — the opaque-name class [runtime-package-layout](2026-07-17-runtime-package-layout.md) retired (`score-change`, `brief_doctor`, `cc_accounting`). The README calls it "the source of the stack rosters, the TOOLS registry."
- `release-prep.sh` reads as release-only, but the maintainer loop runs it after *every* `/harness` edit: it rebuilds the three derived trees, then runs the battery. Release is one caller.
- `refresh-agent-bodies.py` wears the `refresh-` verb that otherwise means "update one consumer slice," yet it renders a producer-side mirror tree.
- `bootstrap.sh` is a vague word for "materialize the three samples."

## Decision

**Producer-side script names encode scope. A tool that acts on the whole reference takes the `-harness` suffix; a tool that builds one derived tree names that tree; the shared facts module is `registry`.**

The convention:

- **Whole-reference scope → `-harness`.** `verify-harness` (check it), `propagate-harness` (rebuild all its derived trees, then verify), `audit-harness` / `review-harness` (assess it).
- **One derived tree → name the tree.** `render-agent-mirrors`, `materialize-samples`, `package-marketplace`.
- **Consumer verbs stay skill-anchored.** `init`, `materialize`. In-place consumer-slice updates keep `refresh-<slice>`: `refresh-gitignore`, `refresh-settings`, `refresh-chapters`.
- **Shared facts are `registry`,** not `helpers`.
- **A skill's deterministic-measurement input names the skill's domain.** `deps-report`, `review-survey`.

The four renames this convention forces:

- **`helpers` → `registry` (`.py` and `.sh`).** It holds `STACKS`/`TOOLS`/`CHANNELS`, `detect_stack`, and `read_harness_layout` — the registry every tool derives from. The `.sh` mirror renames in lockstep (parity-gated). The test-loader that finds the toolbox root by locating `helpers.py` repoints its sentinel to `registry.py`.
- **`release-prep` → `propagate-harness`.** It rebuilds the derived trees and calls `verify-harness`; the `-harness` suffix marks its whole-reference scope, and the verify half is delegated to the tool named for it. `release-version.sh` keeps its accurate name and calls it.
- **`refresh-agent-bodies` → `render-agent-mirrors`.** A producer-side render of the per-tool mirror trees, moved out of the consumer `refresh-*` family into the tree-builder convention beside `package-marketplace`.
- **`bootstrap` → `materialize-samples`.** Names its target, so the call chain reads: `propagate-harness` → `render-agent-mirrors` + `materialize-samples` + `package-marketplace` + `verify-harness`.

## Options Considered

1. **Keep the names** — rejected: opaque (`helpers`) and misleading (`release-prep`) fail the self-describe standard [runtime-package-layout](2026-07-17-runtime-package-layout.md) set for the shipped side.
2. **`rebuild-derived` for the orchestrator** — considered: it names the destination (the derived trees) directly. Rejected for `propagate-harness` so whole-reference scope reads through the `-harness` suffix, consistent with `verify`/`audit`/`review`.
3. **Also rename `package-marketplace` → `render-marketplace` and align `deps-report`/`review-survey`** — rejected: `package` is a distinct, legitimate verb, and the two measurement scripts produce genuinely different outputs. Uniformity is not the goal; legibility is.
4. **Encode scope — `-harness` for the whole, the tree name for one** (chosen).

## Consequences

- Positive: `harness/` reads as a toolset, not a pile; the suffix encodes scope at a glance; a new script has a rule to follow instead of a coin flip.
- Negative: ~25 living files update — importers, the `.sh` mirror and its parity gate, the test-loader sentinel, the `CLAUDE.md` maintainer loop, four skills, the docs, and `pyproject.toml`. The `harness-lifecycle` figure labels `bootstrap` and needs a separate `/diagram-update` pass; it is not battery-gated. All churn is internal.
- Non-consequence: no CLI, flag, output, or exit-code change; no consumer churn (every renamed script is producer-side, never shipped); `docs/adr/` keeps its historical names.

## References

- [The Deterministic Battery Is Renamed `verify-harness`](2026-07-18-verify-harness-rename.md) — the precedent that opened the naming question; this generalizes it to the whole toolbox.
- [The Shipped Runtime Becomes Domain Packages Under a Composition Root](2026-07-17-runtime-package-layout.md) — retired the opaque shipped-side names; this extends the self-describe standard to the producer side.
- [A Typed, Checker-Enforced Standard for the Harness Python Core](2026-07-17-typed-python-core.md) — the producer-side tier this convention names.
