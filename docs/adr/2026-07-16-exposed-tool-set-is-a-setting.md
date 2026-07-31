# The Exposed Tool Set Is a Setting, Not an Invariant

**Status:** Accepted (pod-reachability premise amended by [2026-07-17](2026-07-17-default-deny-pod-host-egress.md); preflight gating amended 2026-07-31)

> Amended 2026-07-17: the default-deny egress filter closes the pod's gateway path, and a kernel DNAT bridge replaces the in-pod relay. Statements below about unconditional pod-to-IDE reachability and about the relay describe the pre-filter state. The core decision stands: Exposed Tools remains the only control that binds every client.

> Amended 2026-07-31: the preflight is gated on `--ide`. The every-launch run predated the default-deny egress; since then a launch without the flag opens no path to the IDE, so the warning informed only about other clients' exposure. Against that residual value: a probe against a starting IntelliJ trips an upstream bug that spams its log. The standing drift check is `ide_preflight.py --discover`, run directly. The core decision stands unchanged.

## Context

The IDE oracle's safety rested on one sentence in both integration docs: *"No exposed tool writes to disk. Claude Code is the sole writer through its own file edits. This removes write-coherence failure modes — persistence uncertainty, multi-file staleness, write races — **by construction**."*

Three findings, all from enumerating a live IDE rather than reading documentation, showed that sentence was false and that its shape was wrong.

**The set had already drifted.** IntelliJ IDEA 2026.1.4 exposed seven tools where the policy names six. The extra was `apply_patch` — *"Apply a patch using the Codex apply_patch format… Supports Add, Delete, and Update operations"* — which writes files, arrived enabled, and appears nowhere in JetBrains' documented tool list. GoLand exposed six. Nobody chose this; an upgrade did.

**The set is shared, mutable state.** `Exposed Tools` is a settings dialog, and JetBrains Settings Sync propagates it across IDEs and machines: a change made in one IDE was observed reaching the other. So the set is not a per-project decision recorded once — it moves.

**The docs could not have caught it.** Two research passes worked from JetBrains' help pages and from `plugins/mcp-server/` in `JetBrains/intellij-community`. Neither could say what was live on the machine. The documented 2026.1 list omits `apply_patch` entirely; the source ships tools the docs never mention. Only `tools/list` against the running IDE was authoritative.

Two further findings landed at the same time and bear on the same policy.

**`build_project` failed the exposure policy's own criterion.** The policy admits a tool only if it *"carries information plain text cannot reconstruct."* Compiler errors are exactly what `./gradlew build` and `go build ./...` reconstruct, from the same disk, and the project build is canonical anyway. The IDE build was a faster route to identical information — never new information.

**And the docs' claim about it was false.** `intellij-idea/SKILL.md` asserted *"`build_project` is how the IDE catches up to you."* Read in `AnalysisToolset.kt`: the default `build_project` call performs no VFS refresh and no document save; `CompileDriver` refreshes output roots only, never sources. `get_file_problems` is the tool that refreshes — it calls `awaitExternalChangesAndIndexing`, a project-wide VFS refresh that waits for indexing. So a green `build_project` never made `search_symbol` current, and the coherence rule pointed at the wrong tool.

Separately, the IDE's loopback bind is not the boundary it appears to be. JetBrains binds `127.0.0.1` deliberately for security ([IJPL-200926](https://youtrack.jetbrains.com/issue/IJPL-200926)), but on macOS Docker proxies `host.docker.internal` to host loopback, so any container reaches it — verified with a bare `docker run alpine`. The server has no authentication; its only gate is a spoofable `Host: localhost` header. A permission-skipped `claude-pod` session therefore reaches the IDE whether or not anything bridges it.

## Options Considered

1. **Fix `apply_patch` and restate the invariant** — rejected: it treats a recurrence as an accident. The next upgrade adds the next tool, and the claim is false again with nobody watching.
2. **Bridge the oracle into the pod behind a filtering proxy** — rejected: the pod reaches the IDE directly, so a proxy filters nothing. It would have been ~250 lines of security theatre next to an open wall.
3. **Restrict the exposed set in the IDE and verify it mechanically** (chosen) — the only enforcement point that binds every client, because the server authenticates none of them.

