"""grading.config — the layout-config ACL for the grading engine.

Loads the grading rules from scripts/layout.toml — the classification globs,
module rules, [review] config, and declared extra reviewers — validates them at
load, and exposes them as one namespace. The rules are data, so a repo in any
language forks the config, not the engine. Everything downstream (features,
planner, the entry) reads the layout only through this module. The change set's
exclude filter is a separate slice of the same file, owned by the change-set
layer's ACL (changeset.config); the two read layout.toml independently, each
validating only its own sections (ADR 2026-07-17 runtime-package-layout).

Stdlib only.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("grading.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2) from None

# The mandatory reviewer floor (doctor-expectations.toml [reviewers] floor).
# These keys are always present in the reviewers row — null when a floor
# reviewer has not spoken. Declared extra_reviewers are not enumerated here:
# any other review-feedback author found in the log enters the row too (see
# handoff_facts.read_handoff), so an extra reviewer's verdict is never
# silently dropped.
REVIEWERS = (
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
)

# The four-reviewer floor is the same tuple read_handoff enumerates
# (REVIEWERS above). A file's changed *review surface* maps to the dimensions
# that judge it: a reviewer joins a pass only when the change set contains
# surface its dimension reviews. doc-reviewer is dropped from a pure production
# change (small prod diffs route to the planner, not to a docs read). These are
# the fail-safe defaults; a project overrides per surface via layout.toml
# [review.surface_reviewers] (validated against the roster in review_config).
# No "prod" row: a production-code change never takes the surface path — it
# routes to the planner or the full battery — so a prod mapping would be dead
# config that still marks its extras "mapped" and silently narrows them.
SURFACE_REVIEWERS = {
    "docs": ("doc-reviewer",),
    "test": ("test-reviewer", "code-quality-reviewer"),
    "config": ("code-quality-reviewer", "security-reviewer"),
}

# Review-kind default globs. fnmatch's `*` crosses `/`, so the bare `*.md`
# variant already matches any depth; the `**/` variants document intent. A
# project overrides these in layout.toml [review]. Config is data-file
# extensions only — never a `config/**` directory, which would misclassify
# production code that happens to live under it.
_DEFAULT_DOCS_GLOBS = ("**/*.md", "*.md", "docs/**")
_DEFAULT_CONFIG_GLOBS = (
    "**/*.toml",
    "*.toml",
    "**/*.yaml",
    "*.yaml",
    "**/*.yml",
    "*.yml",
    "**/*.json",
    "*.json",
)
_DEFAULT_SIZE_THRESHOLD = 80


def validate_module_rules(rules: Any) -> Any:
    """Validate each module rule's shape and strategy at load time.

    Catches the two misconfigurations that would otherwise fail obscurely deep
    in the per-file diff loop: a rule missing `match`/`from` (a bare KeyError in
    features.module_of), and an unknown `from` strategy (which module_of would
    fall through, silently yielding module=None). Both are operator config
    errors, best surfaced where the loader already promises a well-formed
    config. The accepted strategies mirror the branches in module_of. Returns
    the rules unchanged.
    """
    for i, rule in enumerate(rules):
        if "match" not in rule or "from" not in rule:
            raise ValueError(
                f"layout.toml: [[module]] entry {i} needs both 'match' and "
                f"'from' keys (got {sorted(rule)})"
            )
        strategy = rule["from"]
        if strategy not in ("dir", "maven") and not strategy.startswith(
            "first-segment-after:"
        ):
            raise ValueError(
                f"layout.toml: [[module]] entry {i} has unknown 'from' strategy "
                f"{strategy!r} (expected 'dir', 'maven', or 'first-segment-after:<prefix>')"
            )
    return rules


def validate_reviewer_extras(extras: Any) -> Any:
    """Validate the [harness] extra_reviewers declaration at load time.

    route blocks loudly (layout-invalid) on the same malformed declaration;
    the plan engine must not disagree by silently dropping a declared gate.
    Returns the list unchanged."""
    if not isinstance(extras, list) or not all(
        isinstance(e, str) and e for e in extras
    ):
        raise ValueError(
            "layout.toml: [harness] extra_reviewers must be a list of "
            f"reviewer names (got {extras!r})"
        )
    return extras


def _load_layout() -> SimpleNamespace:
    """Load the per-project layout rules from scripts/layout.toml.

    The file sits at the composition root (this module's parent directory),
    beside the entry launchers. TOML is read by the stdlib `tomllib` (Python
    3.11+), keeping the engine dependency-free. A missing or malformed
    layout.toml is a broken install, not a runtime data gap, so it raises here
    rather than nulling the feature row. A `[[module]]` entry missing `match`
    or `from` is validated here too, so a broken rule fails cleanly at load
    instead of as a bare KeyError deep in the per-file diff loop. The returned
    namespace exposes the rule sets the classifier and planner consume.
    """
    path = Path(__file__).resolve().parent.parent / "layout.toml"
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    review = raw.get("review", {})
    if not isinstance(review, dict):
        raise ValueError(f"layout.toml: [review] must be a table (got {review!r})")
    extras = validate_reviewer_extras(raw.get("harness", {}).get("extra_reviewers", []))
    return SimpleNamespace(
        TEST=raw.get("test", []),
        PROD_ROOTS=raw.get("prod_roots", []),
        SENSITIVE=raw.get("sensitive", []),
        MODULE=validate_module_rules(raw.get("module", [])),
        REVIEW=review,
        EXTRA_REVIEWERS=extras,
    )


# Loaded lazily by get_layout() on first use — see below. Kept a public module
# global (not loaded at import) so a unit test can both import this package
# without a sibling layout.toml AND inject rules by assigning `layout` directly.
layout: SimpleNamespace | None = None


def get_layout() -> SimpleNamespace:
    """Return the layout rules, loading and caching them on first use.

    Deferred (not loaded at import) so the package imports without a sibling
    layout.toml; the load still happens before any classification, inside
    cmd_extract's call chain. A test may pre-set the module global `layout` to a
    fake to bypass the load entirely.
    """
    global layout
    if layout is None:
        layout = _load_layout()
    return layout


def effective_roster() -> list[str]:
    """The four-reviewer floor plus declared extras, in roster order."""
    roster = list(REVIEWERS)
    for extra in get_layout().EXTRA_REVIEWERS or []:
        if isinstance(extra, str) and extra and extra not in roster:
            roster.append(extra)
    return roster


def review_config() -> dict[str, Any]:
    """The [review] table from layout.toml, with fail-safe defaults.

    Every key is optional: an absent [review] table yields the built-in
    defaults, so the engine runs correctly on a project that never declared one.
    `mode = "always-full"` is the opt-out that reproduces pre-plan behavior.
    A malformed value raises — no plan is appended, so route falls closed to
    the full battery; a config error is loud, never a silently wrong roster.
    """
    raw = get_layout().REVIEW or {}
    docs = raw.get("docs", list(_DEFAULT_DOCS_GLOBS))
    config = raw.get("config", list(_DEFAULT_CONFIG_GLOBS))
    for key, val in (("docs", docs), ("config", config)):
        if not isinstance(val, list) or not all(isinstance(g, str) for g in val):
            raise ValueError(
                f"layout.toml: [review] {key} must be a list of glob strings "
                f"(got {val!r})"
            )
    threshold = raw.get("size_threshold", _DEFAULT_SIZE_THRESHOLD)
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
        raise ValueError(
            "layout.toml: [review] size_threshold must be a positive integer "
            f"(got {threshold!r})"
        )
    mode = raw.get("mode", "risk")
    if mode not in ("risk", "always-full"):
        raise ValueError(
            f"layout.toml: [review] mode must be 'risk' or 'always-full' (got {mode!r})"
        )
    surface = raw.get("surface_reviewers", {})
    if not isinstance(surface, dict):
        raise ValueError(
            "layout.toml: [review.surface_reviewers] must be a table of "
            f"surface → reviewer-name lists (got {surface!r})"
        )
    merged = {kind: list(names) for kind, names in SURFACE_REVIEWERS.items()}
    roster = effective_roster()
    for kind, names in surface.items():
        if kind not in merged:
            raise ValueError(
                f"layout.toml: [review.surface_reviewers] unknown surface "
                f"{kind!r} (expected one of {sorted(merged)}; a production "
                "change never takes the surface path, so 'prod' is not "
                "overridable)"
            )
        if (
            not isinstance(names, list)
            or not names
            or not all(isinstance(n, str) and n in roster for n in names)
        ):
            raise ValueError(
                f"layout.toml: [review.surface_reviewers] {kind} must be a "
                "non-empty list of roster reviewer names (the floor plus "
                f"declared extras; got {names!r})"
            )
        merged[kind] = list(names)
    return {
        "docs": docs,
        "config": config,
        "size_threshold": threshold,
        "mode": mode,
        "surface_reviewers": merged,
    }
