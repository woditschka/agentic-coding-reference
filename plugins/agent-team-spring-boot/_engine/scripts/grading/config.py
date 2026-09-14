"""Load and validate the grading sections of scripts/layout.toml.

The rules are data, so a project in any language forks the config, not the engine.
The change set's exclude filter is a separate slice of the same file, read by the
change-set layer's own loader; each validates only its own sections.
"""

import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NamedTuple, TypeAlias

from .conventions import Conventions

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("grading.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2) from None

Raw: TypeAlias = dict[str, Any]
Table: TypeAlias = Mapping[str, object]
Mode = Literal["risk", "always-full"]

# The mandatory reviewer floor (doctor-expectations.toml [reviewers] floor).
# Every key is present in the reviewers row, null when a floor reviewer has
# not spoken; a declared extra's verdict enters the row the same way.
REVIEWERS = (
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
)

# A file's changed review surface maps to the dimensions that judge it. No
# "prod" row: a production change never takes the surface path, so a prod
# mapping would be dead config that still marks its extras "mapped".
SURFACE_REVIEWERS: Mapping[str, tuple[str, ...]] = {
    "docs": ("doc-reviewer",),
    "test": ("test-reviewer", "code-quality-reviewer"),
    "config": ("code-quality-reviewer", "security-reviewer"),
}

# fnmatch's `*` crosses `/`, so the bare `*.md` variant already matches any
# depth; the `**/` variants document intent. Config is data-file extensions
# only, never a `config/**` directory that would misclassify code under it.
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
_MODES: tuple[Mode, ...] = ("risk", "always-full")

# A named layout expands to exactly `regex:<pattern>`: same match, same
# parent-directory fallback. "maven" and "gradle" share the src/<set>/<lang>
# source-set convention; the module id is the module root, the prefix ending at
# src/, so a prod file and its test derive one id and a repo-root tree
# derives "src".
_SRC_TREE_PATTERN = r"((?:.*?/)?src)/(?:main|test)/[^/]+/"
NAMED_MODULE_LAYOUTS = {
    "maven": _SRC_TREE_PATTERN,
    "gradle": _SRC_TREE_PATTERN,
}

# The keys a stack may default from scripts/layout-defaults.toml, which is
# harness-owned and carries the stack's own syntax. Every other key is a
# project fact, and a harness file carrying one fails the load.
STACK_DEFAULT_KEYS: dict[str, tuple[str, ...]] = {
    "review": ("security_surface",),
    "conventions": (
        "comment_markers",
        "construction",
        "construction_ignore",
        "constant_declaration",
    ),
}

_DEFAULT_COMMENT_MARKERS = ("//", "#", "/*", "*", "*/", "--")
# A line assigning an UPPER_CASE name, or carrying a const/static-final
# keyword, declares a named value: its literal is the name's definition.
_DEFAULT_CONSTANT_DECLARATION = r"\bstatic\s+final\b|\bconst\b|\b[A-Z][A-Z0-9_]{2,}\s*="


class LayoutError(ValueError):
    """A layout value the engine cannot run on; the doctor and the roots catch it as a ValueError."""


class ModuleRule(NamedTuple):
    """One [[module]] entry: the paths it matches and how it derives their module id."""

    match: str
    strategy: str


@dataclass(frozen=True, slots=True)
class ReviewConfig:
    """The validated [review] table: the surface globs, the size threshold, the mode, the maps."""

    docs: tuple[str, ...]
    config: tuple[str, ...]
    size_threshold: int
    mode: Mode
    surface_reviewers: Mapping[str, tuple[str, ...]]
    security_surface: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Layout:
    """The grading rules of one project, with the stack defaults merged under its tables.

    The [review] table validates in the commands that read it, before their
    first git read, and the [conventions] table where the map is drawn, so a
    broken advisory table never takes a gate down with it.
    """

    test_globs: tuple[str, ...]
    prod_roots: tuple[str, ...]
    sensitive: tuple[str, ...]
    module_rules: tuple[ModuleRule, ...]
    extra_reviewers: tuple[str, ...]
    review: Table
    conventions: Table

    @property
    def roster(self) -> tuple[str, ...]:
        """Return the four-reviewer floor plus the declared extras, in roster order."""
        roster = list(REVIEWERS)
        for extra in self.extra_reviewers:
            if extra not in roster:
                roster.append(extra)
        return tuple(roster)

    def review_config(self) -> ReviewConfig:
        """Validate the [review] table; a malformed value raises so no plan is appended."""
        return validate_review(self.review, self.roster)

    def conventions_config(self) -> Conventions:
        """Validate the [conventions] table in the map's own call chain, never at load."""
        return validate_conventions(self.conventions)


def load_layout(scripts_dir: Path) -> Layout:
    """Read scripts/layout.toml and the stack defaults beside it; a missing or broken file raises."""
    raw = _read_toml(scripts_dir / "layout.toml")
    defaults = load_stack_defaults(scripts_dir)
    review = merged_table("review", raw, defaults)
    extras = validate_reviewer_extras(raw.get("harness", {}).get("extra_reviewers", []))
    conventions = merged_table("conventions", raw, defaults)
    return Layout(
        test_globs=_string_list(raw, "test"),
        prod_roots=_string_list(raw, "prod_roots"),
        sensitive=_string_list(raw, "sensitive"),
        module_rules=validate_module_rules(raw.get("module", [])),
        extra_reviewers=extras,
        review=review,
        conventions=conventions,
    )


def _read_toml(path: Path) -> Raw:
    """Parse one layout file; a missing or malformed file is a broken install."""
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise LayoutError(f"{path.name}: {exc}") from exc


def load_stack_defaults(scripts_dir: Path) -> dict[str, Raw]:
    """Return the stack's shipped defaults, restricted to STACK_DEFAULT_KEYS; {} without the file."""
    path = scripts_dir / "layout-defaults.toml"
    if not path.is_file():
        return {}
    raw = _read_toml(path)
    foreign = sorted(set(raw) - set(STACK_DEFAULT_KEYS))
    if foreign:
        raise LayoutError(
            "layout-defaults.toml: only the "
            f"{' and '.join(STACK_DEFAULT_KEYS)} tables may carry stack defaults "
            f"(got {', '.join(foreign)})"
        )
    for name, table in raw.items():
        if not isinstance(table, dict):
            raise LayoutError(
                f"layout-defaults.toml: [{name}] must be a table (got {table!r})"
            )
        stray = sorted(set(table) - set(STACK_DEFAULT_KEYS[name]))
        if stray:
            raise LayoutError(
                f"layout-defaults.toml: [{name}] may default only "
                f"{', '.join(STACK_DEFAULT_KEYS[name])} (got {', '.join(stray)})"
            )
    return {name: dict(table) for name, table in raw.items()}


def merged_table(name: str, raw: Table, defaults: Mapping[str, Table]) -> Raw:
    """Return the project's table over the stack's default, key by key; a declared key wins."""
    table = raw.get(name, {})
    if not isinstance(table, dict):
        raise LayoutError(f"layout.toml: [{name}] must be a table (got {table!r})")
    return {**defaults.get(name, {}), **table}


def shadowed_keys(raw: Table, defaults: Mapping[str, Table]) -> list[str]:
    """Name the `table.key` entries the project restates with the stack default's exact value."""
    shadowed: list[str] = []
    for name, table in defaults.items():
        project = raw.get(name, {})
        if not isinstance(project, dict):
            continue
        for key, value in table.items():
            if key in project and project[key] == value:
                shadowed.append(f"{name}.{key}")
    return shadowed


def _string_list(raw: Table, key: str) -> tuple[str, ...]:
    """Reject a non-list or an empty entry: "" prefixes every path and would widen a class to all."""
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise LayoutError(
            f"layout.toml: {key} must be a list of non-empty strings (got {value!r})"
        )
    return tuple(value)


def validate_module_rules(rules: object) -> tuple[ModuleRule, ...]:
    """Reject a rule the module derivation would fail on mid-diff: a missing key, an unknown strategy."""
    if not isinstance(rules, list):
        raise LayoutError(
            f"layout.toml: [[module]] must be a list of tables (got {rules!r})"
        )
    return tuple(_module_rule(index, rule) for index, rule in enumerate(rules))


def _module_rule(index: int, rule: object) -> ModuleRule:
    if not isinstance(rule, dict) or "match" not in rule or "from" not in rule:
        keys = sorted(rule) if isinstance(rule, dict) else rule
        raise LayoutError(
            f"layout.toml: [[module]] entry {index} needs both 'match' and "
            f"'from' keys (got {keys})"
        )
    match, strategy = rule["match"], rule["from"]
    if not isinstance(strategy, str):
        raise LayoutError(
            f"layout.toml: [[module]] entry {index} 'from' must be a string "
            f"(got {type(strategy).__name__})"
        )
    if not isinstance(match, str):
        raise LayoutError(
            f"layout.toml: [[module]] entry {index} 'match' must be a glob string "
            f"(got {type(match).__name__})"
        )
    _check_strategy(index, strategy)
    return ModuleRule(match, strategy)


def _check_strategy(index: int, strategy: str) -> None:
    if strategy == "dir" or strategy in NAMED_MODULE_LAYOUTS:
        return
    if strategy.startswith("first-segment-after:"):
        return
    if strategy.startswith("regex:"):
        _check_module_regex(index, strategy.removeprefix("regex:"))
        return
    raise LayoutError(
        f"layout.toml: [[module]] entry {index} has unknown 'from' strategy "
        f"{strategy!r} (expected 'dir', 'first-segment-after:<prefix>', "
        "'regex:<pattern>', or a named layout: "
        f"{', '.join(sorted(NAMED_MODULE_LAYOUTS))})"
    )


def _check_module_regex(index: int, pattern: str) -> None:
    """Require the pattern to compile and to capture group 1, the module id."""
    try:
        groups = re.compile(pattern).groups
    except re.error as exc:
        raise LayoutError(
            f"layout.toml: [[module]] entry {index} regex strategy does not "
            f"compile: {exc}"
        ) from exc
    if groups < 1:
        raise LayoutError(
            f"layout.toml: [[module]] entry {index} regex strategy needs a "
            "capture group (group 1 is the module id)"
        )


def validate_reviewer_extras(extras: object) -> tuple[str, ...]:
    """Reject a malformed [harness] extra_reviewers, the declaration route blocks on too."""
    if not isinstance(extras, list) or not all(
        isinstance(e, str) and e for e in extras
    ):
        raise LayoutError(
            "layout.toml: [harness] extra_reviewers must be a list of "
            f"reviewer names (got {extras!r})"
        )
    return tuple(extras)


def validate_review(raw: Table, roster: Sequence[str]) -> ReviewConfig:
    """Validate the merged [review] table; the doctor and the engine share this one wall."""
    docs = _glob_list(raw, "docs", _DEFAULT_DOCS_GLOBS)
    config = _glob_list(raw, "config", _DEFAULT_CONFIG_GLOBS)
    threshold = raw.get("size_threshold", _DEFAULT_SIZE_THRESHOLD)
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
        raise LayoutError(
            "layout.toml: [review] size_threshold must be a positive integer "
            f"(got {threshold!r})"
        )
    mode = raw.get("mode", "risk")
    if mode not in _MODES:
        raise LayoutError(
            f"layout.toml: [review] mode must be 'risk' or 'always-full' (got {mode!r})"
        )
    surface = raw.get("surface_reviewers", {})
    if not isinstance(surface, dict):
        raise LayoutError(
            "layout.toml: [review.surface_reviewers] must be a table of "
            f"surface → reviewer-name lists (got {surface!r})"
        )
    probe = _regex_list(raw.get("security_surface", []), "[review] security_surface")
    return ReviewConfig(
        docs, config, threshold, mode, _surface_reviewers(surface, roster), probe
    )


def _glob_list(raw: Table, key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = raw.get(key, list(default))
    if not isinstance(value, list) or not all(isinstance(g, str) for g in value):
        raise LayoutError(
            f"layout.toml: [review] {key} must be a list of glob strings "
            f"(got {value!r})"
        )
    return tuple(value)


def _surface_reviewers(
    surface: Table, roster: Sequence[str]
) -> Mapping[str, tuple[str, ...]]:
    """Overlay the project's surface map on the default; every target must sit on the roster."""
    merged = dict(SURFACE_REVIEWERS)
    for kind, names in surface.items():
        if kind not in merged:
            raise LayoutError(
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
            raise LayoutError(
                f"layout.toml: [review.surface_reviewers] {kind} must be a "
                "non-empty list of roster reviewer names (the floor plus "
                f"declared extras; got {names!r})"
            )
        merged[kind] = tuple(names)
    return merged


def _regex_list(value: object, label: str) -> tuple[str, ...]:
    """Require a list of non-empty patterns that compile; an empty pattern matches everything."""
    if not isinstance(value, list) or not all(isinstance(p, str) and p for p in value):
        raise LayoutError(f"{label} must be a list of regex strings (got {value!r})")
    for pattern in value:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise LayoutError(
                f"{label} {pattern!r} is not a valid regex: {exc}"
            ) from None
    return tuple(value)


def validate_conventions(raw: object) -> Conventions:
    """Validate the merged [conventions] table and compile its patterns once."""
    if not isinstance(raw, dict):
        raise LayoutError(f"layout.toml: [conventions] must be a table (got {raw!r})")
    markers = raw.get("comment_markers", list(_DEFAULT_COMMENT_MARKERS))
    if (
        not isinstance(markers, list)
        or not markers
        or not all(isinstance(m, str) and m for m in markers)
    ):
        raise LayoutError(
            "layout.toml: [conventions] comment_markers must be a non-empty list "
            f"of strings (got {markers!r})"
        )
    construction = _pattern(raw, "construction", None)
    constant = _pattern(raw, "constant_declaration", _DEFAULT_CONSTANT_DECLARATION)
    ignore = _regex_list(
        raw.get("construction_ignore", []),
        "layout.toml: [conventions] construction_ignore",
    )
    return Conventions(
        comment_markers=tuple(markers),
        construction=construction,
        construction_ignore=tuple(re.compile(p) for p in ignore),
        constant_declaration=constant,
    )


def _pattern(raw: Table, key: str, default: str | None) -> re.Pattern[str] | None:
    """Compile one optional regex key; an absent or empty value lists nothing."""
    value = raw.get(key, default)
    if value is not None and not isinstance(value, str):
        raise LayoutError(
            f"layout.toml: [conventions] {key} must be a regex string (got {value!r})"
        )
    if not value:
        return None
    try:
        return re.compile(value)
    except re.error as exc:
        raise LayoutError(
            f"layout.toml: [conventions] {key} is not a valid regex: {exc}"
        ) from None
