#!/usr/bin/env python3
"""score-change.py — deterministic feature extraction for the change grader.

This script extracts the *structural feature row* for a change and appends it to
the append-only handoff log as a `grader-features` record. It contains NO verdict
logic: it never decides clear/concern, never grades, never reads a hunk's meaning.
It extracts facts and persists one record. The grader (an LLM agent loading the
change-grading skill) decides, by reading the diff. Keeping decision out of the
script is load-bearing — see the change-grading skill.

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
     .scratch/handoff.jsonl records, and scripts/layout.toml. The base ref is
     explicit (--base); it is never an implicit HEAD~1.
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

Subcommand:
  extract   compute the feature row and append one `grader-features` record

Stdlib only.
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


def _validate_module_rules(rules):
    """Validate each module rule's shape and strategy at load time.

    Catches the two misconfigurations that would otherwise fail obscurely deep
    in the per-file diff loop: a rule missing `match`/`from` (a bare KeyError in
    _module_of), and an unknown `from` strategy (which _module_of would fall
    through, silently yielding module=None). Both are operator config errors,
    best surfaced where the loader already promises a well-formed config. The
    accepted strategies mirror the branches in _module_of. Returns the rules
    unchanged.
    """
    for i, rule in enumerate(rules):
        if "match" not in rule or "from" not in rule:
            raise ValueError(
                f"layout.toml: [[module]] entry {i} needs both 'match' and "
                f"'from' keys (got {sorted(rule)})"
            )
        strategy = rule["from"]
        if strategy not in ("dir", "maven") and not strategy.startswith("first-segment-after:"):
            raise ValueError(
                f"layout.toml: [[module]] entry {i} has unknown 'from' strategy "
                f"{strategy!r} (expected 'dir', 'maven', or 'first-segment-after:<prefix>')"
            )
    return rules


def _load_layout():
    """Load the per-project layout rules from the sibling layout.toml.

    The rules are declarative data, so a repo in any language forks the config,
    not the engine. TOML is read by the stdlib `tomllib` (Python 3.11+), keeping
    the script dependency-free. A missing or malformed layout.toml is a broken
    install, not a runtime data gap, so it raises here rather than nulling the
    feature row. A `[[module]]` entry missing `match` or `from` is validated
    here too, so a broken rule fails cleanly at load instead of as a bare
    KeyError deep in the per-file diff loop. The returned namespace exposes the
    four rule sets the classifier consumes (TEST, PROD_ROOTS, SENSITIVE, MODULE).
    """
    path = Path(__file__).resolve().parent / "layout.toml"
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return SimpleNamespace(
        TEST=raw.get("test", []),
        PROD_ROOTS=raw.get("prod_roots", []),
        SENSITIVE=raw.get("sensitive", []),
        MODULE=_validate_module_rules(raw.get("module", [])),
    )


layout = _load_layout()

SCRATCH = Path(".scratch")
HANDOFF = SCRATCH / "handoff.jsonl"

# Canonical environment for every git invocation — kills locale/timezone/
# quoting drift so two runs over the same refs agree byte-for-byte.
_GIT_ENV = {**os.environ, "LC_ALL": "C", "TZ": "UTC", "GIT_PAGER": "cat"}


def _git(*args, check=True, env=None):
    """Run a git command under the canonical environment; return stdout.

    Pass env to override the default canonical environment — e.g. the worktree
    snapshot adds a GIT_INDEX_FILE so it stages into a throwaway index. The
    `-c core.renames=true` override is inert for commands that ignore it (add,
    write-tree), so the same wrapper serves both diff and snapshot calls.
    """
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-c", "core.renames=true", *args],
        capture_output=True,
        text=True,
        env=_GIT_ENV if env is None else env,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _resolve_ref(ref):
    """Return the resolved SHA for ref, or None if it cannot be resolved.

    A ref starting with '-' is rejected outright: it cannot name a real commit
    and could only be an attempt to smuggle a git option into the argument list.
    """
    if not ref or ref.startswith("-"):
        return None
    try:
        out = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    except RuntimeError:
        return None
    out = out.strip()
    return out or None


def _snapshot_worktree():
    """Write a tree object capturing the full working-tree state and return its
    SHA, or None on failure.

    Stages every worktree file — tracked edits, deletions, and untracked
    non-ignored files — into a throwaway index under .scratch/tmp, then
    write-tree. `git add -A` honours .gitignore, so build output and scratch
    stay out. The real index and working tree are never read or written; the
    temp index is removed afterward. The resulting tree is content-addressed, so
    an unchanged working tree yields the same SHA on every run.
    """
    tmp_dir = SCRATCH / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_index = tmp_dir / "grader.index"
    try:
        tmp_index.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        return None

    # git resolves a relative GIT_INDEX_FILE against the repo toplevel, not the
    # cwd; make it absolute so the snapshot also works from a subdirectory.
    env = {**_GIT_ENV, "GIT_INDEX_FILE": str(tmp_index.resolve())}

    try:
        _git("add", "-A", env=env)
        tree = _git("write-tree", env=env).strip()
    except RuntimeError:
        return None
    finally:
        try:
            tmp_index.unlink()
        except OSError:
            pass
    return tree or None


# ---------------------------------------------------------------------------
# Classification (engine logic; data lives in scripts/layout.toml)
# ---------------------------------------------------------------------------


def _matches_any(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def _classify_kind(path):
    """Return the file's kind: 'test', 'prod', or 'unknown'.

    Precedence: test wins over prod. A file under no PROD_ROOT and matching no
    TEST glob is 'unknown' — never coerced to prod. Sensitivity is a separate
    overlay (see _sensitive).
    """
    if _matches_any(path, layout.TEST):
        return "test"
    if any(path.startswith(root) for root in layout.PROD_ROOTS):
        return "prod"
    return "unknown"


def _sensitive(path):
    return _matches_any(path, layout.SENSITIVE)


# Maven/Gradle src layout: the package root is .../src/{main,test}/<lang>.
# Compiled once at module load since _module_of runs per changed file.
_MAVEN_RE = re.compile(r"(.*?/src/(?:main|test)/[^/]+)/")


def _module_of(path):
    """Derive the module id for path via the first matching MODULE rule.

    Returns None when no rule matches (the file contributes to scatter only if
    it has a module identity; an unmatched path is left out of the module set
    but still recorded as a file with its own kind).
    """
    for rule in layout.MODULE:
        if not fnmatch.fnmatch(path, rule["match"]):
            continue
        strategy = rule["from"]
        if strategy == "dir":
            parent = str(Path(path).parent)
            return parent if parent != "." else path
        if strategy.startswith("first-segment-after:"):
            prefix = strategy.split(":", 1)[1]
            rest = path[len(prefix):] if path.startswith(prefix) else path
            seg = rest.split("/", 1)[0]
            return f"{prefix}{seg}" if seg else None
        if strategy == "maven":
            m = _MAVEN_RE.match(path)
            return m.group(1) if m else str(Path(path).parent)
    return None


# ---------------------------------------------------------------------------
# Git-derived structural features
# ---------------------------------------------------------------------------


def _diff_features(base_sha, head_sha, churn_ref, want_churn):
    """Return the git-derived portion of the feature row.

    head_sha may be a commit (--head mode) or the tree of a working-tree
    snapshot (default); both are valid right-hand sides for `git diff`. churn_ref
    is the commit tip used for the churn log range — distinct from head_sha,
    which can be a tree with no commit history. Every field is null when base_sha
    is None (no resolvable base => no diff), and so is the whole row when head_sha
    is None (the working-tree snapshot failed). May raise RuntimeError if a git
    command fails; the caller turns that into a clean CLI error rather than a
    traceback.
    """
    null_row = {
        "files": None,
        "files_changed": None,
        "modules": None,
        "module_count": None,
        "test_lines": None,
        "prod_lines": None,
        "test_prod_ratio": None,
        "hunks": None,
        "sensitive_paths": None,
        "unknown_paths": None,
        "binary_files": None,
        "churn": None,
    }
    if base_sha is None or head_sha is None:
        return null_row

    numstat = _git("diff", "--numstat", "--find-renames", base_sha, head_sha)
    unified = _git("diff", "--unified=0", "--find-renames", base_sha, head_sha)

    files = []
    modules = set()
    sensitive_paths = []
    unknown_paths = []
    binary_files = 0
    test_lines = 0
    prod_lines = 0

    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added_s, deleted_s, path = parts
        # Binary files report "-" for added/deleted: their line delta is
        # unknowable, so it stays null and does NOT contribute a false 0 to the
        # line totals (it is counted as a binary file instead).
        try:
            added = None if added_s == "-" else int(added_s)
            deleted = None if deleted_s == "-" else int(deleted_s)
        except ValueError:
            # Not git's documented numstat shape; skip rather than crash.
            continue
        kind = _classify_kind(path)
        module = _module_of(path)
        files.append(
            {
                "path": path,
                "added": added,
                "deleted": deleted,
                "kind": kind,
                "module": module,
                "sensitive": _sensitive(path),
            }
        )
        if module:
            modules.add(module)
        if _sensitive(path):
            sensitive_paths.append(path)
        if kind == "unknown":
            unknown_paths.append(path)
        if added is None or deleted is None:
            binary_files += 1
            continue
        changed = added + deleted
        if kind == "test":
            test_lines += changed
        elif kind == "prod":
            prod_lines += changed

    # Hunk count: every "@@" header in the unified diff is one hunk.
    hunks = sum(1 for ln in unified.splitlines() if ln.startswith("@@"))

    ratio = (test_lines / prod_lines) if prod_lines > 0 else None

    churn = None
    if want_churn and churn_ref:
        log = _git("log", "--format=%an", f"{base_sha}..{churn_ref}")
        authors = sorted({a for a in log.splitlines() if a})
        commits = sum(1 for a in log.splitlines() if a)
        churn = {"commits": commits, "authors": len(authors)}

    files.sort(key=lambda f: f["path"])
    return {
        "files": files,
        "files_changed": len(files),
        "modules": sorted(modules),
        "module_count": len(modules),
        "test_lines": test_lines,
        "prod_lines": prod_lines,
        "test_prod_ratio": ratio,
        "hunks": hunks,
        "sensitive_paths": sorted(sensitive_paths),
        "unknown_paths": sorted(unknown_paths),
        "binary_files": binary_files,
        "churn": churn,
    }


# ---------------------------------------------------------------------------
# Handoff-log-derived features (deterministic records; null if absent)
# ---------------------------------------------------------------------------

_REVIEWERS = (
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
)


def _read_handoff(req_id):
    """Read .scratch/handoff.jsonl records for req_id.

    Returns a dict of deterministic facts, every field null when the log is
    absent or unreadable. The records are append-only, so build-failure counts
    are never lost on success — the retry trail is the diagnostic. The log is
    streamed line by line and a single malformed line is skipped (not allowed
    to null the whole row).
    """
    null = {
        "build_passed": None,
        "reviewers": None,
        "build_retries": None,
        "consultations": None,
        "design_revisions": None,
    }
    if not HANDOFF.exists():
        return null

    records = []
    try:
        with HANDOFF.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip one bad line; don't null the whole row
                if obj.get("req_id") == req_id:
                    records.append(obj)
    except OSError:
        return null

    if not records:
        return null

    def indices_of_type(t):
        return [i for i, r in enumerate(records) if r.get("type") == t]

    # Latest design-block line bounds the current retry cycle.
    db_lines = indices_of_type("design-block")
    last_db = db_lines[-1] if db_lines else -1

    bf_lines = indices_of_type("build-failure")
    bp_lines = indices_of_type("build-pass")
    # build_passed: a build-pass exists that post-dates every build-failure in
    # the current cycle. Absent => null (the grader reads null as not gated).
    if bp_lines:
        last_bp = bp_lines[-1]
        later_bf = [i for i in bf_lines if i > last_bp]
        build_passed = len(later_bf) == 0
    else:
        build_passed = None

    build_retries = sum(1 for i in bf_lines if i > last_db)
    consultations = len(indices_of_type("consultation-request"))
    design_revisions = sum(
        1 for r in records if r.get("type") == "design-block" and r.get("supersedes_record_at")
    )

    reviewers = {}
    for who in _REVIEWERS:
        verdicts = [
            r.get("verdict")
            for r in records
            if r.get("type") == "review-feedback" and r.get("author") == who
        ]
        reviewers[who] = verdicts[-1] if verdicts else None
    if all(v is None for v in reviewers.values()):
        reviewers = None

    return {
        "build_passed": build_passed,
        "reviewers": reviewers,
        "build_retries": build_retries,
        "consultations": consultations,
        "design_revisions": design_revisions,
    }


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------


def cmd_extract(args):
    req_id = args.feature
    base_sha = _resolve_ref(args.base) if args.base else None

    # The commit the slice sits on — bounds the merge-base and the churn log.
    tip = _resolve_ref(args.head) if args.head != "WORKTREE" else _resolve_ref("HEAD")

    if args.head == "WORKTREE":
        head_kind = "worktree"
        head_sha = _snapshot_worktree()
        if head_sha is None:
            print(
                "extract: warning — could not snapshot the working tree; diff features are null",
                file=sys.stderr,
            )
    else:
        head_kind = "commit"
        head_sha = tip

    if base_sha and tip:
        mb = _git("merge-base", base_sha, tip, check=False).strip()
        if mb:
            base_sha = mb
        else:
            print(
                "extract: warning — no merge-base for base/head; diffing against the raw base ref",
                file=sys.stderr,
            )

    features = {"base_ref": base_sha, "head_ref": head_sha, "head_kind": head_kind}
    try:
        features.update(_diff_features(base_sha, head_sha, tip, args.churn))
    except RuntimeError as err:
        print(f"extract: git command failed: {err}", file=sys.stderr)
        return 1
    features.update(_read_handoff(req_id))

    record = {
        "type": "grader-features",
        "req_id": req_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "author": "change-grader",
        "features": features,
    }

    SCRATCH.mkdir(exist_ok=True)
    with HANDOFF.open("a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")

    print(f"extract: appended grader-features record for {req_id} to {HANDOFF}")
    if base_sha is None:
        print("extract: base ref unresolved — diff features are null (-> concern)")
    elif head_sha is None:
        print("extract: working-tree snapshot failed — diff features are null (-> concern)")
    else:
        print(
            f"extract: {features['files_changed']} files, "
            f"{features['module_count']} modules, {features['hunks']} hunks, "
            f"build_passed={features['build_passed']}, "
            f"unknown_paths={len(features['unknown_paths'])}"
        )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="compute the row and append a grader-features record")
    p_extract.add_argument("--feature", required=True, help="req_id, e.g. REQ-CBA-108")
    p_extract.add_argument("--base", default="main", help="base ref to diff against (default: main)")
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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
