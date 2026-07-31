#!/usr/bin/env python3
"""Scaffold the project-OWNED files a harness consumer commits.

    harness/init.py <stack> <target-dir> <project-name> <project-description> [harness-version] [tools-csv] [channel]

harness-version is the artifact version, independent of the API spec_version.
Omit it (or pass empty) and init reads harness/VERSION — the single source of
truth — so callers normally do not supply it. The provenance line of every
materialized brief is stamped with the harness RELEASE DATE (harness/VERSION-
DATE), not the version: the same neutral, orderable token CLAUDE.md carries,
while the version proper stays a plugin/marketplace concern.

tools-csv is the comma-separated tool surfaces to install (claude is always on;
copilot, opencode, junie optional). Default: all four. The /init skill asks.

channel is "copy" (default — runtime committed into the repo), "manifest"
(runtime materialized and gitignored, not committed), or "marketplace" (the
tool-discovered surfaces — skills, agents, hooks — ship as a plugin; the
project keeps only the materialized engine sliver, gitignored). Copy keeps the
harness self-contained and version-controlled; manifest and marketplace keep
the repo lean and deliver the runtime out-of-band. The /init skill detects an
existing project's channel and defaults a greenfield one to copy — no prompt.
A channel already declared in the target's scripts/layout.toml is
authoritative: init adopts it, and a conflicting argument fails loud.

This lays down only what the PROJECT owns and commits — its CLAUDE.md rules
file, .claude/settings.json, scripts/layout.toml (with the channel
declaration), the docs/ brief roster, and the .gitignore block. It does NOT
install the harness runtime: that is materialize.py, which delivers the
runtime (.claude/skills, agents, schemas, scripts) — committed under the copy
channel (default), gitignored under manifest.

init never overwrites a project file that already exists — re-running it only
fills gaps. A greenfield setup runs init once, then materialize once (or just
/materialize, which runs init first when the project-owned files are missing).

Sources live in harness/init/ (core overlaid with stacks/<stack>) and the
doctor's brief templates (harness/core/.claude/skills/doctor/templates).

Stdlib only. Tested by test_init.py.
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import (  # noqa: E402
    ALL_TOOLS,
    CHANNELS,
    STACKS,
    LayoutError,
    logical_abspath,
    read_harness_layout,
    read_stamp,
)

USAGE = (
    "usage: init.py <stack> <target> <project-name> <project-description> "
    "[harness-version] [tools-csv] [channel]"
)

BRIEFS = (
    ("prd.md", "docs/prd.md"),
    ("system-design.md", "docs/system-design.md"),
    ("ubiquitous-language.md", "docs/ubiquitous-language.md"),
    ("testing-principles.md", "docs/testing-principles.md"),
    ("architecture-principles.md", "docs/architecture-principles.md"),
    ("security-principles.md", "docs/security-principles.md"),
    ("adr-README.md", "docs/adr/README.md"),
)


def norm_tools(tools_csv: str) -> list[str]:
    """The normalized tool names of a tools-csv — blanks trimmed, empties
    dropped. The single normalization shared by the validation in main() and
    tools_toml, so what is validated is exactly what is written."""
    return [n for n in (t.strip().replace(" ", "") for t in tools_csv.split(",")) if n]


def tools_toml(tools_csv: str) -> str:
    """The TOML array literal for the tool list — normalized, claude forced on."""
    tools = norm_tools(tools_csv)
    if "claude" not in tools:
        tools.insert(0, "claude")
    return "[" + ", ".join(f'"{t}"' for t in tools) + "]"


def fill(path: Path, replacements: dict[str, str]) -> list[str]:
    """Literal placeholder fill; trailing newlines normalized to exactly one.

    Returns every placeholder token still present after the fill except
    {{FILL}} — the one marker a consumer completes by hand. A survivor is a
    skeleton token the replacement map does not cover; the caller fails on it
    so the leak never reaches a consumer's committed docs."""
    content = path.read_text(encoding="utf-8")
    for token, value in replacements.items():
        content = content.replace("{{" + token + "}}", value)
    write_guard.write_text(path, content.rstrip("\n") + "\n", encoding="utf-8")
    return [t for t in re.findall(r"\{\{([A-Za-z0-9_-]+)\}\}", content) if t != "FILL"]


