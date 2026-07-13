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
from pathlib import Path
from types import SimpleNamespace

# A resolved tree object name: 40 (SHA-1) or 64 (SHA-256) lowercase hex digits.
# The same constraint the review-plan schema pins on the tree_sha fields, applied
# on the untrusted read path (a log field the schema does not re-validate).
_TREE_SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")


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
        REVIEW=raw.get("review", {}),
        EXTRA_REVIEWERS=raw.get("harness", {}).get("extra_reviewers", []),
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


def _resolve_tree(sha):
    """Return the resolved tree SHA for a raw tree object, or None.

    Distinct from _resolve_ref, which resolves commits: a review-plan's tree_sha
    is a bare tree (the worktree snapshot has no commit), so a fix-delta review
    diffs against it directly. Only a bare hex object name is accepted — this
    both blocks a '-'-prefixed value from smuggling a git option into the
    argument list and rejects a symbolic revision (HEAD, @{-1}, :/regex) that
    would otherwise diff the fix delta against an attacker-chosen tree and
    under-scope the roster. The engine writes only hex here (git output,
    schema-validated); the guard closes the untrusted read path the schema
    does not re-check."""
    if not isinstance(sha, str) or not _TREE_SHA_RE.match(sha):
        return None
    try:
        out = _git("rev-parse", "--verify", "--quiet", f"{sha}^{{tree}}", check=False)
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
        "review_roster": None,
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

    # The latest review-plan's roster is the set of reviewers this pass actually
    # dispatched. The grader reads it so a floor reviewer silent because a
    # focused plan scoped it out is not misread as a hedge (change-grading
    # § reviewer_hedging). Null when no plan was recorded (full-battery default).
    review_roster = None
    for r in records:
        if r.get("type") == "review-plan":
            roster = r.get("roster")
            review_roster = roster if isinstance(roster, list) else None

    return {
        "build_passed": build_passed,
        "reviewers": reviewers,
        "review_roster": review_roster,
        "build_retries": build_retries,
        "consultations": consultations,
        "design_revisions": design_revisions,
    }


# ---------------------------------------------------------------------------
# Shared append: validate against the record's schema, write canonical form
# ---------------------------------------------------------------------------


