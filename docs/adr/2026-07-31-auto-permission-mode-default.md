# The Default Permission Posture Is Auto Mode, Not Skip

**Status:** Accepted

## Context

Since its first version, claude-dev launched every session with `--dangerously-skip-permissions`. The premise was that the harness's loops need fully unattended runs. A third-party security review of the tool recommended `--permission-mode auto` as the default instead. The operator then restated the actual requirement: full unattended operation is not needed; heavily reduced approvals suffice.

Auto mode exists in current Claude Code and is documented. A classifier reviews each action, approves routine ones, and falls back to an interactive prompt on the ones it flags. In headless `-p` runs, repeated classifier blocks abort the session rather than prompting.

Much of the behavioral risk auto mode addresses is already closed by the container: no credentials are shared, egress is an allow-list with source control absent by default, and the mount set is enumerated. Package publishing, force pushes, and infrastructure changes die at those boundaries. What auto mode adds is a check on the remainder — destructive operations inside the writable project directory, and misuse of the allowed channels.

## Options Considered

1. **Keep `--dangerously-skip-permissions` as the default** — rejected: it optimizes for a requirement (zero prompts, ever) the operator does not hold, and forgoes a cheap behavioral layer on the risks the container cannot see.
2. **Auto mode as the default, other postures via pass-through** (chosen).
3. **A launcher-owned `--skip-perms` flag for the old posture** — rejected: the launcher already forwards unrecognized flags to `claude`, so `--dangerously-skip-permissions` passes through as-is. A second spelling of one answer costs maintenance and a reviewer check ([ADR 2026-07-29](2026-07-29-proxy-enforced-egress.md)); the long, scary name is also the honest one. The pre-existing `--no-skip-perms` retires on the same ground — a passed-through `--permission-mode default` is the same answer, and no legacy flag survives.
4. **A `permissions` key in `claude-dev.toml`** — rejected: the posture is a per-run choice, and the config file deliberately holds only what has more than one standing value per install ([ADR 2026-07-29](2026-07-29-proxy-enforced-egress.md)).

Two adjacent recommendations from the same review were dispositioned separately:

- **Importing Claude settings allowlists into the proxy** — declined. The threat it targets — a repo widening its own egress — is already closed: the launcher reads no project file. The import would break the single-file audit property (`claude-dev.toml` plus `claude-dev access` is the whole truth) and translate between two allowlist semantics that differ.
- **`sandbox.enableWeakerNestedSandbox`** — measured 2026-07-31, declined. Documentation suggests the mode avoids the user-namespace requirement, which would dissolve the seccomp trade recorded in [ADR 2026-07-29](2026-07-29-proxy-enforced-egress.md). The live measurement says otherwise. Under the launcher's shipped flags (claude 2.1.220, Rancher Desktop, `cap-drop=ALL` + `no-new-privileges` + default seccomp), every sandboxed Bash command fails with bwrap's namespace error — the weaker mode still creates namespaces. `failIfUnavailable=true` does not refuse startup; the session runs with Bash fully bricked, failing per command. `bwrap` under `cap-add=SYS_ADMIN` fails at `pivot_root` on the same engine, and granting that capability is refused regardless — the review's own principle. The sandbox stays off; re-measure when a Claude release changes the nested-sandbox mechanism.

## Decision

**The launcher injects `--permission-mode auto` by default, and owns no permission flag of its own.** A passed-through `--permission-mode` or `--dangerously-skip-permissions` suppresses the injection entirely, so the user's flag never fights the default over argv order. Fully unattended runs pass `--dangerously-skip-permissions`; stock prompting passes `--permission-mode default`.

**Auto mode is a behavioral layer, never a boundary.** The classifier runs in the session's own process and reads the same context a hostile repo poisons. The README's security model counts three boundaries, all enforced outside the session; that count is unchanged, and every boundary stays sized to hold with permissions fully skipped.

## Consequences

Positive:

- Approvals drop heavily while flagged actions keep a human gate — the posture the operator actually asked for.
- Destructive operations inside the project directory — the one risk class the container cannot see — gain a check.
- The classifier's API traffic needs no policy change: it calls `api.anthropic.com`, mandatory on the allow-list since the proxy design landed.

Negative:

- Sessions can stall on a fallback prompt with nobody watching. Accepted: the operator is present enough, and the skip posture remains one passed-through flag away.
- Headless `-p` runs abort after repeated classifier blocks. Disclosed in the launcher help and the README; scripted runs pass `--dangerously-skip-permissions`.
- Each flagged action costs a classifier model call — latency and tokens the skip posture did not spend.
- The classifier is a model judging model output. Under prompt injection it is a mitigation, not an enforcement point; the ADR's boundary framing exists so nobody mistakes it for one.

## References

- [Egress Is Enforced by an External Proxy, Not by the Workload](2026-07-29-proxy-enforced-egress.md) — the boundary set this posture sits above; also holds the sandbox measurement this ADR defers to.
- [`tools/claude-dev/README.md`](../../tools/claude-dev/README.md) — the operator-facing statement of the postures and their flags.
