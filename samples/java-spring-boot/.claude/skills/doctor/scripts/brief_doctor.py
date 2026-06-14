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

DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "brief-expectations.toml"

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
    "scripts/handoff.py",
    "scripts/test_handoff.py",
    "scripts/score-change.py",
    "scripts/test_score_change.py",
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
        return [(FAIL, "project-data", f"{rel} missing")], None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [(FAIL, "project-data", f"{rel} unparseable: {exc}")], None

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


def check_cross_doc(manifest, root):
    cfg = manifest["cross_doc"]
    source = root / cfg["source"]
    target = root / cfg["defined_in"]
    if not source.is_file() or not target.is_file():
        return [(SKIP, "cross-doc", "source or target missing (reported above)")]
    pattern = re.compile(cfg["req_id_pattern"])
    cited = set(pattern.findall(source.read_text(encoding="utf-8")))
    defined = set(pattern.findall(target.read_text(encoding="utf-8")))
    unknown = sorted(cited - defined)
    if unknown:
        return [(FAIL, "cross-doc",
                 f"cited in {cfg['source']} but not defined in {cfg['defined_in']}: "
                 + ", ".join(unknown))]
    return [(PASS, "cross-doc", f"{len(cited)} REQ-ID citation(s), all defined")]


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
    # their content ships with the harness (installed skills, or reference-only).
    # A project migrating from an older harness that copied them into docs/ should
    # remove them — /materialize proposes exactly this. None of the roster files
    # are denylist names, so the roster is never implicated.
    names = manifest["handbook"]["denylist"]
    docs = root / "docs"
    stale = sorted(n for n in names if (docs / n).is_file())
    if stale:
        return [(FAIL, "handbook-docs",
                 "docs/ holds harness-owned handbook doc(s) — remove them, they ship "
                 f"with the harness: {', '.join(stale)}")]
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


def run(project_root, manifest_path):
    manifest = tomllib.loads(Path(manifest_path).read_text(encoding="utf-8"))
    root = Path(project_root)
    results = []
    project_data_results, channel, extensions = check_project_data(manifest, root)
    results.extend(project_data_results)
    for entry in manifest["file"]:
        results.extend(check_file_entry(entry, root))
    results.extend(check_cross_doc(manifest, root))
    results.extend(check_handbook_refs(manifest, root))
    results.extend(check_handbook_docs_absent(manifest, root))
    results.extend(check_channel_invariants(channel, root, extensions))
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
