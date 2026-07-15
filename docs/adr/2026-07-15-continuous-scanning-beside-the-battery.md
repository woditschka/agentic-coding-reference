# Continuous Scanning Sits Beside the Deterministic Battery, Not Inside It

**Status:** Accepted

## Context

The reference is public and adopted, and its runtime executes on consumers' machines — the `scripts/*.py` engines and the `.claude/hooks/*.py` that fire on their tool calls. [The battery gates every push](2026-07-13-server-side-battery-enforcement.md) under `--strict`: shellcheck over the shell scripts, bandit over the Python, neither able to skip silently.

Two detection gaps remained. Bandit matches patterns; it does no interprocedural dataflow, so a taint path across functions passes it. And nothing detected a CVE published against an already-pinned dependency: `/deps-upgrade` answers whether a version is current, not whether it is vulnerable, and only when a maintainer invokes it.

The exposure is narrow. The shipped runtime imports only the standard library — no `requirements.txt`, no `pyproject.toml`, and `samples/go/go.mod` declares no dependencies. The single manifest with real dependencies is `samples/java-spring-boot/build.gradle`, which never ships but is copied by imitation, because a reference implementation exists to be copied.

GitHub offers CodeQL and Dependabot alerts. Both are repo settings, not repo content.

## Options Considered

1. **Add CVE scanning to the battery** (an `osv-scanner` step). Rejected: the battery is deterministic — same input, same result — which is what qualifies it to gate a push. A vulnerability database changes daily, so an unchanged commit would pass today and fail tomorrow, turning `main` red for work nobody did.
2. **CodeQL advanced setup** (a committed `codeql.yml`). Rejected: the scanning is identical, and the badge plus in-tree record cost a SHA-pinned action that freezes the query bundle until `/deps-upgrade` bumps it. Default setup updates queries continuously, which catches more than a pinned workflow does.
3. **Scan Go and Java.** Rejected: `samples/go/main.go` is 17 lines and the Java sample is 37 — no taint sources, no sinks. Neither ships (`harness/**/*.{go,java}` is empty). Enabling `java-kotlin` adds a Gradle autobuild to every scan.
4. **Dependabot security or version updates.** Rejected: both auto-open pull requests, and this repo commits to `main`. `/deps-upgrade` already bumps and verifies through the battery.
5. **CodeQL default setup on Python, plus Dependabot alerts** (chosen).

## Decision

**Detection runs continuously outside the battery; the battery stays the deterministic push gate.** CodeQL default setup scans the Python with the interprocedural taint tracking bandit cannot do. Dependabot alerts read `build.gradle`, `go.mod`, and the workflow's pinned actions — two of the three supply-chain inputs [the push gate](2026-07-13-server-side-battery-enforcement.md) flagged as needing tracking. The `pipx install` of bandit sits inside a run step, so no scanner reads it; `/deps-upgrade` still owns that pin. Both scanners are advisory — they notify, they never gate. Go and Java CodeQL stay off.

Both are configured in repo settings rather than the tree. This ADR is their record.

## Implementation

The scanners are out-of-tree settings. One in-tree change lands with them: `check_stdlib_only` (battery step 1c) enforces the stdlib-only contract that this ADR's Context relies on to argue the exposure is narrow. That contract was recorded by [logic-in-python](2026-07-06-logic-in-python-orchestration-in-bash.md) and restated by [single-pricing-source](2026-07-13-single-pricing-source-vendored-copy.md); it had no gate, so the property held by discipline. The step covers every tree that reaches a consumer on any channel, and the manifest half of the claim. `docs/adoption-guide.md` states the property to consumers; the step is what keeps that statement true. `README.md` surfaces the battery's attestation as a badge.

## Consequences

**Positive:** taint tracking over the shipped Python and CVE notification over the sample manifests, at no maintenance cost and no new supply-chain pin. Queries update without a bump. The battery stays deterministic, so its badge keeps meaning "these steps passed" rather than "no CVE was published today."

**Negative:** the configuration is invisible to a reader and disableable without a commit, and this ADR is the only record that it exists. That failure mode yields no alerts rather than a false green, unlike the bandit lapse that motivated the push gate. Gradle resolves the starters through the Spring Boot plugin and the Modulith BOM, so static parsing cannot pin their versions. Java coverage reaches the explicit pins, not the resolved tree. Revisit Go and Java scanning, and Gradle dependency submission, when a sample grows code with real inputs.

## References

- [Security in Both Arms of the Audit](2026-07-06-security-lens-in-the-audit.md) — the posture this extends. Its rejection of "a deterministic Python security linter only" is the premise CodeQL answers; the arms are now three.
- [The Battery Gates Every Push](2026-07-13-server-side-battery-enforcement.md) — the deterministic gate this complements; its `--strict` contract is what keeps the badge honest.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — the doctrine step 1c follows. The scanners do not: they add detection, and Consequences records the invisibility that costs.
- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — records the stdlib-only contract step 1c enforces.
- [Materialize-Time Runtime Verification](2026-07-13-materialize-time-runtime-verification.md) — verifies the runtime at install; this covers the source it installs from.
