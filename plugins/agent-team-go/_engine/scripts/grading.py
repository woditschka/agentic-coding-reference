#!/usr/bin/env python3
"""Extract the structural feature row of a change and plan its review.

The composition root over the grading package: it loads the layout, resolves
the change set through the changeset package, and runs one command.

  extract          append the change's grader-features record
  review-plan      append the review-plan naming the roster and read scope
  contracts-sync   check the slice's req_id is recorded in the PRD and the design doc
  coverage-map     list the slice's Done-when bullets and declared tests beside their tests
  conventions-map  list the added comments, constructions, and literals per changed file

A feature row is a pure function of pinned inputs, holds no verdict, and
records null, never a false zero, for a fact it cannot read. Stdlib only.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

# The packages resolve through this script's own directory, which python
# puts on sys.path only when the script runs as a script; a loader by path
# from another working directory needs the entry added.
if (_HERE := str(Path(__file__).resolve().parent)) not in sys.path:
    sys.path.insert(0, _HERE)

from changeset.config import ChangeSetError, load_exclude_globs
from changeset.emit import default_base
from changeset.git_facts import (
    WORKTREE,
    ChangeSet,
    resolve_changeset,
    run_git,
)
from grading.config import Layout, LayoutError, Raw, ReviewConfig, load_layout
from grading.contracts import check_contracts_sync
from grading.conventions import conventions_map, render as render_conventions
from grading.coverage import coverage_map, render
from grading.features import (
    basis_files,
    classify_kind,
    delta_numstat,
    diff_features,
    parse_numstat,
    tree_files,
)
from grading.handoff_facts import (
    HANDOFF,
    append_validated,
    declared_test_names,
    load_records,
    read_handoff,
)
from grading.planner import (
    GitReaders,
    Plan,
    PlanContext,
    PlanInputs,
    derive_plan,
    plan_context,
)

SCRIPTS_DIR = Path(_HERE)


def cmd_extract(args: argparse.Namespace) -> int:
    """Append the change's grader-features record and return the exit code."""
    req_id = args.feature
    layout, review, exclude_globs = load_install()
    changeset = resolve_changeset(default_base(args), args.head, exclude_globs)
    if args.head == WORKTREE and changeset.head is None:
        report(
            "extract",
            "warning — could not snapshot the working tree; diff features are null",
        )
    if changeset.base and changeset.tip and changeset.merge_base is None:
        report(
            "extract",
            "warning — no merge-base for base/head; diffing against the raw base ref",
        )
    features: Raw = {
        "base_ref": changeset.base,
        "head_ref": changeset.head,
        "head_kind": changeset.head_kind,
    }
    try:
        features.update(diff_features(layout, review, changeset, churn=args.churn))
    except RuntimeError as exc:
        report("extract", f"git command failed: {exc}")
        return 1
    features.update(read_handoff(req_id))
    record: Raw = {
        "type": "grader-features",
        "req_id": req_id,
        "author": "change-grader",
        "features": features,
    }
    if append_validated(record, "grader-features", "extract"):
        return 1
    print(f"extract: appended grader-features record for {req_id} to {HANDOFF}")
    print(_extract_summary(changeset, features))
    return 0


def _extract_summary(changeset: ChangeSet, features: Raw) -> str:
    if changeset.base is None:
        return "extract: base ref unresolved — diff features are null (-> scrutinize)"
    if changeset.head is None:
        return "extract: working-tree snapshot failed — diff features are null (-> scrutinize)"
    return (
        f"extract: {features['files_changed']} files, "
        f"{features['module_count']} modules, {features['hunks']} hunks, "
        f"build_passed={features['build_passed']}, "
        f"unknown_paths={len(features['unknown_paths'])}"
    )


