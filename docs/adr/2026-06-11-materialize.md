# Materialize Is a Complete Replacement Run From the Root

**Status:** Accepted

## Context

Each sample once carried its own `seed` and `harvest` skills, about 90% identical, so every harness change landed twice and shared bugs twice: neither copy seeded `scripts/`. `/seed` resolved to whichever sample's skill a session found first; a Go target picked up the Java skill until the user noticed.

The install itself was additive. A rename or move in the harness left the old file behind as an orphan, invisible on a gitignored-runtime channel because the doctor's channel check sees only tracked files. Orphan classification was per-file judgment over `git log`, degraded to ask-the-user when the source was a plugin without history. The marketplace setup skill accreted hand-written delete lists, 16 files across two upgrade notes by v0.3.6. The install wrote every file unconditionally, so the overwrite blast radius was computed nowhere, and two producer scripts parsed `layout.toml` with disagreeing grammars.

Consumer builds were wired to the harness's own test suites: three Gradle `Exec` tasks, a `make` target, the quality-gate text, and the init skeleton. Adding one module missed two of five surfaces, and a harness self-test could block unrelated feature work mid-slice. When verification moved to install time, `unittest discover` over the target's tree executed pre-existing project Python that merely sat under the discovery directory.

## Options Considered

1. **Keep per-sample seed/harvest, fix bugs in both.** Rejected: double maintenance and the wrong-template hazard stay.
2. **A thin root dispatcher over the sample skills.** Rejected: fixes invocation, keeps the duplication.
3. **Additive copy plus a separate prune command.** Rejected: the second command is forgotten and orphans persist by default.
4. **A stored install manifest or persisted plan.** Rejected: a new gitignored artifact to maintain; the source tree on disk is the authoritative unit set.
5. **Per-release retirement delta files.** Rejected: a consumer skipping versions needs the union; one cumulative file gives it by construction.
6. **Consumer-side git archaeology against the plugin.** Rejected: plugins carry no history.
7. **A full load → validate → plan → apply → verify lifecycle with a transaction engine.** Rejected: four phases already exist as functions; git is the recovery layer.
8. **Gate the consumer-build suite roster with a parity check.** Rejected: it hardens a coupling that should not exist.
9. **Drop runtime verification entirely.** Rejected: a partial copy or host-python incompatibility would surface mid-pipeline.
10. **Keep `unittest discover` and correct the skill prose.** Rejected: an installer kept executing unrelated project code.
11. **Root-owned `init`/`materialize`/`harvest` with stack auto-detection, complete replacement, mechanical retirements, a transient plan, and exact-module verification.** Chosen.

## Decision

**One root-owned `/materialize` makes a consumer's runtime equal the current harness: detect the stack, replace the runtime, classify extras by set arithmetic, preview before writing, verify the installed suites.**