def _append_validated(record, rtype, prefix):
    """Append one record to the handoff log through handoff.py's validator.

    Both engine writers here (grader-features, review-plan) are records the
    grader/router own, so they append directly rather than through handoff.py's
    stdin CLI — but they must not bypass the log's validation: one malformed
    append wedges every gate query until the log is hand-repaired. This routes
    through handoff.py's schema check and canonical serializer so the write is
    byte-compatible with `handoff.py append`, and mirrors its newline-safety so
    a prior record missing its trailing newline is never glued onto this one.
    Returns None on success, or an error message (already printed) on failure.
    It also mirrors the append-boundary ts stamp: handoff.ts_now() is the
    log's one clock, so the engine writers supply no ts of their own.
    """
    handoff = _load_handoff()
    record["ts"] = handoff.ts_now()
    try:
        schema = handoff.load_schema(
            SCHEMAS, rtype, handoff.read_layout(LAYOUT_FOR_SCHEMAS)
        )
    except handoff.SchemaError as err:
        print(f"{prefix}: {err}", file=sys.stderr)
        return str(err)
    schema_errors = handoff.validate_record(record, schema)
    if schema_errors:
        for err in schema_errors:
            print(f"{prefix}: {err}", file=sys.stderr)
        print(f"{prefix}: record failed validation — nothing appended", file=sys.stderr)
        return "record failed validation"
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
    return None


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
        "author": "change-grader",
        "features": features,
    }

    # The grader owns this write: grader-features is a terminal advisory record
    # (it never routes), so it is appended here rather than through handoff.py's
    # stdin CLI. It still goes through that engine's schema check and canonical
    # serializer — an unvalidated append (e.g. a malformed --feature) would fail
    # handoff.py validate and wedge every gate query over the log.
    err = _append_validated(record, "grader-features", "extract")
    if err:
        return 1

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
    --head with no --base is rejected (see _base_arg). --base-tree overrides all
    of this: it diffs a raw tree (a review-plan's tree_sha) against the worktree
    with no commit resolution or merge-base — the fix-delta scope a re-review
    reads. On error the shas are None and error is a message.
    """
    base_tree = getattr(args, "base_tree", None)
    if base_tree:
        tree = _resolve_tree(base_tree)
        if tree is None:
            return None, None, f"--base-tree {base_tree!r} is not a valid tree object"
        head_sha = _snapshot_worktree() if args.head == "WORKTREE" else _resolve_ref(args.head)
        return tree, head_sha, None
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


# ---------------------------------------------------------------------------
# review-plan: the risk-proportional review estimate
# ---------------------------------------------------------------------------

# The four-reviewer floor is the same tuple _read_handoff enumerates
# (_REVIEWERS above). A file's changed *review surface* maps to the dimensions
# that judge it: a reviewer joins a pass only when the change set contains
# surface its dimension reviews. doc-reviewer is dropped from a pure production
# change (small prod diffs route to the planner, not to a docs read).
_SURFACE_REVIEWERS = {
    "docs": ("doc-reviewer",),
    "test": ("test-reviewer", "code-quality-reviewer"),
    "config": ("code-quality-reviewer", "security-reviewer"),
    "prod": ("code-quality-reviewer", "test-reviewer", "security-reviewer"),
}

# An open finding's quality-bar clause implicates one reviewer's dimension, so a
# fix cycle re-runs that reviewer even when its own verdict was approved — the
# cross-dimension safety net (review-workflow reference.md § Quality-Bar Clause Mapping).
_BAR_CLAUSE_REVIEWER = {
    "secure-by-design": "security-reviewer",
    "operationally-honest": "security-reviewer",
    "correct": "test-reviewer",
    "tested-as-spec": "test-reviewer",
    "fit-for-purpose": "code-quality-reviewer",
    "legible-cold": "code-quality-reviewer",
    "consistent-with-codebase": "code-quality-reviewer",
    "spec-grounded": "doc-reviewer",
    "human-maintainable": "doc-reviewer",
}

# Review-kind default globs. fnmatch's `*` crosses `/`, so the bare `*.md`
# variant already matches any depth; the `**/` variants document intent. A
# project overrides these in layout.toml [review]. Config is data-file
# extensions only — never a `config/**` directory, which would misclassify
# production code that happens to live under it.
_DEFAULT_DOCS_GLOBS = ("**/*.md", "*.md", "docs/**")
_DEFAULT_CONFIG_GLOBS = (
    "**/*.toml", "*.toml", "**/*.yaml", "*.yaml",
    "**/*.yml", "*.yml", "**/*.json", "*.json",
)
_DEFAULT_SIZE_THRESHOLD = 80
# A first-pass low/gray plan carries its per-file list so the next fix cycle can
# verify containment against it. A large diff is never low/gray (it trips
# oversize -> high), so capping the list keeps the record proportional without
# losing the containment anchor the cheap paths rely on.
_BASIS_FILE_CAP = 25


def _review_config():
    """The [review] table from layout.toml, with fail-safe defaults.

    Every key is optional: an absent [review] table yields the built-in
    defaults, so the engine runs correctly on a project that never declared one.
    `mode = "always-full"` is the opt-out that reproduces pre-plan behavior.
    """
    raw = _get_layout().REVIEW or {}
    return {
        "docs": raw.get("docs", list(_DEFAULT_DOCS_GLOBS)),
        "config": raw.get("config", list(_DEFAULT_CONFIG_GLOBS)),
        "size_threshold": raw.get("size_threshold", _DEFAULT_SIZE_THRESHOLD),
        "mode": raw.get("mode", "risk"),
    }


def _effective_roster():
    """The four-reviewer floor plus declared extras, in roster order."""
    roster = list(_REVIEWERS)
    for extra in _get_layout().EXTRA_REVIEWERS or []:
        if isinstance(extra, str) and extra and extra not in roster:
            roster.append(extra)
    return roster


def _review_kind(path, cfg):
    """The review surface a changed file presents: docs, test, config, prod, or
    unknown. Precedence docs > test > config > prod: a markdown file under a
    production root is documentation, a data file is config, and anything that
    matches no positive rule is unknown — which trips the full battery, never a
    silent omission. Kept separate from _classify_kind (test/prod/unknown) so
    the grader's frozen classification contract is untouched."""
    if _matches_any(path, cfg["docs"]):
        return "docs"
    if _matches_any(path, _get_layout().TEST):
        return "test"
    if _matches_any(path, cfg["config"]):
        return "config"
    if any(path.startswith(root) for root in _get_layout().PROD_ROOTS):
        return "prod"
    return "unknown"


def _loc_path(location):
    """The file path an open finding's `location` names (path before ':line')."""
    if not isinstance(location, str):
        return None
    return location.split(":", 1)[0]


def _load_records(req_id):
    """Ordered (lineno, record) for req_id from the handoff log; [] if absent.

    A single malformed line is skipped, never allowed to drop the whole log —
    the same tolerance _read_handoff applies. 1-based line numbers so a record's
    position can anchor an ordering comparison (a plan is 'fix' when a prior
    review-plan sits before the current build-pass)."""
    if not HANDOFF.exists():
        return []
    out = []
    try:
        with HANDOFF.open() as fh:
            for no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("req_id") == req_id:
                    out.append((no, obj))
    except OSError:
        return []
    return out


def _plan_context(records):
    """What the pass about to be planned inherits from the log: whether a prior
    plan exists (first vs fix pass), the reviewed surface and tree it covered,
    and the dissenters and open findings of the round being responded to.

    The current build-pass is the anchor: the engine runs right after the
    implementer appends it. A review-plan before that build-pass means an
    earlier round already reviewed this slice, so this is a fix pass. The prior
    review round is the review-feedback between the previous build-pass and the
    current one."""
    def latest(rtype, before=None):
        match = None
        for no, rec in records:
            if rec.get("type") == rtype and (before is None or no < before):
                match = (no, rec)
        return match

    # A fix pass is one with a prior review-plan *since the latest design-block*
    # (the schema's definition of first vs fix). Bounding by the design-block is
    # load-bearing: a re-triage (superseding design-block + fresh build-pass)
    # starts a new cycle, so the previous cycle's plan must not be read as this
    # pass's prior — that would diff a stale pre-re-triage tree and pull
    # dissenters from the wrong round. Mirrors _read_handoff's last_db scoping.
    last_db = 0
    for no, rec in records:
        if rec.get("type") == "design-block":
            last_db = no

    cur_bp = latest("build-pass")
    cur_bp_line = cur_bp[0] if cur_bp else len(records) + 1
    prev_plan = None
    for no, rec in records:
        if rec.get("type") == "review-plan" and last_db < no < cur_bp_line:
            prev_plan = rec
    if prev_plan is None:
        return {"pass": "first", "prev_tree_sha": None, "reviewed_files": [],
                "dissenters": [], "open_findings": [], "critical_prior": False}

    prev_bp = latest("build-pass", before=cur_bp_line)
    prev_bp_line = prev_bp[0] if prev_bp else 0
    # The prior review round is the feedback between the previous build-pass and
    # the current one — never reaching across the design-block into an old cycle.
    window_start = max(prev_bp_line, last_db)
    dissenters, open_findings, critical = [], [], False
    for no, rec in records:
        if not (window_start < no < cur_bp_line) or rec.get("type") != "review-feedback":
            continue
        who = rec.get("author")
        if rec.get("verdict") != "approved" and who not in dissenters:
            dissenters.append(who)
        for finding in rec.get("findings", []) or []:
            if not isinstance(finding, dict):
                continue
            if finding.get("severity") == "critical":
                critical = True
            open_findings.append({
                "reviewer": who,
                "location": finding.get("location"),
                "tag": finding.get("tag"),
                "bar_clause": finding.get("bar_clause"),
                "severity": finding.get("severity"),
            })
    basis = prev_plan.get("basis") or {}
    reviewed = [f.get("path") for f in (basis.get("files") or []) if isinstance(f, dict)]
    return {"pass": "fix", "prev_tree_sha": basis.get("tree_sha"),
            "reviewed_files": reviewed, "dissenters": dissenters,
            "open_findings": open_findings, "critical_prior": critical}


def _delta_features(prev_tree, cur_tree, cfg):
    """The fix delta between two snapshot trees: changed paths, their review
    kinds, and whether any is sensitive or binary. None when the diff cannot be
    computed (which forces the fix pass to fail closed).

    prev_tree comes from an agent-authored review-plan record (untrusted), so it
    is resolved through _resolve_tree before reaching git — the same hardening
    the --base-tree CLI path applies. Resolution yields a bare 40-hex SHA or
    None, so a crafted value like "--output=<file>" cannot smuggle a git option
    into the diff (it fails resolution and the pass falls closed to the full
    battery). cur_tree is our own worktree snapshot but is resolved too, for
    symmetry and defense in depth."""
    if not prev_tree or not cur_tree:
        return None
    prev = _resolve_tree(prev_tree)
    cur = _resolve_tree(cur_tree)
    if prev is None or cur is None:
        return None
    try:
        ex = _exclude_pathspecs()
        numstat = _git("diff", "--numstat", "--find-renames", prev, cur, *ex)
    except RuntimeError:
        return None
    paths, kinds, sensitive, binary = [], [], False, False
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        paths.append(path)
        kinds.append(_review_kind(path, cfg))
        if _sensitive(path):
            sensitive = True
        if added == "-" or deleted == "-":
            binary = True
    return {"paths": paths, "kinds": kinds, "sensitive": sensitive, "binary": binary}


def _surface_roster(kinds, roster, cfg):
    """Floor reviewers whose dimension has surface among the changed review
    kinds, in roster order, plus every declared extra. Extras always join: an
    extra reviewer's dimension is project-specific with no surface map, so
    including it fails closed rather than silently skipping a declared gate."""
    want = set()
    for kind in kinds:
        want.update(_SURFACE_REVIEWERS.get(kind, ()))
    picked = [r for r in roster if r in _REVIEWERS and r in want]
    picked += [r for r in roster if r not in _REVIEWERS]
    return picked


def _plan_result(risk, roster, scope, rationale, triggers=None, open_findings=None):
    return {"risk": risk, "roster": roster, "scope": scope,
            "rationale": rationale, "triggers": triggers,
            "open_findings": open_findings}


def _derive_fix_plan(features, ctx, roster, cfg, tree_sha, base_triggers):
    """A re-review cycle: dissenters plus bar-clause-implicated reviewers read
    the fix delta, unless the fix escaped the reviewed surface or the delta is
    itself risky — then the full roster reads it (cold, when the surface grew)."""
    delta = _delta_features(ctx["prev_tree_sha"], tree_sha, cfg)
    dissenters = [r for r in roster if r in ctx["dissenters"]]
    widened = []
    for finding in ctx["open_findings"]:
        who = _BAR_CLAUSE_REVIEWER.get(finding.get("bar_clause"))
        if who and who in roster and who not in dissenters and who not in widened:
            widened.append(who)
    reviewers = [r for r in roster if r in set(dissenters) | set(widened)]

    triggers = list(base_triggers)
    escaped = False
    if delta is None:
        triggers.append("delta-unavailable")
    else:
        if delta["sensitive"]:
            triggers.append("delta-sensitive")
        if delta["binary"]:
            triggers.append("delta-binary")
        if any(k == "unknown" for k in delta["kinds"]):
            triggers.append("delta-unknown-surface")
        allowed = set(ctx["reviewed_files"]) | {
            _loc_path(f["location"]) for f in ctx["open_findings"] if f.get("location")
        }
        if any(p not in allowed for p in delta["paths"]):
            escaped = True
            triggers.append("delta-escaped-surface")

    if triggers:
        # An escaped surface (or an uncomputable delta) needs a cold full read;
        # a risky-but-contained delta gets the full roster over the delta only.
        cold = escaped or "delta-unavailable" in triggers
        scope = "full-diff" if cold else "fix-delta"
        return _plan_result(
            "high", list(roster), scope,
            f"fix-cycle risk ({', '.join(triggers)}); full roster",
            triggers=triggers, open_findings=ctx["open_findings"],
        )
    note = f" (widened for {', '.join(widened)})" if widened else ""
    return _plan_result(
        "low", reviewers, "fix-delta",
        f"fix contained to reviewed surface; dissenters re-review the delta{note}",
        triggers=triggers, open_findings=ctx["open_findings"],
    )


def _derive_plan(features, history, ctx, roster, cfg, tree_sha):
    """Apply the risk ladder to the change set and slice history, returning the
    plan fragment (risk, roster, scope, rationale, triggers). Fail-closed: any
    null diff feature, unclassifiable surface, or noisy history yields high with
    the full roster."""
    files = features.get("files")
    if files is None or tree_sha is None:
        return _plan_result("high", list(roster), "full-diff",
                            "diff features unavailable; full battery (fail-closed)",
                            triggers=["null-features"])

    kinds = [_review_kind(f["path"], cfg) for f in files]
    triggers = []
    if any(k == "unknown" for k in kinds):
        triggers.append("unknown-surface")
    if features.get("sensitive_paths"):
        triggers.append("sensitive")
    if features.get("binary_files"):
        triggers.append("binary")
    if (features.get("module_count") or 0) > 1:
        triggers.append("multi-module")
    size = (features.get("prod_lines") or 0) + (features.get("test_lines") or 0)
    if size > cfg["size_threshold"]:
        triggers.append("oversize")
    if (history.get("build_retries") or 0) >= 2:
        triggers.append("build-retries")
    if (history.get("design_revisions") or 0) >= 1:
        triggers.append("design-revision")
    if ctx["critical_prior"]:
        triggers.append("prior-critical")

    # A fix cycle with real dissenters routes through the delta logic; a fix
    # pass with none left (e.g. an autofix-only round) falls to the surface
    # logic below, treated as a fresh small change.
    if ctx["pass"] == "fix" and ctx["dissenters"]:
        return _derive_fix_plan(features, ctx, roster, cfg, tree_sha, triggers)

    if triggers:
        return _plan_result("high", list(roster), "full-diff",
                            f"risk triggers present ({', '.join(triggers)}); full battery",
                            triggers=triggers)
    if "prod" not in kinds:
        picked = _surface_roster(kinds, roster, cfg)
        if not picked:
            # A non-prod change that maps to no reviewer (no known surface, no
            # extras) has nothing to scope down to — fail closed to the full
            # battery rather than emit a low plan with an empty roster the
            # grader would misread as "nobody reviewed".
            return _plan_result("high", list(roster), "full-diff",
                                "changed surface maps to no reviewer; full battery",
                                triggers=["no-surface-match"])
        surfaces = ", ".join(sorted(set(kinds)))
        return _plan_result("low", picked, "full-diff",
                            f"non-production surface ({surfaces}); reviewers matched to changed surface",
                            triggers=[])
    return _plan_result("gray", None, "full-diff",
                        "small clean production change; planner judges roster and scope",
                        triggers=[])


def _basis_files(features, cfg):
    """The per-file review classification for the plan's basis, or null for a
    diff too large to carry (which is always a high plan anyway)."""
    files = features.get("files")
    if files is None or len(files) > _BASIS_FILE_CAP:
        return None
    return [{
        "path": f["path"],
        "review_kind": _review_kind(f["path"], cfg),
        "module": f.get("module"),
        "sensitive": f.get("sensitive"),
    } for f in files]


def cmd_review_plan(args):
    req_id = args.feature
    base_arg, base_err = _base_arg(args)
    if base_err:
        print(f"review-plan: {base_err}", file=sys.stderr)
        return 1
    base_sha = _resolve_ref(base_arg)
    tip = _resolve_ref("HEAD") if args.head == "WORKTREE" else _resolve_ref(args.head)
    head_sha = _snapshot_worktree() if args.head == "WORKTREE" else tip
    if base_sha and tip:
        mb = _git("merge-base", base_sha, tip, check=False).strip()
        if mb:
            base_sha = mb

    try:
        features = _diff_features(base_sha, head_sha, tip, False)
    except RuntimeError as err:
        print(f"review-plan: git command failed: {err}", file=sys.stderr)
        return 1

    history = _read_handoff(req_id)
    ctx = _plan_context(_load_records(req_id))
    cfg = _review_config()
    roster = _effective_roster()

    if cfg["mode"] == "always-full":
        result = _plan_result("high", list(roster), "full-diff",
                              "review.mode = always-full; full battery",
                              triggers=["mode-always-full"])
    else:
        result = _derive_plan(features, history, ctx, roster, cfg, head_sha)

    basis = {
        "tree_sha": head_sha,
        "pass": ctx["pass"],
        "prev_tree_sha": ctx["prev_tree_sha"],
        "files": _basis_files(features, cfg),
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
    record = {
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

    if _append_validated(record, "review-plan", "review-plan"):
        return 1
    shown = "—" if result["roster"] is None else ",".join(result["roster"]) or "(empty)"
    print(f"review-plan: appended {result['risk']} plan for {req_id} "
          f"(pass={ctx['pass']}, scope={result['scope']}, roster={shown})")
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
        "--base-tree",
        default=None,
        dest="base_tree",
        help="diff against a raw tree object (a review-plan's tree_sha) instead "
        "of a commit ref — the fix-delta scope a re-review reads",
    )
    p_cs.add_argument(
        "--name-only",
        action="store_true",
        dest="name_only",
        help="print changed paths only (the review's scope), not the unified diff",
    )
    p_cs.set_defaults(func=cmd_changeset)

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
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
