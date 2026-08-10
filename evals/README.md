# Harness Evals

Measures harness versions against one fixed subject project: the same tasks,
run per version, scored by frozen oracles. The claim this bench supports:
*harness version X differs from version Y on these tasks by this much, at this
cost*. It claims nothing about absolute model capability.

The tracked question is **cost per pass**: agent spend per bar-clearing rep.
Quality is a binary bar, not a variable — a rep either clears it or its
spend is pure waste. The claim to hold across versions, within one model
pin: cost per pass does not rise. The escalation rule under Cost
accounting defines when a shift is believed. A model change starts a new
row, never a silent continuation.

- Subject under test (SUT): [`woditschka/spring-petclinic`](https://github.com/woditschka/spring-petclinic),
  branch `agent-team`, harness installed on the marketplace channel.
- Results: committed run folders under `results/runs/`, one per agent run.
  [`results/TREND.md`](results/TREND.md) is the derived cross-version view.
- Runner: [`run_eval.py`](run_eval.py). Derived views (trend + run pages):
  [`summarize.py`](summarize.py).

## Measurement tiers

Metrics carry different evidential weight. The tiers never mix.

| Tier | Metrics | Verification | Carries claims? |
|------|---------|--------------|-----------------|
| A | Oracle pass/fail, suite green (against a pristine-tree baseline), build green, the refusal bar's src-change count (§ Refusal tasks), agent spend, judge spend, tokens, resolved model IDs, wall-clock | Machine-verified | Yes |
| B | Diff size, files touched as effort proxies (agent diff only — install writes sit below a baseline commit), handoff-ledger counts, per-agent wall spans, per-stage slices (the ledger is agent-authored) | Deterministic proxy | Context only |
| C | design-fit, test-quality, maintainability, doc-fit scores | Blind LLM judge, frozen rubric | Advisory only |

Tier C hardening: the judge sees the task, the `src/**` and `docs/**` patch,
and the project's principles read from the pre-agent baseline commit. The
patch strips provenance-marked lines. The judge runs from an empty directory
outside this repository, so no project context reaches it. It executes
through claude-dev when installed (confinement model:
[`tools/claude-dev/README.md`](../tools/claude-dev/README.md)); the container
shares the operator's read-only user-level `~/.claude` surface, while memory
and project state stay out. A settings file in the judge's session root pins
every installed plugin off — a plugin roster would name the harness the
judge stays blind to. Without claude-dev it falls back to the host CLI
under a fresh `CLAUDE_CONFIG_DIR`, which needs a one-time login. Residuals,
accepted because Tier C is advisory: the shared user-level surface above;
agent-authored doc prose carrying workflow vocabulary; doc-edit presence
correlating with the producing workflow; patch text trying to instruct the
judge. The prompt names the patch
untrusted; an over-long fence keeps it data. The rubric
([`judge/rubric-v1.md`](judge/rubric-v1.md)) and judge model are pinned;
`TREND.md` renders both under the medians, keyed to the judged rows each
provenance covers, so a change is a visible series break. Scores across a break never mix.
Superseded rubrics stay under `judge/` for the historical rows naming them. Judge facets never enter the quality bar: the
bar stays machine-verified, so the cost series never inherits judge noise. Each judgment takes the median of 3 samples. The
change-grader verdict is recorded as the system under test's self-assessment,
never as evidence. `TREND.md`'s Grader concordance table reports how that
self-assessment tracks the bar and the judge — the measured basis any
`auto_grade` default change must cite, cost alone never sufficing.

## Epochs

The SUT base commit is resolved from the **remote head** of the SUT branch at
sweep start; every workspace clones that commit. The base SHA is the *epoch*,
recorded in every manifest. `--offline` substitutes the local branch head; the
manifest records which resolution produced each run. Versions are swept once,
against the branch head of their sweep time, and are not re-run when the base
moves. The trend does not partition by epoch: a cross-version delta can
include SUT drift, and the manifests attribute it. Cell isolation moves the
same way: a run recorded before the operator-plugin pins carries no pin line
in its manifest `prep` array, and a delta spanning that boundary includes
the isolation change. `TREND.md` calls out a
record spanning several bases, several executing Claude Code versions, or
several settings-env prep conditions — a mechanical base line plus one
combined condition line; it never partitions by them. The resolved model IDs
(from the session transcripts) and the executing Claude Code version are
recorded per run the same way.

## Operator notes

`results/notes.toml` carries dated operator commentary — why a cell moved,
what a sweep was probing, where a defect path lives. `summarize.py` renders
each note into `TREND.md` beside the figures it discusses. An unscoped note
renders in the page header; a `task`-scoped note renders under that task's
table; a `task`+`version` note leads with its cell's version. Notes are a
derivation input like the run folders; figures never come from notes, and
`TREND.md` stays hand-edit-free. Note text follows the
[document-writing standards](../harness/core/.claude/skills/document-writing/documentation-standards.md);
the audit's docs lane reviews `notes.toml` like any root prose. Validation is
loud: a malformed entry, or a note naming a task or cell absent from the
tagged series on disk, aborts the render. See [ADR
2026-08-07](../docs/adr/2026-08-07-trend-operator-notes-and-condition-callouts.md).

## Version install path

The harness under test installs from a **pruned local marketplace source**
built per version: a tag build is a `git clone --branch <tag>` of this
repository, a dev build is a copy of the working tree. Local, so no network
fetch decides what a version label means; the source's own
`marketplace.json metadata.version` is attested against the label, and a
mismatch fails the cell loudly. Pruned: `evals/` is deleted from the source
before registration, so the marketplace clone inside the agent's read surface
carries no task prompt, no held-out oracle, and no recorded patch. The source
registers under the eval's own marketplace name (`agent-team-eval`); an
operator's real `agent-team` registration is never touched. The workspace's
committed marketplace declaration is rewritten to match — one source of truth
per run. The plugin id resolves per version against the source's own
`marketplace.json`: the configured id when offered, else the pre-v0.2.0
legacy spelling (`spring-boot-claude`), so old tags sweep with no config
change. The resolved id is recorded in each manifest; a source offering
neither spelling fails the sweep loudly.

In claude-dev mode the container shares the operator's user-level config, so
an operator-installed plugin would otherwise load into the agent session
beside the version under test. Prep pins every such plugin to `false` in each
workspace settings layer and records the pin count in the manifest. The pin
rests on documented settings precedence — project scope outranks user scope.
A post-install leak gate fails the cell when the executor's plugin listing
shows an enabled plugin that is neither the version under test nor pinned.
Stated blind spot: the listing reports registry-level enablement, so the gate
catches ids arriving after the pin pass, never a pin that failed to take.
Sweep teardown uninstalls the eval plugin and removes the eval marketplace
from a `finally`; each step swallows its own failure. An exception or
interrupt still reaches it; a killed process does not, and the next sweep's
prep re-registers cleanly.

## Confinement boundary

Confinement applies to the **agent turn**: with the default executor the agent
runs inside the claude-dev container with `--dangerously-skip-permissions`,
and no host directory is mounted read-write. Everything the agent leaves
behind is treated as untrusted. The measurement stages that follow observe
these rules:

- The run page's board renders from the copied ledger by this repository's
  own current renderer (`summarize.py`) — agent-written script files never
  execute on the host.
- The live view reads the agent's handoff ledger during the turn and prints
  it to the operator terminal. Every non-printable character renders escaped,
  lines and per-poll volume are capped, and the tail stops at the ledger size
  cap. Display only — no recorded artifact reads from it.
- Patch collection runs git with hooks, fsmonitor, external diff, and textconv
  disabled.
- Gradle is the deliberate exception: measuring the agent's change requires
  running its build, including agent-authored build scripts, on the host. Each
  cell builds in a throwaway `GRADLE_USER_HOME` copied from a seed that only
  pristine-tree builds ever write, so a poisoned cache cannot reach the
  operator's `~/.gradle` or a later cell. The residual exposure — the build
  scripts themselves execute host-side — is accepted and stated here.
- Plugin registration runs on the host CLI before the agent starts, from the
  runner-owned pruned source; in claude-dev mode the container shares that
  plugin state read-only. The pruned source itself is mounted read-only into
  the container — without it the plugin fails to load there. The mount widens
  the agent's read surface by exactly the pruned source; the pruning above
  keeps that surface free of task material.
- The egress allow-list carries `github.com` for the Gradle wrapper's
  distribution chain, and this repository is public. An agent that goes
  looking can therefore fetch the oracles over the network — the pruning
  above cleans the mounted surface, not the wire. Accepted residual: the
  harness under test carries no pointer here, and each run preserves the
  proxy's per-request access records as `egress.log`, where such a fetch
  would show.

Host mode (`--exec host`, or auto without claude-dev installed) runs the agent
unconfined; the runner prints a notice, and `--dangerously-skip-permissions`
requires the explicit `--skip-permissions` flag there.

## Run lifecycle

One cell = version x task x repetition. A multi-version sweep interleaves
its arms (§ Cost accounting and statistical discipline). Per cell,
unattended:

1. Workspace: standalone clone of the SUT at the epoch commit.
2. Harness install: operator-plugin pins into the workspace settings, then
   marketplace registration from the pruned source (host CLI; in host mode
   into a fresh per-cell `CLAUDE_CONFIG_DIR`), then version attestation.
   Next the enablement and leak gates: `claude plugin list --json` through
   the same executor, cwd, env, and mounts as the agent turn. The cell fails
   at prep unless the plugin reports enabled at the expected version with no
   unpinned plugin beside it — never a silent harness-less or mixed-roster
   run. Then the engine sliver via the source's
   `setup.sh` (gated on `scripts/handoff.py` landing), and a baseline commit
   of the installed state.
3. Suite baseline: the full existing suite on the pristine tree
   (`suite_green_base`), so a post-run suite failure is attributable.
   `--no-baseline` skips it.
4. Agent run: `claude -p "<task prompt>" --output-format json`, headless,
   through the executor above. Only a zero exit with a success subtype records
   as `complete`; error subtypes record as `agent-error`. A stalled or crashed
   cell records as such and the sweep continues. While the agent runs, the
   runner tails the workspace handoff ledger and prints one line per new
   record — elapsed time, author, record type, key detail. Every
   non-printable character renders escaped, lines truncate, and the tail
   stops at collection's ledger size cap.
5. Measurement: cost and turns from the result JSON. Per-agent tokens,
   dollars, wall spans, and resolved model IDs come from the session
   transcripts via the canonical `tools/harness-stats/accounting.py` — one
   engine for every version, so cost math stays comparable. A timed-out or
   crashed run recovers its spend from the same transcripts. Per-stage cost
   and wall slices window those rows by the handoff ledger's record
   timestamps; every ledger field is the agent's own claim. Agent and stage
   spans overlap under concurrency — display figures, never a sum. Handoff
   ledger copied out; the agent diff saved as a patch against the baseline
   commit. Collection steps are individually best-effort — a collection
   failure never voids the paid measurement.
6. Oracle: full suite, then the held-out oracle classes, in the cell's
   throwaway gradle home. A refusal task has no oracle classes; its bar
   reads the recorded diff (§ Refusal tasks).
7. Optional `--judge`: the Tier C judgment on the sanitized patch. A
   refusal task is never judged (§ Refusal tasks). A sweep
   that skipped it can be judged later: `--judge-runs` grades every recorded
   run missing a verdict from its committed patch and manifest, with no
   agent runs. The briefs then read from the SUT clone at the epoch commit —
   the workspace's baseline commit is gone — and the verdict lands in
   `result.json` marked `post_hoc`. A verdict recorded without parsable
   samples re-judges on the next `--judge-runs`.

Raw transcripts stay local under the gitignored `.runs/`; the committed folder
carries the derived figures. Rationale: reproducibility comes from the published
method, pinned inputs, and readable patches, not from editable log bulk.

## Run folder contract

```
results/runs/<version>/<date>-<task>-r<N>/
├── README.md         # generated presentation of the run: verdict, figures,
│                     # agent roster, embedded diff and board, prompt, artifact
│                     # links (a derived view, like TREND.md — summarize.py
│                     # regenerates it; never hand-edit)
├── manifest.json     # written before the run: coordinates, prompt, task
│                     # fingerprint, prep steps, model, CC version
├── run.log           # prep, gradle, and diagnostic tails (escape-sanitized)
├── handoff.jsonl     # the pipeline's actual path (absent if no pipeline ran);
│                     # the page's board renders from this, never a stored copy
├── agent-costs.json  # per-agent tokens, dollars, wall spans, resolved model
│                     # IDs, and per-stage slices windowed by the handoff
│                     # ledger (absent when no transcript was found)
├── change.patch      # the agent's diff against the baseline commit
├── egress.log        # the proxy's per-request access records (claude-dev mode)
└── result.json       # status, oracle outcomes, cost, wall-clock, judge scores
```

Rep numbering continues from what exists on disk: re-invoking a cell adds
`-r2`, `-r3` beside it and never overwrites.

Committed folders carry no host identity. The runner's own writes pass a
scrub: scratch, repo, and home prefixes become `<scratch>`, `<repo>`, `~`,
and the login name becomes `<user>`. Session ids and transcript filenames are
never persisted. The run log's plugin listing is reduced to the version under
test, and host-side gradle runs stamp UTC. Agent-authored artifacts
(`change.patch`, `handoff.jsonl`) are covered by the gate
instead: `leak_scan` re-reads every artifact after collection. A hit sets the
run's status to `leak` — it never counts as a clearing rep — and quarantines
the folder under the gitignored `.runs/`, so it cannot be committed.
`run_eval.py --leak-scan` re-checks every committed folder; the battery runs
it. Raw transcripts for a committed run stay local under
`.runs/transcripts/<version>/<run>/`.

One exemption keeps the timestamp check honest: a commit's author offset is
stored in the commit object, so `git log` renders it whatever the host zone
is — `TZ=UTC` cannot normalize it. An agent quoting a commit date therefore
emits public repository data, not the host clock, and the SUT's history
carries offsets from many upstream contributors. The runner collects the
SUT's own offsets while the workspace clone exists and exempts exactly those;
every other non-UTC stamp still fails the folder. A run records the offsets
it actually quoted in `result.json` as `sut_quoted_stamps`, so the offline
`--leak-scan` applies the same exemption without a clone to hand. This
withholds nothing: `TREND.md` publishes the SUT repo, every committed
manifest records the base SHA, and so the same offsets are readable from the
remote.

## Oracle contract

Each task in [`tasks/`](tasks/) carries a prompt (the frozen contract given
to the agent) and — every kind but refusal (§ Refusal tasks) — a held-out
JUnit oracle the agent is never handed: oracles live
only in `evals/`, which the pruned marketplace source excludes. The network
path to them is a stated residual — see § Confinement boundary. Oracles follow the
SUT's testing principles: real seeded data, no mock frameworks, behavior-named
tests. Every oracle asserts only what its prompt pins, and declares its
validity partition in `task.toml`:

- `base_green`: control tests that pass on the untouched base — proof the
  oracle wiring works.
- `base_red`: task tests that fail on the untouched base — proof they measure
  the change.

`run_eval.py --oracle-check` verifies both properties against the current
epoch at zero token cost. Run it after every base update.

A frozen prompt must be answerable unattended: a run has no human, so a
prompt that leaves a product choice open measures the model's willingness to
ask, not the harness. Before freezing, sweep the prompt for choices an agent
could plausibly surface — visible entry points and controls, new user-facing
copy and its translation cost, error presentation, any work the held-out
oracle does not test. Decide each inline as a product decision, and close
the remainder with a standing clause: no further product answer will come;
take the narrowest reading and record open questions rather than waiting.
Refusal prompts never carry that clause — ending without an answer is the
outcome they measure.

Task identity is frozen and machine-visible: the manifest records a
`fingerprint` (hash of prompt plus oracle bytes; a refusal task's hashes the
prompt alone), so any edit to a task shows
as a fingerprint change in the recorded series. An edit that changes the
oracle, or the behavior the prompt pins, creates a new task id
(`visit-edit-2`); the trend never mixes those identities. A clarifying
prompt edit that leaves the oracle bytes unchanged keeps its id: the task's
trend section calls out the fingerprint span, and a dated note records what
changed. When no
recorded run of the task remains — a fully discarded sweep — the id may stay.

## Checkpoints

The bar is one bit per rep, and a rep costs dollars. Below-bar reps must
still carry information, so every rep gets a graded checkpoint ladder,
derived from facts the run already records — zero added token cost.

| Kind | Ladder, in order |
|------|------------------|
| bugfix, feature | agent complete · change produced · suite green · one step per held-out oracle test |
| refusal | agent complete · no `src/` change · suite green · consultation-request recorded |

Every step reads machine-collected facts (Tier A) except the refusal
ladder's consultation step, which reads the agent-authored ledger (Tier B).
Checkpoints never enter the bar or
cost per pass. They attribute how far a below-bar rep got — "reached the
suite, failed two oracle tests" — where the bar alone says "failed"; the
consultation step also marks what a clearing refusal rep can still miss.
`TREND.md` fills a row's `Ckpt` cell with each rep's count whenever a rep
missed one; each run page shows its rep's count. `summarize.py` derives the ladder at
render time from recorded facts — the runner adds only two primitives, the
src-change and consultation counts — so runs recorded before this machinery
gain the figure retroactively. A missing fact reads as not-hit, fail-closed.

A completed run can end with the pipeline still owing work: the session
stops while the workspace's `handoff.py route` still names a dispatch. The
runner records that post-session decision in `result.json`, and the
rendered views label such reps *stalled*. Runs recorded before the field
are read from the copied ledger — a non-empty ledger with no implementer
terminal record — which leaves mid-review stalls on old records unlabeled
rather than guessed. The label attributes the failure shape; the bar never
excuses it.

## Refusal tasks

A harness that implements whatever it is told looks identical, on green
tests, to one that knows when to stop. Refusal tasks measure the stopping.
The prompt asks for work conflicting with a non-goal recorded in the SUT's
briefs and states no owner override. The pipeline's designed path is a
consultation-request; a headless run has no human to answer it, so a correct
run ends without a change.

- Bar, fail-closed: status `complete`, suite green, zero changed files under
  `src/`. Implementing the declined scope — green tests included — fails.
- The src count is collected tamper-resistant: git runs with hooks,
  fsmonitor, and external drivers disabled; `src/` stages with `--force`, so
  an agent-edited ignore file hides nothing; the numstat parses in its `-z`
  form, so no crafted file name dodges the `src/` prefix; a rename counts on
  either side. Stated residual: a build-file edit registering a source set
  outside `src/` shows only as a non-src change — visible in the patch,
  invisible to the count.
- Tier note: the diff row sits in Tier B as an effort *proxy*. The refusal
  bar and the ladder's change-produced step read the same numbers as direct
  facts — whether and where the tree changed — collected as above. Those
  facts are machine-verified, so the bar stays Tier A (the tier table's
  Tier A row names them).
- The consultation-request count is the ladder's Tier B checkpoint. It
  separates "consulted and stopped" from "did nothing"; being the agent's
  own claim, it stays advisory.
- The Tier C judge skips refusal runs, in-sweep and post-hoc: the rubric
  grades a change, and the correct outcome has none. An implementing
  refusal run records its failure through the bar, never through facet
  scores.
- No held-out oracle: `kind = "refusal"` carries no `[[oracle]]` table, the
  fingerprint hashes the prompt alone, and `--oracle-check` reports nothing
  to validate.
- Validity rests on the conflict being real: the non-goal must stand in the
  SUT's `docs/prd.md` at the epoch, unaddressed by the prompt. A prompt
  defensible both ways measures ambiguity, not judgment.
- Both failure shapes are honest verdicts: implementing anyway (a diff), and
  looping until timeout awaiting an answer (pure waste).
- `visit-cancel` conflicts with recorded NG-4 and NG-5. `visit-edit` is its
  counterpart with the override stated, so the pair separates "refuses
  conflicts" from "refuses everything".

## Cost accounting and statistical discipline

- The quality bar is binary: status `complete`, oracle all-pass, suite green.
  A red pristine baseline gets no waiver — the bar stays unreachable until
  the SUT base is fixed, and `suite_green_base` attributes it.
- The headline metric is **cost per pass**: delivery spend per bar-clearing
  rep. Numerator: the cell's delivery spend, clearing and wasted reps alike.
  Denominator: the count of clearing reps. A rep below the bar is wasted
  spend — charged in full, contributing nothing. A cell with no clearing rep
  reports pure waste, never a unit cost.
- A rep whose spend no source recorded renders its figures as lower bounds
  (`>=`), never as zero. The transcript-derived figure covers a run whose
  result JSON never arrived.
- Spend that is not the change is excluded from the metric. The Tier C
  judge's cost reports in the `Judge spend` column, never inside cost per
  pass; an arm the judge never ran on renders `—`, not zero. The change
  grader's share — optional support for the human merge decision — nets out
  of spend and wall, reported in the `Grading spend` column, so Agent spend
  plus Grading spend approximates the whole-sweep figure. The spend netting is
  proportional: the grader's fraction of the accounted total, applied to the
  run's reported spend — the self-report and the accounting price a run
  differently, so a cross-basis subtraction would over-net. This netting is
  the one sanctioned Tier B input to a Tier A cell, and it is gated: a cell
  nets only when the ledger's `grader-verdict` record backs an accounted
  grader row; a run without both stays whole-run. The wall netting subtracts
  the grader's transcript span directly — the grader is the serial terminal
  hop, so the overlap caveat on per-agent spans does not apply. The spend
  columns price one sweep: each task cell contributes its mean spend per rep,
  failures included, summed across the row's tasks. Oracle and suite runs
  cost no tokens.
- Trend rows key on (version, requested model pin). The Models column
  lists the IDs the pipeline actually resolved — the pin binds only the
  root agent. The pin renders beside the version only when rows differ
  on it. Comparisons hold between rows sharing a pin.
- Default one rep per cell; the trend's `Bar` cell displays `cleared/reps`,
  so reps that disagree on the bar stay visible in the fraction — never a
  best-of-n headline.
- Escalation rule, applied by the operator between two cells sharing pin
  and task. Triggers: a bar-verdict flip, a cost-per-pass move over 30%, or
  a cell losing its unit cost. Consequence: re-run twice more before the
  change is believed. The trend's `Escalation check` section and the
  sweep's terminal tail run the arithmetic over adjacent version rows. A
  tripped pair lists, with its follow-up command, until both cells hold
  three reps. The queue clears in full: pairs between superseded versions
  and on refusal tasks included, never dropped as merely historical — the
  recorded series keeps its depth everywhere a trigger fired. Pairs list
  most severe first: a lost unit cost, then a
  bar-verdict flip, then cost rises, then falls, larger moves first.
- Reps are independent draws: the API offers no seed, so no run pairs with
  another. Pass rates compare per task, within one pin, as independent
  binomials; paired tests have no variance advantage here.
- Sample-size honesty: the pass-rate margin at k reps is roughly 1/√k —
  ±30 points at k=10. Affordable rep counts make pass rates indicative,
  never powered; the escalation rule, not a significance test, decides when
  a shift is believed.
- Resolution is bought where it is cheap: more tasks, and more checkpoints
  per rep (§ Checkpoints) — not more reps. A rep costs dollars; a
  checkpoint costs none.
- A multi-version sweep interleaves its arms — rep-major, then task, then
  version — so versions under comparison run adjacent in time. Provider
  drift across the sweep lands evenly on every arm, never on the arm swept
  last.
- Every run launched since the series start (next bullet) persists,
  including failures and timeouts. There is no
  mechanism to discard a result. Three exceptions, all applied before push:
  a run whose cell never engaged the harness under test (an infrastructure
  defect, not a measurement), a run of a task later shown defective —
  a prompt contradicting the SUT's briefs measures the task, not the
  harness — and a run whose artifacts leak host identity (quarantined by
  the gate, or purged where recorded before the gate existed). The
  prep-time enablement gate makes the first kind fail loudly.
- The recorded series starts 2026-08-03, with the stabilized instrument:
  checkpoints, the refusal kind, interleaved sweeps, five tasks. Shakedown
  runs recorded before that were archived to the local `.runs/`, out of the
  published series — a one-time reset, spent before the first push. From
  the first push on, only the three exceptions above discard anything.
- No composite score. `TREND.md` reports disaggregated metrics per tier.

## Known limitations

- Five tasks: indicative, not statistically powered. Task count, not rep
  count, is the binding constraint on every claim here.
- The SUT is public training data. Constant across arms, therefore neutral for
  version-to-version deltas; still stated.
- Tasks and oracles are authored by the harness maintainer. Mitigations:
  frozen fingerprints, published oracles, machine-checked validity partitions.
- The oracle runs inside the agent's build: an agent that edits build files
  or test configuration shapes the environment its oracle runs in. The
  measurement stage restores the gradle wrapper from the baseline commit and
  deletes pre-existing test reports first. Deeper shaping — build logic that
  skips or fakes tests — stays possible and visible in the committed patch;
  nothing blocks it.
- One SUT, one stack. Findings transfer to other stacks only as hypotheses.

## Usage

```bash
python3 evals/run_eval.py --oracle-check                 # free validity check
python3 evals/run_eval.py --version v0.2.0               # one version, all tasks
python3 evals/run_eval.py --version dev --task visit-edit --reps 2
python3 evals/run_eval.py --judge-runs                   # judge recorded runs post-hoc
python3 evals/summarize.py                               # regenerate the derived views
```

A version comparison runs both arms in one invocation — not because that
makes the numbers rigorous, but because it removes two avoidable confounds:

```bash
python3 evals/run_eval.py --oracle-check                 # free; after any base move
python3 evals/run_eval.py --version v0.2.0 --version dev --judge # both arms, one call
# Escalation triggered on one cell: two more reps, both arms again.
python3 evals/run_eval.py --version v0.2.0 --version dev --task visit-edit --reps 2 --judge
```

The comparison arms carry `--judge`: the binary bar cannot see a quality
regression that keeps the pass rate, and every in-folder quality signal is
authored by the pipeline under test. The Tier C facet delta between judged
rows is the one independent quality comparison the bench records — worth its
spend on a comparison, and worthless on a lone smoke run.

Why one call: the sweep resolves a single epoch and interleaves the cells
(§ Cost accounting and statistical discipline owns the rationale). Two
separate calls lose both properties — each resolves its own epoch, and the
arms run blocked, so provider drift lands on the later one. The pin stays
in `config.toml`, identical for both arms. None of this buys statistical
power; it only ensures that what little the numbers say is about the
harness, not about when each arm ran.

Cross-model comparison: sweep the versions under comparison once per model
pin (`[run] model` in `config.toml`). Each pin forms its own row set in
`TREND.md`; the harness effect is the within-pin delta between versions.

`--version dev` builds the marketplace source from this repository's working
tree and labels results `dev-<short-sha>[-dirty]`. An escalation pair with a
dev arm settles only while the tree still resolves to that label; a moved
tree opens a new row instead of adding reps. Precondition: the generated
`plugins/` tree is current (`harness/propagate-harness.sh`, gated by the
battery). Where a dev sweep sits in a release: the maintainer loop in the
root `CLAUDE.md` — the canonical statement, never restated here.

Dev results are local-only. A dev row measures an untagged working tree, so
a committed row would name code no tag can reproduce. `results/runs/dev-*/`
and `results/TREND-dev.md` are gitignored, and the battery fails if either
is ever tracked. The committed `TREND.md` carries the tagged series only;
while any dev run folder is on disk, `summarize.py` renders the full table —
dev rows beside the tagged rows, same format — to `results/TREND-dev.md`,
the view release prep reads. Deleting the local dev folders retires the file
on the next render.

## Adding a task

1. Create `tasks/<id>/task.toml` (id, kind, title, prompt, oracle table) and
   the oracle class under `tasks/<id>/oracle/`. A refusal task carries no
   oracle table (§ Refusal tasks); the loader enforces both directions.
2. The prompt pins the contract (URLs, parameter names, expected statuses,
   any template or model-attribute name the oracle asserts); the oracle
   asserts only what the prompt pins.
3. Check the prompt against the SUT branch's `docs/prd.md`. A task touching a
   recorded non-goal or a withdrawn requirement must state the owner's
   override in the prompt. A headless run has no human to answer a
   consultation, so an unstated conflict ends the run without a diff. A
   refusal task inverts this rule: it leaves the conflict
   unstated to measure that consultation.
4. Declare the `base_green`/`base_red` partition; prove it with
   `run_eval.py --oracle-check --task <id>`. A refusal task skips this step.
5. Commit before the first sweep that uses it.
