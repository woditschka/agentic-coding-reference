#!/usr/bin/env python3
"""Render the per-tool agent mirror bodies from their .claude base, in place.

    harness/render-agent-mirrors.py [layer-dir ...]   # default: core and every stack

Each agent's body below the frontmatter is shared doctrine held once in the
.claude base; the mirrors keep their hand-owned frontmatter and receive the
body, with skill links rewritten to the mirror-relative form. A missing
mirror fails loud, since its frontmatter is a per-tool decision; a mirror
whose base is gone is pruned, never on a layer with failures. Stdlib only.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import AGENT_DOC_STEMS, STACKS, mirror_surfaces  # noqa: E402

# READMEs and wrong-suffix strays are never rendered or pruned.
MIRROR_SURFACES = mirror_surfaces()
BASE_LINK_FORM = "../skills/"
MIRROR_LINK_FORM = "../../.claude/skills/"
VARIANT_SUFFIX = "-routine"

FENCE = re.compile(r"^---[ \t]*$")
VARIANT_OF = re.compile(r"^variant-of:[ \t]*([A-Za-z0-9_-]+)[ \t]*$")


@dataclass(slots=True)
class Tally:
    """What one render did, and every failure it found."""

    rendered: int = 0
    current: int = 0
    pruned: int = 0
    errors: list[str] = field(default_factory=list)


def split_agent_file(text: str) -> tuple[list[str], list[str]] | None:
    """Split an agent file into its frontmatter and body lines, or None when the fence pair is missing."""
    # Only the fence pair is stripped: a "---" rule inside the body is content.
    lines = text.splitlines()
    if not lines or not FENCE.match(lines[0]):
        return None
    for i, line in enumerate(lines[1:], start=1):
        if FENCE.match(line):
            return lines[: i + 1], lines[i + 1 :]
    return None


def variant_target(frontmatter: list[str]) -> str | None:
    """Return the base agent a `variant-of:` frontmatter key names, or None."""
    for line in frontmatter:
        match = VARIANT_OF.match(line)
        if match:
            return match.group(1)
    return None


def mirror_links(body_lines: list[str]) -> list[str]:
    """Rewrite the base link form into the mirror link form."""
    return [line.replace(BASE_LINK_FORM, MIRROR_LINK_FORM) for line in body_lines]


def default_layers() -> list[Path]:
    """Return core plus every roster stack."""
    # The roster, not a directory glob: a roster stack whose tree is missing
    # fails loud, and a stray directory is ignored.
    return [HERE / "core"] + [HERE / "stacks" / s for s in STACKS]


def rel(path: Path) -> str:
    """Return the path relative to harness/ for a report line."""
    try:
        return path.relative_to(HERE).as_posix()
    except ValueError:
        return path.as_posix()


def read_raw(path: Path) -> str:
    """Read a file without newline translation, so a CRLF mirror fails the fence check."""
    return path.read_bytes().decode("utf-8")


def check_base(base: Path) -> tuple[list[str] | None, str | None]:
    """Return the base's body lines, or the error that makes the base unusable."""
    parts = split_agent_file(read_raw(base))
    if parts is None:
        return None, f"FAIL: {base} has no frontmatter fence pair"
    _, body = parts
    if not any(body):
        return None, f"FAIL: {base} has an empty body"
    text = "\n".join(body)
    if MIRROR_LINK_FORM in text:
        return None, (
            f"FAIL: {base} uses the mirror link form "
            "(../../.claude/skills/) — a base uses ../skills/"
        )
    # ../../skills/ is broken from .claude/agents/ and would be rewritten to
    # ../../../.claude/skills/ by the render.
    if "../../skills/" in text:
        return (
            None,
            f"FAIL: {base} links ../../skills/ — broken from .claude/agents/; use ../skills/",
        )
    return body, None


def _agent_bases(agents_dir: Path) -> list[Path]:
    # The sanctioned doc files are never bases; any other file here is an
    # agent, so an unlisted doc fails loudly instead of shipping unchecked.
    return [b for b in sorted(agents_dir.glob("*.md")) if b.stem not in AGENT_DOC_STEMS]


def render_layer(layer: Path, tally: Tally) -> None:
    """Render one layer's variants and mirrors, then prune orphans when the layer is clean."""
    agents_dir = layer / ".claude" / "agents"
    if not agents_dir.is_dir():
        tally.errors.append(f"FAIL: no .claude/agents under {layer}")
        return
    errors_before = len(tally.errors)
    _render_variants(agents_dir, tally)
    bases = _render_mirrors(layer, agents_dir, tally)
    # An empty roster is a renamed path or a gutted layer, not a no-op.
    if bases == 0:
        tally.errors.append(
            f"FAIL: no agent bases under {agents_dir} — roster empty or path renamed"
        )
        return
    # A renamed base looks like missing mirrors plus orphans, and pruning the
    # orphans would destroy the authored frontmatter a git mv could keep.
    if len(tally.errors) > errors_before:
        print(
            f"  prune skipped under {layer}: resolve the failures above, then re-run",
            file=sys.stderr,
        )
        return
    _prune(layer, agents_dir, tally)