def cmd_contracts_sync(args: argparse.Namespace) -> int:
    """Check the slice's req_id is recorded in the PRD and the design doc; return the exit code."""
    failures = check_contracts_sync(args.feature, Path.cwd())
    for failure in failures:
        report("contracts-sync", failure)
    if failures:
        return 1
    print(f"contracts-sync: {args.feature} recorded in the PRD and design doc")
    return 0


def cmd_coverage_map(args: argparse.Namespace) -> int:
    """Print the slice's coverage map and return the exit code."""
    layout = load_layout(SCRIPTS_DIR)
    declared = declared_test_names(args.feature)
    print(render(coverage_map(args.feature, Path.cwd(), layout.test_globs, declared)))
    return 0


def cmd_conventions_map(args: argparse.Namespace) -> int:
    """Print the change's conventions map and return the exit code."""
    layout = load_layout(SCRIPTS_DIR)
    exclude_globs = load_exclude_globs(SCRIPTS_DIR)
    changeset = resolve_changeset(default_base(args), args.head, exclude_globs)
    if not changeset.resolved:
        report("conventions-map", "base or head unresolved — nothing to map")
        return 1
    try:
        conventions = layout.conventions_config()
        diff = run_git(
            "diff",
            "--unified=0",
            "--find-renames",
            str(changeset.base),
            str(changeset.head),
            *changeset.pathspecs,
        )
    except (RuntimeError, ValueError) as exc:
        report("conventions-map", str(exc))
        return 1
    rows = conventions_map(diff, lambda path: classify_kind(path, layout), conventions)
    print(render_conventions(rows, str(changeset.base)[:7]))
    return 0


def cmd_review_plan(args: argparse.Namespace) -> int:
    """Append the review-plan record for the next review pass and return the exit code."""
    req_id = args.feature
    layout, review, exclude_globs = load_install()
    changeset = resolve_changeset(default_base(args), args.head, exclude_globs)
    try:
        features = diff_features(layout, review, changeset, churn=False)
    except RuntimeError as exc:
        report("review-plan", f"git command failed: {exc}")
        return 1
    context: PlanContext = plan_context(load_records(req_id))
    inputs = PlanInputs(
        features,
        read_handoff(req_id),
        context,
        layout,
        review,
        changeset.head,
        changeset.base,
    )
    plan = derive_plan(inputs, _git_readers(layout, review, exclude_globs))
    record: Raw = {
        "type": "review-plan",
        "req_id": req_id,
        "author": "review-plan-engine",
        "risk": plan.risk,
        "scope": plan.scope,
        "basis": plan_basis(inputs, plan),
        "rationale": plan.rationale,
    }
    if plan.roster is not None:
        record["roster"] = list(plan.roster)
    if append_validated(record, "review-plan", "review-plan"):
        return 1
    shown = "—" if plan.roster is None else ",".join(plan.roster) or "(empty)"
    print(
        f"review-plan: appended {plan.risk} plan for {req_id} "
        f"(pass={context.pass_}, scope={plan.scope}, roster={shown})"
    )
    return 0


def _git_readers(
    layout: Layout, review: ReviewConfig, exclude_globs: Sequence[str]
) -> GitReaders:
    """Bind the planner's two git-backed reads; every agent-authored tree resolves through the gateway first."""

    def delta(prev_tree: object, cur_tree: object) -> Raw | None:
        numstat = delta_numstat(prev_tree, cur_tree, exclude_globs)
        return None if numstat is None else parse_numstat(numstat, layout, review)

    return GitReaders(
        delta, lambda base_tree, tree: tree_files(base_tree, tree, exclude_globs)
    )


