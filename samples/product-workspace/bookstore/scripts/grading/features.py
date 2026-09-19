"""Classify changed paths and build the structural feature rows of a change.

Classification is a pure function of a path and the layout; the row builders
gather their facts through the change-set git gateway. Nothing here decides:
the model extracts facts, and the grader reads the diff.
"""

import fnmatch
import re
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Literal, NamedTuple

from changeset.git_facts import (
    ChangeSet,
    exclude_pathspecs,
    globs_for,
    prefix_listing,
    prefix_numstat,
    resolve_tree,
    run_git,
)

from .config import NAMED_MODULE_LAYOUTS, Layout, Raw, ReviewConfig
from .conventions import changed_lines

Kind = Literal["test", "prod", "unknown"]
ReviewKind = Literal["docs", "test", "config", "prod", "unknown"]
KindOf = Callable[[str], Kind]

# A first-pass low/gray plan carries its per-file list so the next fix cycle
# can verify containment against it. A larger diff is never low/gray, so the
# cap keeps the record proportional without losing the containment anchor.
_BASIS_FILE_CAP = 25
_NUMSTAT_COLUMNS = 3
_NULL_ROW: Raw = {
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
    "security_surface_paths": None,
    "churn": None,
}


def classify_kind(path: str, layout: Layout) -> Kind:
    """Return test, prod, or unknown; test wins, and an unmatched path is never coerced to prod."""
    if _matches_any(path, layout.test_globs):
        return "test"
    if _under_prod_root(path, layout):
        return "prod"
    return "unknown"


def is_sensitive(path: str, layout: Layout) -> bool:
    """Return whether the path sits on the sensitive overlay."""
    return _matches_any(path, layout.sensitive)


def module_of(path: str, layout: Layout) -> str | None:
    """Derive the module id from the first matching rule; None when no rule matches."""
    for rule in layout.module_rules:
        if fnmatch.fnmatch(path, rule.match):
            return _module_by(rule.strategy, path)
    return None


def _module_by(strategy: str, path: str) -> str | None:
    if strategy in NAMED_MODULE_LAYOUTS:
        strategy = "regex:" + NAMED_MODULE_LAYOUTS[strategy]
    if strategy == "dir":
        parent = str(Path(path).parent)
        return parent if parent != "." else path
    if strategy.startswith("first-segment-after:"):
        prefix = strategy.removeprefix("first-segment-after:")
        segment = path.removeprefix(prefix).split("/", 1)[0]
        return f"{prefix}{segment}" if segment else None
    if strategy.startswith("regex:"):
        # Group 1 is the module id; a non-match, an unparticipating group, or
        # an empty capture falls back to the parent directory, so a module id
        # is never None or empty on a matching path.
        found = re.match(strategy.removeprefix("regex:"), path)
        module = found.group(1) if found else None
        return module or str(Path(path).parent)
    return None


def review_kind(path: str, layout: Layout, review: ReviewConfig) -> ReviewKind:
    """Return the review surface a changed file presents; docs > test > config > prod > unknown."""
    if _matches_any(path, review.docs):
        return "docs"
    if _matches_any(path, layout.test_globs):
        return "test"
    if _matches_any(path, review.config):
        return "config"
    if _under_prod_root(path, layout):
        return "prod"
    return "unknown"


def _matches_any(path: str, globs: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) for g in globs)


def _under_prod_root(path: str, layout: Layout) -> bool:
    return any(path.startswith(root) for root in layout.prod_roots)


def security_surface_paths(
    unified: str, patterns: Sequence[str], kind_of: KindOf
) -> list[str]:
    """Return the production files whose added or removed lines hit the security-surface probe.

    A removed match is a weakened guard and hits like an added one. An empty
    probe hits nothing, and the planner keeps the security reviewer on it.
    """
    if not patterns:
        return []
    compiled = [re.compile(p) for p in patterns]
    hits: set[str] = set()
    for path, lines in changed_lines(unified).items():
        if kind_of(path) != "prod":
            continue
        if any(c.search(text) for text in lines for c in compiled):
            hits.add(path)
    return sorted(hits)


