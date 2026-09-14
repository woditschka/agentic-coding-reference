"""Shape record text for display: gists, plurals, and clipped locations, pure over str."""

import re

GIST_LIMIT = 75
LOCATION_LIMIT = 38
_SPACES = re.compile(r"\s+")
_DIRECTORY = re.compile(r"^.*/")


def gist(text: object, limit: int = GIST_LIMIT) -> str:
    """Return text collapsed to one line and clipped with an ellipsis."""
    if not isinstance(text, str):
        return ""
    cleaned = _SPACES.sub(" ", text).strip()
    return cleaned[: limit - 1] + "…" if len(cleaned) > limit else cleaned


def full_or_gist(text: object, *, verbose: bool, limit: int = GIST_LIMIT) -> str:
    """Return the whole text under --verbose, else its one-line gist."""
    if verbose and isinstance(text, str):
        return text.strip()
    return gist(text, limit)


def plural(count: int, word: str) -> str:
    """Return the count with the word pluralized."""
    if count == 1:
        return f"1 {word}"
    return f"{count} {word}" + ("es" if word.endswith("s") else "s")


def short_location(location: object, limit: int = LOCATION_LIMIT) -> str:
    """Return a finding location clipped to its file name and the limit."""
    if not isinstance(location, str):
        return ""
    clipped = location.split(" (")[0].strip()
    return _DIRECTORY.sub("", clipped)[:limit]