## Decision

**Treat the exposed tool set as configuration to verify, not a property to assert.** Three parts:

- **The policy gains a second test.** A tool must (1) carry information plain text cannot reconstruct, *and* (2) neither write files nor execute code. Read-only-as-to-files is not read-only-as-to-execution; conflating them is what admitted `build_project`.
- **`build_project` is retired** from both stacks, failing both tests independently. It duplicates the canonical gate, and with Gradle delegation on — the default — it executes `build.gradle`, turning one injected line into host code execution from inside a confined pod. Go's case is narrower (no build script) but still puts the IDE on the execution path via `#cgo` directives. The exposed set is five: `get_file_problems`, `search_symbol`, `get_symbol_info`, `get_project_modules`, `get_project_dependencies`.
- **The coherence rule inverts.** `get_file_problems` is the refresh and must run first; the other four answer from a pre-edit index until it does. Its refresh is watcher-gated and so not a guarantee — which is a further reason the project build, which reads disk directly, stays canonical.

`tools/claude-dev/ide_preflight.py` enumerates the live set over MCP and fails on anything outside policy — a strict subset test, because a denylist cannot name what the docs omit. It runs at every pod launch (given host `python3`), *not* gated on `--ide`. The exposure is not gated on `--ide` either. Warning only when the bridge is requested would stay silent in exactly the runs whose operator does not know the path exists.

The warning is honest about its own weakness: it does not block, and declining to start the relay denies the agent nothing it could not reach itself. It points at `Exposed Tools`, which is the only control that holds.

## Consequences

- Positive:
  - The invariant becomes machine-checked instead of asserted, and catches the next `apply_patch` without anyone reading a changelog.
  - The pod's reach into the IDE is disclosed rather than latent, and the oracle is off the execution path entirely.
  - `get_file_problems`-first makes the other four trustworthy where the old rule left them stale after a green build.
- Negative:
  - The inner loop loses the IDE's compile pre-check and waits for the project build. The cost is small: a TDD cycle compiles when it runs its tests, and the build was always the gate.
  - A strict subset test refuses on harmless additions too; the fix is a settings toggle.
  - Preflight is a snapshot and the relay is TOCTOU, so both lose to a mid-session widening. Whether the IDE's file watcher sees writes made from inside the pod is unverified — a miss degrades to a stale answer, not an error.
  - `claude-pod` gains a host-side `python3` dependency. Without it, `--ide` prints a notice and continues; a plain launch skips the check silently.
- The pod/oracle overlap is narrower than it looks: the oracle needs the project open in the IDE, which already means Gradle import executed its build config on the host. The confined-untrusted-repo case never had an oracle to bridge.

**Why the check lives in `claude-pod`, not the doctor.** The `intellij-idea-doctor` / `goland-doctor` skills are the natural place a developer checks the oracle when using the IDE natively without a pod — but they cannot host the exposed-set check. They are agent-run: the agent cannot call `tools/list` (it is not an MCP tool), and its granted IDE tools are role-partitioned, so it never sees the full exposed set. And `tools/claude-dev/ide_preflight.py` is user-level tooling that does not ship into a consumer project, so a doctor materialized into a sample could not reference it without dangling. The mechanical enumeration therefore lives only where a standalone process can run `tools/list` — the pod launcher. The doctor skills keep their prose caveat ("if an unexpected tool appears, say so rather than calling it"); the native-IDE developer who wants the mechanical check runs `ide_preflight.py` directly.

## References

- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — the boundary rule this obeys: preflight and the relay are logic, so they are tested Python; `claude-pod` stays orchestration.
- [`docs/harness-project-api.md` § Optional Capabilities](../harness-project-api.md) — never roster-required, probed not declared, never load-bearing. Every failure path here is non-fatal because of it, and the IDE-assigned port is read from `~/.claude.json` rather than assumed.
- [`tools/claude-dev/README.md` § Security Model](../../tools/claude-dev/README.md) — the disclosure.
