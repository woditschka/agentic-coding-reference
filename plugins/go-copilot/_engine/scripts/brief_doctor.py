#!/usr/bin/env python3
"""Deterministic checks for the harness-project API.

Validates a project's docs/ brief against brief-expectations.toml — the
machine-checkable subset of the harness-project API spec. This is the blocking
layer: existence, required sections, data slots, naming conventions, and
channel invariants. Judgment checks live in the audit-docs skill, not here.

Stdlib only. Requires Python 3.11+ (tomllib).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("brief_doctor requires Python 3.11+ (tomllib)\n")
    sys.exit(2)

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

DEFAULT_MANIFEST = Path(__file__).resolve().parent / "brief-expectations.toml"

# Harness-managed chapters of the project-owned CLAUDE.md, identified by their
# exact `## ` heading. /init scaffolds each and /materialize refreshes it in
# place from the single source (harness/claude-md/managed-chapters.md) on every
# upgrade. The check asserts each required chapter exists and is non-empty. Kept
# in lockstep with that source file's headings by the parity guard in
# harness/test-materialize.sh.
REQUIRED_CHAPTERS = [
    "## Agent Usage (Mandatory)",
    "## Memory",
    "## Writing Standards",
    "## Scratch Directory",
    "## Documentation Updates",
]

# Paths that hold harness runtime content. On the manifest and marketplace
# channels none of these may be tracked by git: the runtime arrives out-of-band
# (materialized from /harness, or via plugin). This list mirrors the runtime
# block in a consumer's .gitignore — project-owned files (settings.json,
# scripts/layout.toml, docs/) are deliberately absent so they stay tracked.
RUNTIME_PATHS = [
    ".claude/skills",
    ".claude/agents",
    ".claude/hooks",
    ".claude/templates",
    ".github/agents",
    ".opencode/agents",
    ".junie/agents",
    ".junie/config.json",
    "schemas/scratch",
    "scripts/gate.sh",
    "scripts/handoff.py",
    "scripts/test_handoff.py",
    "scripts/score-change.py",
    "scripts/changeset.sh",
    "scripts/test_score_change.py",
    "scripts/brief_doctor.py",
    "scripts/test_brief_doctor.py",
    "scripts/brief-expectations.toml",
]


def parse_sections(text):
    """Map each '## ' heading to its body text (up to the next '## ')."""
    sections = {}
    current = None
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines)
            current = line[3:].strip()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines)
    return sections


def lookup(data, dotted):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def check_project_data(manifest, root):
    cfg = manifest["project_data"]
    rel = cfg["path"]
    path = root / rel
    if not path.is_file():
        return [(FAIL, "project-data", f"{rel} missing")], None, None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [(FAIL, "project-data", f"{rel} unparseable: {exc}")], None, None

    results = []
    for dotted in cfg["required_keys"]:
        value = lookup(data, dotted)
        if value is None:
            results.append((FAIL, "project-data", f"{rel}: key {dotted} missing"))
        else:
            results.append((PASS, "project-data", f"{dotted} = {value}"))

    channel = lookup(data, "harness.channel")
    if channel is not None and channel not in cfg["channel_values"]:
        results.append(
            (FAIL, "project-data",
             f"channel must be one of {cfg['channel_values']}, got {channel!r}")
        )
        channel = None

    declared = lookup(data, "harness.spec_version")
    if declared is not None and declared != manifest["spec_version"]:
        results.append(
            (FAIL, "project-data",
             f"spec_version {declared} does not match manifest {manifest['spec_version']}")
        )

    extensions = lookup(data, "harness.extensions")
    if extensions is not None and not (
        isinstance(extensions, list) and all(isinstance(e, str) for e in extensions)
    ):
        results.append(
            (FAIL, "project-data",
             "harness.extensions must be a list of runtime-relative paths")
        )
        extensions = None
    return results, channel, extensions


def check_directory_entry(entry, root):
    rel = entry["path"]
    path = root / rel
    if not path.is_dir():
        return [(FAIL, rel, f"missing — materialize {entry['template']}")]
    results = [(PASS, rel, "exists")]
    readme = path / "README.md"
    if readme.is_file():
        results.append((PASS, rel, "README.md present"))
    else:
        results.append((FAIL, rel, "README.md missing — materialize " + entry["template"]))
    pattern = re.compile(entry["entry_pattern"])
    for child in sorted(path.iterdir()):
        if child.name == "README.md" or not child.name.endswith(".md"):
            continue
        if pattern.match(child.name):
            results.append((PASS, rel, f"{child.name} conforms"))
        else:
            results.append(
                (FAIL, rel, f"{child.name} violates entry naming YYYY-MM-DD-kebab.md")
            )
    return results


def check_file_entry(entry, root):
    if entry.get("directory"):
        return check_directory_entry(entry, root)
    rel = entry["path"]
    path = root / rel
    if not path.is_file():
        return [(FAIL, rel, f"missing — materialize {entry['template']}")]
    results = [(PASS, rel, "exists")]
    sections = parse_sections(path.read_text(encoding="utf-8"))
    for required in entry.get("required_sections", []):
        if required in sections:
            results.append((PASS, rel, f"section '{required}' present"))
        else:
            results.append((FAIL, rel, f"required section '## {required}' missing"))
    for slot in entry.get("slots", []):
        body = sections.get(slot["section"])
        if body is None:
            continue  # the missing-section failure is already recorded
        if re.search(slot["must_match"], body):
            results.append((PASS, rel, f"slot in '{slot['section']}' filled"))
        else:
            results.append(
                (FAIL, rel,
                 f"section '{slot['section']}' lacks required data "
                 f"(pattern {slot['must_match']})")
            )
    return results


# Any token shaped like a REQ-ID, regardless of digit count. Compared against
# the manifest's req_id_pattern to surface near-miss ids (e.g. REQ-AB-1000) at
# doctor time — the scratch schemas anchor req_id to the canonical shape, so a
# near-miss would otherwise pass here and fail only on the first pipeline append.
_REQ_TOKEN_RE = re.compile(r"\bREQ-[A-Z]+-[0-9]+\b")


def check_cross_doc(manifest, root):
    cfg = manifest["cross_doc"]
    source = root / cfg["source"]
    target = root / cfg["defined_in"]
    if not source.is_file() or not target.is_file():
        return [(SKIP, "cross-doc", "source or target missing (reported above)")]
    pattern = re.compile(cfg["req_id_pattern"])
    src_text = source.read_text(encoding="utf-8")
    tgt_text = target.read_text(encoding="utf-8")
    cited = set(pattern.findall(src_text))
    defined = set(pattern.findall(tgt_text))
    results = []
    malformed = sorted(
        {tok for text in (src_text, tgt_text) for tok in _REQ_TOKEN_RE.findall(text)
         if not pattern.fullmatch(tok)}
    )
    if malformed:
        results.append(
            (FAIL, "cross-doc",
             "malformed REQ-ID token(s) — the record schemas require "
             "REQ-<LETTERS>-<3 digits>: " + ", ".join(malformed)))
    unknown = sorted(cited - defined)
    if unknown:
        results.append(
            (FAIL, "cross-doc",
             f"cited in {cfg['source']} but not defined in {cfg['defined_in']}: "
             + ", ".join(unknown)))
    if not results:
        results.append(
            (PASS, "cross-doc", f"{len(cited)} REQ-ID citation(s), all defined"))
    return results


def check_handbook_refs(manifest, root):
    names = manifest["handbook"]["denylist"]
    results = []
    for entry in manifest["file"]:
        path = root / entry["path"]
        if entry.get("directory"):
            files = sorted(path.glob("*.md")) if path.is_dir() else []
        else:
            files = [path] if path.is_file() else []
        for f in files:
            hits = sorted({n for n in names if n in f.read_text(encoding="utf-8")})
            if hits:
                results.append(
                    (FAIL, "handbook-refs",
                     f"{f.relative_to(root)} references harness-owned doc(s): "
                     + ", ".join(hits))
                )
    if not results:
        results.append((PASS, "handbook-refs", "no roster file references handbook documents"))
    return results


def check_handbook_docs_absent(manifest, root):
    # A consumer's docs/ must not carry harness-owned handbook docs themselves:
    # their content lives with the harness — as installed skills or as docs in
    # the reference repo. A project migrating from an older harness that copied
    # them into docs/ should remove them — /materialize proposes exactly this.
    # None of the roster files are denylist names, so the roster is never
    # implicated. (Project vocabulary belongs in docs/ubiquitous-language.md,
    # never in a docs/glossary.md of its own.)
    names = manifest["handbook"]["denylist"]
    docs = root / "docs"
    stale = sorted(n for n in names if (docs / n).is_file())
    if stale:
        return [(FAIL, "handbook-docs",
                 "docs/ holds harness-owned handbook doc(s) — remove them; the "
                 "harness or its reference repo carries the canonical copy: "
                 f"{', '.join(stale)}")]
    return [(PASS, "handbook-docs", "no harness-owned handbook docs in docs/")]


def check_channel_invariants(channel, root, extensions=None):
    if channel is None:
        return [(SKIP, "channel", "channel undeclared (reported above)")]
    if channel == "copy":
        return [(PASS, "channel", "copy channel: harness runtime committed by design")]
    # manifest and marketplace both deliver the runtime out-of-band: it is
    # materialized into the working tree but must never be tracked by git.
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", *RUNTIME_PATHS],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return [(SKIP, "channel", "git unavailable; untracked invariant not verified")]
    tracked = [line for line in out.splitlines() if line.strip()]
    # Declared extensions are project-owned skills/agents that live in the runtime
    # tree but are the project's own work — they stay tracked by design, so exclude
    # them from the untracked invariant. A path under any declared extension prefix
    # is not a harness runtime file.
    exts = [e.rstrip("/") for e in (extensions or [])]
    if exts:
        tracked = [
            p for p in tracked
            if not any(p == e or p.startswith(e + "/") for e in exts)
        ]
    if tracked:
        sample = ", ".join(tracked[:5])
        return [(FAIL, "channel",
                 f"{channel} channel but {len(tracked)} harness runtime file(s) "
                 f"tracked: {sample}")]
    msg = f"{channel} channel: no harness runtime files tracked"
    if exts:
        msg += f"; {len(exts)} declared extension(s) kept tracked"
    return [(PASS, "channel", msg)]


def check_reviewer_roster(manifest, root, channel, extensions):
    """Enforce the reviewer roster: the mandatory floor plus declared extras.

    The floor reviewers gate every change and cannot be dropped; a project adds
    reviewers through scripts/layout.toml [harness] extra_reviewers, never
    subtracts. Each roster reviewer must have an agent body in every declared
    tool surface. Each extra reviewer must also be listed in [harness]
    extensions so /materialize preserves it across upgrades. On the marketplace
    channel the bodies ship in the plugin, not the project tree, so the
    existence check is skipped (validated at package time).
    """
    cfg = manifest.get("reviewers")
    if cfg is None:
        return [(SKIP, "reviewer-roster", "manifest declares no [reviewers] floor")]

    rel = manifest["project_data"]["path"]
    path = root / rel
    if not path.is_file():
        return [(SKIP, "reviewer-roster", f"{rel} missing (reported above)")]
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return [(SKIP, "reviewer-roster", f"{rel} unparseable (reported above)")]

    floor = list(cfg["floor"])
    tool_dirs = cfg["tool_dirs"]

    extra = lookup(data, "harness.extra_reviewers")
    if extra is None:
        extra = []
    elif not (isinstance(extra, list) and all(isinstance(e, str) for e in extra)):
        return [(FAIL, "reviewer-roster",
                 "harness.extra_reviewers must be a list of reviewer names")]

    # Declaration check (every channel): an extra reviewer's name must follow the
    # *-reviewer convention, so its review-feedback records match the schema.
    name_re = re.compile(cfg["name_pattern"])
    name_results = [
        (FAIL, "reviewer-roster",
         f"extra reviewer {e!r} must match the *-reviewer naming convention")
        for e in extra if not name_re.match(e)
    ]
    extra = [e for e in extra if name_re.match(e)]

    # A floor reviewer is already in the roster; re-declaring it in
    # extra_reviewers is a mistake (it would also demand a floor body in
    # extensions). Reject it and drop it from the extras set.
    floor_set = set(floor)
    name_results += [
        (FAIL, "reviewer-roster",
         f"{e!r} is a floor reviewer and must not be listed in extra_reviewers")
        for e in extra if e in floor_set
    ]
    extra = [e for e in extra if e not in floor_set]

    tools = lookup(data, "harness.tools")
    if not (isinstance(tools, list) and all(isinstance(t, str) for t in tools)):
        tools = list(tool_dirs)  # absent/invalid: assume every known surface
    tools = [t for t in tools if t in tool_dirs]
    exts = extensions or []

    if channel == "marketplace":
        return name_results + [(SKIP, "reviewer-roster",
                 f"marketplace channel: {len(floor) + len(extra)} reviewer "
                 "bodies ship in the plugin, not the tree")]

    agent_dirs = {(root / tool_dirs[t].format(name="_probe")).parent for t in tools}
    if not any(d.is_dir() for d in agent_dirs):
        return name_results + [(SKIP, "reviewer-roster",
                 "no agent directories present — runtime not materialized in tree")]

    results = list(name_results)
    for name in floor:
        for tool in tools:
            expected = tool_dirs[tool].format(name=name)
            if (root / expected).is_file():
                results.append((PASS, "reviewer-floor", f"{expected} present"))
            else:
                results.append((FAIL, "reviewer-floor",
                                f"floor reviewer body missing: {expected} "
                                "— the four-reviewer floor is mandatory"))
    for name in extra:
        for tool in tools:
            expected = tool_dirs[tool].format(name=name)
            if not (root / expected).is_file():
                results.append((FAIL, "reviewer-roster",
                                f"extra reviewer body missing: {expected}"))
            elif expected not in exts:
                results.append((FAIL, "reviewer-roster",
                                f"extra reviewer {expected} not in [harness] "
                                "extensions — /materialize would prune it"))
            else:
                results.append((PASS, "reviewer-roster", f"{expected} present and kept"))

    # Drift check: a *-reviewer body in the tree that is neither floor nor a
    # declared extra would silently never gate. Declaration is authoritative;
    # this catches the forgotten wiring. Scan EVERY known tool surface, not just
    # the declared ones — a reviewer body dropped into an undeclared surface is
    # exactly the forgotten wiring this check exists to surface.
    roster = set(floor) | set(extra)
    discovered = set()
    for tool in tool_dirs:
        prefix, suffix = tool_dirs[tool].split("{name}")
        agent_dir = root / prefix.rstrip("/")
        if not agent_dir.is_dir():
            continue
        for child in agent_dir.iterdir():
            if not (child.is_file() and child.name.endswith(suffix)):
                continue
            name = child.name[: -len(suffix)] if suffix else child.name
            if name.endswith("-reviewer"):
                discovered.add(name)
    for name in sorted(discovered - roster):
        results.append((FAIL, "reviewer-roster",
                        f"{name} agent body present but not in [harness] "
                        "extra_reviewers — it will not gate; declare it or remove it"))
    return results


# The working-memory artifact a reviewer body must never instruct reading. The
# fresh-eyes invariant: a reviewer judges the change set against long-term memory
# (docs/) and does not take the implementer's plan as review input. The bare slug
# (no `.md`) is matched, so `implementation-plan` and `.scratch/implementation-
# plan.md` both trip it. This is a deterministic regression backstop for the one
# concrete, checkable case — a body re-introducing the plan read. It does NOT
# police prose paraphrase, nor the handoff log a reviewer reads to anchor its
# dispatch (the discipline there lives in the review-workflow skill, not here).
# `design-block` is deliberately NOT forbidden: it is a record inside the handoff
# log every reviewer already reads to find its build-pass anchor, so a body-prose
# grep can neither detect nor prevent seeing it, and the token also matches a body
# that names design-block only to say it must not be consulted.
_FORBIDDEN_REVIEWER_REFS = ("implementation-plan",)


def check_reviewer_fresh_eyes(manifest, root, channel):
    """Fail if any reviewer body instructs reading the implementer's plan.

    Scans every *-reviewer body present in the tree across all known tool
    surfaces. Skipped on the marketplace channel, where bodies are rendered from
    the same source the copy-channel doctor checks, and when no bodies are
    materialized yet.
    """
    cfg = manifest.get("reviewers")
    if cfg is None:
        return [(SKIP, "reviewer-fresh-eyes", "manifest declares no [reviewers] floor")]
    if channel == "marketplace":
        return [(SKIP, "reviewer-fresh-eyes",
                 "marketplace channel: bodies are rendered from the same source "
                 "the copy-channel doctor checks")]

    tool_dirs = cfg["tool_dirs"]
    results = []
    found_any = False
    for tool in tool_dirs:
        prefix, suffix = tool_dirs[tool].split("{name}")
        agent_dir = root / prefix.rstrip("/")
        if not agent_dir.is_dir():
            continue
        for child in sorted(agent_dir.iterdir()):
            if not (child.is_file() and child.name.endswith(suffix)):
                continue
            name = child.name[: -len(suffix)] if suffix else child.name
            if not name.endswith("-reviewer"):
                continue
            found_any = True
            rel = child.relative_to(root)
            text = child.read_text(encoding="utf-8")
            hits = [tok for tok in _FORBIDDEN_REVIEWER_REFS if tok in text]
            if hits:
                results.append((FAIL, "reviewer-fresh-eyes",
                                f"{rel} references working memory ({', '.join(hits)}) "
                                "— a reviewer reads the change set, not the "
                                "implementer's plan (fresh-eyes invariant)"))
            else:
                results.append((PASS, "reviewer-fresh-eyes",
                                f"{rel} reads no working memory"))
    if not found_any:
        return [(SKIP, "reviewer-fresh-eyes",
                 "no reviewer bodies present — runtime not materialized in tree")]
    return results


def check_hook_registration(root):
    """Every hook script in .claude/hooks/ must be registered in settings.

    A hook file with no registration in .claude/settings.json (or the local
    settings.local.json override) never runs — dead weight that silently
    disables whatever it guards. This matters on upgrade: the hook scripts are
    harness-owned runtime that /materialize replaces, and its settings refresh
    now registers each delivered hook deterministically (an added PreToolUse
    matcher, ensure-present), so a freshly materialized project passes. This
    check still guards a project not yet re-materialized, or a settings.json a
    human de-registered — it surfaces any hook left unregistered. On the
    marketplace channel hooks ship in the plugin (registered in its hooks.json),
    not the project tree, so an absent .claude/hooks/ is expected and skipped.
    """
    hooks_dir = root / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return [(SKIP, "hook-registration", "no .claude/hooks/ in tree")]
    scripts = sorted(p.name for p in hooks_dir.glob("*.sh") if p.is_file())
    if not scripts:
        return [(SKIP, "hook-registration", "no hook scripts in .claude/hooks/")]
    blob = ""
    for name in ("settings.json", "settings.local.json"):
        sp = root / ".claude" / name
        if sp.is_file():
            try:
                blob += sp.read_text(encoding="utf-8") + "\n"
            except OSError:
                pass
    if not blob:
        return [(FAIL, "hook-registration",
                 f"{len(scripts)} hook script(s) in .claude/hooks/ but no "
                 ".claude/settings.json to register them")]
    results = []
    for name in scripts:
        # Match the basename as a path segment ("/<name>"), not a bare substring,
        # so a short hook (allow.sh) is not masked by a longer registered one
        # (handoff-allow.sh). Every registration references the hook by path, so
        # the leading slash is always present.
        if "/" + name in blob:
            results.append((PASS, "hook-registration", f"{name} registered"))
        else:
            results.append((FAIL, "hook-registration",
                            f"{name} present in .claude/hooks/ but not registered in "
                            ".claude/settings.json — the hook never runs; add its "
                            "PreToolUse matcher (or remove the script)"))
    return results


def check_required_chapters(root):
    """CLAUDE.md must carry each harness-managed chapter, filled.

    CLAUDE.md is project-owned, but the orchestration doctrine (the
    `## Agent Usage (Mandatory)` chapter) is stack-agnostic harness content,
    identified by its heading rather than by marker comments. /init scaffolds it
    and /materialize refreshes it in place from the single source on every
    upgrade, so the rules stay current without a per-project edit. Each required
    chapter must exist as an exact heading line and have a non-empty body (at
    least one non-blank line before the next `## ` heading or end of file). A
    CLAUDE.md missing or with an empty chapter is a legacy file the /materialize
    migration has not yet converted. Channel-independent — CLAUDE.md is
    project-owned on every channel.
    """
    cm = root / "CLAUDE.md"
    if not cm.is_file():
        return [(FAIL, "required-chapter", "no CLAUDE.md in project root")]
    try:
        lines = cm.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        return [(FAIL, "required-chapter", f"cannot read CLAUDE.md: {e}")]
    # Locate real `## ` headings — those outside fenced code blocks. A heading
    # inside a ```fence``` is illustrative, not a live chapter; skipping fences
    # matches the convention of check_field_tables and check_req_acceptance.
    h2_lines, heading_at, heading_count, in_fence = set(), {}, {}, False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and ln.startswith("## "):
            h2_lines.add(i)
            heading_at.setdefault(ln, i)   # first real occurrence wins
            heading_count[ln] = heading_count.get(ln, 0) + 1
    results = []
    for title in REQUIRED_CHAPTERS:
        start = heading_at.get(title)
        if start is None:
            results.append((FAIL, "required-chapter",
                            f"CLAUDE.md has no '{title}' chapter — run /materialize"))
            continue
        if heading_count[title] > 1:
            # render refreshes only the first occurrence; a second is left stale.
            results.append((FAIL, "required-chapter",
                            f"CLAUDE.md has {heading_count[title]} '{title}' chapters — keep one (run /materialize)"))
            continue
        end = min((i for i in h2_lines if i > start), default=len(lines))
        body = lines[start + 1:end]
        if not any(ln.strip() for ln in body):
            results.append((FAIL, "required-chapter",
                            f"'{title}' chapter is empty — run /materialize"))
        else:
            results.append((PASS, "required-chapter", f"'{title}' present and filled"))
    return results


# The harness stamp: a single greppable line refresh-chapters.sh writes at the top
# of CLAUDE.md — `<!-- harness: <YYYY-MM-DD> -->`, the release date of the
# materialized version. Because CLAUDE.md is the one file injected into every
# session's context, the token lands in every transcript, letting downstream
# analysis attribute a session to the harness that produced it (the docs' line-1
# provenance reaches only the few sessions that open a doc). The date maps
# one-to-one to the version and is orderable. The check is structural — present,
# single, well-formed ISO date. It cannot verify "matches the materializing
# version": a consumer has no harness/VERSION-DATE. check-sync's materialization-
# faithfulness step enforces that for the samples. The well-formed check validates
# shape (`\d{4}-\d{2}-\d{2}`), not calendar ranges — the value is machine-written
# from VERSION-DATE, so an impossible date never reaches a real consumer.
STAMP_LINE = re.compile(r"^<!--\s*harness:")
STAMP_WELL_FORMED = re.compile(r"^<!--\s*harness:\s*(\d{4}-\d{2}-\d{2})\b.*-->\s*$")


def check_harness_stamp(root):
    """CLAUDE.md must carry a single, well-formed harness date stamp."""
    cm = root / "CLAUDE.md"
    if not cm.is_file():
        return [(FAIL, "harness-stamp", "no CLAUDE.md in project root")]
    try:
        # Read bytes, not read_text: read_text does universal-newline translation,
        # which strips \r and would hide the CRLF case the branch below detects.
        raw = cm.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [(FAIL, "harness-stamp", f"cannot read CLAUDE.md: {e}")]
    stamps = [ln for ln in text.splitlines() if STAMP_LINE.match(ln.lstrip())]
    if not stamps:
        # refresh-chapters.sh refuses to stamp a CRLF file, so "no stamp" on a CRLF
        # CLAUDE.md really means CRLF — point there, not into a /materialize loop.
        if b"\r\n" in raw:
            return [(FAIL, "harness-stamp",
                     "CLAUDE.md has CRLF line endings — normalize to LF, then run /materialize")]
        return [(FAIL, "harness-stamp",
                 "CLAUDE.md has no '<!-- harness: <YYYY-MM-DD> -->' stamp — run /materialize")]
    if len(stamps) > 1:
        return [(FAIL, "harness-stamp",
                 f"CLAUDE.md has {len(stamps)} harness stamps — keep one (run /materialize)")]
    m = STAMP_WELL_FORMED.match(stamps[0].strip())
    if not m:
        return [(FAIL, "harness-stamp",
                 "CLAUDE.md harness stamp is malformed — expected "
                 "'<!-- harness: <YYYY-MM-DD> -->' (run /materialize)")]
    return [(PASS, "harness-stamp", f"harness stamp present: {m.group(1)}")]


def count_words(text):
    """Word count matching `wc -w`, after stripping HTML comments.

    HTML comments carry template boilerplate (the provenance line, AGENT
    hints) that should not count against a near-empty materialized doc. Words,
    not lines, is the metric: under the no-hard-wrap writing standard a
    paragraph is a single logical line, so a line count is blind to prose bloat.
    """
    stripped = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    return len(stripped.split())


def _load_layout(manifest, root):
    """Parse the project's layout.toml, or {} when absent/unparseable."""
    path = root / manifest["project_data"]["path"]
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}