def replace_first_line(path: Path, prefix: str, replacement: str) -> None:
    """Replace the first line starting with prefix; every other line verbatim.
    A file with no matching line is left byte-untouched."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = replacement
            write_guard.write_text(path, "\n".join(lines) + "\n", encoding="utf-8")
            return


def main(argv: list[str]) -> int:
    if len(argv) < 5 or len(argv) > 8:
        print(USAGE, file=sys.stderr)
        return 2
    stack, target_arg, project_name, project_description = argv[1:5]
    # Validate the slug against registry.STACKS, the same guard materialize.py
    # applies: an unknown slug would otherwise scaffold the core layer alone
    # (the overlay loop skips a missing stacks/<stack>) and report success —
    # the `java` vs `java-spring-boot` silent-success trap.
    if stack not in STACKS:
        print(
            f"init: unknown stack {stack!r} — no harness/init/stacks/{stack}/ "
            f"(valid: {', '.join(sorted(STACKS))})",
            file=sys.stderr,
        )
        return 2
    harness_version = argv[5] if len(argv) > 5 else ""
    tools_csv = (argv[6] if len(argv) > 6 else "") or ",".join(ALL_TOOLS)
    # Same silent-success trap as the stack slug: a typo'd tool name would be
    # written into layout.toml verbatim, and every later materialize would
    # silently drop that tool's surfaces (the doctor filters unknown names
    # without failing). Reject it here, where it is fixable.
    unknown = sorted(set(norm_tools(tools_csv)) - set(ALL_TOOLS))
    if unknown:
        print(
            f"init: unknown tool(s) {', '.join(unknown)} in tools-csv "
            f"(valid: {', '.join(ALL_TOOLS)})",
            file=sys.stderr,
        )
        return 2
    channel_arg = argv[7] if len(argv) > 7 else ""
    channel = channel_arg or "copy"
    if channel not in CHANNELS:
        print(
            f"init: channel must be 'copy', 'manifest', or 'marketplace', got '{channel}'",
            file=sys.stderr,
        )
        return 1

    target = logical_abspath(target_arg)
    if not target.is_dir():
        print(f"init: no such target directory {target_arg}", file=sys.stderr)
        return 1
    init_src = HERE / "init"
    templates = HERE / "core" / ".claude" / "skills" / "doctor" / "templates"
    toml_array = tools_toml(tools_csv)

    # Artifact version: explicit argument wins; otherwise the harness/VERSION
    # source of truth. Decoupled from spec_version (doctor-validated separately).
    if not harness_version:
        harness_version = read_stamp(
            HERE / "VERSION", "init (or pass [harness-version])"
        )
    # Release date for the brief provenance line (and the CLAUDE.md stamp).
    harness_date = read_stamp(HERE / "VERSION-DATE", "init")
    replacements = {
        "PROJECT_NAME": project_name,
        "PROJECT_DESCRIPTION": project_description,
        "HARNESS_VERSION": harness_version,
        "HARNESS_DATE": harness_date,
    }

    created = skipped = 0
    leaks: list[tuple[str, str]] = []
    layout = target / "scripts" / "layout.toml"
    layout_preexisting = layout.exists()

    # A pre-existing [harness] declaration is authoritative — init never flips
    # it (the adoption guide's channel-switching section owns migration). A
    # conflicting explicit argument fails loud BEFORE any file is written;
    # without one, the declared value drives the remaining steps (gitignore
    # block, migration aid) and the summary, so a re-run cannot misreport the
    # channel it left in place.
    if layout_preexisting:
        try:
            declared_layout = read_harness_layout(target)
        except LayoutError as exc:
            print(f"init: {exc}", file=sys.stderr)
            return 1
        if declared_layout.channel_declared:
            if channel_arg and channel_arg != declared_layout.channel:
                print(
                    f"init: {layout} already declares channel = "
                    f"'{declared_layout.channel}' — init never flips a "
                    "declaration; edit the file to switch channels (adoption "
                    "guide § Distribution channels)",
                    file=sys.stderr,
                )
                return 1
            channel = declared_layout.channel

    with write_guard.write_scope(target):
        # 1. Project-owned skeletons: overlay init/core then init/stacks/<stack>.
        for layer in ("core", f"stacks/{stack}"):
            src = init_src / layer
            if not src.is_dir():
                continue
            for path in sorted(p for p in src.rglob("*") if p.is_file()):
                rel = path.relative_to(src).as_posix()
                if rel == "gitignore-runtime.txt":  # appended below, not a file to copy
                    continue
                dest = target / rel
                if dest.exists():
                    skipped += 1
                    continue
                write_guard.mkdir(dest.parent, parents=True, exist_ok=True)
                write_guard.copy(path, dest)
                leaks += [(rel, t) for t in fill(dest, replacements)]
                created += 1

        # 1a. Fill the harness-managed chapters in the scaffolded CLAUDE.md. The
        # skeleton ships each managed heading with an empty body; copy the single
        # source (harness/claude-md/managed-chapters.md) into them. Idempotent and
        # a no-op ("absent") for any heading the skeleton omits — materialize
        # refreshes them on every upgrade thereafter.
        if (target / "CLAUDE.md").is_file():
            refresh = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "claude-md" / "refresh-chapters.py"),
                    str(target / "CLAUDE.md"),
                    str(HERE),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if refresh.returncode != 0:
                # Re-emit the child's diagnostic — a swallowed stderr leaves only
                # an exit code to debug a broken harness tree with.
                sys.stderr.write(refresh.stderr)
                raise SystemExit(refresh.returncode)

        # 1b. Channel declaration. If the target already had scripts/layout.toml
        # (so the overlay above kept it), it may predate the manifest channel and
        # lack the [harness] table. Additively inject it — append-only, touching no
        # existing key. This is the one exception to "never modify an existing
        # project file": a key the doctor requires, added without altering the
        # project's own rules. It is how an existing copy-channel project migrates.
        harness_injected = 0
        if layout.is_file():
            layout_text = layout.read_text(encoding="utf-8")
            if not re.search(r"^\[harness\]", layout_text, re.MULTILINE):
                skeleton = init_src / "stacks" / stack / "scripts" / "layout.toml"
                spec = "0.1.0"
                if skeleton.is_file():
                    m = re.search(
                        r'^spec_version = "(.*)"',
                        skeleton.read_text(encoding="utf-8"),
                        re.MULTILINE,
                    )
                    if m:
                        spec = m.group(1)
                layout_text += (
                    "\n# Harness identity (added by init): distribution channel + "
                    "harness-project API revision.\n"
                    f'[harness]\nchannel = "{channel}"\nspec_version = "{spec}"\n'
                    f"tools = {toml_array}\nextensions = []\n"
                )
                write_guard.write_text(layout, layout_text, encoding="utf-8")
                harness_injected = 1

        # 1c. Normalize channel and tool surfaces on a freshly scaffolded
        # layout.toml. The skeleton ships channel="copy" and all four tools; set
        # both to the requested values so the user's choice wins. A pre-existing
        # project owns these lines — leave them untouched (the migration injection
        # above wrote the requested values when it added the table).
        if not layout_preexisting and layout.is_file():
            replace_first_line(layout, "channel = ", f'channel = "{channel}"')
            replace_first_line(layout, "tools = ", f"tools = {toml_array}")

        # 2. docs/ brief roster from the doctor templates (project-owned defaults).
        for template, rel in BRIEFS:
            src = templates / template
            if not src.is_file():
                print(f"init: missing brief template {template}", file=sys.stderr)
                return 1
            dest = target / rel
            if dest.exists():
                skipped += 1
                continue
            write_guard.mkdir(dest.parent, parents=True, exist_ok=True)
            write_guard.copy(src, dest)
            leaks += [(rel, t) for t in fill(dest, replacements)]
            created += 1

        # 3. .gitignore. Manifest and marketplace deliver the runtime out-of-band,
        # so it is materialized (or plugin-supplied) and never committed; copy
        # commits the runtime, so only the handoff ledger is ignored. Both append
        # once, guarded by the same case-insensitive "harness runtime" token
        # refresh-gitignore.py writes, so whichever of init or the refresh runs
        # first, the other recognizes the block and never re-appends it (the two
        # must share one detection rule).
        gitignore = target / ".gitignore"
        gi_text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
        appended = 0
        if channel != "copy":
            if "harness runtime" not in gi_text.lower():
                block = (init_src / "core" / "gitignore-runtime.txt").read_text(
                    encoding="utf-8"
                )
                write_guard.write_text(
                    gitignore, gi_text + "\n" + block, encoding="utf-8"
                )
                appended = 1
        elif ".scratch/" not in gi_text.splitlines():
            # copy channel: runtime is committed; ignore only the per-session ledger.
            write_guard.write_text(
                gitignore,
                gi_text
                + "\n# Handoff ledger (per-session, never committed)\n.scratch/\n",
                encoding="utf-8",
            )
            appended = 1

    # 4. Migration aid (manifest/marketplace). Under any out-of-band channel the
    # runtime is gitignored, but a project migrating from the copy channel still
    # has those files git-TRACKED (a new .gitignore does not untrack what is
    # already committed). Git is never run against the user's repo; the report
    # carries the exact untrack command.
    tracked_note = ""
    if channel != "copy" and _inside_git_worktree(target):
        runtime_paths: list[str] = []
        for line in (
            (init_src / "core" / "gitignore-runtime.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        ):
            if not line or line.startswith("#") or line == ".scratch/":
                continue
            runtime_paths.append(line.removesuffix("/*"))
        # Declared extensions are project-owned and stay tracked — exclude them
        # from the untrack so the migration never strips the project's own
        # skills/agents. The layout is already valid here (adopted or injected
        # above); a best-effort read keeps a malformed edit from crashing a
        # migration hint.
        ext_excludes: list[str] = []
        try:
            ext_excludes = [f":!{e}" for e in read_harness_layout(target).extensions]
        except LayoutError:
            ext_excludes = []
        if runtime_paths:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(target),
                    "ls-files",
                    "--",
                    *runtime_paths,
                    *ext_excludes,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            tracked = [l for l in result.stdout.splitlines() if l.strip()]
            if tracked:
                n = len(tracked)
                tracked_note = f", {n} tracked-runtime-file(s)-need-untracking"
                print(
                    f"init: NOTE {n} harness runtime file(s) are git-tracked; "
                    f"untrack them for the {channel} channel:",
                    file=sys.stderr,
                )
                # --ignore-unmatch: a partial-tool project lacks some runtime
                # paths; without it git rm fails atomically on the first
                # non-matching pathspec. Quote each pathspec so the printed
                # command survives a path with spaces.
                hint = "".join(f' "{p}"' for p in runtime_paths + ext_excludes)
                print(
                    f'  git -C "{target}" rm -r --cached --ignore-unmatch{hint}',
                    file=sys.stderr,
                )

    # Self-verify: a token init was asked to fill must not survive into a
    # consumer's committed docs. {{FILL}} rows outside the replacement map
    # are the consumer's to complete and are not checked here.
    if leaks:
        for rel, token in leaks:
            print(
                f"init: FAIL unfilled placeholder {{{{{token}}}}} in {rel}",
                file=sys.stderr,
            )
        return 1

    print(
        f"init stack={stack} channel={channel} tools={toml_array}: "
        f"{created} created, {skipped} pre-existing kept, "
        f"gitignore-block-appended={appended}, "
        f"harness-table-injected={harness_injected}{tracked_note} → {target}"
    )
    return 0


def _inside_git_worktree(target: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
