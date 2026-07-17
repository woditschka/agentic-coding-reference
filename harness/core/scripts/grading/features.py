"""grading.features — the structural feature model of a change.

Classification (kind / module / sensitive / review surface) is a pure function
of a path and the loaded layout rules; the row builders (diff_features,
delta_features, tree_files) gather their facts through the git gateway. The
model contains NO verdict logic: it never decides clear/concern, never grades,
never reads a hunk's meaning — it extracts facts (see the change-grading
skill).

Stdlib only.
"""

import fnmatch
import re
from pathlib import Path
from typing import Any

from changeset.git_facts import exclude_pathspecs, resolve_tree, run_git

from .config import get_layout

# A first-pass low/gray plan carries its per-file list so the next fix cycle can
# verify containment against it. A large diff is never low/gray (it trips
# oversize -> high), so capping the list keeps the record proportional without
# losing the containment anchor the cheap paths rely on.
_BASIS_FILE_CAP = 25


def _matches_any(path: str, globs: Any) -> bool:
    return any(fnmatch.fnmatch(path, g) for g in globs)


def classify_kind(path: str) -> str:
    """Return the file's kind: 'test', 'prod', or 'unknown'.

    Precedence: test wins over prod. A file under no PROD_ROOT and matching no
    TEST glob is 'unknown' — never coerced to prod. Sensitivity is a separate
    overlay (see is_sensitive).
    """
    if _matches_any(path, get_layout().TEST):
        return "test"
    if any(path.startswith(root) for root in get_layout().PROD_ROOTS):
        return "prod"
    return "unknown"


def is_sensitive(path: str) -> bool:
    return _matches_any(path, get_layout().SENSITIVE)


# Maven/Gradle src layout: the package root is .../src/{main,test}/<lang>.
# Compiled once at module load since module_of runs per changed file.
_MAVEN_RE = re.compile(r"(.*?/src/(?:main|test)/[^/]+)/")


def module_of(path: str) -> str | None:
    """Derive the module id for path via the first matching MODULE rule.

    Returns None when no rule matches (the file contributes to scatter only if
    it has a module identity; an unmatched path is left out of the module set
    but still recorded as a file with its own kind).
    """
    for rule in get_layout().MODULE:
        if not fnmatch.fnmatch(path, rule["match"]):
            continue
        strategy = rule["from"]
        if strategy == "dir":
            parent = str(Path(path).parent)
            return parent if parent != "." else path
        if strategy.startswith("first-segment-after:"):
            prefix = strategy.split(":", 1)[1]
            rest = path[len(prefix) :] if path.startswith(prefix) else path
            seg = rest.split("/", 1)[0]
            return f"{prefix}{seg}" if seg else None
        if strategy == "maven":
            m = _MAVEN_RE.match(path)
            return m.group(1) if m else str(Path(path).parent)
    return None


def review_kind(path: str, cfg: dict[str, Any]) -> str:
    """The review surface a changed file presents: docs, test, config, prod, or
    unknown. Precedence docs > test > config > prod: a markdown file under a
    production root is documentation, a data file is config, and anything that
    matches no positive rule is unknown — which trips the full battery, never a
    silent omission. Kept separate from classify_kind (test/prod/unknown) so
    the grader's frozen classification contract is untouched."""
    if _matches_any(path, cfg["docs"]):
        return "docs"
    if _matches_any(path, get_layout().TEST):
        return "test"
    if _matches_any(path, cfg["config"]):
        return "config"
    if any(path.startswith(root) for root in get_layout().PROD_ROOTS):
        return "prod"
    return "unknown"


