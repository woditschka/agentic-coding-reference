"""Read the PRD's Non-Goals table and the rows that changed against HEAD.

A leaf over handoff.repository.
"""

import re

from .repository import Repository

# Up to three leading spaces still render as a table row.
NG_ROW_RE = re.compile(r"^ {0,3}\|\s*(NG-[0-9]+)\s*\|")


def ng_rows(text: str) -> dict[str, str]:
    """Return the Non-Goals table rows of a PRD text keyed by their id; any reword is a change."""
    rows: dict[str, str] = {}
    for line in text.splitlines():
        match = NG_ROW_RE.match(line)
        if match:
            rows[match.group(1)] = line.strip()
    return rows


def changed_rows(old_text: str, new_text: str) -> tuple[str, ...]:
    """Return the ids of the old text's rows the new text rewords or drops, sorted."""
    new_rows = ng_rows(new_text)
    return tuple(
        sorted(ng for ng, line in ng_rows(old_text).items() if new_rows.get(ng) != line)
    )


def non_goal_delta(repository: Repository) -> tuple[str, ...] | None:
    """Return the Non-Goals rows changed or removed against HEAD; None fails Gate 1 closed."""
    state = repository.state()
    if state is None:
        return None
    if state != "ok":
        return ()
    old_lines = repository.committed_prd_lines()
    if old_lines is None:
        return None
    new_text = repository.worktree_prd_text()
    if new_text is None:
        return None
    return changed_rows("\n".join(old_lines), new_text)
