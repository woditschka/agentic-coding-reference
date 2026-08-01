#!/usr/bin/env python3
"""grading.py — deterministic feature extraction for the change grader.

This tool extracts the *structural feature row* for a change and appends it to
the append-only handoff log as a `grader-features` record. It contains NO verdict
logic: it never decides clear/concern, never grades, never reads a hunk's meaning.
It extracts facts and persists one record. The grader (an LLM agent loading the
change-grading skill) decides, by reading the diff. Keeping decision out of the
script is load-bearing — see the change-grading skill.

This file is the CLI entry point — a launcher over the grading package composed
on the change-set layer (the changeset package) (ADR 2026-07-17
runtime-package-layout; renamed from score-change.py to match the change-grading
artifact family). The logic lives in four grading modules plus the shared
changeset gateway:

  grading.config         the layout-config ACL — loads and validates the
                         grading slices of scripts/layout.toml (classification,
                         the reviewer floor, [review])
  grading.features       the feature model — classification and the
                         diff/delta/basis row builders (reads every diff through
                         the changeset git gateway)
  grading.handoff_facts  the handoff-log gateway — reads degrade, writes go
                         through the handoff package's validator API
  grading.planner        the pure risk ladder — plan context, surface roster,
                         first-pass and fix-cycle derivation (git reads
                         injected by this launcher)
  changeset.git_facts    the git gateway (shared with the emit verb) —
                         canonical-env runs, ref/tree hardening, the worktree
                         snapshot, exclude pathspecs
  changeset.emit         the base-ref rule (base_arg) this launcher reuses so
                         the grader's row and a reviewer's diff share one base

The grader runs before the human commits, so by default the change under review
lives in the working tree, not in any commit. `extract` therefore snapshots the
live working tree (tracked edits plus untracked, non-ignored files) into a
throwaway index, writes a tree object from it, and diffs base..<that tree>. The
real index and working tree are never touched. Pass --head <ref> to diff a
committed range instead (post-hoc grading of an already-committed slice).

Determinism contract (see the change-grading skill):
  1. A feature row is a pure function of pinned inputs: the resolved base ref,
     the head (a committed --head ref, or the content-addressed tree of the
     working-tree snapshot — identical worktree content yields the identical
     tree SHA, so two runs over an unchanged tree agree), the
     .scratch/handoff.jsonl records, and scripts/layout.toml. The base ref
     defaults to HEAD for the live worktree flow (the uncommitted delta) and is
     otherwise explicit (--base); it is never an implicit HEAD~1.
  2. No nondeterministic sources enter the row: no model, no network, no
     randomness, no wall-clock. (The record carries a `ts` field as metadata;
     it is not a feature and does not affect the structural row.)
  3. Git runs under a canonical environment (LC_ALL=C, TZ=UTC, quotepath off)
     and every collected list is sorted before emit.
  4. Missing data emits null, never a false zero. Shallow clone (no churn),
     unresolved base (no diff), unreadable handoff log, or a binary file with
     no line delta -> the affected field is null, which the grader reads as
     concern.

The grader is advisory-only. There is no calibration loop, shadow log, or
auto-approval automation in this version; those are future work (see the skill
§ Scope and non-goals).

Subcommands:
  extract      compute the feature row and append one `grader-features` record
  review-plan  estimate review risk and append a review-plan record naming the
               roster and read scope for the next review pass

The change set defaults to the uncommitted working tree against HEAD (the delta
on whatever branch); --base overrides it for a post-hoc committed range. The
grader and a reviewer resolve it through one definition — the base rule and git
gateway live in the changeset package, and `changeset.py` emits the same diff a
reviewer reads — so both judge byte-identical content.

Stdlib only.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

# The grading package resolves via this script's own directory — the directory
# python already puts on sys.path when grading.py is run as a script. When it
# is loaded by path instead (a test loader) from another cwd, that entry is
# absent, so add it here before the package imports below; this keeps the
# tool's cwd-independence (ADR 2026-07-17 runtime-package-layout).
if (_HERE := str(Path(__file__).resolve().parent)) not in sys.path:
    sys.path.insert(0, _HERE)

# --- Composition (ADR 2026-07-17 runtime-package-layout) --------------------
# This entry point is a launcher: it composes the grading package over the
# change-set layer (the changeset package). It imports only the names its cmd_*
# layer uses, submodule-form (never bare `import grading`, which a solo strict
# run would resolve to this file). The base-ref rule (base_arg) and the git
# gateway come from changeset — the same definitions the emit verb resolves, so
# the grader's row and a reviewer's diff share one base and one gateway. The
# planner's git-backed fix-cycle reads are injected here — the composition
# point — so the ladder itself stays pure.
from changeset.emit import base_arg
from changeset.git_facts import resolve_ref, run_git, snapshot_worktree
from grading.config import effective_roster, review_config
from grading.features import (
    basis_files,
    delta_features,
    diff_features,
    tree_files,
)
from grading.handoff_facts import (
    HANDOFF,
    append_validated,
    load_records,
    read_handoff,
)
from grading.planner import derive_plan, plan_context


def cmd_extract(args: Any) -> int:
    req_id = args.feature
    base, base_err = base_arg(args)
    if base_err:
        print(f"extract: {base_err}", file=sys.stderr)
        return 1
    base_sha = resolve_ref(base)

    # The commit the slice sits on — bounds the merge-base and the churn log.
    tip = resolve_ref(args.head) if args.head != "WORKTREE" else resolve_ref("HEAD")

    if args.head == "WORKTREE":
        head_kind = "worktree"
        head_sha = snapshot_worktree()
        if head_sha is None:
            print(
                "extract: warning — could not snapshot the working tree; diff features are null",
                file=sys.stderr,
            )
    else:
        head_kind = "commit"
        head_sha = tip

    if base_sha and tip:
        mb = run_git("merge-base", base_sha, tip, check=False).strip()
        if mb:
            base_sha = mb
        else:
            print(
                "extract: warning — no merge-base for base/head; diffing against the raw base ref",
                file=sys.stderr,
            )

    features: dict[str, Any] = {
        "base_ref": base_sha,
        "head_ref": head_sha,
        "head_kind": head_kind,
    }
    try:
        features.update(diff_features(base_sha, head_sha, tip, args.churn))
    except RuntimeError as exc:
        print(f"extract: git command failed: {exc}", file=sys.stderr)
        return 1
    features.update(read_handoff(req_id))

    record: dict[str, Any] = {
        "type": "grader-features",
        "req_id": req_id,
        "author": "change-grader",
        "features": features,
    }

    # The grader owns this write: grader-features is a terminal advisory record
    # (it never routes), so it is appended here rather than through handoff.py's
    # stdin CLI. It still goes through that engine's schema check and canonical
    # serializer — an unvalidated append (e.g. a malformed --feature) would fail
    # handoff.py validate and wedge every gate query over the log.
    err = append_validated(record, "grader-features", "extract")
    if err:
        return 1

    print(f"extract: appended grader-features record for {req_id} to {HANDOFF}")
    if base_sha is None:
        print("extract: base ref unresolved — diff features are null (-> concern)")
    elif head_sha is None:
        print(
            "extract: working-tree snapshot failed — diff features are null (-> concern)"
        )
    else:
        print(
            f"extract: {features['files_changed']} files, "
            f"{features['module_count']} modules, {features['hunks']} hunks, "
            f"build_passed={features['build_passed']}, "
            f"unknown_paths={len(features['unknown_paths'])}"
        )
    return 0


def cmd_review_plan(args: Any) -> int:
    req_id = args.feature
    base, base_err = base_arg(args)
    if base_err:
        print(f"review-plan: {base_err}", file=sys.stderr)
        return 1
    base_sha = resolve_ref(base)
    tip = resolve_ref("HEAD") if args.head == "WORKTREE" else resolve_ref(args.head)
    head_sha = snapshot_worktree() if args.head == "WORKTREE" else tip
    if base_sha and tip:
        mb = run_git("merge-base", base_sha, tip, check=False).strip()
        if mb:
            base_sha = mb

    try:
        features = diff_features(base_sha, head_sha, tip, False)
    except RuntimeError as err:
        print(f"review-plan: git command failed: {err}", file=sys.stderr)
        return 1

    history = read_handoff(req_id)
    ctx = plan_context(load_records(req_id))
    cfg = review_config()
    roster = effective_roster()

    if cfg["mode"] == "always-full":
        result = {
            "risk": "high",
            "roster": list(roster),
            "scope": "full-diff",
            "rationale": "review.mode = always-full; full battery",
            "triggers": ["mode-always-full"],
            "open_findings": None,
        }
    else:
        # The two injected readers MUST be the tree-sha-hardening ones
        # (features.delta_features/tree_files, which resolve every untrusted
        # tree through git_facts.resolve_tree before it reaches git). The
        # planner trusts its readers to harden; a reader that skipped
        # resolve_tree would hand an agent-authored tree_sha straight to git
        # argv. These two are that guarantee — do not swap in an un-hardened
        # reader here.
        result = derive_plan(
            features,
            history,
            ctx,
            roster,
            cfg,
            head_sha,
            delta_features,
            tree_files,
            base_sha=base_sha,
        )

    basis = {
        "tree_sha": head_sha,
        "pass": ctx["pass"],
        "prev_tree_sha": ctx["prev_tree_sha"],
        "files": basis_files(features, cfg),
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
        "open_findings": result.get("open_findings"),
        "triggers": result.get("triggers"),
    }
    record: dict[str, Any] = {
        "type": "review-plan",
        "req_id": req_id,
        "author": "review-plan-engine",
        "risk": result["risk"],
        "scope": result["scope"],
        "basis": basis,
        "rationale": result["rationale"],
    }
    if result["roster"] is not None:
        record["roster"] = result["roster"]

    if append_validated(record, "review-plan", "review-plan"):
        return 1
    shown = "—" if result["roster"] is None else ",".join(result["roster"]) or "(empty)"
    print(
        f"review-plan: appended {result['risk']} plan for {req_id} "
        f"(pass={ctx['pass']}, scope={result['scope']}, roster={shown})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser(
        "extract", help="compute the row and append a grader-features record"
    )
    p_extract.add_argument("--feature", required=True, help="req_id, e.g. REQ-CBA-108")
    p_extract.add_argument(
        "--base",
        default=None,
        help="base ref to diff against (default: HEAD for the live worktree; "
        "required when --head names a committed range)",
    )
    p_extract.add_argument(
        "--head",
        default="WORKTREE",
        help="head to diff: a commit ref for post-hoc grading, or the default "
        "WORKTREE to snapshot the uncommitted working tree",
    )
    p_extract.add_argument(
        "--churn",
        action="store_true",
        help="include churn (commit/author count); slower, needs full history",
    )
    p_extract.set_defaults(func=cmd_extract)

    p_rp = sub.add_parser(
        "review-plan",
        help="estimate review risk and append a review-plan record naming the "
        "roster and read scope for the next review pass",
    )
    p_rp.add_argument("--feature", required=True, help="req_id, e.g. REQ-CBA-108")
    p_rp.add_argument(
        "--base",
        default=None,
        help="base ref to diff against (default: HEAD for the live worktree)",
    )
    p_rp.add_argument(
        "--head",
        default="WORKTREE",
        help="head to diff: the default WORKTREE snapshot, or a commit ref",
    )
    p_rp.set_defaults(func=cmd_review_plan)

    args = parser.parse_args(argv)
    # args.func is the subparser-bound cmd_* handler; each returns an int exit
    # code. The annotated local narrows the Any that Namespace attribute access
    # yields, so the return stays int-typed.
    exit_code: int = args.func(args)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
