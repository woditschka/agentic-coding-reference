#!/usr/bin/env python3
"""Local deterministic gate for the harness + samples: the mechanical,
no-judgment half of an audit-harness review. This header is the authoritative
step list — docs reference it rather than re-enumerating:
  1  shellcheck (harness/ + tools/)      3f  verdict-enum sync (schemas)
  1b bandit (python security lint)       3g  stack-agnostic core
  1c stdlib-only shipped runtime         3h  root link integrity
  1d ruff format --check                 3i  parity gates (stacks)
  1e ruff check (lint)                   4   sample test suites
  1f mypy --strict (typed scope)         4b  sample build-file script refs
  1g import boundaries (scripts)         4c  pinned-version sync (deps-report)
  1h no-network egress (glue)            5   sample doctors
  1i confined writes (glue)              6   harness unit suites
  2  python syntax                       6a  tools install completeness
  2b agent body parity (per-tool copies) 6b  tools unit suites
  2c agent-body renderer self-test       6bb pod toolchain pins
  2d accounting vendored-copy sync       6bc eval bench unit suites
  3  materialization faithfulness        6c  generic-stack self-test
  3b sample layout invariants            7   marketplace faithfulness
  3c project-owned roster sync           8   marketplace acceptance
  3d placeholder gate                    9   real plugin install (claude CLI)
  3e handbook delta + self-containment
Aggregates failures (does not stop at the first) and exits non-zero if any
check fails. Sole exception: a materialize-samples crash in step 3 aborts the run —
the sample checks that follow read the tree it produces.
Tier 0 of the maintainer loop (root CLAUDE.md): run it after
every edit — via propagate-harness.sh after a /harness edit. Two push-time gates
mirror it: the .githooks/pre-push hook blocks an unscanned local push, and the
.github/workflows/checks.yml GitHub Actions workflow attests every push and
pull request. Both invoke --strict. See
docs/adr/2026-07-13-server-side-battery-enforcement.md.

    harness/verify-harness.py [--quick] [--strict]

--quick is tier 0 for an edit that touches none of harness/, samples/,
plugins/, .claude-plugin/ (i.e. docs, root skills, tools/, evals/). It REFUSES
to run while any of those trees is dirty vs HEAD; only then does it skip — with
a loud SKIP line each — the steps that re-render or execute those trees
(2c, 3, 4, 5, 6, 6c, 7, 8, 9). Every static check still runs, so --quick can
never skip a check the pending edit could affect. Steps 4c, 6a, 6b, 6bb, and
6bc are deliberately NOT skippable. tools/ and evals/ are exactly what --quick
is for, so their unit suites (6b, 6bc) must run in the mode that covers their
edits; 6a and 6bb guard tools/ specifically. Step 4c reads README.md and .github/workflows/,
which sit outside the guard. A /harness edit takes the full battery via
propagate-harness.sh, unchanged; an /audit-harness run always uses the full
battery.

--strict makes a missing shellcheck, bandit, ruff, or mypy a FAIL, not a SKIP;
the two push-time gates set it so the lint and type steps cannot silently
no-op. Without it an absent tool skips with a note — the dev-machine default.

Needs git and python3; bash for the shell sub-suites; shellcheck, bandit,
ruff, and mypy if present (each skipped with a note if not, or failed under
--strict). The ruff and mypy config lives in the root pyproject.toml (the only
manifest the stdlib-only scan permits, kept outside every shipped tree). No
Go/Java toolchain required.
The faithfulness
step re-materializes the samples in place: it is dirty-tree-safe — it flags
only changes the re-materialize *introduces* (a /harness edit not yet
materialized, or a hand-edited sample), never already-pending work.

Pure helpers are unit-tested by test_verify_harness.py (battery step 6).
"""

