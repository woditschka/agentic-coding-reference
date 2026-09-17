"""Parse frontmatter, markdown structure, and paths for the battery; the package's leaf."""

import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent

FENCE = re.compile(r"^---[ \t]*$")
FENCE_PAIR = 2
SKILL_ROW = re.compile(r"^\| `([a-z0-9-]*)`")
TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):")
SUB_KEY = re.compile(r'^[ \t]+"?([A-Za-z0-9_*./-]+)"?:[ \t]*(.*)$')
FENCE_MARKS = ("```", "~~~")
BINARY_PROBE_BYTES = 8192

LOCAL_SKILL_LINK = "../skills/"
SIBLING_SKILL_LINK = "../../.claude/skills/"


def strip_frontmatter(text: str) -> list[str]:
    """Return the body lines below the first frontmatter fence pair, or [] without one."""
    fences = 0
    body = []
    for line in text.splitlines():
        if fences < FENCE_PAIR and FENCE.match(line):
            fences += 1
            continue
        if fences >= FENCE_PAIR:
            body.append(line)
    return body


def norm_links(lines: list[str]) -> list[str]:
    """Rewrite the sibling skill-link form to the base form."""
    return [line.replace(SIBLING_SKILL_LINK, LOCAL_SKILL_LINK) for line in lines]


def frontmatter_lines(text: str) -> list[str]:
    """Return the raw lines inside the first frontmatter fence pair, or [] without one."""
    fences = 0
    inner: list[str] = []
    for line in text.splitlines():
        if FENCE.match(line):
            fences += 1
            if fences >= FENCE_PAIR:
                break
            continue
        if fences == 1:
            inner.append(line)
    return inner if fences >= FENCE_PAIR else []


def frontmatter_top_keys(text: str) -> list[str]:
    """Return the top-level frontmatter keys in order."""
    keys = []
    for line in frontmatter_lines(text):
        match = TOP_KEY.match(line)
        if match:
            keys.append(match.group(1))
    return keys


def _clean_value(raw: str) -> str:
    """Strip a trailing YAML comment and matching outer quotes from a scalar."""
    value = re.sub(r"(^|\s)#.*$", "", raw).strip()
    quoted = value[:1] in ("'", '"') and value.endswith(value[0]) and value != value[0]
    if quoted:
        value = value[1:-1]
    return value


def frontmatter_scalar(text: str, key: str) -> str:
    """Return the inline value on one top-level key's line, or "" when absent or a block."""
    for line in frontmatter_lines(text):
        match = TOP_KEY.match(line)
        if match and match.group(1) == key:
            return _clean_value(line.split(":", 1)[1])
    return ""


def frontmatter_block(text: str, key: str) -> list[tuple[str, str]]:
    """Return the (subkey, value) pairs of the indented map under one top-level key."""
    entries: list[tuple[str, str]] = []
    in_block = False
    depth: int | None = None
    for line in frontmatter_lines(text):
        if TOP_KEY.match(line):
            in_block = line.split(":", 1)[0] == key
            depth = None
            continue
        if not in_block:
            continue
        match = SUB_KEY.match(line)
        if not match:
            continue
        indent = len(line) - len(line.lstrip(" \t"))
        if depth is None:
            depth = indent
        # Deeper lines are nested content; a subkey opening a nested map
        # carries an empty value.
        if indent > depth:
            continue
        entries.append((match.group(1), _clean_value(match.group(2))))
    return entries


def section_rows(text: str, heading_pattern: str) -> list[str]:
    """Return the skill-name table rows inside the H2 sections matching heading_pattern."""
    in_section = False
    rows = []
    pattern = re.compile(heading_pattern)
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = bool(pattern.search(line))
        if in_section:
            match = SKILL_ROW.match(line)
            if match:
                rows.append(match.group(1))
    return rows


def fence_state(line: str, fence: str | None) -> str | None:
    """Advance the fenced-code state by one line, returning the open marker or None."""
    # A block closes only on its own opening marker, so a ~~~ line inside a
    # ``` block stays literal content.
    stripped = line.lstrip()
    if fence is None:
        return stripped[:3] if stripped.startswith(FENCE_MARKS) else None
    return None if stripped.startswith(fence) else fence


def h2_headings(body_lines: list[str]) -> list[str]:
    """Return the H2 heading texts of a body, fenced blocks skipped."""
    headings = []
    fence = None
    for line in body_lines:
        fence = fence_state(line, fence)
        if fence is None and line.startswith("## "):
            headings.append(line[3:].strip())
    return headings