def diff_features(
    layout: Layout,
    review: ReviewConfig,
    changesets: Sequence[ChangeSet],
    *,
    churn: bool,
) -> Raw:
    """Return the git-derived feature row over every set; every field is null unless each set resolved both ends.

    Raises RuntimeError when a git command fails; the entry turns that into a
    clean error.
    """
    if not changesets or any(c.base is None or c.head is None for c in changesets):
        return dict(_NULL_ROW)
    numstat = "".join(_numstat_of(c) for c in changesets)
    unified = "".join(_unified_of(c) for c in changesets)
    files = sorted(_file_rows(numstat, layout), key=lambda row: row["path"])
    counted = [
        row for row in files if row["added"] is not None and row["deleted"] is not None
    ]
    modules = {row["module"] for row in files if row["module"]}
    test_lines = _lines_of(counted, "test")
    prod_lines = _lines_of(counted, "prod")
    hunks = sum(1 for line in unified.splitlines() if line.startswith("@@"))
    surface = security_surface_paths(
        unified, review.security_surface, lambda path: classify_kind(path, layout)
    )
    return {
        "files": files,
        "files_changed": len(files),
        "modules": sorted(modules),
        "module_count": len(modules),
        "test_lines": test_lines,
        "prod_lines": prod_lines,
        "test_prod_ratio": (test_lines / prod_lines) if prod_lines > 0 else None,
        "hunks": hunks,
        "sensitive_paths": [row["path"] for row in files if row["sensitive"]],
        "unknown_paths": [row["path"] for row in files if row["kind"] == "unknown"],
        "binary_files": len(files) - len(counted),
        "security_surface_paths": surface,
        "churn": _churn(changesets) if churn else None,
    }


def _numstat_of(changeset: ChangeSet) -> str:
    """Return one set's numstat, its paths spelled from the project."""
    out = run_git(
        "diff",
        "--numstat",
        "--find-renames",
        str(changeset.base),
        str(changeset.head),
        *changeset.pathspecs,
        root=changeset.root,
    )
    return prefix_numstat(out, changeset.prefix)


def _unified_of(changeset: ChangeSet) -> str:
    """Return one set's zero-context diff, its header paths spelled from the project."""
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


def _file_rows(numstat: str, layout: Layout) -> Iterator[Raw]:
    """Yield one row per numstat line; a binary file keeps null counts, an undocumented line is skipped."""
    for added_text, deleted_text, path in _numstat_columns(numstat):
        try:
            added = None if added_text == "-" else int(added_text)
            deleted = None if deleted_text == "-" else int(deleted_text)
        except ValueError:
            continue
        yield {
            "path": path,
            "added": added,
            "deleted": deleted,
            "kind": classify_kind(path, layout),
            "module": module_of(path, layout),
            "sensitive": is_sensitive(path, layout),
        }


def _numstat_columns(numstat: str) -> Iterator[tuple[str, str, str]]:
    """Yield the three columns of every well-formed numstat line."""
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) == _NUMSTAT_COLUMNS:
            yield parts[0], parts[1], parts[2]


def _lines_of(counted: Sequence[Raw], kind: Kind) -> int:
    return sum(row["added"] + row["deleted"] for row in counted if row["kind"] == kind)


def _churn(changesets: Sequence[ChangeSet]) -> dict[str, int] | None:
    """Count the commits and distinct authors between base and tip across the sets that have a tip; None when none has."""
    with_tip = [c for c in changesets if c.tip]
    if not with_tip:
        return None
    authors: list[str] = []
    for changeset in with_tip:
        log = run_git(
            "log",
            "--format=%an",
            f"{changeset.base}..{changeset.tip}",
            root=changeset.root,
        )
        authors.extend(a for a in log.splitlines() if a)
    return {"commits": len(authors), "authors": len(set(authors))}


