#!/usr/bin/env python3
"""Render the per-tool agent mirror bodies from their .claude base, in place.

    harness/render-agent-mirrors.py [layer-dir ...]

Named per ADR 2026-07-18 producer-script-naming: a tree-builder names its tree.

With no arguments, renders every source layer: harness/core and each
harness/stacks/<stack>.

Each agent exists four times per layer: the base in .claude/agents/<name>.md
and three mirrors — .junie/agents/<name>.md, .opencode/agents/<name>.md,
.github/agents/<name>.agent.md. The body below the frontmatter is shared
doctrine and must be byte-identical (verify-harness step 2b gates it); the
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

A base whose frontmatter carries `variant-of: <name>` is an effort-tier
variant (ADR 2026-09-01): its body renders from the named plain base in the
same directory before the mirror pass, so the shared doctrine stays one
source. Variant frontmatter is hand-owned like any base's; chains are refused.

Stdlib only. Tested by test_render_agent_mirrors.py.
"""

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import AGENT_DOC_STEMS, STACKS, mirror_surfaces  # noqa: E402

# Mirror surfaces: directory and the tool's agent-file suffix, derived from
# registry.TOOLS (shared data; the parsing logic stays local).
# READMEs and wrong-suffix strays are never rendered or pruned.
MIRROR_SURFACES = mirror_surfaces()

FENCE = re.compile(r"^---[ \t]*$")
VARIANT_OF = re.compile(r"^variant-of:[ \t]*([A-Za-z0-9_-]+)[ \t]*$")


def split_agent_file(text: str) -> tuple[list[str], list[str]] | None:
    """(frontmatter lines incl. both fences, body lines) — or None when the
    file is not well-formed: line 1 must open a fence and a second fence must
    close it somewhere below. Only the fence pair is stripped — a "---" rule
    inside the body is content (same rule as verify-harness 2b)."""
    lines = text.splitlines()
    if not lines or not FENCE.match(lines[0]):
        return None
    for i, line in enumerate(lines[1:], start=1):
        if FENCE.match(line):
            return lines[: i + 1], lines[i + 1 :]
    return None


def variant_target(frontmatter: list[str]) -> str | None:
    """The base agent a `variant-of:` frontmatter key names, or None."""
    for line in frontmatter:
        match = VARIANT_OF.match(line)
        if match:
            return match.group(1)
    return None


def mirror_links(body_lines: list[str]) -> list[str]:
    """Base link form → mirror link form (inverse of verify_harness.text.norm_links)."""
    return [l.replace("../skills/", "../../.claude/skills/") for l in body_lines]


def default_layers() -> list[Path]:
    """core plus every roster stack — the roster, not a directory glob, so a
    roster stack whose tree is missing fails loud in render_layer instead of
    being silently skipped, and a stray non-roster directory is ignored."""
    return [HERE / "core"] + [HERE / "stacks" / s for s in STACKS]


def rel(path: Path) -> str:
    """Path relative to harness/ for report lines."""
    return os.path.relpath(path, HERE)


def read_raw(path: Path) -> str:
    """File text without universal-newline translation: a CRLF mirror must
    fail the fence check loudly (as the bash awk did), not slip past a
    translated comparison as "already current" and stay CRLF on disk."""
    return path.read_bytes().decode("utf-8")


def check_base(base: Path) -> tuple[list[str] | None, str | None]:
    """The base's body lines, or an error message when the base is unusable."""
    parts = split_agent_file(read_raw(base))
    if parts is None:
        return None, f"FAIL: {base} has no frontmatter fence pair"
    _, body = parts
    if not any(body):
        return None, f"FAIL: {base} has an empty body"
    text = "\n".join(body)
    if "../../.claude/skills/" in text:
        return None, (
            f"FAIL: {base} uses the mirror link form "
            "(../../.claude/skills/) — a base uses ../skills/"
        )
    # ../../skills/ is broken from .claude/agents/ AND would be over-rewritten
    # to ../../../.claude/skills/ by the render — refuse rather than propagate.
    if "../../skills/" in text:
        return (
            None,
            f"FAIL: {base} links ../../skills/ — broken from .claude/agents/; use ../skills/",
        )
    return body, None


