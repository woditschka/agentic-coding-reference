---
name: diagram-update
description: >-
  Regenerate the reference's architecture figures when the harness changes, in
  one consistent house style. Owns the figures as native .drawio sources
  exported to embedded-XML PNGs; the sources are the style spec. The skill
  holds the intentions behind the style, each figure's composition, the
  draw.io export command, and the README embedding convention. Load when the
  pipeline, agents, loops, distribution channels, or harvest flow change, or
  to add a new figure. Root-only (Claude Code).
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# diagram-update

The architecture figures in the README are hand-authored draw.io diagrams. They
are documentation, not generated artifacts, so they drift when the harness
changes unless someone redraws them. This skill keeps them faithful and on-style.

## Figures

| Source (`docs/images/`) | README section | Shows | Redraw when… |
|---|---|---|---|
| `pipeline-flow.drawio` → `.drawio.png` | Intro — the "in one minute" summary (the ASCII breakdown stays in The Pipeline) | The pipeline as three stacked layers — a long-term-memory band of durable specs on top, the vertical specialist flow inside four nested loop bands in the middle, a short-term-memory `handoff.jsonl` band on the bottom — with the coordinator as a slim routing layer between the flow and the log | the agent roster, loop model, routing, handoff record types, or durable-spec set change |
| `harness-lifecycle.drawio` → `.drawio.png` | Distribution channels | One `/harness` source fanning into the three channels, with the harvest return path | a channel is added/removed, a script is renamed, plugin count changes, or harvest behaviour changes |
| `spec-flow.drawio` → `.drawio.png` | `specialist-agent-workflow.md` — "How Specs Flow Through the Pipeline" (sole figure; the prior ASCII was removed as redundant, and the figure's `alt` text carries the full flow for text-only readers) | Long-term specs → owning agents → short-term handoff records → implementer, with the consultation-request return path | the spec owners, record types, or consultation routing change |

Each figure is committed as **two files**: the `.drawio` text source (diffable,
easy to edit) and the `.drawio.png` render with embedded XML (re-openable in
draw.io, referenced by the README).

## When to run

- After a `/harness` change that alters what a figure depicts (see the table's last column).
- When adding a new architecture figure to the README — author it in the house style below.
- These are documentation assets, not part of `check-sync`; freshness is a judgment check, like `history-update`.

## House style

**The committed `.drawio` sources are the canonical exemplars of this style.**
When you regenerate a figure or add a new one, open them, reuse their exact
styles, and match them. This section records only the *intentions* behind the
style and the techniques the XML cannot explain — the concrete values live in
the sources alone.

One restrained palette, one accent, typographic hierarchy, generous grid. The
composition carries the concept — nested bands for loops, a left-to-right fan for
distribution. Flat (no shadows), no XML comments.

### Why this style — the intentions behind the specifics

The figures aim at an **editorial, printed-book register**, not slideware. Four
intentions drive every value below. Hold the intentions when the spec runs out —
a new figure, an unlisted case — and the additions stay coherent.

- **Color is semantic, never decorative.** The single accent marks the control element — the coordinator, the source, the loop and channel labels. Everything else is ink on white or muted grey. Hence one accent rather than a palette, muted secondary text, and flat fills. A reader learns "accent = the spine" once.
- **The composition teaches the concept before the words.** Layout encodes the idea: nested bands are nested loops; a left-to-right fan with a return arrow is one source, many channels, a harvest. Pick the geometry that makes the structure legible pre-verbally; text only confirms it.
- **Recede everything that is not the point.** Thin grey connectors, dashed background bands lightest-outward, no shadows — the nodes dominate and structure stays ambient. Outputs fold into their producing card, an attribute rather than a node, to cut element count.
- **Each card answers two questions at two priorities.** Who (bold ink) and what it emits or does (muted). The muting sets the reading order — actors first, detail on demand. Shape encodes role: stadium pills for human entry and exit, the accent fill for the orchestrator — a card in the lifecycle figure, a slim routing layer in the pipeline.
- **A figure is self-contained.** The title states the subject and the foot caption states the mechanism, so it reads correctly lifted out of the surrounding prose — the book-figure convention.

When extending the style, ask: does this stay editorial, keep color semantic, and let the composition carry the idea? If yes, it belongs.

### Palette, typography, and shape values

Read them from the committed `.drawio` sources — copy an existing element's
style string rather than re-deriving values. Three techniques worth naming
because a fresh read of the XML does not reveal *why*:

- **`whiteSpace=wrap` is mandatory on every card** — without it, text overruns the box.
- **XML mechanics that fail silently**: escape `&`, `<`, `>` in labels as entities, and give every edge a child `mxGeometry` with `relative="1"`. A fresh element missing either renders broken; copy an existing element rather than authoring one from scratch.
- **One card width per figure**, consistent vertical rhythm, gaps of roughly 40px so edge labels sit cleanly between boxes.
- **Route to avoid crossings.** When two return arrows share a margin, the farther-reaching one exits lower and wraps around the nearer. An unavoidable crossing (into a nested band) crosses once, perpendicular.
- **Band labels knock out the lines behind them**: the label carries its band's fill, no stroke, and sits **last in the file** so it renders above every edge. Trim its box so the fill does not occlude unrelated arrows.

### Pipeline-flow composition (three layers)

`pipeline-flow.drawio` is a portrait, GitHub-column-friendly figure (≈640 wide) built as three stacked layers. Hold this structure on regeneration:

- **Top layer — long-term memory.** A full-width dashed long-term-memory band holds the durable specs as memory chips (`prd.md`, `system-design.md`, `adr/`, `ubiquitous-language`). They spread evenly to read as *shared* — every agent reads and writes them, so they align to no single agent.
- **Middle layer — the specialist flow.** The agents run top-to-bottom (`User request` → Product Requirements → System Design → Feature Implementer → Reviewer roster → Change Grader → `Human reviews and merges`) inside the four nested loop bands. The bands carry only a small depth-colored `↺` marker, not a verbose label — the loop names live in the foot caption. The endpoints are stadium pills.
- **Coordinator as a routing layer, not a flow step.** The coordinator is **not** a card in the chain. It is a slim full-width accent routing layer between the flow and the log it reads. Its label states it routes every handoff and validates every record; a thin `reads` connector drops to the short-term band. This keeps it the orchestration substrate without dominating as the head of the chain.
- **Requested flows, not every routed arrow.** Forward steps are drawn directly; do **not** draw agent→coordinator→agent for each hop. Draw only the meaningful coordinator-mediated requests, as accent dashed arrows in the side margins, each colored by its loop depth:
  - `consultation · clarify` — Feature Implementer → System Design and → PRD (right margin).
  - `rework` — Reviewer → Feature Implementer (left).
  - `next slice` — Change Grader → Product Requirements (left).
- **Bottom layer — short-term memory.** A full-width solid short-term-memory band for `.scratch/handoff.jsonl`, holding the append-only record chips (`prd-entry`, `design-block`, `build-pass`, `review-feedback`, `grader-verdict`).

### Spec-flow composition (layered, compact)

`spec-flow.drawio` is a compact, near-square figure (540-unit source canvas, embedded at `width="660"`) that shows how durable specs feed the per-feature work. Its depth comes from **nesting**, not loop bands. Hold this structure on regeneration:

- **Durable layer, outside the pipeline.** A dashed long-term-memory band on top holds the spec chips (`docs/prd.md`, `ubiquitous-language.md`, `docs/system-design.md`). It sits *outside* the pipeline band below — the geometry says long-term memory outlives the feature.
- **A nested per-feature pipeline band.** One dashed lightest band (the `arch`-tint) wraps the whole working flow: the two owning agents, the short-term-memory band, and the implementer. Its label reads `PER-FEATURE PIPELINE — working memory, discarded after merge`. This nesting is the layered-depth device, in place of pipeline-flow's loop bands.
- **Short-term memory nested inside it.** A solid short-term-memory band for `.scratch/handoff.jsonl`, holding the `prd-entry` and `design-block` record chips, sits *inside* the per-feature band — ephemeral working memory within the feature's scope.
- **Two lanes converging on the implementer.** Left lane: `docs/prd.md` → `product-requirements-expert` → `prd-entry`. Right lane: `docs/system-design.md` → `system-design-expert` → `design-block`. Both records are read by a single centered `feature-implementer` card whose muted line states it *never edits long-term memory directly*.
- **The arrows, by role.** Four kinds, each consistent with the house palette:
  - `reads · writes` — thin grey dashed double arrow, each agent ↔ the long-term band.
  - `appends` — grey, agent → its record.
  - `reads` — grey, record → implementer.
  - `consultation-request` — accent dashed risers up the outer margins, implementer → each owning agent, labelled with rotated text.

  No coordinator appears; this figure is about memory flow, and routing is stated in the foot caption.

The generic draw.io mechanics — `.drawio` mxGraphModel structure, the CLI flags, URL mode — live in the user-level `drawio` skill. This skill adds the house style, the specific figures, and their placement.

## Authoring and regeneration

1. **Edit the source.** Change `docs/images/<name>.drawio` (the text mxGraphModel) to match the new harness reality, holding the house style above. For a new figure, copy an existing source as the styling template.
2. **Export to PNG** with embedded XML at 2× for crispness:
   ```bash
   /Applications/draw.io.app/Contents/MacOS/draw.io \
     -x -f png -e -b 12 -s 2 \
     -o docs/images/<name>.drawio.png docs/images/<name>.drawio
   ```
   `-e` embeds the XML (keeps the PNG editable), `-s 2` is 2× scale, `-b 12` is the border. If the draw.io CLI is absent, keep the `.drawio` and tell the user to install the desktop app or open the file to export.
3. **View and verify** — Read the exported PNG and check it against the list below.
4. **Embed in the README or doc** with a width-controlled, centered figure (a bare `![]()` renders the 2× file too large in previews). Use a path relative to the embedding file — `docs/images/<name>.drawio.png` from the root README, `images/<name>.drawio.png` from a file in `docs/`:
   ```html
   <p align="center">
     <img src="docs/images/<name>.drawio.png" width="<W>" alt="<description>">
   </p>
   ```
   Width tracks aspect and should use a good share of GitHub's ~880px content column without going flush to the border: portrait figures sit around `width="640"`, near-square around `width="660"`, landscape around `width="720"`. Keep `W` below the PNG's native pixel width so the source is never upscaled — the `-s 2` export leaves about 2× headroom. Keep descriptive alt text.

## Verification checklist

- No text overruns a box; every card has `whiteSpace=wrap` and fits its content.
- Text does not collide with arrows; edge labels carry a white knockout, and a band label crossed by a connector carries the band-colored knockout (rendered last).
- Lines do not cross where a reroute avoids it; unavoidable crossings (into a nested band) are single and perpendicular.
- Bands nest correctly and their labels sit in the gaps, not over cards.
- Palette and typography match the spec — one accent, muted secondary text, flat.
- The `<img>` width still suits the figure's aspect, fits GitHub's ~880px column, and does not upscale the source; alt text describes it.
- Both files are present and in sync: re-export after any `.drawio` edit.

## What it reuses, and does not do

- **Reuses** the user-level `drawio` skill for draw.io XML and CLI mechanics; this skill owns only the house style, the figures, and their README or doc placement.
- **Does not gate.** Figures are documentation, not deterministic artifacts — no `check-sync` step. Staleness is caught by judgment when the harness changes.
- **Does not auto-detect drift.** A PNG cannot be diffed against pipeline semantics; the redraw triggers in the figures table are the prompt to act.
