#!/usr/bin/env python3
"""Run the deterministic gate over the harness and the samples.

This header is the authoritative step list; docs reference it rather than
re-enumerating:
  1  shellcheck (harness/ + tools/)      3d  placeholder gate
  1b bandit (python security lint)       3e  handbook delta (root vs core copy)
  1c stdlib-only shipped runtime         3f  verdict-enum sync (schemas)
  1d ruff format --check                 3g  stack-agnostic core
  1e ruff check (lint)                   3h  root link integrity
  1f mypy --strict (typed scope)         3i  parity gates (stacks)
  1g import boundaries (scripts)         3j  route-rule inventory sync
  1h no-network egress (glue)            3k  retired-paths manifest
  1i confined writes (glue)              3l  adr-index sync
                                         3m  gitignore-block sync
                                         3n  shipped prose self-containment
                                         3o  runtime-number-free prose
                                         3p  enforcer tactic pin (stack skills)
  2  python syntax                       4   sample test suites
  2a annotation evaluation (runtime)     4b  sample build-file script refs
  2b agent body parity (per-tool copies)
  2c agent-mirror renderer self-test     4c  pinned-version sync (deps-report)
  2d accounting vendored-copy sync       5   sample doctors
  2e frontmatter vocabulary (per-tool)   6   harness unit suites
  2f spec-version sync                   6a  tools install completeness
  2g bundled-skill-name collision        6b  tools unit suites
  3  materialization faithfulness        6bb claude-dev toolchain and confinement pins
  3b sample layout invariants            6bc eval bench unit suites
  3c project-owned roster sync           6c  generic-stack self-test
                                         7   marketplace faithfulness
                                         8   marketplace acceptance
                                         9   real plugin install (claude CLI)

Failures aggregate and the run exits non-zero once at the end. The sole
abort is a materialize-samples crash in step 3, since the sample checks that
follow read the tree it produces. Tier 0 of the maintainer loop runs it after
every edit, via propagate-harness.sh after a /harness edit; the pre-push hook
and the GitHub Actions workflow run it with --strict.

    harness/verify-harness.py [--quick] [--strict]

--quick is tier 0 for an edit that touches none of harness/, samples/,
plugins/, or .claude-plugin/. It refuses to run while any of those trees is
dirty against HEAD; only then does it skip, with a loud SKIP line each, the
steps that re-render or execute those trees (2c, 3, 4, 5, 6, 6c, 7, 8, 9).
Every static check still runs. The tools/ and evals/ suites (6b, 6bc) run
whenever either tree carries a pending change and skip jointly when both are
clean; a gitignored dev-run artifact still has its derived views validated
before 6bc skips. Steps 4c, 6a, and 6bb always run, since their inputs sit
outside the guard.

--strict makes a missing shellcheck, bandit, ruff, or mypy a FAIL, not a
SKIP. Needs git and python3, bash for the shell sub-suites, and the four
static tools when present; the ruff and mypy config lives in the root
pyproject.toml. The faithfulness step re-materializes the samples in place
and flags only the changes the render introduces, never pending work.
"""

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
    check_annotation_evaluation,
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
    check_adr_index,
    check_agent_body_parity,
    check_bundled_skill_collision,
    check_enforcer_pin,
    check_faithfulness,
    check_frontmatter_vocabulary,
    check_gitignore_block,
    check_handbook_delta,
    check_layout_invariants,
    check_parity_gates,
    check_placeholder_gate,
    check_prose_self_containment,
    check_retired_paths,
    check_root_links,
    check_roster_sync,
    check_route_rules,
    check_runtime_number_free_prose,
    check_spec_version_sync,
    check_stack_agnostic_core,
    check_verdict_enums,
)

FLAGS = ("--quick", "--strict")
GUARDED_TREES = ("harness/", "samples/", "plugins/", ".claude-plugin/")
SHOWN_DIRTY_LINES = 10
USAGE_EXIT = 2


def _line_buffer(stream: object) -> None:
    """Flush a stream per line so step headers and failure details interleave in order."""
    # typeshed types the streams as TextIO, which lacks reconfigure; a
    # redirected StringIO lacks it at runtime too.
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(line_buffering=True)


def _quick_refusal() -> str | None:
    """Return the refusal for --quick when a guarded tree carries a pending change."""
    # A skipped step could be the one that catches a change under it, so the
    # guard refuses rather than weakening the gate.
    dirty = git_status(*GUARDED_TREES)
    if not dirty:
        return None
    shown = "\n".join(f"    {line}" for line in dirty.splitlines()[:SHOWN_DIRTY_LINES])
    return (
        "--quick refused — pending changes touch the derived surfaces it would "
        f"skip:\n{shown}\nRun the full battery: harness/verify-harness.py (or "
        "harness/propagate-harness.sh after a /harness edit)."
    )


def _run_steps(b: Battery) -> None:
    """Dispatch every step in the header's order."""
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
    check_annotation_evaluation(b)
    check_agent_body_parity(b)
    b.run_suite(
        "agent-mirror renderer self-test", "harness/tests/test_render_agent_mirrors.py"
    )
    check_accounting_sync(b)
    check_frontmatter_vocabulary(b)
    check_spec_version_sync(b)
    check_bundled_skill_collision(b)
    check_faithfulness(b)
    check_layout_invariants(b)
    check_roster_sync(b)
    check_placeholder_gate(b)
    check_handbook_delta(b)
    check_verdict_enums(b)
    check_stack_agnostic_core(b)
    check_root_links(b)
    check_parity_gates(b)
    check_route_rules(b)
    check_retired_paths(b)
    check_adr_index(b)
    check_gitignore_block(b)
    check_prose_self_containment(b)
    check_runtime_number_free_prose(b)
    check_enforcer_pin(b)
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


def _verdict(b: Battery) -> int:
    """Print the run's verdict line and return its exit code."""
    print()
    if b.failed:
        b.fail("verify-harness: see failures above")
        return 1
    if b.quick:
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


def main(argv: list[str]) -> int:
    """Run the battery and return its exit code."""
    for stream in (sys.stdout, sys.stderr):
        _line_buffer(stream)
    flags = argv[1:]
    b = Battery(quick="--quick" in flags, strict="--strict" in flags)
    if any(flag not in FLAGS for flag in flags):
        b.fail("usage: harness/verify-harness.py [--quick] [--strict]")
        return USAGE_EXIT
    if b.quick:
        refusal = _quick_refusal()
        if refusal:
            b.fail(refusal)
            return 1
    _run_steps(b)
    return _verdict(b)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
