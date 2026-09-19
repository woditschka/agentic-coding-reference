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
from changeset.emit import changesets_for
from changeset.git_facts import (
    WORKTREE,
    ChangeSet,
    run_git,
)
from changeset.workspace import Member, WorkspaceError, load_members
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


class Install(NamedTuple):
    """What a gate command loads before it reads an argument or git: the layout, its review table, the exclude filter."""

    layout: Layout
    review: ReviewConfig
    exclude_globs: tuple[str, ...]
    members: tuple[Member, ...]

    def changesets(self, args: argparse.Namespace) -> tuple[ChangeSet, ...]:
        """Return the project's change set and one per present member, resolved from the arguments."""
        return changesets_for(args, self.exclude_globs, self.members)


def cmd_extract(args: argparse.Namespace) -> int:
    """Append the change's grader-features record and return the exit code."""
    req_id = args.feature
    install = load_install()
    changesets = install.changesets(args)
    changeset = changesets[0]
    if args.head == WORKTREE and any(c.head is None for c in changesets):
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
        features.update(
            diff_features(install.layout, install.review, changesets, churn=args.churn)
        )
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
    changesets = changesets_for(args, exclude_globs, load_members(SCRIPTS_DIR))
    if not all(c.resolved for c in changesets):
        report("conventions-map", "base or head unresolved — nothing to map")
        return 1
    try:
        conventions = layout.conventions_config()
        diff = "".join(_unified_diff(c) for c in changesets)
    except (RuntimeError, ValueError) as exc:
        report("conventions-map", str(exc))
        return 1
    rows = conventions_map(diff, lambda path: classify_kind(path, layout), conventions)
    print(render_conventions(rows, str(changesets[0].base)[:7]))
    return 0


def _unified_diff(changeset: ChangeSet) -> str:
    """Return one set's zero-context diff with its paths spelled from the project."""
    return run_git(
        "diff",
        "--unified=0",
        "--find-renames",
        *changeset.diff_options,
        str(changeset.base),
        str(changeset.head),
        *changeset.pathspecs,
        root=changeset.root,
    )


def cmd_review_plan(args: argparse.Namespace) -> int:
    """Append the review-plan record for the next review pass and return the exit code."""
    req_id = args.feature
    install = load_install()
    layout, review = install.layout, install.review
    changesets = install.changesets(args)
    try:
        features = diff_features(layout, review, changesets, churn=False)
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
        changesets[0].head,
        changesets[0].base,
        members_basis(install.members, changesets, context.prev_members),
    )
    plan = derive_plan(inputs, _git_readers(install, changesets, context.prev_members))
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


def members_basis(
    members: Sequence[Member],
    changesets: Sequence[ChangeSet],
    prev_members: Raw | None,
) -> Raw | None:
    """Return the plan's member map: each declared member's path, presence, snapshot, and the governing plan's snapshot; None without members."""
    if not members:
        return None
    by_path = {c.member_path: c for c in changesets if c.member_path is not None}
    previous = prev_members or {}
    basis: Raw = {}
    for member in members:
        current = by_path.get(member.path)
        earlier = previous.get(member.key)
        basis[member.key] = {
            "path": member.path,
            "present": current is not None,
            "tree_sha": None if current is None else current.head,
            "prev_tree_sha": earlier.get("tree_sha")
            if isinstance(earlier, dict)
            else None,
        }
    return basis


def _git_readers(
    install: Install, changesets: Sequence[ChangeSet], prev_members: Raw | None
) -> GitReaders:
    """Bind the planner's two git-backed reads over every present repository; every agent-authored tree resolves through the gateway first, and one unreadable repository fails the read closed."""
    layout, review, exclude_globs = (
        install.layout,
        install.review,
        install.exclude_globs,
    )
    member_sets = [c for c in changesets if c.member_path is not None]
    by_path = {m.path: m for m in install.members}
    previous = prev_members or {}

    def prev_tree_of(changeset: ChangeSet) -> object:
        earlier = previous.get(by_path[str(changeset.member_path)].key)
        return earlier.get("tree_sha") if isinstance(earlier, dict) else None

    def delta(prev_tree: object, cur_tree: object) -> Raw | None:
        listings = [delta_numstat(prev_tree, cur_tree, exclude_globs)]
        listings.extend(
            delta_numstat(prev_tree_of(c), c.head, exclude_globs, c.member_path)
            for c in member_sets
        )
        if any(listing is None for listing in listings):
            return None
        return parse_numstat(
            "".join(str(listing) for listing in listings), layout, review
        )

    def reviewed(base_tree: object, tree: object) -> list[str] | None:
        listings = [tree_files(base_tree, tree, exclude_globs)]
        listings.extend(
            tree_files(c.base, prev_tree_of(c), exclude_globs, c.member_path)
            for c in member_sets
        )
        if any(listing is None for listing in listings):
            return None
        return [path for listing in listings for path in (listing or [])]

    return GitReaders(delta, reviewed)


def plan_basis(inputs: PlanInputs, plan: Plan) -> Raw:
    """Return the facts a review-plan records: the tree, the pass, the classification, the size, the history, the ladder's outputs."""
    features, history, context = inputs.features, inputs.history, inputs.context
    return {
        "tree_sha": inputs.tree_sha,
        "pass": context.pass_,
        "prev_tree_sha": context.prev_tree_sha,
        "files": basis_files(features, inputs.layout, inputs.review),
        **({} if inputs.members is None else {"members": inputs.members}),
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


def load_install() -> Install:
    """Load the install first, so a broken one fails loud before any argument or git fault."""
    layout = load_layout(SCRIPTS_DIR)
    return Install(
        layout,
        layout.review_config(),
        load_exclude_globs(SCRIPTS_DIR),
        load_members(SCRIPTS_DIR),
    )


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
    except (LayoutError, ChangeSetError, WorkspaceError) as exc:
        # A broken layout.toml or an argument naming no range is reported the
        # way every command reports a git failure: one stderr line, exit 1.
        report(args.cmd, str(exc))
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
