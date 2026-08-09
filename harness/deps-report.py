#!/usr/bin/env python3
"""deps-report: collect every pinned tool/plugin version the upgrade-deps
skill tracks, group by item, and fail on intra-item drift.

The mechanical half of the upgrade-deps skill's collect step, plus its
consistency rule: one item, one version, however many locations restate it
(build file, README table, CLAUDE.md table, init skeleton). Judgment —
upstream lookup, changelog risk, approval, the bump itself — stays in the
skill. A missing location or a version disagreement exits non-zero: the
class of drift where a bump lands in the sample but not the skeleton every
new consumer is scaffolded from.

    harness/deps-report.py [--resolve-shas]

--resolve-shas additionally verifies each workflow action's `# vX.Y.Z`
comment names the same release as its pinned SHA, via `git ls-remote`
against github.com (network; no extra tooling — git is already required).
Without it the SHA/comment pair is only checked for internal consistency
across workflow files.

The local half runs on every battery pass as verify-harness step 4c; the
network half stays in the upgrade-deps skill.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# item → the locations that restate its pin (the upgrade-deps skill's
# "Pinned In" columns, including the init skeletons). Every location must
# exist and match; the first capture group is the version string.
ITEMS: dict[str, list[tuple[str, str]]] = {
    "go": [
        ("samples/go/go.mod", r"^go (\S+)"),
        ("samples/go/README.md", r"^\| Go \| ([^|]+?) \|"),
        ("samples/go/CLAUDE.md", r"^\| Go \| ([^|]+?) \|"),
        ("harness/init/stacks/go/CLAUDE.md", r"^\| Go \| ([^|]+?) \|"),
    ],
    "golangci-lint": [
        ("samples/go/Makefile", r"^GOLANGCI_LINT_VERSION\s*[?:]?=\s*(\S+)"),
        ("samples/go/README.md", r"^\| golangci-lint \| ([^|]+?) \|"),
        ("samples/go/CLAUDE.md", r"^\| golangci-lint \| ([^|]+?) \|"),
        ("harness/init/stacks/go/CLAUDE.md", r"^\| golangci-lint \| ([^|]+?) \|"),
    ],
    "java": [
        ("samples/java-spring-boot/build.gradle", r"JavaLanguageVersion\.of\((\d+)\)"),
        ("samples/java-spring-boot/README.md", r"^\| Java \| ([^|]+?) \|"),
        ("samples/java-spring-boot/CLAUDE.md", r"^\| Java \| ([^|]+?) \|"),
        ("harness/init/stacks/java-spring-boot/CLAUDE.md", r"^\| Java \| ([^|]+?) \|"),
    ],
    "gradle": [
        (
            "samples/java-spring-boot/gradle/wrapper/gradle-wrapper.properties",
            r"gradle-([0-9][0-9.]*)-bin\.zip",
        ),
        ("samples/java-spring-boot/README.md", r"^\| Gradle \| ([^|]+?) \|"),
        ("samples/java-spring-boot/CLAUDE.md", r"^\| Gradle \| ([^|]+?) \|"),
        (
            "harness/init/stacks/java-spring-boot/CLAUDE.md",
            r"^\| Gradle \| ([^|]+?) \|",
        ),
        ("README.md", r"Gradle ([0-9][0-9.]*)"),
        (
            "samples/java-spring-boot/docs/system-design.md",
            r"^\| Build tool \| Gradle[^|]*\| ([^|]+?) \|",
        ),
    ],
    "spring-boot": [
        (
            "samples/java-spring-boot/build.gradle",
            r"id 'org\.springframework\.boot' version '([^']+)'",
        ),
        ("samples/java-spring-boot/README.md", r"^\| Spring Boot \| ([^|]+?) \|"),
        ("samples/java-spring-boot/CLAUDE.md", r"^\| Spring Boot \| ([^|]+?) \|"),
        (
            "harness/init/stacks/java-spring-boot/CLAUDE.md",
            r"^\| Spring Boot \| ([^|]+?) \|",
        ),
    ],
    "spring-dependency-management": [
        (
            "samples/java-spring-boot/build.gradle",
            r"id 'io\.spring\.dependency-management' version '([^']+)'",
        ),
    ],
    "spotless": [
        (
            "samples/java-spring-boot/build.gradle",
            r"id 'com\.diffplug\.spotless' version '([^']+)'",
        ),
    ],
    "google-java-format": [
        ("samples/java-spring-boot/build.gradle", r"googleJavaFormat\('([^']+)'\)"),
    ],
    "spring-modulith-bom": [
        ("samples/java-spring-boot/build.gradle", r"spring-modulith-bom:([^']+)'"),
    ],
}

# Subpath actions (owner/repo/path@sha) are captured too — the gh call below
# resolves tags against the first two segments.
USES_RE = re.compile(
    r"uses:\s*([\w.-]+/[\w.-]+(?:/[\w.-]+)*)@([0-9a-f]{40})\s*#\s*(v\S+)"
)


@dataclass(frozen=True)
class ActionPin:
    """One SHA-pinned workflow action: the pinned commit, its `# vX.Y.Z`
    comment tag, and the first workflow file that pinned it (named in the
    disagreement message). Replaces a positional (sha, tag, wf) tuple so the
    reads are `pin.workflow`, not `pin[2]`."""

    sha: str
    tag: str
    workflow: str


def collect() -> tuple[list[tuple[str, str, int]], list[str]]:
    """(rows, problems): one row per item, one problem string per defect."""
    rows: list[tuple[str, str, int]] = []
    problems: list[str] = []
    for item, locations in ITEMS.items():
        found: dict[str, str] = {}
        for rel, pattern in locations:
            path = ROOT / rel
            if not path.is_file():
                problems.append(f"{item}: missing file {rel}")
                continue
            m = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
            if m is None:
                problems.append(f"{item}: no pin matched in {rel}")
                continue
            found[rel] = m.group(1).strip()
        values = set(found.values())
        if len(values) > 1:
            detail = "; ".join(f"{rel}={v}" for rel, v in sorted(found.items()))
            problems.append(f"{item}: locations disagree — {detail}")
        rows.append((item, ", ".join(sorted(values)) or "—", len(found)))
    return rows, problems


def collect_actions() -> tuple[dict[str, ActionPin], list[str]]:
    """(pins, problems): every SHA-pinned workflow action with its comment
    tag. The same action pinned in several workflows must agree exactly."""
    pins: dict[str, ActionPin] = {}
    problems: list[str] = []
    for wf in sorted((ROOT / ".github/workflows").glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        # Every remote action must match USES_RE in full: a tag-only pin or a
        # SHA pin whose `# vX.Y.Z` comment was dropped would otherwise vanish
        # from the report instead of failing it. Local `./` actions carry no
        # pin and are exempt.
        for line in text.splitlines():
            m = re.search(r"uses:\s*(\S+)", line)
            if m and not m.group(1).startswith("./") and not USES_RE.search(line):
                problems.append(
                    f"{wf.name}: '{line.strip()}' is not a full-SHA pin with "
                    "a '# vX.Y.Z' comment — invisible to this report"
                )
        for action, sha, tag in USES_RE.findall(text):
            prior = pins.setdefault(action, ActionPin(sha, tag, wf.name))
            if (sha, tag) != (prior.sha, prior.tag):
                problems.append(
                    f"{action}: {wf.name} pins {sha[:12]} {tag}, "
                    f"{prior.workflow} pins {prior.sha[:12]} {prior.tag}"
                )
    return pins, problems


def resolve_shas(pins: dict[str, ActionPin]) -> list[str]:
    """Verify each '# vX.Y.Z' comment names the commit its SHA pins.

    The pinned SHA is what runs; the comment is what a reviewer reads. A
    valid-but-wrong SHA passes CI green while the comment lies — the exact
    supply-chain scenario SHA-pinning exists for. Resolution uses
    `git ls-remote` (no GitHub CLI in this environment); the peeled `^{}`
    line is the commit an annotated tag points at."""
    problems: list[str] = []
    for action, pin in sorted(pins.items()):
        sha, tag = pin.sha, pin.tag
        repo = "/".join(action.split("/")[:2])
        try:
            result = subprocess.run(
                [
                    "git",
                    "ls-remote",
                    f"https://github.com/{repo}.git",
                    f"refs/tags/{tag}",
                    f"refs/tags/{tag}^{{}}",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            problems.append(f"{action}: cannot run git ls-remote ({exc})")
            break
        rows = dict(
            (ref, obj)
            for obj, ref in (
                line.split(None, 1)
                for line in result.stdout.splitlines()
                if line.strip()
            )
        )
        real = rows.get(f"refs/tags/{tag}^{{}}") or rows.get(f"refs/tags/{tag}")
        if result.returncode != 0 or not real:
            problems.append(
                f"{action}: cannot resolve tag {tag} on github.com "
                f"({result.stderr.strip().splitlines()[:1]})"
            )
            continue
        if real != sha:
            problems.append(
                f"{action}: comment says {tag} ({real[:12]}…) but the "
                f"pinned SHA is {sha[:12]}… — the comment lies about "
                "what runs"
            )
    return problems


def main(argv: list[str]) -> int:
    # Fail loud on an unknown flag: a typo like --resolve-sha would otherwise
    # silently skip the SHA verification while printing the same table.
    # main() receives sys.argv[1:], so every element is an argument.
    unknown = [a for a in argv if a != "--resolve-shas"]
    if unknown:
        print(
            f"deps-report: unknown argument(s): {' '.join(unknown)} "
            "(only --resolve-shas is accepted)",
            file=sys.stderr,
        )
        return 2
    resolve = "--resolve-shas" in argv
    rows, problems = collect()
    pins, action_problems = collect_actions()
    problems += action_problems
    if resolve:
        problems += resolve_shas(pins)

    width = max(len(item) for item, _, _ in rows)
    for item, version, n in rows:
        print(f"  {item:<{width}}  {version}  ({n} location(s))")
    for action, pin in sorted(pins.items()):
        print(
            f"  {action:<{width}}  {pin.tag} @ {pin.sha[:12]}"
            f"{'  (sha resolved)' if resolve else ''}"
        )
    if problems:
        print()
        for p in problems:
            print(f"deps-report: FAIL {p}", file=sys.stderr)
        return 1
    print("deps-report: all pins consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
