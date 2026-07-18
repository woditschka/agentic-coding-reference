# One Layout Reader; Materialize Previews a Transient Plan

**Status:** Accepted

## Context

Two producer scripts interpret `scripts/layout.toml` independently. `read_layout` validates channel and tools (`materialize.py:86-142`); `init.py:197-214` reimplements a channel-only subset, and the channel-enum check is written a third time on the CLI arg (`init.py:156-161`). Extensions are parsed by two disagreeing grammars: `init.py:116-121` is un-anchored with a quote-scan, `materialize.py:361-369` is anchored with a comma-split. A valid multi-line TOML array — which the doctor's tomllib read accepts — returns `[]` in init and errors in materialize. No test gates the two grammars against each other.

Separately, `install()` copies each file unconditionally — no `dest.exists()` check (`materialize.py:184-186`). So the create-versus-overwrite blast radius is computed nowhere, and the first thing a consumer sees is output from an install that already replaced the runtime. On the copy channel the overwrite lands as a reviewable `git diff`; on the manifest and marketplace channels the runtime is gitignored, so no diff exists before or after.

A generic proposal argued for a full `load → validate → plan → apply → verify` lifecycle plus a transaction engine. A resilience-first review found four of the five phases already exist as named functions.

## Options Considered

1. **Full lifecycle with a `Plan` dataclass threaded through five phases.** Rejected: `read_layout` (load+validate), `install` (apply), and `verify_runtime` (verify) already exist; formalizing them moves no rule up an enforcement tier — reshuffle, not enforcement — and adds a type a consumer never sees.
2. **Transaction/rollback engine.** Rejected: git is the recovery layer; a staging layer maintains code for a failure mode `git checkout` already covers.
3. **Persisted plan or install manifest.** Rejected: contradicts the no-persistent-artifact stance of [2026-06-13](2026-06-13-materialize-complete-replacement.md).
4. **One shared reader plus a transient plan materialize can print** (chosen).

## Decision

**One producer-side reader interprets `layout.toml`; materialize builds a transient plan it can print without writing.**

- **Shared reader in `helpers.py`.** It parses the `[harness]` table once — channel, tools, extensions — with tomllib semantics matching the doctor's accepted grammar, and returns whether channel was explicitly declared (init's conflict check needs that distinction). `init` drops its channel-only validation and its regex `parse_extensions`; two of the three channel-enum checks collapse into the reader, and init's CLI-arg check remains its own guard. The reader applies `record_extension`'s path-safety predicate to declared extensions — a control-character entry fails loud, never reaches a terminal. Writes stay textual splices — materialize's extensions rewrite, init's table injection — to preserve comments.
- **Boundary.** The reader is producer-side only. It never lands in `core/scripts/` (that ships bytes to every consumer), never absorbs `doctor.py` (consumer-side, cannot import producer `helpers.py`), and never absorbs check-sync's checker regexes (deliberate independence, parity-gated instead).
- **Transient plan.** A stat-only `plan_install` pass partitions each destination into created (absent) versus overwritten (present), over the same `_install_pairs` stream `install()` copies; `excluded_prefixes` and `extras = scan_present − installed` already exist. `--dry-run`/`--show-plan` runs read → resolve → a stat-only pass, prints created, overwritten, excluded-by-channel, extras-preserved, and managed-chapters-to-rewrite, then returns before any write. The plan is in-memory; it is never persisted, so it adds no artifact under [2026-06-13](2026-06-13-materialize-complete-replacement.md).
- **Extras stay candidates.** The plan reports extras, never "will delete." Classification remains the `/materialize` skill's judgment; the script never prunes.

## Consequences

**Positive:**
- One reader collapses the extensions-grammar divergence; every command validates the project identically. init gains materialize's tools validation; both commands now fail loud on a malformed or unsafe extensions value.
- `--dry-run` makes the overwrite blast radius legible before the write — the only preview a `materialize.py` run gets on the gitignored-runtime channels, where no git diff exists. The managed-chapter rewrite, the one genuinely unrecoverable edit, is named in the plan.
- The plan is unit-testable without a subprocess, as `TestVerifyRuntime` already asserts against a hand-built target.
- The materialize skill drops three exact-format stdout restatements; the plan payload documents the preview once.

**Negative:**
- materialize grows a stat pass and a flag; the create/overwrite partition adds about a dozen lines plus tests.
- Real marketplace consumers install through the plugin's `setup.sh`, which still overwrites unconditionally — the preview exists only where `materialize.py` runs. A setup-side preview is future work.
- One more producer convention the audit holds: the shared reader must not drift into `core/scripts/` or absorb the consumer-side doctor.

## Implementation

`harness/helpers.py` (shared reader), `harness/init.py` (drops the weaker reads), `harness/materialize.py` (create/overwrite partition, `--dry-run`/`--show-plan`), and the `/materialize` skill (subsumes the stdout prose). `harness/test_helpers.py` pins the reader to the doctor's accepted grammar — both parse with tomllib — and to the fail-loud validation; the battery's unit-suite step runs it.

## References

- [Materialize Is a Complete Replacement](2026-06-13-materialize-complete-replacement.md) — the extras, no-prune, and no-manifest model this preserves; the plan previews it and never persists it.
- [Materialize-Time Runtime Verification](2026-07-13-materialize-time-runtime-verification.md) — the verify phase the plan reuses; `--dry-run` installs nothing, so it verifies nothing.
- [Resilience-First Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — the shared reader is deduplication accepted on merit; the full lifecycle was rejected as reshuffle, not enforcement.
- [The Shipped Runtime Becomes Domain Packages](2026-07-17-runtime-package-layout.md) — the producer-imports-shipped direction the reader honors, never the reverse.
- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — the reader parses and decides, so it is tested Python.