- **Root owns onboarding.** `init`, `materialize`, and `harvest` live only in the root `.claude/skills/`; the samples carry none. The stack comes from the build marker: `go.mod` is Go, `pom.xml` or `build.gradle` is Spring Boot, otherwise generic.
- **The script installs and reports; the skill decides.** `harness/materialize.py <stack> <target>` copies `core ∪ stacks/<stack>` into the surfaces the project declares in `[harness] tools`. It then lists extras under the harness-owned directories between machine-readable markers. It never deletes. It refreshes the managed chapters, the gitignore block, and the settings keys, and respects the declared channel; it never flips it.
- **Extras classify mechanically first.** `harness/retired-paths.txt` records every consumer-relative runtime path the harness once produced and no longer does. `retired_paths.py update` appends the produced-set difference, and `release-version.sh` runs it before every propagate. Classification is present − produced − extensions − retired. The script annotates covered extras `[retired]`; the skill removes them, `rm` under manifest and a scoped `git rm` under copy. The battery gates both directions: a path the last `v*` tag produced that is gone without an entry fails, and an entry the source produces again fails. Judgment over harness history, asking when unsure and defaulting to keep, remains only for paths the manifest predates. A confirmed keep is recorded in `[harness] extensions`.
- **Marketplace removal is bounded.** The bundled `prune-retired.py` deletes only inside the engine-sliver namespaces (`registry.ENGINE_SLIVER`), never under `.claude/agents/`, and only paths resolving inside the target, symlinks skipped. Currently-produced paths and declared extensions win, an unparseable `layout.toml` prunes nothing, and a pruner failure never aborts the install.
- **The plan is transient.** `--dry-run` (alias `--show-plan`) runs read → resolve → a stat-only pass over the same install stream. It prints created, overwritten, excluded-by-channel, extras preserved, and managed chapters to rewrite, then returns before any write. Extras print as candidates, never "will delete". One producer-side reader (`read_layout`) interprets the `[harness]` table with tomllib semantics matching the doctor's; it never ships in `core/scripts/` and never absorbs the consumer-side doctor.
- **Verification runs once, at install.** `verify_runtime` converts each installed `scripts/**/test_*.py` to its dotted module name. It purges `__pycache__`, then runs one `python -E -B -m unittest -- <modules...>` from the scripts dir; `setup.sh` does the same over the engine sliver. The suite list derives from the install's own file set, never a target-tree glob, so a project-authored test file is never run as a suite. An empty module list never reaches `unittest`, since an argument-less call is `discover`. The guard covers the list, not the import surface: installers point only at trusted trees, and failure tails print with control characters stripped. A zero-tests result fails unless every suite skipped by channel key. `--no-verify` exists for harness-internal callers whose battery runs the same suites. Project builds verify project code only; `scripts/handoff.py validate` stays in the project gate because it checks project data.
- **Project-owned files change only through the consented tiers** recorded in the harness–project API decision.

## Consequences

**Positive:**
- One skill file per direction; a re-materialize is idempotent and self-healing after renames.
- The plugin channel's ask-mode disappears for listed paths, and the hand delete lists are gone; a forgotten retirement fails at tier 0.
- The overwrite blast radius is legible before the write on channels with no `git diff`.
- A harness suite change touches only `/harness`, and a self-test failure surfaces at install, not mid-slice.

**Negative:**
- The complete-replacement guarantee lives in the skill, not the raw script.
- A mid-cycle clone sees a rename one release before the manifest carries it. A path one stack retires while another ships never enters the manifest. Both fall to the judgment path.
- Strict battery runs need reachable `v*` tags.
- The preview exists only where `materialize.py` runs; the plugin's `setup.sh` still overwrites unconditionally.
- A host python upgraded between materializations is exercised only on first pipeline use.
- A target-authored module the install did not produce, including one shadowing a stdlib name, still executes on import during verification.
- A stale suite outside the engine sliver on the marketplace channel is left inert rather than removed.

## Implementation

`harness/materialize.py` (`read_layout`, `plan_install`, `verify_runtime`, `record_extension`), `harness/init.py`, `harness/retired-paths.txt` with `harness/retired_paths.py`, `harness/release-version.sh`, `harness/verify_harness/checks/sync.py` (the retired-paths step), `harness/marketplace/setup.sh` and `prune-retired.py`, `harness/package-marketplace.py`, the root `materialize`, `init`, and `harvest` skills, and the suites under `harness/tests/`.

## References

- [2026-06-12-docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md) — the project-owned/runtime boundary this install enforces, and the `tools` and `extensions` declarations it reads
- [2026-06-14-distribution-channels](2026-06-14-distribution-channels.md) — copy, manifest, and marketplace: the channel decides how a confirmed orphan is removed
- [2026-06-14-the-doctor](2026-06-14-the-doctor.md) — the validation every materialize ends with
- [2026-06-14-layout-declares-the-project](2026-06-14-layout-declares-the-project.md) — the `[harness]` table the shared reader interprets
- [2026-07-17-module-derivation](2026-07-17-module-derivation.md) — the shipped package layout whose import needs named-module verification serves
- [2026-06-03-principles-over-rigid-rules](2026-06-03-principles-over-rigid-rules.md) — the boundary the retired-paths manifest applies: a mechanical promise belongs in an engine, not in prose recall
- [2026-07-12-resilience-first-improvement-doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — why the full lifecycle was rejected as reshuffle and the shared reader accepted on merit
- [`harness/README.md`](../../harness/README.md) — the maintainer scripts and their flags