def render_layer(layer: Path, stats: dict[str, int], errors: list[str]) -> None:
    """Render one layer's mirrors; append report lines to stats/errors."""
    agents_dir = layer / ".claude" / "agents"
    if not agents_dir.is_dir():
        errors.append(f"FAIL: no .claude/agents under {layer}")
        return

    errors_before = len(errors)

    # Variant pass first: a base whose frontmatter carries `variant-of: <name>`
    # gets its BODY rendered from the named plain base in the same directory
    # (ADR 2026-09-01: the effort-tier variant is never hand-maintained
    # duplication). Frontmatter stays hand-owned; chains are refused. The
    # mirror loop below then treats the freshly rendered variant like any base.
    for base in sorted(agents_dir.glob("*.md")):
        if base.stem in AGENT_DOC_STEMS:
            continue
        raw = read_raw(base)
        parts = split_agent_file(raw)
        if parts is None:
            continue  # the mirror loop below reports the fence failure
        frontmatter, _ = parts
        target = variant_target(frontmatter)
        if target is None:
            continue
        source = agents_dir / f"{target}.md"
        if not source.is_file():
            errors.append(f"FAIL: {base} names variant-of {target}, which has no base")
            continue
        source_parts = split_agent_file(read_raw(source))
        if source_parts is not None and variant_target(source_parts[0]) is not None:
            errors.append(f"FAIL: {base} chains variant-of onto variant {target}")
            continue
        # Naming rule: the only sanctioned variant shape is <target>-routine. It
        # keeps `variant-of` from silently replacing an arbitrary agent's body
        # with another's — one frontmatter line must not repurpose an agent.
        if base.stem != f"{target}-routine":
            errors.append(
                f"FAIL: {base} carries variant-of {target} but is not named "
                f"{target}-routine — the render refuses to rewrite it"
            )
            continue
        body, error = check_base(source)
        if error or body is None:
            errors.append(error or f"FAIL: {source} is unusable")
            continue
        new_text = "\n".join(frontmatter + body) + "\n"
        if raw != new_text:
            write_guard.write_text(base, new_text)
            stats["rendered"] += 1
            print(f"  rendered {rel(base)}")

    bases = 0
    for base in sorted(agents_dir.glob("*.md")):
        # Sanctioned doc files (registry.AGENT_DOC_STEMS) are never agent
        # bases to mirror; any other file here is treated as an agent, so an
        # unlisted doc fails loudly instead of shipping unchecked.
        if base.stem in AGENT_DOC_STEMS:
            continue
        bases += 1
        name = base.stem
        body, error = check_base(base)
        if error or body is None:  # body is None exactly when error is set
            errors.append(error or f"FAIL: {base} is unusable")
            continue
        rendered_body = mirror_links(body)
        for mirror_dir, suffix in MIRROR_SURFACES:
            mirror = layer / mirror_dir / f"{name}{suffix}"
            if not mirror.is_file():
                errors.append(
                    f"FAIL: missing mirror {mirror} — author its frontmatter once, then re-run"
                )
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
                write_guard.write_text(mirror, new_text)
                stats["rendered"] += 1
                print(f"  rendered {rel(mirror)}")

    # An empty roster is a renamed path or a gutted layer, not a no-op — same
    # verdict verify-harness 2b reaches on the committed tree.
    if bases == 0:
        errors.append(
            f"FAIL: no agent bases under {agents_dir} — roster empty or path renamed"
        )
        return

    # Prune: removal follows the base. A mirror whose base is gone is deleted;
    # only files matching the tool's agent-file pattern are touched — doc
    # stems are never pruned (2b's reverse sweep fails them as strays instead
    # of this script deleting content); wrong-suffix strays are likewise left
    # for that sweep to flag. Never prune a layer that just failed: a renamed base looks like
    # missing mirrors PLUS orphans, and deleting the orphans would destroy the
    # authored frontmatter a git mv could have kept. Resolve the failures,
    # re-run, then prune fires.
    if len(errors) > errors_before:
        print(
            f"  prune skipped under {layer}: resolve the failures above, then re-run",
            file=sys.stderr,
        )
        return
    for mirror_dir, suffix in MIRROR_SURFACES:
        d = layer / mirror_dir
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or not f.name.endswith(suffix):
                continue
            name = f.name[: -len(suffix)]
            if name in AGENT_DOC_STEMS or not name:
                continue
            if not (agents_dir / f"{name}.md").is_file():
                write_guard.unlink(f)
                stats["pruned"] += 1
                print(f"  pruned {rel(f)}")


def main(argv: list[str]) -> int:
    layers = [Path(a) for a in argv[1:]] or default_layers()
    stats = {"rendered": 0, "current": 0, "pruned": 0}
    errors: list[str] = []
    # Mirror renders and prunes land under <layer>/<mirror_dir>. The variant
    # pass additionally writes the specific .claude bases that carry a
    # `variant-of:` key — those exact files join the scope, so a plain base
    # stays unwritable even through a renderer bug.
    roots = [
        layer / mirror_dir for layer in layers for mirror_dir, _ in MIRROR_SURFACES
    ]
    for layer in layers:
        agents_dir = layer / ".claude" / "agents"
        if not agents_dir.is_dir():
            continue
        for f in sorted(agents_dir.glob("*.md")):
            parts = split_agent_file(read_raw(f))
            if parts is not None and variant_target(parts[0]) is not None:
                roots.append(f)
    with write_guard.write_scope(*roots):
        for layer in layers:
            render_layer(layer, stats, errors)
    for error in errors:
        print(error, file=sys.stderr)
    print(
        f"{stats['rendered']} rendered, {stats['current']} already current, "
        f"{stats['pruned']} pruned"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
