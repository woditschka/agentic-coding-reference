# Deck

The conference deck for the reference: one slide source, two variants, and a landing page linking each. The talk runs 40 minutes; the lightning talk runs 2 to 5 minutes. GitHub Pages serves the directory from `main:/docs`. Offline, every page runs from a clone: open `docs/deck/index.html`.

| File | Role | Edited by |
|------|------|-----------|
| `index.html` | Landing page: one card per version, presenter keys | hand |
| `slides.html` | All slides; `data-variants` places a slide in the talk, the lightning talk, or both | hand |
| `deck.css` | Fonts, the default look's color variables, and the layout every look shares | hand |
| `deck.js` | Variant filter, demo slots, key hand-off to the player | hand |
| `casts/*.cast` | Demo recordings, asciicast format | recorder or `deck.py ledger-cast` |
| `casts/casts.js` | Every cast inlined, so `file://` needs no fetch | generated |
| `qr-code.svg` | Scan code to the repository, on the closing slide | generated once (§ Scan code) |
| `vendor/` | reveal.js 6.0.2 (MIT), asciinema-player 3.17.0 (Apache-2.0), Inter 5.3.0 and JetBrains Mono 5.3.0 (SIL OFL 1.1, Fontsource builds), the Catppuccin palette license (MIT) | upstream release files |

## Addresses

| Version | Query |
|---------|-------|
| Talk, recorded demos | `slides.html?v=talk` |
| Talk, live demos | `slides.html?v=talk&demo=live` |
| Lightning | `slides.html?v=lightning` |
| Lightning, unattended loop | `slides.html?v=lightning&auto=1` |

`&theme=<name>` picks a look other than the default (§ Looks). A slide's `id` extends any address to that slide: `slides.html?v=talk#/demo`.

## Presenting

A demo slot is a `<div class="term">` naming its cast in `data-cast` and its live terminal in `data-live`. On a demo slide, the next key plays the recording, or skips to its next marker while it plays. After the recording ends, the next key advances the slide. `L` switches the slot between live and recorded. `S` opens the speaker view with notes and the variant's time budget.

Live mode embeds a terminal served by [ttyd](https://github.com/tsl0922/ttyd) on the presenting machine. A slot whose terminal does not answer within 2.5 seconds plays its recording and shows a red badge. Run live talks from the local clone: an HTTPS page embedding `http://localhost` depends on each browser's mixed-content rules.

1. Prepare the demo repository at the state the talk starts from.
2. Start the terminal: `ttyd -p 7681 -i 127.0.0.1 -W zsh`.
3. Open `docs/deck/slides.html?v=talk&demo=live` from the clone.

## Recording a demo

The committed casts are ledger replays of committed eval runs, stand-ins until a session recording replaces each. A recording is a fresh interactive run of the same eval task. Commit its run folder beside the cast, so the slide's figures link the run shown.

1. Record at the slot's terminal size: `asciinema rec --cols 90 --rows 24 --idle-time-limit 2 casts/<name>.cast`.
2. Cut the Claude Code welcome banner, and scrub home paths, email addresses, and account or organization names.
3. Add a marker event, `[<seconds>, "m", "<label>"]`, at each pause point.
4. Rebuild the generated files.

To regenerate a stand-in from a committed run: `tools/deck/deck.py ledger-cast evals/results/runs/<version>/<run> docs/deck/casts/<name>.cast`.

## Looks

The default look, `paper`, is a light editorial page with a dark terminal. Every color is a variable on `:root` in `deck.css`; the layout reads only the variables. `?theme=<name>` sets `data-theme="<name>"` on the page root, and a name without a stylesheet shows the default.

To add a look, for example a conference's:

1. Create `themes/<name>.css`, overriding the variables under `:root[data-theme="<name>"]`, plus any rules scoped to that selector.
2. Link it after `deck.css` in `slides.html` and `index.html`.
3. Open any address with `&theme=<name>`; the landing page passes the parameter into its deck links.
4. Commit a conference-supplied asset only under the conference's terms, and credit it on the closing slide.

## Scan code

`qr-code.svg` on the closing slide encodes `https://github.com/woditschka/agentic-coding-reference`, the address printed beside it, at error-correction level M. The repository README links the deck, so one scan reaches both. The file is static, generated once with the qrcode-generator npm package (MIT) and checked by decoding it with jsQR; neither package ships with the deck. Regenerate it only when the address changes; the file's comment names the address it encodes.

## Building

`tools/deck/deck.py build` regenerates `casts/casts.js` after any change to a cast. `tools/deck/deck.py build --check` lists a stale bundle and exits non-zero, writing nothing.

## Exporting a PDF

A conference that asks for a PDF gets one from the browser: open `slides.html?v=talk&print-pdf` in Chrome and print to PDF. A demo slide prints as its terminal frame only; the recording plays only in the browser.

## Publishing

GitHub Pages serves this directory at `https://woditschka.github.io/agentic-coding-reference/deck/` once the repository's Pages source is set to *Deploy from a branch*, `main`, `/docs`. `docs/.nojekyll` makes Pages serve the files as they are, without a Jekyll build, and `docs/index.html` sends the site root to the deck. Pages publishes all of `docs/`; every file there is already public in the repository.

## Rights

The layout is original; the palettes and fonts are licensed as listed under `vendor/`; the figures are this repository's own. Every font is a file in this directory, so no page contacts a font service. The one outside request is the about slide's portrait, loaded from the GitHub avatar service without a referrer so the repository carries no copy; the slide shows initials when it fails. Product names identify the tools the harness targets, without logos. The closing slide and the landing page state non-affiliation and credit every third-party component. A new asset enters only with its license in hand and its credit on the closing slide.