def parse_numstat(numstat: str, layout: Layout, review: ReviewConfig) -> Raw:
    """Fold a numstat listing into the fix delta: paths, review kinds, sensitivity, binary, size.

    The size uses the first pass's metric, production and test lines by
    classify_kind, so both rungs of the size ladder measure one quantity.
    """
    paths: list[str] = []
    kinds: list[str] = []
    sensitive = False
    binary = False
    lines = 0
    for added, deleted, path in _numstat_columns(numstat):
        paths.append(path)
        kinds.append(review_kind(path, layout, review))
        sensitive = sensitive or is_sensitive(path, layout)
        if added == "-" or deleted == "-":
            binary = True
        elif classify_kind(path, layout) in ("prod", "test"):
            lines += _line_count(added, deleted)
    return {
        "paths": paths,
        "kinds": kinds,
        "sensitive": sensitive,
        "binary": binary,
        "lines": lines,
    }


def _line_count(added: str, deleted: str) -> int:
    """Return the changed lines of one row; an undocumented shape counts nothing."""
    try:
        return int(added) + int(deleted)
    except ValueError:
        return 0


def delta_numstat(
    prev_tree: object,
    cur_tree: object,
    exclude_globs: Sequence[str],
    member_path: str | None = None,
) -> str | None:
    """Return the numstat between two snapshot trees of one repository, paths spelled from the project; None when it cannot be read.

    Both trees resolve through the gateway before reaching git, so an
    agent-authored value never smuggles an option into the diff.
    """
    tree_range = _tree_diff(prev_tree, cur_tree, exclude_globs, member_path)
    listing = None if tree_range is None else tree_range.listing("--numstat")
    if listing is None:
        return None
    return prefix_numstat(listing, _prefix(member_path))


def tree_files(
    base: object,
    tree: object,
    exclude_globs: Sequence[str],
    member_path: str | None = None,
) -> list[str] | None:
    """Return every path changed between the slice base and a prior pass's tree of one repository; None on failure."""
    tree_range = _tree_diff(base, tree, exclude_globs, member_path)
    listing = None if tree_range is None else tree_range.listing("--name-only")
    if listing is None:
        return None
    spelled = prefix_listing(listing, _prefix(member_path))
    return [p for p in spelled.splitlines() if p]


def _prefix(member_path: str | None) -> str:
    return "" if member_path is None else f"{member_path}/"


class _TreeRange(NamedTuple):
    """Two resolved trees of one repository and the pathspecs their diff drops."""

    left: str
    right: str
    root: Path | None
    pathspecs: list[str]

    def listing(self, form: str) -> str | None:
        """Return the diff in the given listing form; None when git fails or a path did not decode."""
        try:
            out = run_git(
                "diff",
                form,
                "--find-renames",
                self.left,
                self.right,
                *self.pathspecs,
                root=self.root,
            )
        except RuntimeError:
            return None
        return _intact(out)


def _intact(listing: str) -> str | None:
    """Return the listing, or None when a path did not decode: a replaced path can alias another, so the fix cycle fails closed."""
    return None if "\ufffd" in listing else listing


def _tree_diff(
    left: object,
    right: object,
    exclude_globs: Sequence[str],
    member_path: str | None,
) -> _TreeRange | None:
    """Resolve two trees of one repository and the globs that apply inside it; None on any unresolved end, so a fix cycle fails closed."""
    if not left or not right:
        return None
    root = None if member_path is None else Path(member_path)
    resolved_left = resolve_tree(left, root)
    resolved_right = resolve_tree(right, root)
    if resolved_left is None or resolved_right is None:
        return None
    globs = globs_for(exclude_globs, _prefix(member_path))
    return _TreeRange(resolved_left, resolved_right, root, exclude_pathspecs(globs))


def basis_files(
    features: Raw, layout: Layout, review: ReviewConfig
) -> list[Raw] | None:
    """Return the per-file review classification of the plan's basis; null for a diff too large to carry."""
    files = features.get("files")
    if files is None or len(files) > _BASIS_FILE_CAP:
        return None
    return [
        {
            "path": f["path"],
            "review_kind": review_kind(f["path"], layout, review),
            "module": f.get("module"),
            "sensitive": f.get("sensitive"),
        }
        for f in files
    ]