def plan_basis(inputs: PlanInputs, plan: Plan) -> Raw:
    """Return the facts a review-plan records: the tree, the pass, the classification, the size, the history, the ladder's outputs."""
    features, history, context = inputs.features, inputs.history, inputs.context
    return {
        "tree_sha": inputs.tree_sha,
        "pass": context.pass_,
        "prev_tree_sha": context.prev_tree_sha,
        "files": basis_files(features, inputs.layout, inputs.review),
        "size": {
            "prod_lines": features.get("prod_lines"),
            "test_lines": features.get("test_lines"),
            "hunks": features.get("hunks"),
            "module_count": features.get("module_count"),
        },
        "history": {
            "build_retries": history.get("build_retries"),
            "design_revisions": history.get("design_revisions"),
            "consultations": history.get("consultations"),
        },
        "open_findings": (
            None
            if plan.open_findings is None
            else [finding.as_dict() for finding in plan.open_findings]
        ),
        "triggers": list(plan.triggers),
        "security_surface": {
            "declared": bool(inputs.review.security_surface),
            "paths": features.get("security_surface_paths"),
        },
    }


class Install(NamedTuple):
    """What a gate command loads before it reads an argument or git: the layout, its review table, the exclude filter."""

    layout: Layout
    review: ReviewConfig
    exclude_globs: tuple[str, ...]


def load_install() -> Install:
    """Load the install first, so a broken one fails loud before any argument or git fault."""
    layout = load_layout(SCRIPTS_DIR)
    return Install(layout, layout.review_config(), load_exclude_globs(SCRIPTS_DIR))


def report(command: str, message: str) -> None:
    """Write one command message to stderr."""
    print(f"{command}: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run one grading command."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    base_help = (
        "base ref to diff against (default: HEAD for the live worktree; "
        "required when --head names a committed range)"
    )
    head_help = "head to diff: the default WORKTREE snapshot, or a commit ref"

    extract = sub.add_parser(
        "extract", help="compute the row and append a grader-features record"
    )
    extract.add_argument("--feature", required=True, help="req_id, e.g. REQ-CBA-108")
    extract.add_argument("--base", default=None, help=base_help)
    extract.add_argument("--head", default=WORKTREE, help=head_help)
    extract.add_argument(
        "--churn",
        action="store_true",
        help="include churn (commit/author count); slower, needs full history",
    )
    extract.set_defaults(func=cmd_extract)

    contracts = sub.add_parser(
        "contracts-sync",
        help="gate check: the slice's req_id appears in docs/prd.md and "
        "docs/system-design.md (vacuous without the design brief)",
    )
    contracts.add_argument("--feature", required=True, help="req_id, e.g. REQ-CBA-108")
    contracts.set_defaults(func=cmd_contracts_sync)

    coverage = sub.add_parser(
        "coverage-map",
        help="walk aid: the slice's Done-when bullets, declared test names, and "
        "the capability group's edge cases beside the tests that define or "
        "cite them (a map, never a gate)",
    )
    coverage.add_argument("--feature", required=True, help="req_id, e.g. REQ-CBA-108")
    coverage.set_defaults(func=cmd_coverage_map)

    conventions = sub.add_parser(
        "conventions-map",
        help="walk aid: every added comment block per changed code file, and every "
        "raw construction and literal-bearing line per changed test file, for the "
        "Test-Conventions Walk and the reviewer checklists (a map, never a gate)",
    )
    conventions.add_argument("--base", default=None, help=base_help)
    conventions.add_argument("--head", default=WORKTREE, help=head_help)
    conventions.set_defaults(func=cmd_conventions_map)

    plan = sub.add_parser(
        "review-plan",
        help="estimate review risk and append a review-plan record naming the "
        "roster and read scope for the next review pass",
    )
    plan.add_argument("--feature", required=True, help="req_id, e.g. REQ-CBA-108")
    plan.add_argument("--base", default=None, help=base_help)
    plan.add_argument("--head", default=WORKTREE, help=head_help)
    plan.set_defaults(func=cmd_review_plan)

    args = parser.parse_args(argv)
    try:
        exit_code: int = args.func(args)
    except (LayoutError, ChangeSetError) as exc:
        # A broken layout.toml or an argument naming no range is reported the
        # way every command reports a git failure: one stderr line, exit 1.
        report(args.cmd, str(exc))
        return 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
