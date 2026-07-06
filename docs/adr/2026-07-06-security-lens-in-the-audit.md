# The Audit Carries a Security Lens, Deterministic and Judgment

**Status:** Accepted

## Context

The `view` subcommand added to `handoff.py` rendered agent-authored log content to the maintainer's terminal. It printed record strings unescaped: an embedded ESC byte could set the window title, hide text, or clear the screen. A passing `/audit-harness` run shipped it — three adversarial reviewers probed crashes and regressions, none carried a security mandate. The gap was the process, not the diff: the audit had no security dimension, and the tier-0 battery ran shellcheck over bash but nothing over Python. The reviewer floor's `security-reviewer` exists only in the sample pipeline; root maintainer-loop changes never pass through it.

## Options Considered

1. **Fix the one finding, add nothing** — rejected: the escape-injection class recurs on every surface that renders log content (`view`, `show`), and the next such surface ships the same hole. A finding without a standing check is a finding that returns.
2. **A deterministic Python security linter only** — rejected as insufficient alone: bandit catches shell-injection and unsafe calls, but no bandit plugin sees terminal-escape injection, path-trust, or a hook's auto-approve scope. The mechanical gate cannot reason about trust boundaries.
3. **A judgment security lens only** — rejected as insufficient alone: a per-run LLM review is not a regression gate; a mechanical issue a linter catches every time should not depend on a reviewer remembering to look.
4. **Both halves, split by what each does well** (chosen) — a deterministic linter for the mechanical findings, a standing Layer 3 lens for the trust-boundary judgment.

## Decision

**The audit carries security in both arms: bandit as tier-0 battery step 1b, and a standing Layer 3 security lens.** The linters gate what is mechanical; the lens hunts what they cannot.

Load-bearing details:

- **Battery step 1b runs bandit** at medium+ severity over `harness/` and `tools/`, on the exact shellcheck contract: gate when installed, loud SKIP when absent. `--ignore-nosec` so an in-tree `# nosec` cannot silently disarm a finding — suppression is a review decision, not a source-file one.
- **Layer 3 gains a security bullet** over four untrusted-input surfaces. They are: log content rendered to a terminal, shell command construction, path handling, and any change to the `PreToolUse` hooks' auto-approve or deny scope. Its framing: the handoff log is agent-authored — treat every field as untrusted input.
- **The rendering fix generalizes to a rule:** log content reaching a terminal is sanitized at a single choke point. In the `view` renderer that is `_style`; `show` sanitizes its own plain text. C0/C1 control bytes are dropped, tabs and newlines become spaces.

## Consequences

- Positive: the escape-injection class is closed at the render choke point, not per-call-site; every Python security regression bandit knows fails the tier-0 gate; the audit reviews trust boundaries by standing instruction, not by luck.
- Negative: bandit is a third toolchain dependency that SKIPs when absent, so the deterministic half is contingent on a local install; its ruleset is unpinned, matching the shellcheck precedent, so two machines can disagree at the margin; the security lens is one more Layer 3 mandate the audit must staff.

## References

- [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) — why the shipped logic is testable Python; bandit lints that same surface.
- [Handoff Log Access: Single Deterministic Tool](2026-06-11-handoff-log-access-tool.md) — the tool whose reader surface (`view`, `show`) motivated the terminal-injection rule.
- [Tiered Maintainer Workflow](2026-07-02-tiered-maintainer-workflow.md) — the audit tiers this extends with a security dimension.
