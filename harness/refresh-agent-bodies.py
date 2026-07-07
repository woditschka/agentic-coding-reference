#!/usr/bin/env python3
"""Render the per-tool agent mirror bodies from their .claude base, in place.

    harness/refresh-agent-bodies.py [layer-dir ...]

With no arguments, renders every source layer: harness/core and each
harness/stacks/<stack>.

Each agent exists four times per layer: the base in .claude/agents/<name>.md
and three mirrors — .junie/agents/<name>.md, .opencode/agents/<name>.md,
.github/agents/<name>.agent.md. The body below the frontmatter is shared
doctrine and must be byte-identical (check-sync step 2b gates it); the
frontmatter is hand-owned per tool because it encodes per-tool decisions:
Copilot's handoffs blocks, OpenCode's mcp-deny permissions, Junie dropping
the IDE oracle.

This script makes the shared half mechanical — the same split managed
chapters use for CLAUDE.md (claude-md/refresh-chapters.py): keep each
mirror's frontmatter, replace everything below its closing fence with the
base body. Skill links are rewritten to the mirror-relative form on the way
(../skills/ → ../../.claude/skills/), the one documented body difference
step 2b normalizes.

The .claude base is the source of truth for the roster, in both directions.
Adding an agent means authoring its three mirror frontmatters once — a
per-tool policy decision that stays an explicitly reviewed human step, so a
missing mirror fails loud, never auto-created. Removing an agent is one base
deletion: the render prunes any mirror whose base is gone — but never on a
layer with failures, so a rename (missing mirrors plus orphans) keeps its
authored frontmatter for a git mv. After that, every body edit is one file:
the base.

Stdlib only. Tested by test_refresh_agent_bodies.py.
"""

import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from helpers import STACKS, mirror_surfaces  # noqa: E402

# Mirror surfaces: directory and the tool's agent-file suffix, derived from
# the helpers.TOOLS registry (shared data; the parsing logic stays local).
# READMEs and wrong-suffix strays are never rendered or pruned.
MIRROR_SURFACES = mirror_surfaces()

FENCE = re.compile(r"^---[ \t]*$")


def split_agent_file(text):
    """(frontmatter lines incl. both fences, body lines) — or None when the
    file is not well-formed: line 1 must open a fence and a second fence must
    close it somewhere below. Only the fence pair is stripped — a "---" rule
    inside the body is content (same rule as check-sync 2b)."""
    lines = text.splitlines()
    if not lines or not FENCE.match(lines[0]):
        return None
    for i, line in enumerate(lines[1:], start=1):
        if FENCE.match(line):
            return lines[: i + 1], lines[i + 1:]
    return None


def mirror_links(body_lines):
    """Base link form → mirror link form (inverse of check-sync's norm_links)."""
    return [l.replace("../skills/", "../../.claude/skills/") for l in body_lines]


def default_layers():
    """core plus every roster stack — the roster, not a directory glob, so a
    roster stack whose tree is missing fails loud in render_layer instead of
    being silently skipped, and a stray non-roster directory is ignored."""
    return [HERE / "core"] + [HERE / "stacks" / s for s in STACKS]


def rel(path):
    """Path relative to harness/ for report lines."""
    return os.path.relpath(path, HERE)


def atomic_write(path, text):
    """Temp file in the target's own directory: the rename is a same-filesystem
    atomic replace, never a cross-device copy an interruption could truncate."""
    fd, tmp = tempfile.mkstemp(prefix=".agent-body.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def read_raw(path):
    """File text without universal-newline translation: a CRLF mirror must
    fail the fence check loudly (as the bash awk did), not slip past a
    translated comparison as "already current" and stay CRLF on disk."""
    return path.read_bytes().decode("utf-8")


def check_base(base):
    """The base's body lines, or an error message when the base is unusable."""
    parts = split_agent_file(read_raw(base))
    if parts is None:
        return None, f"FAIL: {base} has no frontmatter fence pair"
    _, body = parts
    if not any(body):
        return None, f"FAIL: {base} has an empty body"
    text = "\n".join(body)
    if "../../.claude/skills/" in text:
        return None, (f"FAIL: {base} uses the mirror link form "
                      "(../../.claude/skills/) — a base uses ../skills/")
    # ../../skills/ is broken from .claude/agents/ AND would be over-rewritten
    # to ../../../.claude/skills/ by the render — refuse rather than propagate.
    if "../../skills/" in text:
        return None, f"FAIL: {base} links ../../skills/ — broken from .claude/agents/; use ../skills/"
    return body, None


def render_layer(layer, stats, errors):
    """Render one layer's mirrors; append report lines to stats/errors."""
    agents_dir = layer / ".claude" / "agents"
    if not agents_dir.is_dir():
        errors.append(f"FAIL: no .claude/agents under {layer}")
        return

    errors_before = len(errors)
    bases = 0
    for base in sorted(agents_dir.glob("*.md")):
        if base.name == "README.md":
            continue
        bases += 1
        name = base.stem
        body, error = check_base(base)
        if error:
            errors.append(error)
            continue
        rendered_body = mirror_links(body)
        for mirror_dir, suffix in MIRROR_SURFACES:
            mirror = layer / mirror_dir / f"{name}{suffix}"
            if not mirror.is_file():
                errors.append(f"FAIL: missing mirror {mirror} — author its frontmatter once, then re-run")
                continue
            mirror_raw = read_raw(mirror)
            parts = split_agent_file(mirror_raw)
            if parts is None:
                errors.append(f"FAIL: {mirror} has no frontmatter fence pair")
                continue
            frontmatter, _ = parts
            new_text = "\n".join(frontmatter + rendered_body) + "\n"
            if mirror_raw == new_text:
                stats["current"] += 1
            else:
                atomic_write(mirror, new_text)
                stats["rendered"] += 1
                print(f"  rendered {rel(mirror)}")

    # An empty roster is a renamed path or a gutted layer, not a no-op — same
    # verdict check-sync 2b reaches on the committed tree.
    if bases == 0:
        errors.append(f"FAIL: no agent bases under {agents_dir} — roster empty or path renamed")
        return

    # Prune: removal follows the base. A mirror whose base is gone is deleted;
    # only files matching the tool's agent-file pattern are touched — READMEs
    # are never pruned; wrong-suffix strays are left for 2b's reverse sweep to
    # flag. Never prune a layer that just failed: a renamed base looks like
    # missing mirrors PLUS orphans, and deleting the orphans would destroy the
    # authored frontmatter a git mv could have kept. Resolve the failures,
    # re-run, then prune fires.
    if len(errors) > errors_before:
        print(f"  prune skipped under {layer}: resolve the failures above, then re-run",
              file=sys.stderr)
        return
    for mirror_dir, suffix in MIRROR_SURFACES:
        d = layer / mirror_dir
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or not f.name.endswith(suffix):
                continue
            name = f.name[: -len(suffix)]
            if name == "README" or not name:
                continue
            if not (agents_dir / f"{name}.md").is_file():
                f.unlink()
                stats["pruned"] += 1
                print(f"  pruned {rel(f)}")


def main(argv):
    layers = [Path(a) for a in argv[1:]] or default_layers()
    stats = {"rendered": 0, "current": 0, "pruned": 0}
    errors = []
    for layer in layers:
        render_layer(layer, stats, errors)
    for error in errors:
        print(error, file=sys.stderr)
    print(f"{stats['rendered']} rendered, {stats['current']} already current, "
          f"{stats['pruned']} pruned")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
