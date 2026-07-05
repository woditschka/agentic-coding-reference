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
  extract     compute the feature row and append one `grader-features` record
  changeset   emit the change set under review (uncommitted tree vs HEAD) — the
              single definition the reviewer roster and this grader both resolve

The change set defaults to the uncommitted working tree against HEAD (the delta
on whatever branch); --base overrides it for a post-hoc committed range. Both
subcommands share the snapshot, base resolution, and exclude_globs filter, so a
reviewer and the grader judge byte-identical content.

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
    exclude = raw.get("exclude_globs", [])
    if not isinstance(exclude, list) or not all(isinstance(g, str) for g in exclude):
        raise ValueError(
            "layout.toml: exclude_globs must be a list of glob strings "
            f"(got {exclude!r})"
        )
    return SimpleNamespace(
        TEST=raw.get("test", []),
        PROD_ROOTS=raw.get("prod_roots", []),
        SENSITIVE=raw.get("sensitive", []),
        EXCLUDE=exclude,
        MODULE=_validate_module_rules(raw.get("module", [])),
    )


# Loaded lazily by _get_layout() on first use — see below. Kept a public module
# global (not loaded at import) so a unit test can both import this engine
# without a sibling layout.toml AND inject rules by assigning `layout` directly.
layout = None


def _get_layout():
    """Return the layout rules, loading and caching them on first use.

    Deferred (not loaded at import) so the module imports without a sibling
    layout.toml; the load still happens before any classification, inside
    cmd_extract's call chain. A test may pre-set the module global `layout` to a
    fake to bypass the load entirely.
    """
    global layout
    if layout is None:
        layout = _load_layout()
    return layout


SCRATCH = Path(".scratch")
HANDOFF = SCRATCH / "handoff.jsonl"
SCHEMAS = "schemas/scratch"
LAYOUT_FOR_SCHEMAS = "scripts/layout.toml"


