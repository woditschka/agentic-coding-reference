"""Pure text helpers for the battery — the leaf module of the verify_harness
package (ADR 2026-07-18 check-sync-decomposition): no internal import.
Unit-tested by harness/tests/test_verify_harness.py (battery step 6). HERE
(harness/) and ROOT (the repo root) live here because rel() anchors on ROOT;
every other module imports them from this leaf."""

import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # harness/
ROOT = HERE.parent

FENCE = re.compile(r"^---[ \t]*$")
SKILL_ROW = re.compile(r"^\| `([a-z0-9-]*)`")


def strip_frontmatter(text: str) -> list[str]:
    """Body lines below the frontmatter fence pair. Only the first fence pair
    is stripped — a body's own "---" rules stay. No fence pair → empty body
    (the empty-base guard fails it)."""
    fences = 0
    body = []
    for line in text.splitlines():
        if fences < 2 and FENCE.match(line):
            fences += 1
            continue
        if fences >= 2:
            body.append(line)
    return body


def norm_links(lines: list[str]) -> list[str]:
    """Sibling link form → the base form (the one documented body difference)."""
    return [l.replace("../../.claude/skills/", "../skills/") for l in lines]


def section_rows(text: str, heading_pattern: str) -> list[str]:
    """Skill-name rows (| `name` …) inside the sections whose `## ` heading
    matches heading_pattern; every other section's rows are ignored."""
    in_section = False
    rows = []
    pattern = re.compile(heading_pattern)
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = bool(pattern.search(line))
        if in_section:
            m = SKILL_ROW.match(line)
            if m:
                rows.append(m.group(1))
    return rows


FENCE_MARKS = ("```", "~~~")


def _fence_state(line: str, fence: str | None) -> str | None:
    """Track fenced-code state across lines: `fence` is the open marker (None
    = outside). Fences may be indented and use ``` or ~~~; a block closes
    only on its own opening marker, so a ~~~ line inside a ``` block stays
    literal content."""
    s = line.lstrip()
    if fence is None:
        return s[:3] if s.startswith(FENCE_MARKS) else None
    return None if s.startswith(fence) else fence


def h2_headings(body_lines: list[str]) -> list[str]:
    """H2 headings in order, fenced code excluded (indented and ~~~ fences
    included in the exclusion)."""
    out, fence = [], None
    for line in body_lines:
        fence = _fence_state(line, fence)
        if fence is None and line.startswith("## "):
            out.append(line[3:].strip())
    return out


def severity_headings(body_lines: list[str]) -> list[str]:
    """H3 headings inside the '## Severity Classification' section, fenced
    code excluded (indented and ~~~ fences included in the exclusion)."""
    out, in_section, fence = [], False, None
    for line in body_lines:
        fence = _fence_state(line, fence)
        if fence is not None:
            continue
        if line.startswith("## "):
            in_section = line[3:].strip() == "Severity Classification"
        elif in_section and line.startswith("### "):
            out.append(line[4:].strip())
    return out


def github_slug(heading: str) -> str:
    """GitHub's heading→anchor slug: markdown stripped, lowercased, spaces
    to hyphens, everything not alphanumeric/hyphen/underscore dropped."""
    s = heading.strip().lower()
    s = re.sub(r"`([^`]*)`", r"\1", s)  # inline code markers
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # links keep their text
    s = "".join(ch for ch in s if ch.isalnum() or ch in " -_")
    return s.replace(" ", "-")


def heading_anchors(text: str) -> set[str]:
    """Every anchor a markdown file exposes: heading slugs (GitHub duplicate
    suffixing: second 'x' is 'x-1') plus explicit <a id> anchors. Fenced
    blocks are skipped via _fence_state (~~~ and indented fences included)
    — a commented heading is not an anchor."""
    heading_re = re.compile(r"^#{1,6}\s+(\S.*)")
    aid_re = re.compile(r'<a id="([^"]+)"')
    slugs: set[str] = set()
    seen: Counter[str] = Counter()
    fence = None
    for ln in text.splitlines():
        fence = _fence_state(ln, fence)
        if fence is not None:
            continue
        m = heading_re.match(ln)
        if m:
            slug = github_slug(m.group(1))
            n = seen[slug]
            seen[slug] += 1
            slugs.add(slug if n == 0 else f"{slug}-{n}")
        slugs.update(aid_re.findall(ln))
    return slugs


# A candidate tag is any bracketed word, optionally with a (loosely
# captured) :target suffix, so malformed forms reach judgment instead of
# falling out of the scan: a case-variant head ([Blocked]), a spaced colon
# ([CLARIFY :x]), a bad target (uppercase, digits-first, empty,
# whitespace), or a canonical tag styled as a link ([AUTOFIX](note)).
# Regex classes ([A-Z]) and ID placeholders ([REQ-XX-NNN]) carry hyphens
# or stay single-lettered and never match the candidate shape.
TAG_CANDIDATE = re.compile(r"\[([A-Za-z]{2,})(\s*:[^\]]*)?\]")
TAG_TARGET = re.compile(r"^[a-z][a-z0-9-]*$")


def tag_findings(text: str, canon: set[str]) -> tuple[int, list[str]]:
    """Judge every tag-shaped bracket token in text against the canonical
    vocabulary. Returns (judged, problems): judged counts the distinct
    tokens that reached judgment; problems are the defect strings. A token
    reaches judgment when its head is uppercase (tag-shaped) or matches the
    vocabulary case-insensitively; ordinary markdown links and lowercase
    prose brackets never do."""
    judged, problems, seen = 0, [], set()
    for m in TAG_CANDIDATE.finditer(text):
        head, sep = m.group(1), m.group(2)
        linked = text[m.end() : m.end() + 1] == "("
        in_vocab = head.lower() in canon
        if not in_vocab and (linked or not head.isupper()):
            continue  # an ordinary link or prose brackets
        if (head, sep, linked) in seen:
            continue
        seen.add((head, sep, linked))
        judged += 1
        if not in_vocab:
            problems.append(
                f"tag [{head}] is not in review-workflow's "
                f"canonical set {sorted(canon)}"
            )
        elif not head.isupper():
            problems.append(
                f"tag [{head}] has a case-variant head — canonical tags are uppercase"
            )
        elif linked:
            problems.append(
                f"tag [{head}] is immediately followed by '(' "
                "— styled as a markdown link, not a tag"
            )
        elif sep is not None and not sep.startswith(":"):
            problems.append(
                f"tag [{head}{sep}] carries whitespace before "
                "the colon — expected [TAG:target]"
            )
        elif sep is not None and not TAG_TARGET.match(sep[1:]):
            problems.append(
                f"tag [{head}:…] has a malformed target "
                f"{sep[1:]!r} — expected a lowercase agent name"
            )
    return judged, problems


def is_binary(path: Path) -> bool:
    """grep -I semantics: a NUL byte in the head marks a binary file."""
    try:
        return b"\0" in path.read_bytes()[:8192]
    except OSError:
        return True


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def rel(path: str | Path) -> str:
    """Repo-relative display form; a path outside ROOT stays absolute.

    Checks under test run against synthetic temp roots, where a failure
    message must render the path, not crash the check that reports it."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()
