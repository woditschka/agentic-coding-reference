---
name: update-diagrams
description: >-
  Regenerate the reference's architecture figures when the harness changes, in
  one consistent house style. Owns the figures as native .drawio sources
  exported to embedded-XML PNGs; the hand-authored sources are the style spec
  for the doc register, and tools/deck/figures.py is the source for the two
  slide figures. The skill
  holds the intentions behind the style, each figure's composition, the
  draw.io export command, and the README embedding convention. Load when the
  pipeline, agents, loops, distribution channels, harvest flow, or claude-dev
  network topology change, when a recorded sweep
  changes the eval-trend story, when the human-team split or the backlog
  connector changes, or to add a new figure. Root-only (Claude
  Code).
compatibility:
  - claude-code
metadata:
  version: "1.1"
  author: team
---

# update-diagrams

The architecture figures in the README, the docs, and the deck are draw.io
diagrams: documentation, which drifts when the harness changes unless someone
redraws it. The eval-trend data figure is rendered by `evals/render_figure.py`,
and the two slide figures by `tools/deck/figures.py` through
`tools/deck/deck.py build`; the rest are hand-authored. This skill keeps every
figure faithful and on-style.

## Figures

| Source (`docs/images/`) | Embedded in | Shows | Redraw when… |
|---|---|---|---|
| `pipeline-flow.drawio` → `.drawio.png` | README — "Why This Exists" (the "in one minute" summary) | The pipeline as three stacked layers — a long-term-memory band of durable specs on top, the vertical specialist flow inside four nested loop bands in the middle, a short-term-memory `handoff.jsonl` band on the bottom — with the coordinator as a slim routing layer between the flow and the log | the agent roster, loop model, routing, handoff record types, or durable-spec set change; or to adopt the slide figures' memory-band pair, solid long-term and dashed short-term (§ Slide figures) |
| `harness-lifecycle.drawio` → `.drawio.png` | `docs/adoption-guide.md` — "Distribution channels" | One `/harness` source fanning into the three channels, with the harvest return path | a channel is added/removed, a script is renamed, plugin count changes, or harvest behaviour changes |
| `spec-flow.drawio` → `.drawio.png` | `specialist-agent-workflow.md` — "How Specs Flow Through the Pipeline" (sole figure; the prior ASCII was removed as redundant, and the figure's `alt` text carries the full flow for text-only readers) | Long-term specs → owning agents → short-term handoff records → implementer, with the consultation-request return path | the spec owners, record types, or consultation routing change; or to adopt the slide figures' memory-band pair (§ Slide figures) |
| `claude-dev-egress.drawio` → `.drawio.png` | `tools/claude-dev/README.md` — "Egress: the session has no route out" (replaced the prior ASCII; the `alt` text carries the topology for text-only readers) | The host machine as the outer band nesting the engine VM, with the JetBrains IDE card and `last-egress.log` chip below the VM; inside it the two per-run networks, the session innermost and the accent proxy straddling both, the internet outside — the accent dashed IDE pinhole drops straight from the proxy to the IDE, the muted verdict-log drop lands on the chip | the network topology, proxy policy, IDE bridge, or log path changes (ADR 2026-07-29 supersessions) |
| `human-teams.drawio` → `.drawio.png` | `docs/human-teams.md` — "The Same Flight Levels, One Agent-Team per Person" | Three person bands side by side, each holding a person pill, an agent-team card, a private `.scratch/` chip, and a slice-branch line; a solid team-board band above with ranked and claimed REQ chips; a dashed shared-repository band below with the durable-doc chips, the commit rule, and the accent `scripts/backlog.sh` chip. Accent dashed double arrows rise from each team to the board (one standalone accent label in the gap names the `/next` read and claim); muted dashed double arrows drop to the repository | the per-person/shared split changes, the connector contract changes, a shared surface is added, or the durable-doc set changes; or to adopt the slide figures' memory-band pair (§ Slide figures) |
| `pipeline-slide-memory.drawio` → `.drawio.png` | `docs/deck/slides.html` — the "Memory" slide | The human and the agent-team joined by the conversation. Long-term memory under both: a `docs/` folder of the four specs beside the code box. Short-term memory under the agent-team alone: `.scratch/` holding `handoff.jsonl` | the durable-spec set, the memory split, or the deck's palette changes; rendered by `tools/deck/figures.py`, never hand-edited (§ Slide figures) |
| `pipeline-slide-routing.drawio` → `.drawio.png` | `docs/deck/slides.html` — the "Agent-team" slide | The specialist flow left to right inside the four named loop bands, the consultation and rework returns, the slim long-term band above the flow, and the router between the flow and the slim short-term band | the roster, the loop model, the routing, or the deck's palette changes; rendered by `tools/deck/figures.py`, never hand-edited (§ Slide figures) |
| `eval-trend.drawio` → `.drawio.png` | README — "The Eval Bench" · `evals/results/TREND.md` header (embed emitted by `summarize.py`) | A dated data figure rendered by `evals/render_figure.py` from `evals/results/trend-data.json` (the machine-readable derived view): five aligned panels over one ordinal version axis — cost of a clearing rep (successful reps only; features as rolling-mean trends, the refusal task as a raw dashed ~$1 line), wall (median delivery wall of the clearing reps per task, in the cost panel's encoding and at its height), burn rate (spend per delivery minute, same encoding), reliability (share of reps clearing the bar, plus the known-defect clear rate as a dashed rolling-mean trend in the same unit), and quality (blind-judge mean per rubric facet, one raw line per facet, 1–5) | a recorded sweep changes the story — a new spike, an era boundary — never after every sweep; each redraw re-derives the lines from `trend-data.json` via `evals/render_figure.py` and re-stamps the snapshot date |

Each figure is committed as **two files**: the `.drawio` text source (diffable;
hand-edited for the doc figures, script-rendered for eval-trend and the slide
figures) and
the `.drawio.png` render with embedded XML (re-openable in draw.io, referenced
by the home doc in the table above).

## When to run

- After a `/harness` change that alters what a figure depicts (see the table's last column).
- When a recorded sweep changes the eval-trend story (the figures table's eval-trend row names the triggers).
- When adding a new architecture figure to the README or a doc — author it in the house style below.
- When the deck's slide figures change: edit `tools/deck/figures.py` (§ Slide figures).
- Freshness against the harness is a judgment check, like `update-history`. The battery holds only the mechanical part: the deck's figure suite runs in its tools step, and `tools/deck/deck.py build --check` pins the slide sources to the script.

## House style

**For the doc figures, the committed `.drawio` sources are the canonical exemplars of this style.**
A regeneration or a new figure opens them, reuses their exact styles, and
matches them. This section records only the *intentions* behind the
style and the techniques the XML cannot explain — the concrete values live in
the sources alone. For the two slide figures the values live in
`tools/deck/figures.py`, and § Slide figures states how the intentions carry
over to a hall.

One restrained palette, one accent, typographic hierarchy, generous grid. The
composition carries the concept — nested bands for loops, a left-to-right fan for
distribution. Flat (no shadows), no XML comments.

### Why this style — the intentions behind the specifics

The doc figures aim at an **editorial, printed-book register**. Five
intentions drive every value below. Hold the intentions when the spec runs out —
a new figure, an unlisted case — and the additions stay coherent. The slide
figures hold the first three in the projection register, and the shape rule of
the fourth; the fifth they hand to the slide's heading and the speaker
(§ Slide figures).

- **Color is semantic, never decorative.** The single accent marks the control element — the coordinator, the source, the loop and channel labels. Everything else is ink on white or muted grey. Hence one accent rather than a palette, muted secondary text, and flat fills. A reader learns "accent = the spine" once.
- **The composition teaches the concept before the words.** Layout encodes the idea: nested bands are nested loops; a left-to-right fan with a return arrow is one source, many channels, a harvest. Pick the geometry that makes the structure legible pre-verbally; text only confirms it.
- **Recede everything that is not the point.** Thin grey connectors, dashed background bands lightest-outward, no shadows — the nodes dominate and structure stays ambient. Outputs fold into their producing card, an attribute rather than a node, to cut element count.
- **Each card answers two questions at two priorities.** Who (bold ink) and what it emits or does (muted). The muting sets the reading order — actors first, detail on demand. Shape encodes role: stadium pills for human entry and exit, the accent fill for the orchestrator — a card in the lifecycle figure, a slim routing layer in the pipeline.
- **A figure is self-contained.** The title states the subject and the foot caption states the mechanism, so it reads correctly lifted out of the surrounding prose — the book-figure convention.

When extending the style, ask: does this stay editorial, keep color semantic, and let the composition carry the idea? If yes, it belongs.

### Palette, typography, and shape values

For a doc figure, read them from the committed `.drawio` sources — copy an
existing element's style string rather than re-deriving values. For a slide
figure, read the style tables in `tools/deck/figures.py`. Three techniques worth naming
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
- **Router as a routing layer, not a flow step.** The router is **not** a card in the chain. It is a slim full-width accent routing layer between the flow and the log it reads. Its label states the two-part contract: `handoff.py route` executes the table; the coordinator resolves escalate and fresh intake. A thin `reads` connector drops to the short-term band. This keeps it the orchestration substrate without dominating as the head of the chain.
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

### Eval-trend composition (data triptych)

`eval-trend.drawio` is a landscape chart (900-unit canvas, embedded at `width="720"`) — the family's one *data* figure and its one chart: every mark derives from recorded `trend-data.json` rows, so its rules differ from the hand-drawn box diagrams. Hold these on regeneration:

- **A dated snapshot, never a live view.** The subtitle stamps the last measured version and date; the README blockquote under the figure points at `TREND.md` as the live series. The figure never claims currency — that is what keeps a judgment-carrying data figure from becoming a dual-write.
- **Five aligned panels, one figure, one version axis.** Cost of a clearing rep, reliability (share of reps clearing the bar), and quality (blind-judge mean per rubric facet) decompose the tables' headline metric. The identity — cost per pass ≈ cost of a clearing rep ÷ share clearing — is stated in the caption. The panels are inseparable by design: success-only cost is honest **only** with the failure rate rendered beside it. Never publish the cost panel alone, and never fold failures out of the tables — cost per pass stays the headline metric there. The second panel is context beside the cost, at the cost panel's height: each task's median delivery wall over its clearing reps, in the cost panel's encoding — same series styles, smoother, dashed raw refusal line, repeated right-margin labels — so money and time compare directly, and since the tasks differ by an order of magnitude in wall a sum would hide which one moved. The third panel, burn rate ($/min), closes a second identity — cost of a clearing rep ≈ wall × burn rate — each cell the median over its clearing reps of spend per delivery minute (a median of ratios, never a ratio of medians); a flat line means cost tracks time, so the reader can tell longer pipelines from dearer minutes. Reliability follows as a single line. The known-defect clear rate joins it whenever a rep carries a named-defect probe (`trend-data.json` `known_defects`). That rate is the share of probed reps whose recorded diff clears every named defect their task declares, in the panel's own unit; the axis runs from 0 to 100 in every case. Its dots are the recorded per-version shares. Its dashed steel-blue line is the cost panel's centered three-version rolling mean, never a raw curve, since three reps a cell would move a raw curve one lucky rep apart. Quality closes the figure with one raw line per rubric facet in the cost panel's encoding. Each point is the mean of the facet's per-rep medians over the version's judged reps; the dot is that mean, and a repeated right-margin label names the facet. The axis is the rubric's own range, 1 to 5, fixed, so a move reads at its true share of the scale. Every floor in the figure is fixed; only the cost, wall, and burn ceilings adapt to the series, since a moving ceiling keeps the ratio between points and a moving floor does not. A pooled median of a five-point integer scale saturates at 4 and shows no drift inside the top band. Each harness change targets one facet's reviewer or gate, so the facet line is the feedback a maintainer can read. The rubric is ordinal, so the caption calls the mean a reading aid and the tables keep every score. Wall is the page's most condition-sensitive measure (API latency and retries land here, never in cost), which the caption states.
- **Dots are the data; the line is a named smoother.** Every recorded cell renders as a small semi-transparent dot. The cost panel's value is cell spend minus waste over clearing reps, read from `trend-data.json` — the tables' own cells, so every mark is recomputable. Feature trends are centered three-version rolling means with symmetric windows — a window missing a neighbor collapses to the recorded cell, so the line starts and ends on the data. Every line in every panel draws as a monotone cubic through its points — smooth, overshoot-free, never renderer-curved; flat plateaus stay flat by construction. Never draw a curve as if it were the data, and never fit a model (LOESS, polynomial). No per-point numbers — the tables own the figures.
- **The refusal task is raw and dashed.** Its bar inverts, a correct outcome costs ~$1 in every era, and its early failures appear as the reliability panel's dip — never as smoothed cost. A cell with no clearing rep renders no point. The burn panel draws no refusal line: a refusal delivers no change, so it has no delivery minute, and the tables show its burn as a dash.
- **Ordinal x-axis, measured versions only.** Unmeasured releases are absent, and the caption states the axis is ordinal; even spacing is positional, not temporal.
- **No in-plot annotations.** The panels carry only data marks, axes, and the caption. One derived mark is not an annotation: a dashed vertical rule where the requested root model changes between adjacent versions, drawn per panel so it crosses no caption or tick, with a solid-ground label at the top of the cost panel naming the models the later version resolved — both computed from `trend-data.json`. Panel captions center over the plot width, like the title and subtitle. Fixed-position text over moving lines collides on re-derivation, and any candidate annotation restates a fact an operator note or ADR already carries. Commentary lives in those channels, never in the figure. The accent goes to the most-storied series; the rest hold the muted family.

### Slide figures

The family has two registers of the same subject. The doc figures above are the editorial register: portrait or near-square, titled, captioned, hand-authored, read on a page. The two slide figures, `pipeline-slide-memory` and `pipeline-slide-routing`, are the projection register: landscape, script-rendered, read from the back of a hall while a speaker talks. A doc figure never goes on a slide and a slide figure never goes in a doc. The slide markup and its stylesheet contract are in `docs/deck/README.md` § Figure slides. Hold these on regeneration:

- **The script is the source.** `tools/deck/figures.py` holds every coordinate, style, and word. `tools/deck/deck.py build` writes both `.drawio` files, and `build --check` fails on drift, the same mechanism as the casts bundle. A layout change is an edit to the script, never to the XML. The PNG export is step 2 of the procedure below, with the transparent background.
- **The deck's palette, not the doc palette.** The colors mirror the paper look in `docs/deck/deck.css`, with the rule one step darker so a box edge survives projection. Color stays semantic. The accent marks the control elements: on the memory slide the conversation; on the agent-team slide the loop bands with their names, the two return arrows, and the router. One tint, the loop bands', marks the agent-team box on the memory slide, so it reads as the loops it opens into. Every memory element is grey.
- **Words are only what the speaker cannot say.** One to three plain words per card. The specialists carry their real agent names in the mono face, broken one word per line, without hyphens. No card carries the muted descriptor line the doc cards carry. The reviewer roster is the one word `reviewers`. An arrow the talk does not need is not drawn: the next-slice return is absent. No title, no subtitle, no caption; the slide's heading and the speaker carry those. The deck's figure suite pins the exact word set of each slide.
- **One scale across the family.** The shared sizes are the named constants at the top of `figures.py`: box height, name size, title size, arrow-label size. The stylesheet caps each image's height at the same fraction of its exported height, so the two render at one scale on screen. The figure suite pins the rendered sizes to the constants, the caps to the figures, and the palette to the stylesheet.
- **Geometry carries the claim on the memory slide.** The human pill and the agent-team card sit close, joined by a short straight conversation arrow with its label above the line. Long-term memory spans under both; short-term memory sits under the agent-team alone, so the arrows say who reads what. A dash says transient on the slides: the short-term band and the loop bands are dashed, the long-term band is solid. The doc figures hold the opposite pair, a dashed long-term band and a solid short-term band, as their composition sections state. Adopting the slide pair is a redraw trigger in the figures table. A folder is a box in the tone that contrasts its band, named in mono; a file is a white chip. The code box is distinct by its border only, never by a dark fill.
- **Geometry carries the claim on the agent-team slide.** The flow runs left to right through four nested loop bands, stepped by one constant vertically and hugging the cards they hold. The request pill enters from outside the loops; the merge pill sits inside the outermost one. Each loop is named once at a corner, TDD at the bottom-left, clear of the consultation lanes. The consultation label sits between its two lanes above the design card; rework sits under its lane. The two memories collapse to one slim titled band each, because the memory slide has already opened them.
- **One deliberate divergence from the handbook's vocabulary.** The outermost loop is named `codebase`, its unit, where the handbook and the glossary name it the architectural loop. A hall reads the unit cold; the speaker says the name.

The generic draw.io mechanics — `.drawio` mxGraphModel structure, the CLI flags, URL mode — live in the user-level `drawio` skill. This skill adds the house style, the specific figures, and their placement.

## Authoring and regeneration

1. **Edit the source.** Change `docs/images/<name>.drawio` (the text mxGraphModel) to match the new harness reality, holding the house style above. For a new figure, copy an existing source as the styling template. **Eval-trend and the slide figures are the exceptions.** Never hand-edit their `.drawio`; the next render overwrites it wholesale. For eval-trend, run `evals/render_figure.py` (or `evals/refresh_trend.py`); it exports the PNG when the draw.io CLI is present, otherwise it prints the step-2 command for a manual export. For a slide figure, edit `tools/deck/figures.py` and run `tools/deck/deck.py build`, then export with step 2.
2. **Export to PNG** with embedded XML at 2× for crispness:
   ```bash
   /Applications/draw.io.app/Contents/MacOS/draw.io \
     -x -f png -e -b 12 -s 2 \
     -o docs/images/<name>.drawio.png docs/images/<name>.drawio
   ```
   `-e` embeds the XML (keeps the PNG editable), `-s 2` is 2× scale, `-b 12` is the border. A slide figure adds `-t`, a transparent background, so the slide's paper shows through instead of a white plate. If the draw.io CLI is absent, keep the `.drawio` and tell the user to install the desktop app or open the file to export.
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
- Both files are present and in sync: re-export after any `.drawio` edit, or after any `tools/deck/figures.py` edit for a slide figure.
- A slide figure embeds through `docs/deck/slides.html` with no width; the stylesheet's height caps size it (README § Figure slides).

## What it reuses, and does not do

- **Reuses** the user-level `drawio` skill for draw.io XML and CLI mechanics; this skill owns only the house style, the figures, and their README or doc placement.
- **Does not gate the PNGs.** A PNG is documentation, not a deterministic artifact — no `verify-harness` step compares one to the harness. Staleness against the harness is caught by judgment when the harness changes.
- **Does not auto-detect drift** — with two nudges. `summarize.py` prints the eval-trend figure's stamped-version status on every run. `tools/deck/deck.py build --check` fails when a slide source drifts from its script. A PNG cannot be diffed against pipeline semantics; the redraw triggers in the figures table are the prompt to act.