def check_doc_budgets(manifest, root):
    """Fail when a budgeted doc exceeds its word ceiling.

    The ceiling defaults to the manifest's max_words and is overridable per
    project through the layout.toml [harness] key the entry names — a recorded,
    reviewable opt-out for genuine scale, never a silent one. Absence of the doc
    is reported by check_file_entry, not here.
    """
    layout = _load_layout(manifest, root)
    results = []
    for entry in manifest["file"]:
        max_words = entry.get("max_words")
        if max_words is None:
            continue
        path = root / entry["path"]
        if not path.is_file():
            continue
        rel = entry["path"]
        ceiling, source = max_words, "default"
        key = entry.get("budget_override_key")
        if key is not None:
            override = lookup(layout, key)
            if isinstance(override, int) and not isinstance(override, bool) and override > 0:
                ceiling, source = override, f"override {key}={override}"
        words = count_words(path.read_text(encoding="utf-8"))
        if words > ceiling:
            remedy = (
                "compact source-owned detail and superseded entries "
                "(doc-sync skill § Compaction)"
            )
            if key is not None:
                remedy += f", or raise {key} in layout.toml [harness] deliberately"
            results.append(
                (FAIL, "doc-budget",
                 f"{rel} is {words} words, over the {ceiling}-word ceiling "
                 f"({source}) — {remedy}")
            )
        else:
            results.append((PASS, "doc-budget", f"{rel} {words}/{ceiling} words ({source})"))
    return results


