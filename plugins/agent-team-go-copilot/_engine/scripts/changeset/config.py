"""changeset.config — the change set's layout ACL (the exclude filter).

The change set under review is the working-tree delta narrowed by the project's
declared `exclude_globs` — tracked-but-irrelevant paths (vendored trees,
generated-yet-committed files) that neither a reviewer nor the grader should
read. This module is the ACL for that one slice of scripts/layout.toml: it loads
the file, validates exclude_globs, and exposes it. The grading engine's own
config ACL (grading.config) owns the classification, roster, and [review]
slices — the two read the same file, each validating only its own sections, so
neither layer carries knowledge of the other's config.

Stdlib only.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("changeset.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2) from None


def _load_layout() -> SimpleNamespace:
    """Load the exclude filter from scripts/layout.toml.

    The file sits at the composition root (this module's parent's parent — the
    scripts dir), beside the entry launchers. TOML is read by the stdlib
    `tomllib` (Python 3.11+), keeping the engine dependency-free. A missing or
    malformed layout.toml is a broken install, not a runtime data gap, so it
    raises here rather than nulling the change set. Only `exclude_globs` is read
    and validated; the grading ACL validates the other sections.
    """
    path = Path(__file__).resolve().parent.parent / "layout.toml"
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    exclude = raw.get("exclude_globs", [])
    if not isinstance(exclude, list) or not all(isinstance(g, str) for g in exclude):
        raise ValueError(
            "layout.toml: exclude_globs must be a list of glob strings "
            f"(got {exclude!r})"
        )
    return SimpleNamespace(EXCLUDE=exclude)


# Loaded lazily by get_layout() on first use. Kept a public module global (not
# loaded at import) so a unit test can both import this package without a
# sibling layout.toml AND inject an exclude filter by assigning `layout`.
layout: SimpleNamespace | None = None


def get_layout() -> SimpleNamespace:
    """Return the exclude filter, loading and caching it on first use.

    Deferred (not loaded at import) so the package imports without a sibling
    layout.toml; the load still happens before any diff, inside the changeset
    call chain. A test may pre-set the module global `layout` to a fake to
    bypass the load entirely.
    """
    global layout
    if layout is None:
        layout = _load_layout()
    return layout
