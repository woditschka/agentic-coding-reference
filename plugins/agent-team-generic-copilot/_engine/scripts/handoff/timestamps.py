"""Read the ledger's timestamps: ISO-8601 text to seconds, elapsed time, and the clock face."""

import datetime

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
_DATE_LENGTH = 10
_HHMM_MIN_LENGTH = 16
_HHMM = slice(11, 16)


def seconds_of(value: object) -> float | None:
    """Return a raw timestamp value as POSIX seconds, or None when it is not a parseable string."""
    return parse_iso_seconds(value) if isinstance(value, str) else None


def parse_iso_seconds(text: str) -> float | None:
    """Parse an ISO-8601 timestamp to POSIX seconds; a bare timestamp reads as UTC."""
    text = text.strip()
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.UTC)
    return moment.timestamp()


def hhmm_of(value: object) -> str | None:
    """Return the HH:MM of a raw timestamp value, or None."""
    if (
        isinstance(value, str)
        and len(value) >= _HHMM_MIN_LENGTH
        and value[_DATE_LENGTH] == "T"
    ):
        return value[_HHMM]
    return None


def elapsed(first: float | None, last: float | None) -> str | None:
    """Return the formatted time between two moments, or None when it cannot be told."""
    if first is None or last is None or last < first:
        return None
    return format_duration(last - first)


def format_duration(seconds: float) -> str:
    """Return a compact elapsed time: seconds, whole minutes, or hours and minutes."""
    whole = int(seconds)
    if whole < SECONDS_PER_MINUTE:
        return f"{whole}s"
    if whole < SECONDS_PER_HOUR:
        return f"{whole // SECONDS_PER_MINUTE}m"
    hours, rest = divmod(whole, SECONDS_PER_HOUR)
    return f"{hours}h {rest // SECONDS_PER_MINUTE}m"