# A field/parameter/type-table header in system-design.md mirrors a source
# schema that rots when the code changes (document-writing § Prohibited
# Patterns, "Field tables in system-design.md"). The check is anchored at line
# start and fence-aware: a table inside a fenced code block is an illustrative
# example, not a live schema mirror, so it is skipped.
_FIELD_TABLE_HEADER = re.compile(
    r"\s*\|\s*(fields?|parameters?|params?|arguments?|args?)\s*\|",
    re.IGNORECASE,
)


def check_field_tables(manifest, root):
    # The system-design doc owns summaries, not source. A field/parameter table
    # mirrors a source schema that rots when the code changes. The target is the
    # cross_doc source (docs/system-design.md) — the design doc is already named
    # there, so no per-file flag is needed.
    rel = manifest["cross_doc"]["source"]
    path = root / rel
    if not path.is_file():
        return [(SKIP, "field-tables", f"{rel} missing (reported above)")]
    hits, in_fence = [], False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and _FIELD_TABLE_HEADER.match(line):
            hits.append(i)
    if hits:
        shown = ", ".join(str(n) for n in hits[:5])
        return [(FAIL, "field-tables",
                 f"{rel} has {len(hits)} field/parameter table(s) (line(s) {shown}) — "
                 "source is authoritative for field lists; replace each with a one-line "
                 "purpose summary plus a source pointer (document-writing § Prohibited "
                 "Patterns)")]
    return [(PASS, "field-tables", f"{rel}: no field/parameter tables")]