def diff_features(
    base_sha: str | None,
    head_sha: str | None,
    churn_ref: str | None,
    want_churn: Any,
) -> dict[str, Any]:
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
    null_row: dict[str, Any] = {
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

    ex = exclude_pathspecs()
    numstat = run_git("diff", "--numstat", "--find-renames", base_sha, head_sha, *ex)
    unified = run_git("diff", "--unified=0", "--find-renames", base_sha, head_sha, *ex)

    files: list[dict[str, Any]] = []
    modules: set[str] = set()
    sensitive_paths: list[str] = []
    unknown_paths: list[str] = []
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
        kind = classify_kind(path)
        module = module_of(path)
        files.append(
            {
                "path": path,
                "added": added,
                "deleted": deleted,
                "kind": kind,
                "module": module,
                "sensitive": is_sensitive(path),
            }
        )
        if module:
            modules.add(module)
        if is_sensitive(path):
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

    churn: dict[str, int] | None = None
    if want_churn and churn_ref:
        log = run_git("log", "--format=%an", f"{base_sha}..{churn_ref}")
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


def parse_numstat(numstat: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Fold numstat output into the delta-feature dict. Split out from
    delta_features so the parse is testable without a git fixture. The line
    count uses the first-pass oversize metric — classify_kind's production
    and test lines — so both rungs of the size ladder measure the same
    quantity. review_kind feeds only the kinds list (roster matching); a
    config file under a prod root counts toward size like the first pass
    counts it, or delta-oversize would miss what oversize catches."""
    paths: list[str] = []
    kinds: list[str] = []
    sensitive = False
    binary = False
    lines = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        paths.append(path)
        kinds.append(review_kind(path, cfg))
        if is_sensitive(path):
            sensitive = True
        if added == "-" or deleted == "-":
            binary = True
        elif classify_kind(path) in ("prod", "test"):
            try:
                lines += int(added) + int(deleted)
            except ValueError:
                # Not git's documented numstat shape; count nothing rather
                # than crash — mirrors diff_features' guard.
                pass
    return {
        "paths": paths,
        "kinds": kinds,
        "sensitive": sensitive,
        "binary": binary,
        "lines": lines,
    }


def delta_features(
    prev_tree: Any, cur_tree: Any, cfg: dict[str, Any]
) -> dict[str, Any] | None:
    """The fix delta between two snapshot trees: changed paths, their review
    kinds, the production/test line count, and whether any path is sensitive
    or binary. None when the diff cannot be computed (which forces the fix
    pass to fail closed).

    prev_tree comes from an agent-authored review-plan record (untrusted), so it
    is resolved through resolve_tree before reaching git — the same hardening
    the --base-tree CLI path applies. Resolution yields a bare 40-hex SHA or
    None, so a crafted value like "--output=<file>" cannot smuggle a git option
    into the diff (it fails resolution and the pass falls closed to the full
    battery). cur_tree is our own worktree snapshot but is resolved too, for
    symmetry and defense in depth."""
    if not prev_tree or not cur_tree:
        return None
    prev = resolve_tree(prev_tree)
    cur = resolve_tree(cur_tree)
    if prev is None or cur is None:
        return None
    try:
        ex = exclude_pathspecs()
        numstat = run_git("diff", "--numstat", "--find-renames", prev, cur, *ex)
    except RuntimeError:
        return None
    return parse_numstat(numstat, cfg)


def tree_files(base: Any, tree: Any) -> list[str] | None:
    """The file list a prior full-diff pass reviewed: every path changed
    between the slice base and that pass's snapshot tree. Recomputed from git
    when the prior plan's basis was capped (files: null), keeping large-slice
    records small instead of storing the roster. Both refs pass through
    resolve_tree — base is untrusted-adjacent and tree comes from an
    agent-authored record. None when either fails to resolve or git errors
    (the fix pass then fails closed)."""
    if not base or not tree:
        return None
    b = resolve_tree(base)
    t = resolve_tree(tree)
    if b is None or t is None:
        return None
    try:
        out = run_git(
            "diff", "--name-only", "--find-renames", b, t, *exclude_pathspecs()
        )
    except RuntimeError:
        return None
    return [p for p in out.splitlines() if p]


def basis_files(
    features: dict[str, Any], cfg: dict[str, Any]
) -> list[dict[str, Any]] | None:
    """The per-file review classification for the plan's basis, or null for a
    diff too large to carry (which is always a high plan anyway)."""
    files = features.get("files")
    if files is None or len(files) > _BASIS_FILE_CAP:
        return None
    return [
        {
            "path": f["path"],
            "review_kind": review_kind(f["path"], cfg),
            "module": f.get("module"),
            "sensitive": f.get("sensitive"),
        }
        for f in files
    ]