def _render_variants(agents_dir: Path, tally: Tally) -> None:
    # A base carrying `variant-of: <name>` gets its body from the named plain
    # base first, so the mirror pass then treats it like any base; its
    # frontmatter stays hand-owned.
    for base in _agent_bases(agents_dir):
        raw = read_raw(base)
        parts = split_agent_file(raw)
        if parts is None:
            continue
        frontmatter, _ = parts
        target = variant_target(frontmatter)
        if target is None:
            continue
        body = _variant_body(base, target, agents_dir, tally)
        if body is None:
            continue
        new_text = "\n".join(frontmatter + body) + "\n"
        if raw != new_text:
            write_guard.write_text(base, new_text)
            tally.rendered += 1
            print(f"  rendered {rel(base)}")


def _variant_body(
    base: Path, target: str, agents_dir: Path, tally: Tally
) -> list[str] | None:
    source = agents_dir / f"{target}.md"
    if not source.is_file():
        tally.errors.append(
            f"FAIL: {base} names variant-of {target}, which has no base"
        )
        return None
    source_parts = split_agent_file(read_raw(source))
    if source_parts is not None and variant_target(source_parts[0]) is not None:
        tally.errors.append(f"FAIL: {base} chains variant-of onto variant {target}")
        return None
    # The only sanctioned variant shape is <target>-routine, so one
    # frontmatter line can never repurpose an arbitrary agent's body.
    if base.stem != f"{target}{VARIANT_SUFFIX}":
        tally.errors.append(
            f"FAIL: {base} carries variant-of {target} but is not named "
            f"{target}-routine — the render refuses to rewrite it"
        )
        return None
    body, error = check_base(source)
    if error or body is None:
        tally.errors.append(error or f"FAIL: {source} is unusable")
        return None
    return body


def _render_mirrors(layer: Path, agents_dir: Path, tally: Tally) -> int:
    bases = 0
    for base in _agent_bases(agents_dir):
        bases += 1
        body, error = check_base(base)
        if error or body is None:
            tally.errors.append(error or f"FAIL: {base} is unusable")
            continue
        rendered_body = mirror_links(body)
        for mirror_dir, suffix in MIRROR_SURFACES:
            _render_mirror(
                layer / mirror_dir / f"{base.stem}{suffix}", rendered_body, tally
            )
    return bases


def _render_mirror(mirror: Path, rendered_body: list[str], tally: Tally) -> None:
    if not mirror.is_file():
        tally.errors.append(
            f"FAIL: missing mirror {mirror} — author its frontmatter once, then re-run"
        )
        return
    mirror_raw = read_raw(mirror)
    parts = split_agent_file(mirror_raw)
    if parts is None:
        tally.errors.append(f"FAIL: {mirror} has no frontmatter fence pair")
        return
    frontmatter, _ = parts
    new_text = "\n".join(frontmatter + rendered_body) + "\n"
    if mirror_raw == new_text:
        tally.current += 1
        return
    write_guard.write_text(mirror, new_text)
    tally.rendered += 1
    print(f"  rendered {rel(mirror)}")


def _prune(layer: Path, agents_dir: Path, tally: Tally) -> None:
    # Only files matching the tool's agent-file pattern are touched; doc
    # stems and wrong-suffix strays are left for the battery's sweep.
    for mirror_dir, suffix in MIRROR_SURFACES:
        directory = layer / mirror_dir
        if not directory.is_dir():
            continue
        for mirror in sorted(directory.iterdir()):
            if not mirror.is_file() or not mirror.name.endswith(suffix):
                continue
            name = mirror.name[: -len(suffix)]
            if name in AGENT_DOC_STEMS or not name:
                continue
            if not (agents_dir / f"{name}.md").is_file():
                write_guard.unlink(mirror)
                tally.pruned += 1
                print(f"  pruned {rel(mirror)}")


def _write_roots(layers: list[Path]) -> list[Path]:
    # Mirror renders and prunes land under each mirror dir; the variant pass
    # writes the exact .claude bases that carry a variant-of key, so a plain
    # base stays unwritable even through a renderer bug.
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
    return roots


def main(argv: list[str]) -> int:
    """Render the named layers, or every layer, and return the exit code."""
    layers = [Path(a) for a in argv[1:]] or default_layers()
    tally = Tally()
    with write_guard.write_scope(*_write_roots(layers)):
        for layer in layers:
            render_layer(layer, tally)
    for error in tally.errors:
        print(error, file=sys.stderr)
    print(
        f"{tally.rendered} rendered, {tally.current} already current, "
        f"{tally.pruned} pruned"
    )
    return 1 if tally.errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