def check_req_acceptance(manifest, root):
    """Every REQ-ID in the PRD must appear in at least one Markdown list item.

    The PRD is narrative prose tagged inline with [REQ-XX-NNN]; the bounded,
    testable contract is the requirement's "Done when" acceptance bullet (a list
    item). A REQ-ID that appears only in prose, a heading, or a table has no
    bounded bar — the fresh-eyes reviewer judges the change against docs/, so an
    untestable requirement is a real gap. Acceptance bullets and the superseded
    mapping are both lists, so an active or retired requirement always qualifies.
    """
    # The PRD is the cross_doc defined_in doc (docs/prd.md) — already named there,
    # so no per-file flag is needed.
    rel = manifest["cross_doc"]["defined_in"]
    path = root / rel
    if not path.is_file():
        return [(SKIP, "req-acceptance", f"{rel} missing (reported above)")]
    req_pattern = re.compile(manifest["cross_doc"]["req_id_pattern"])
    bullet = re.compile(r"^\s*[-*+]\s")
    in_bullet, anywhere, in_fence = set(), set(), False
    for line in path.read_text(encoding="utf-8").splitlines():
        # A REQ-ID inside a fenced code block is an illustrative example, not a
        # live mention — skip fenced lines, as check_field_tables does.
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        ids = req_pattern.findall(line)
        if not ids:
            continue
        anywhere.update(ids)
        if bullet.match(line):
            in_bullet.update(ids)
    orphans = sorted(anywhere - in_bullet)
    if orphans:
        shown = ", ".join(orphans[:5])
        return [(FAIL, "req-acceptance",
                 f"{rel}: {len(orphans)} requirement(s) mentioned only in prose, with no "
                 f"\"Done when\" acceptance bullet: {shown} — give each a tagged list item "
                 "stating its bounded, testable contract")]
    return [(PASS, "req-acceptance",
             f"{rel}: all {len(anywhere)} requirement(s) carry an acceptance bullet")]


