"""Overlay transcript cost onto the board: the one seam over the vendored accounting module."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Protocol, cast

from .ledger import Entry
from .records import IMPLEMENTER, DispatchStart
from .timestamps import seconds_of

# The overlay is optional: the vendored accounting module may be absent or
# unusable, and the board then omits cost figures rather than failing.
accounting: ModuleType | None
try:
    import accounting as _accounting
except Exception:  # noqa: BLE001  # pragma: no cover
    accounting = None
else:
    accounting = _accounting


@dataclass(frozen=True, slots=True)
class CostFigures:
    """One window's usage in the statusline's cell vocabulary, already formatted."""

    tokens_in: str
    tokens_out: str
    cost: str
    hit_pct: str
    savings_pct: str | None


class CostLookup(Protocol):
    """The cost overlay: one author over one window, the slice roll-up, and the tier probe."""

    def window(
        self, agent: object, start: float | None, end: float | None
    ) -> CostFigures | None:
        """Return the figures of one author over the window, or None."""
        ...

    def slice_window(
        self, agents: Sequence[str], start: float | None, end: float | None
    ) -> CostFigures | None:
        """Return the figures of the authors over the window, or None."""
        ...

    def window_types(
        self, start: float | None, end: float | None
    ) -> tuple[str, ...] | None:
        """Return the implementer tiers the transcripts show in the window, or None."""
        ...


def build_cost_lookup(log: Sequence[Entry]) -> CostLookup | None:
    """Build the cost overlay from the transcripts, or None when nothing can be timed or read."""
    if accounting is None:
        return None
    dispatch_seconds = [
        seconds
        for entry in log
        if isinstance(entry.record, DispatchStart)
        and (seconds := seconds_of(entry.ts)) is not None
    ]
    if not dispatch_seconds:
        return None
    try:
        index = accounting.WindowIndex(since_secs=min(dispatch_seconds))
    except Exception:  # noqa: BLE001 — the board reads, it never gates
        return None
    return TranscriptOverlay(index, accounting)


class TranscriptOverlay:
    """The cost overlay over one transcript index; every failure degrades to no figures."""

    def __init__(self, index: Any, formatter: ModuleType) -> None:  # noqa: ANN401 — the transcript index is untyped
        """Wrap one transcript index with the module that formats its figures."""
        self._index = index
        self._formatter = formatter

    def window(
        self, agent: object, start: float | None, end: float | None
    ) -> CostFigures | None:
        """Return the figures of one author over the window, or None."""
        if not agent:
            return None
        try:
            figures = self._index.totals(agent, start, end)
        except Exception:  # noqa: BLE001 — the board reads, it never gates
            return None
        return self._figures(figures) if figures else None

    def slice_window(
        self, agents: Sequence[str], start: float | None, end: float | None
    ) -> CostFigures | None:
        """Return the figures of the authors over the window, or None."""
        if not agents:
            return None
        try:
            figures = self._index.slice_totals(agents, start, end)
        except Exception:  # noqa: BLE001 — the board reads, it never gates
            return None
        return self._figures(figures) if figures else None

    def window_types(
        self, start: float | None, end: float | None
    ) -> tuple[str, ...] | None:
        """Return the implementer tiers the transcripts show in the window, or None."""
        try:
            return cast(
                "tuple[str, ...] | None",
                self._index.window_types(IMPLEMENTER, start, end),
            )
        except Exception:  # noqa: BLE001 — the board reads, it never gates
            return None

    def _figures(self, figures: Mapping[str, Any]) -> CostFigures:
        savings = figures.get("savings_pct")
        return CostFigures(
            tokens_in=self._formatter.format_tokens(figures["total_input"]),
            tokens_out=self._formatter.format_tokens(figures["output"]),
            cost=self._formatter.format_cost(figures["cost"]),
            hit_pct=str(figures["hit_pct"]),
            savings_pct=None if savings is None else str(savings),
        )