def severity_headings(body_lines: list[str]) -> list[str]:
    """Return the H3 headings under the Severity Classification H2, fenced blocks skipped."""
    headings = []
    in_section = False
    fence = None
    for line in body_lines:
        fence = fence_state(line, fence)
        if fence is not None:
            continue
        if line.startswith("## "):
            in_section = line[3:].strip() == "Severity Classification"
        elif in_section and line.startswith("### "):
            headings.append(line[4:].strip())
    return headings


def github_slug(heading: str) -> str:
    """Return the GitHub anchor slug of a heading text."""
    slug = heading.strip().lower()
    slug = re.sub(r"`([^`]*)`", r"\1", slug)
    slug = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", slug)
    slug = "".join(ch for ch in slug if ch.isalnum() or ch in " -_")
    return slug.replace(" ", "-")


def heading_anchors(text: str) -> set[str]:
    """Return every anchor a markdown file exposes: heading slugs and explicit ids."""
    heading_re = re.compile(r"^#{1,6}\s+(\S.*)")
    anchor_id_re = re.compile(r'<a id="([^"]+)"')
    slugs: set[str] = set()
    seen: Counter[str] = Counter()
    fence = None
    for line in text.splitlines():
        fence = fence_state(line, fence)
        if fence is not None:
            continue
        match = heading_re.match(line)
        if match:
            slug = github_slug(match.group(1))
            ordinal = seen[slug]
            seen[slug] += 1
            slugs.add(slug if ordinal == 0 else f"{slug}-{ordinal}")
        slugs.update(anchor_id_re.findall(line))
    return slugs


# A candidate tag is any bracketed word with an optional, loosely captured
# :target suffix, so a malformed form reaches judgment instead of falling
# out of the scan. Regex classes and id placeholders carry hyphens or stay
# single-lettered and never match the candidate shape.
TAG_CANDIDATE = re.compile(r"\[([A-Za-z]{2,})(\s*:[^\]]*)?\]")
TAG_TARGET = re.compile(r"^[a-z][a-z0-9-]*$")


def _tag_problem(
    head: str, suffix: str | None, canon: set[str], *, linked: bool
) -> str | None:
    """Name the defect of one judged tag token, or None when it is well-formed."""
    if head.lower() not in canon:
        return f"tag [{head}] is not in review-workflow's canonical set {sorted(canon)}"
    if not head.isupper():
        return f"tag [{head}] has a case-variant head — canonical tags are uppercase"
    if linked:
        return (
            f"tag [{head}] is immediately followed by '(' "
            "— styled as a markdown link, not a tag"
        )
    if suffix is not None and not suffix.startswith(":"):
        return (
            f"tag [{head}{suffix}] carries whitespace before "
            "the colon — expected [TAG:target]"
        )
    if suffix is not None and not TAG_TARGET.match(suffix[1:]):
        return (
            f"tag [{head}:…] has a malformed target "
            f"{suffix[1:]!r} — expected a lowercase agent name"
        )
    return None


def tag_findings(text: str, canon: set[str]) -> tuple[int, list[str]]:
    """Judge every tag-shaped bracket token against the canonical vocabulary."""
    # A token reaches judgment when its head is uppercase or matches the
    # vocabulary case-insensitively; ordinary links and prose brackets do not.
    judged = 0
    problems = []
    seen: set[tuple[str, str | None, bool]] = set()
    for match in TAG_CANDIDATE.finditer(text):
        head, suffix = match.group(1), match.group(2)
        linked = text[match.end() : match.end() + 1] == "("
        in_vocabulary = head.lower() in canon
        if not in_vocabulary and (linked or not head.isupper()):
            continue
        if (head, suffix, linked) in seen:
            continue
        seen.add((head, suffix, linked))
        judged += 1
        problem = _tag_problem(head, suffix, canon, linked=linked)
        if problem:
            problems.append(problem)
    return judged, problems


def is_binary(path: Path) -> bool:
    """Tell whether a file is binary by a NUL byte in its head, or unreadable."""
    try:
        return b"\0" in path.read_bytes()[:BINARY_PROBE_BYTES]
    except OSError:
        return True


def read_text(path: str | Path) -> str:
    """Read a file as UTF-8, replacing undecodable bytes."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def rel(path: str | Path) -> str:
    """Return the repo-relative display form of a path, absolute when outside ROOT."""
    # Checks under test run against synthetic temp roots, where a failure
    # message must render the path, not crash the check that reports it.
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()
