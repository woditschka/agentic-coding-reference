"""Read the change set's exclude filter from scripts/layout.toml.

The anti-corruption layer for the one layout section the change set owns; the
grading reader validates the other sections.
"""

import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("changeset.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2) from None


class ChangeSetError(ValueError):
    """A layout value or argument the change set cannot be resolved from."""


def load_exclude_globs(scripts_dir: Path) -> tuple[str, ...]:
    """Read exclude_globs from the layout beside the launchers; a missing or broken file raises."""
    path = scripts_dir / "layout.toml"
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ChangeSetError(f"{path.name}: {exc}") from exc
    globs = raw.get("exclude_globs", [])
    if not isinstance(globs, list) or not all(isinstance(g, str) and g for g in globs):
        raise ChangeSetError(
            "layout.toml: exclude_globs must be a list of non-empty glob strings "
            f"(got {globs!r})"
        )
    return tuple(globs)
