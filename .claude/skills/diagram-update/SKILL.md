---
name: diagram-update
description: >-
  Regenerate the reference's architecture figures when the harness changes, in
  one consistent house style. Owns the two README diagrams — the pipeline flow
  and the build/distribute/harvest lifecycle — as native .drawio sources exported
  to embedded-XML PNGs. Holds the exact palette, typography, shape, and layout
  spec so a regenerated figure matches the originals, plus the draw.io export
  command and the README embedding convention. Load when the pipeline, agents,
  loops, distribution channels, or harvest flow change, or to add a new figure.
  Root-only (Claude Code).
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
| `pipeline-flow.drawio` → `.drawio.png` | Intro — the "in one minute" summary (the ASCII breakdown stays in The Pipeline) | The specialist pipeline as a vertical card spine inside four nested loop bands | the agent roster, loop model, routing, or handoff record types change |
| `harness-lifecycle.drawio` → `.drawio.png` | Distribution channels | One `/harness` source fanning into the three channels, with the harvest return path | a channel is added/removed, a script is renamed, plugin count changes, or harvest behaviour changes |

Each figure is committed as **two files**: the `.drawio` text source (diffable,
easy to edit) and the `.drawio.png` render with embedded XML (re-openable in
draw.io, referenced by the README).

## When to run

- After a `/harness` change that alters what a figure depicts (see the table's last column).
- When adding a new architecture figure to the README — author it in the house style below.
- These are documentation assets, not part of `check-sync`; freshness is a judgment check, like `history-update`.

## House style

**The two committed `.drawio` sources are the canonical exemplars of this style.**
When you regenerate a figure or add a new one, open them, reuse their exact
styles, and match them. The spec below documents what they already encode — it is
the written backup, not the source of truth. If the spec and a source ever
disagree, the source wins; fix the spec.

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
- **Each card answers two questions at two priorities.** Who (bold ink) and what it emits or does (muted). The muting sets the reading order — actors first, detail on demand. Shape encodes role: stadium pills for human entry and exit, the accent card for the orchestrator.
- **A figure is self-contained.** The title states the subject and the foot caption states the mechanism, so it reads correctly lifted out of the surrounding prose — the book-figure convention.

When extending the style, ask: does this stay editorial, keep color semantic, and let the composition carry the idea? If yes, it belongs.

### Palette

| Role | Hex |
|---|---|
| Accent (primary) | `#2F5D8A` · mid `#3B6FB0` · light text `#5E7BA6` |
| Ink (titles) | `#1F2933` |
| Muted (secondary text) | `#6B7280` · faint `#9AA5B1` |
| Card fill / border | `#FFFFFF` / `#C7CDD6` |
| Accent card (coordinator, source) | fill `#E1ECF7`, stroke `#2F5D8A` |
| Endpoint pill (start / end) | fill `#EEF0F2`, stroke `#B9C0C9`, `arcSize=40` (stadium) |
| Neutral card (e.g. consumer) | fill `#F1F3F5`, stroke `#B9C0C9`, `arcSize=10` |
| Channel header pill | fill `#2F5D8A`, white text, `arcSize=50` |
| Script chip | fill `#F3F4F6`, stroke `#D1D7DE`, text `#3B4252`, `arcSize=30`, `fontSize=10` |
| Nested bands (lightest outward) | inner `#E6EEF8`/`#AFC8E8` · middle `#EDF2FA`/`#C2D3EC` · outer `#F3F6FB`/`#CFDBEC` · arch `#F8FAFD`/`#DDE4EE`, all `dashed=1;dashPattern=8 5` |
| Connector | `#9AA5B1`, `strokeWidth=1.2`, `endArrow=block;endSize=6` |
| Accent return arrow (loop / harvest) | `#2F5D8A`, `strokeWidth=1.6`, `dashed=1;dashPattern=6 4` |

### Typography

| Element | Style |
|---|---|
| Figure title | `fontSize=17;fontStyle=1;fontColor=#1F2933`, centered |
| Subtitle | `fontSize=11;fontColor=#6B7280`, centered |
| Foot caption | `fontSize=9;fontStyle=2;fontColor=#9AA5B1`, centered |
| Band label | `fontSize=9;fontStyle=1;letterSpacing=1`, colored by depth (inner `#2F5D8A` → arch `#9AA5B1`), prefixed `↺` |
| Card | title in `&lt;b&gt;…&lt;/b&gt;`, secondary line in `&lt;font color="#6B7280"&gt;…&lt;/font&gt;` |

### Shape and layout rules

- **Cards**: `rounded=1;arcSize=8;whiteSpace=wrap;html=1;verticalAlign=middle;spacingLeft=8;spacingRight=8`. `whiteSpace=wrap` is mandatory — without it, text overruns the box.
- **One card width** per figure; consistent vertical rhythm; gaps of roughly 40px so edge labels sit cleanly between boxes (`labelBackgroundColor=#FFFFFF`).
- **Nested bands**: each band fully contains the next-inner band and its cards; place a band's label in the margin gap above its first card, not over a card.
- **Records / outputs** fold into the producing card as the muted secondary line (`→ prd-entry`), not as separate boxes.
- **Endpoints** (user, human) use the stadium pill; the orchestrator (coordinator, source) uses the accent card.
- No shadows. No XML comments. Escape `&amp;`, `&lt;`, `&gt;`, `&quot;` in values; every edge needs a child `&lt;mxGeometry relative="1" as="geometry"/&gt;`.

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
4. **Embed in the README** with a width-controlled, centered figure (a bare `![]()` renders the 2× file too large in previews):
   ```html
   <p align="center">
     <img src="docs/images/<name>.drawio.png" width="<W>" alt="<description>">
   </p>
   ```
   Portrait figures sit around `width="400"`, landscape around `width="720"`. Tune `W` so the IntelliJ and GitHub previews are not oversized. Keep descriptive alt text.

## Verification checklist

- No text overruns a box; every card has `whiteSpace=wrap` and fits its content.
- Text does not collide with arrows; edge labels carry a white knockout.
- Bands nest correctly and their labels sit in the gaps, not over cards.
- Palette and typography match the spec — one accent, muted secondary text, flat.
- The README `<img>` width still suits the figure's aspect; alt text describes it.
- Both files are present and in sync: re-export after any `.drawio` edit.

## What it reuses, and does not do

- **Reuses** the user-level `drawio` skill for draw.io XML and CLI mechanics; this skill owns only the house style, the figures, and their README placement.
- **Does not gate.** Figures are documentation, not deterministic artifacts — no `check-sync` step. Staleness is caught by judgment when the harness changes.
- **Does not auto-detect drift.** A PNG cannot be diffed against pipeline semantics; the redraw triggers in the figures table are the prompt to act.