def _load_handoff():
    """Load the sibling handoff.py engine by file path.

    The grader owns the grader-features append, but the record must not bypass
    the log's validation: one malformed append would wedge every validated gate
    query until the log is hand-repaired. Reusing handoff.py's schema check and
    canonical serializer keeps this writer byte-compatible with `handoff.py
    append`. Loaded by path (not `import handoff`) so it works under any cwd or
    test loader; loaded lazily so `changeset` runs never need it.
    """
    import importlib.util

    path = Path(__file__).resolve().parent / "handoff.py"
    spec = importlib.util.spec_from_file_location("handoff", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

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
    if _matches_any(path, _get_layout().TEST):
        return "test"
    if any(path.startswith(root) for root in _get_layout().PROD_ROOTS):
        return "prod"
    return "unknown"


def _sensitive(path):
    return _matches_any(path, _get_layout().SENSITIVE)


# Maven/Gradle src layout: the package root is .../src/{main,test}/<lang>.
# Compiled once at module load since _module_of runs per changed file.
_MAVEN_RE = re.compile(r"(.*?/src/(?:main|test)/[^/]+)/")


def _module_of(path):
    """Derive the module id for path via the first matching MODULE rule.

    Returns None when no rule matches (the file contributes to scatter only if
    it has a module identity; an unmatched path is left out of the module set
    but still recorded as a file with its own kind).
    """
    for rule in _get_layout().MODULE:
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


def _exclude_pathspecs():
    """Return git pathspec args dropping the project's `exclude_globs`, or [].

    `git add -A` in the snapshot already honours .gitignore, so build output and
    .scratch stay out. `exclude_globs` is the additional project-declared filter
    (tracked-but-irrelevant paths: vendored trees, generated-yet-committed
    files). Expressed as exclude pathspecs so the same filter applies to every
    diff the change set is read through — numstat, unified, name-only — keeping
    the reviewer's view and the grader's row identical. Empty list => no
    pathspec, i.e. the whole diff.

    The pathspec is repo-root-relative (`:(top)`) so the change set is the same
    from any working directory, and uses glob magic (`:(glob)`) so a glob means
    what layout.toml documents for every other list — `/` is significant and
    `**` crosses directories — rather than git's default pathspec matching.
    """
    globs = _get_layout().EXCLUDE
    if not globs:
        return []
    return ["--", ":(top)", *(f":(top,glob,exclude){g}" for g in globs)]


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

    ex = _exclude_pathspecs()
    numstat = _git("diff", "--numstat", "--find-renames", base_sha, head_sha, *ex)
    unified = _git("diff", "--unified=0", "--find-renames", base_sha, head_sha, *ex)

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

# The mandatory reviewer floor (brief-expectations.toml [reviewers] floor).
# These keys are always present in the reviewers row — null when a floor
# reviewer has not spoken. Declared extra_reviewers are not enumerated here:
# any other review-feedback author found in the log enters the row too (see
# _read_handoff), so an extra reviewer's verdict is never silently dropped.
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

    # Floor reviewers are always present (null when silent); every other
    # review-feedback author — a declared extra reviewer gates the change too —
    # is added as encountered. Last verdict per author wins in both cases.
    reviewers = {who: None for who in _REVIEWERS}
    for r in records:
        if r.get("type") != "review-feedback":
            continue
        who = r.get("author")
        if isinstance(who, str) and who:
            reviewers[who] = r.get("verdict")
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


def _base_arg(args):
    """The base ref to diff against, or (None, error).

    Defaults to HEAD for the live worktree flow — the uncommitted delta on
    whatever branch. A committed --head with no explicit --base is an error: the
    HEAD default would diff that commit against itself (merge-base(HEAD, HEAD) is
    HEAD) and silently emit an empty range, hiding the change instead of grading
    it. Post-hoc grading therefore requires the caller to name the range's start.
    """
    if args.base is not None:
        return args.base, None
    if args.head == "WORKTREE":
        return "HEAD", None
    return None, ("a committed --head needs an explicit --base "
                  "(the start of the range to grade)")


def cmd_extract(args):
    req_id = args.feature
    base_arg, base_err = _base_arg(args)
    if base_err:
        print(f"extract: {base_err}", file=sys.stderr)
        return 1
    base_sha = _resolve_ref(base_arg)

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

    # The grader owns this write: grader-features is a terminal advisory record
    # (it never routes), so it is appended here rather than through handoff.py's
    # stdin CLI. It still goes through that engine's schema check and canonical
    # serializer — an unvalidated append (e.g. a malformed --feature) would fail
    # handoff.py validate and wedge every gate query over the log. Mirror the
    # newline-safety too, so a prior record missing its trailing newline is
    # never glued onto this one.
    handoff = _load_handoff()
    try:
        schema = handoff.load_schema(
            SCHEMAS, "grader-features", handoff.read_layout(LAYOUT_FOR_SCHEMAS)
        )
    except handoff.SchemaError as err:
        print(f"extract: {err}", file=sys.stderr)
        return 1
    schema_errors = handoff.validate_record(record, schema)
    if schema_errors:
        for err in schema_errors:
            print(f"extract: {err}", file=sys.stderr)
        print("extract: record failed validation — nothing appended", file=sys.stderr)
        return 1
    line = handoff.dumps_canonical(handoff.canonicalize(record, schema, schema))
    SCRATCH.mkdir(exist_ok=True)
    payload = line + "\n"
    if HANDOFF.exists() and HANDOFF.stat().st_size > 0:
        with HANDOFF.open("rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                payload = "\n" + payload
    with HANDOFF.open("a", encoding="utf-8") as fh:
        fh.write(payload)

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


def _resolve_changeset(args):
    """Resolve (base_sha, head_sha, error) for the change set.

    Shared by the changeset emit and reusable for any consumer of the same
    definition: snapshot the working tree (default) or resolve a committed
    --head, then narrow base to the merge-base so the diff is the delta, not a
    superset. base defaults to HEAD for the live worktree flow; a committed
    --head with no --base is rejected (see _base_arg). On error the shas are
    None and error is a message.
    """
    base_arg, base_err = _base_arg(args)
    if base_err:
        return None, None, base_err
    base_sha = _resolve_ref(base_arg)
    tip = _resolve_ref(args.head) if args.head != "WORKTREE" else _resolve_ref("HEAD")
    if args.head == "WORKTREE":
        head_sha = _snapshot_worktree()
    else:
        head_sha = tip
    if base_sha and tip:
        mb = _git("merge-base", base_sha, tip, check=False).strip()
        if mb:
            base_sha = mb
    return base_sha, head_sha, None


def cmd_changeset(args):
    """Emit the change set under review — the reviewer/grader shared definition.

    Default: the uncommitted working tree vs HEAD, filtered by exclude_globs.
    --name-only prints changed paths (the review's scope); otherwise the unified
    diff (the hunks). A reviewer reads this instead of an ad-hoc `git diff`, so
    its view matches the grader's row exactly. Unresolved base or a failed
    snapshot exits non-zero rather than emitting a misleading empty diff.
    """
    base_sha, head_sha, err = _resolve_changeset(args)
    if err:
        print(f"changeset: {err}", file=sys.stderr)
        return 1
    if base_sha is None or head_sha is None:
        print(
            "changeset: base ref or working-tree snapshot unresolved; no diff emitted",
            file=sys.stderr,
        )
        return 1
    ex = _exclude_pathspecs()
    try:
        if args.name_only:
            out = _git("diff", "--name-only", "--find-renames", base_sha, head_sha, *ex)
        else:
            out = _git("diff", "--find-renames", base_sha, head_sha, *ex)
    except RuntimeError as err:
        print(f"changeset: git command failed: {err}", file=sys.stderr)
        return 1
    sys.stdout.write(out)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="compute the row and append a grader-features record")
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

    p_cs = sub.add_parser(
        "changeset",
        help="emit the change set (uncommitted tree vs base) for review",
    )
    p_cs.add_argument(
        "--base",
        default=None,
        help="base ref to diff against (default: HEAD for the live worktree; "
        "required when --head names a committed range)",
    )
    p_cs.add_argument(
        "--head",
        default="WORKTREE",
        help="head to diff: the default WORKTREE snapshot, or a commit ref for "
        "a post-hoc committed range",
    )
    p_cs.add_argument(
        "--name-only",
        action="store_true",
        dest="name_only",
        help="print changed paths only (the review's scope), not the unified diff",
    )
    p_cs.set_defaults(func=cmd_changeset)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
