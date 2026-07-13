# The Battery Gates Every Push: A Pre-Push Hook and Server-Side CI

**Status:** Accepted

## Context

The deterministic battery (`harness/check-sync.py`) was enforced by discipline. The maintainer ran it locally, tier 0 of the loop. Three places recorded a "local-only, no server-side CI" stance: the script header, `harness/README.md`, and `audit-harness` — the last telling the audit to never propose CI. The rationale was simplicity for a solo maintainer.

Two facts changed the trade-off. The reference is now public and adopted. Its shipped runtime executes on consumers' machines — the `scripts/*.py` engines and the three `.claude/hooks/*.py` that fire on their tool calls. Separately, the battery's `bandit` SAST step was rostered but the tool was uninstalled. So it skipped silently on every run: shipped code reached consumers unscanned while the battery reported green.

## Options Considered

1. **Keep local-only, rely on discipline** (status quo). Rejected: the uninstalled-`bandit` lapse proved a local gate can skip silently, and nothing external attests the installed code passed.
2. **A local pre-push hook only.** Rejected as the sole measure. It blocks the maintainer's own unscanned push, but it is bypassable and invisible — no public attestation for an adopted reference.
3. **Server-side CI only.** Rejected as the sole measure. The local loop loses its fast pre-push safety net, so failures surface only after a push.
4. **Both a pre-push hook and server-side CI** (chosen).

## Decision

**The full battery runs at two gates, both under `--strict`: a `.githooks/pre-push` hook and a GitHub Actions workflow on push-to-`main` and every pull request.** The hook *prevents* an unscanned local push. The workflow *attests* every push and pull request, and blocks a merge only where branch protection requires the check. `--strict` makes a missing `shellcheck` or `bandit` a failure, not a skip, so the SAST steps cannot silently no-op — the gap that motivated this decision. This supersedes the "local-only, no server-side CI" stance in `check-sync.py`, `harness/README.md`, and `audit-harness`. The workflow installs `shellcheck` and a pinned `bandit`, then runs the battery; step 9 (real plugin install) self-skips without the claude CLI and no Go/Java toolchain is needed. The hook is installed per clone with `git config core.hooksPath .githooks`.

## Consequences

**Positive:** the scripts and hooks that run on consumers' machines cannot pass an unscanned local push. `--strict` turns a missing scanner into a loud failure at both gates. A public green check attests every push passed the deterministic gate.

**Negative:** the local hook is opt-in per clone and bypassable with `--no-verify`, so a fresh clone has no gate until configured. The CI action and the pinned `bandit` are supply-chain inputs to track. `actions/checkout` is pinned to a commit SHA (`v5.0.1`); refreshing the pin is a manual step until `deps-upgrade` automates it.

## References

- [Materialize-Time Runtime Verification](2026-07-13-materialize-time-runtime-verification.md) — verifies the runtime once at install; this extends verification to a push-time gate on the source.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — the doctrine this follows: close a silent-failure gap over adding features.
- [Tiered Maintainer Workflow](2026-07-02-tiered-maintainer-workflow.md) — the loop this augments; the battery stays tier 0, now enforced at push.