def run(project_root, manifest_path):
    manifest = tomllib.loads(Path(manifest_path).read_text(encoding="utf-8"))
    root = Path(project_root)
    results = []
    project_data_results, channel, extensions = check_project_data(manifest, root)
    results.extend(project_data_results)
    for entry in manifest["file"]:
        results.extend(check_file_entry(entry, root))
    results.extend(check_doc_budgets(manifest, root))
    results.extend(check_field_tables(manifest, root))
    results.extend(check_req_acceptance(manifest, root))
    results.extend(check_cross_doc(manifest, root))
    results.extend(check_handbook_refs(manifest, root))
    results.extend(check_handbook_docs_absent(manifest, root))
    results.extend(check_channel_invariants(channel, root, extensions))
    results.extend(check_reviewer_roster(manifest, root, channel, extensions))
    results.extend(check_reviewer_fresh_eyes(manifest, root, channel))
    results.extend(check_hook_registration(root))
    results.extend(check_required_chapters(root))
    results.extend(check_harness_stamp(root))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        results = run(args.project_root.resolve(), args.manifest)
    except (OSError, tomllib.TOMLDecodeError, KeyError, re.error) as exc:
        sys.stderr.write(f"brief_doctor: {exc}\n")
        return 2

    failures = sum(1 for status, _, _ in results if status == FAIL)
    if args.json:
        print(json.dumps(
            [{"status": s, "check": c, "detail": d} for s, c, d in results],
            indent=2,
        ))
    else:
        for status, check, detail in results:
            print(f"{status:4} {check}: {detail}")
        print(f"\n{failures} failure(s), {len(results)} check(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