# The steps live in the verify_harness/ package (ADR 2026-07-18
# check-sync-decomposition): text (pure helpers), battery (aggregator + run
# harness), checks/ (the step functions grouped by the evidence they read).
# This launcher keeps the header above and the ordered dispatch below.

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from verify_harness.battery import Battery, git_status  # noqa: E402
from verify_harness.checks.confinement import (  # noqa: E402
    check_confined_writes,
    check_no_network,
)
from verify_harness.checks.lint import (  # noqa: E402
    check_bandit,
    check_import_boundaries,
    check_mypy,
    check_python_syntax,
    check_ruff_format,
    check_ruff_lint,
    check_shellcheck,
    check_stdlib_only,
)
from verify_harness.checks.suites import (  # noqa: E402
    check_build_file_refs,
    check_deps_report,
    check_eval_suites,
    check_marketplace_faithfulness,
    check_pod_toolchain_pins,
    check_sample_doctors,
    check_sample_suites,
    check_tools_install_complete,
    check_tools_suites,
    check_unit_suites,
)
from verify_harness.checks.sync import (  # noqa: E402
    check_accounting_sync,
    check_agent_body_parity,
    check_faithfulness,
    check_handbook_delta,
    check_layout_invariants,
    check_parity_gates,
    check_placeholder_gate,
    check_root_links,
    check_roster_sync,
    check_stack_agnostic_core,
    check_verdict_enums,
)


def main(argv: list[str]) -> int:
    # Line-buffer both streams so step headers (stdout) and FAIL details
    # (stderr) interleave in true order when the battery is redirected to a
    # file or a pipe — block-buffered stdout would otherwise reorder them.
    # typeshed declares sys.stdout/stderr as TextIO, which lacks reconfigure;
    # at runtime both are io.TextIOWrapper, which has it.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[union-attr]
    flags = argv[1:]
    quick = "--quick" in flags
    strict = "--strict" in flags
    if any(f not in ("--quick", "--strict") for f in flags):
        print("usage: harness/verify-harness.py [--quick] [--strict]", file=sys.stderr)
        return 2

    # The --quick guard. Quick mode is sound only while the derived-surface
    # inputs are untouched: any pending change under them — staged, unstaged,
    # or untracked — means a skipped step could be the one that catches it.
    # Refuse rather than weaken the gate.
    if quick:
        dirty = git_status("harness/", "samples/", "plugins/", ".claude-plugin/")
        if dirty:
            print(
                "FAIL: --quick refused — pending changes touch the derived "
                "surfaces it would skip:",
                file=sys.stderr,
            )
            for line in dirty.splitlines()[:10]:
                print(f"    {line}", file=sys.stderr)
            print(
                "Run the full battery: harness/verify-harness.py (or "
                "harness/propagate-harness.sh after a /harness edit).",
                file=sys.stderr,
            )
            return 1

    b = Battery(quick, strict)
    check_shellcheck(b)
    check_bandit(b)
    check_stdlib_only(b)
    check_ruff_format(b)
    check_ruff_lint(b)
    check_mypy(b)
    check_import_boundaries(b)
    check_no_network(b)
    check_confined_writes(b)
    check_python_syntax(b)
    check_agent_body_parity(b)
    b.run_suite(
        "agent-mirror renderer self-test", "harness/tests/test_render_agent_mirrors.py"
    )
    check_accounting_sync(b)
    check_faithfulness(b)
    check_layout_invariants(b)
    check_roster_sync(b)
    check_placeholder_gate(b)
    check_handbook_delta(b)
    check_verdict_enums(b)
    check_stack_agnostic_core(b)
    check_root_links(b)
    check_parity_gates(b)
    check_sample_suites(b)
    check_build_file_refs(b)
    check_deps_report(b)
    check_sample_doctors(b)
    check_unit_suites(b)
    check_tools_install_complete(b)
    check_tools_suites(b)
    check_pod_toolchain_pins(b)
    check_eval_suites(b)
    b.run_suite("generic-stack self-test", "harness/tests/test-generic-stack.sh")
    check_marketplace_faithfulness(b)
    b.run_suite("marketplace acceptance", "harness/tests/test-marketplace.sh")
    b.run_suite(
        "real plugin install (claude CLI)",
        "harness/tests/test-plugin-install.sh",
        skip_re=r"^SKIP",
        skip_label="skip (no claude CLI)",
    )

    print()
    if b.failed:
        print("FAIL verify-harness: see failures above", file=sys.stderr)
        return 1
    if quick:
        print(
            "PASS verify-harness --quick: static checks green (re-render and "
            "sub-suite steps skipped — guard proved their inputs untouched)"
        )
    else:
        print(
            "PASS verify-harness: lint, syntax, parity, faithfulness, invariants, "
            "tests, doctors, marketplace all green"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
