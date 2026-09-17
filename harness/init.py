#!/usr/bin/env python3
"""Scaffold the project-owned files a harness consumer commits, and never overwrite one.

    harness/init.py <stack> <target-dir> <project-name> <project-description> [harness-version] [tools-csv] [channel]

The producer-side scaffold over harness/init/ (core overlaid with the stack)
and the doctor's brief templates: the rules file, the settings, the layout
with its channel declaration, the brief roster, and the .gitignore block. The
runtime itself is materialize.py's. Stdlib only.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402
from registry import (  # noqa: E402
    ALL_TOOLS,
    CHANNELS,
    FAILURE_EXIT,
    STACKS,
    USAGE_EXIT,
    LayoutError,
    logical_abspath,
    read_harness_layout,
    read_stamp,
)

USAGE = (
    "usage: init.py <stack> <target> <project-name> <project-description> "
    "[harness-version] [tools-csv] [channel]"
)
REQUIRED_ARGS = 5
MAX_ARGS = 8
DEFAULT_CHANNEL = "copy"
DEFAULT_SPEC_VERSION = "0.2.0"
GITIGNORE_BLOCK = "gitignore-runtime.txt"
# The token init and refresh-gitignore share, so whichever runs first, the
# other recognizes the block and never appends it twice.
GITIGNORE_SENTINEL = "harness runtime"
LEDGER_IGNORE = "\n# Handoff ledger (per-session, never committed)\n.scratch/\n"

INIT_SRC = HERE / "init"

BRIEFS = (
    ("prd.md", "docs/prd.md"),
    ("system-design.md", "docs/system-design.md"),
    ("ubiquitous-language.md", "docs/ubiquitous-language.md"),
    ("testing-principles.md", "docs/testing-principles.md"),
    ("architecture-principles.md", "docs/architecture-principles.md"),
    ("security-principles.md", "docs/security-principles.md"),
    ("adr-README.md", "docs/adr/README.md"),
)


class InitError(Exception):
    """A failure init reports on stderr and exits on with its code."""

    def __init__(self, code: int, message: str, *, verbatim: bool = False) -> None:
        """Carry the exit code and the message; verbatim writes the message as is."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.verbatim = verbatim


def report(message: str) -> None:
    """Write one line to stderr."""
    print(message, file=sys.stderr)


@dataclass(frozen=True, slots=True)
class Request:
    """The scaffold as asked on the command line."""

    stack: str
    target_arg: str
    project_name: str
    project_description: str
    harness_version: str
    tools_csv: str
    channel_arg: str


@dataclass(frozen=True, slots=True)
class Plan:
    """The scaffold resolved against the target: its channel, sources, and replacement map."""

    request: Request
    target: Path
    channel: str
    templates: Path
    toml_array: str
    replacements: dict[str, str]
    layout: Path
    layout_preexisting: bool


@dataclass(slots=True)
class Tally:
    """What one scaffold run wrote, kept, and left unfilled."""

    created: int = 0
    skipped: int = 0
    appended: int = 0
    harness_injected: int = 0
    leaks: list[tuple[str, str]] = field(default_factory=list)


def norm_tools(tools_csv: str) -> list[str]:
    """Return the normalized tool names of a tools-csv: blanks trimmed, empties dropped."""
    # The one normalization shared by the validation and the TOML render, so
    # what is validated is exactly what is written.
    return [n for n in (t.strip().replace(" ", "") for t in tools_csv.split(",")) if n]


def tools_toml(tools_csv: str) -> str:
    """Render the TOML array literal for the tool list, with claude forced on."""
    tools = norm_tools(tools_csv)
    if "claude" not in tools:
        tools.insert(0, "claude")
    return "[" + ", ".join(f'"{t}"' for t in tools) + "]"


def fill(path: Path, replacements: dict[str, str]) -> list[str]:
    """Fill the placeholders of a file in place and return the tokens still present, {{FILL}} aside."""
    # {{FILL}} is the one marker a consumer completes by hand; any other
    # survivor is a skeleton token the replacement map does not cover.
    content = path.read_text(encoding="utf-8")
    for token, value in replacements.items():
        content = content.replace("{{" + token + "}}", value)
    write_guard.write_text(path, content.rstrip("\n") + "\n", encoding="utf-8")
    return [t for t in re.findall(r"\{\{([A-Za-z0-9_-]+)\}\}", content) if t != "FILL"]


def replace_first_line(path: Path, prefix: str, replacement: str) -> None:
    """Replace the first line starting with prefix; a file with no such line stays untouched."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = replacement
            write_guard.write_text(path, "\n".join(lines) + "\n", encoding="utf-8")
            return


def parse_request(argv: list[str]) -> Request:
    """Read the command line into a request, rejecting an unknown stack, tool, or channel."""
    if len(argv) < REQUIRED_ARGS or len(argv) > MAX_ARGS:
        raise InitError(USAGE_EXIT, USAGE)
    stack, target_arg, project_name, project_description = argv[1:REQUIRED_ARGS]
    # An unknown slug would scaffold the core layer alone and report success,
    # the silent-success trap materialize guards the same way.
    if stack not in STACKS:
        raise InitError(
            USAGE_EXIT,
            f"init: unknown stack {stack!r} — no harness/init/stacks/{stack}/ "
            f"(valid: {', '.join(sorted(STACKS))})",
        )
    optional = [*argv[REQUIRED_ARGS:], "", "", ""]
    harness_version, tools_arg, channel_arg = optional[:3]
    tools_csv = tools_arg or ",".join(ALL_TOOLS)
    # A typo'd tool name written into layout.toml would make every later
    # materialize silently drop that tool's surfaces.
    unknown = sorted(set(norm_tools(tools_csv)) - set(ALL_TOOLS))
    if unknown:
        raise InitError(
            USAGE_EXIT,
            f"init: unknown tool(s) {', '.join(unknown)} in tools-csv "
            f"(valid: {', '.join(ALL_TOOLS)})",
        )
    channel = channel_arg or DEFAULT_CHANNEL
    if channel not in CHANNELS:
        raise InitError(
            FAILURE_EXIT,
            f"init: channel must be 'copy', 'manifest', or 'marketplace', got '{channel}'",
        )
    return Request(
        stack,
        target_arg,
        project_name,
        project_description,
        harness_version,
        tools_csv,
        channel_arg,
    )


def resolve_plan(request: Request) -> Plan:
    """Resolve the request against the target: its directory, the sources, and the channel in force."""
    target = logical_abspath(request.target_arg)
    if not target.is_dir():
        raise InitError(
            FAILURE_EXIT, f"init: no such target directory {request.target_arg}"
        )
    harness_version = request.harness_version or read_stamp(
        HERE / "VERSION", "init (or pass [harness-version])"
    )
    # The brief provenance line and the CLAUDE.md stamp carry the release
    # date, the same neutral, orderable token, not the version.
    harness_date = read_stamp(HERE / "VERSION-DATE", "init")
    layout = target / "scripts" / "layout.toml"
    layout_preexisting = layout.exists()
    return Plan(
        request=request,
        target=target,
        channel=_channel_in_force(
            request, target, layout, preexisting=layout_preexisting
        ),
        templates=_templates(),
        toml_array=tools_toml(request.tools_csv),
        replacements={
            "PROJECT_NAME": request.project_name,
            "PROJECT_DESCRIPTION": request.project_description,
            "HARNESS_VERSION": harness_version,
            "HARNESS_DATE": harness_date,
        },
        layout=layout,
        layout_preexisting=layout_preexisting,
    )


def _templates() -> Path:
    # Two layouts share this file: the harness tree keeps the templates under
    # core/.claude/skills, the plugin cache under skills/.
    templates = HERE / "core" / ".claude" / "skills" / "doctor" / "templates"
    if templates.is_dir():
        return templates
    return HERE / "skills" / "doctor" / "templates"


def _channel_in_force(
    request: Request, target: Path, layout: Path, *, preexisting: bool
) -> str:
    # A pre-existing declaration is authoritative: init never flips it, and a
    # conflicting explicit argument fails before any file is written.
    channel = request.channel_arg or DEFAULT_CHANNEL
    if not preexisting:
        return channel
    try:
        declared = read_harness_layout(target)
    except LayoutError as exc:
        raise InitError(FAILURE_EXIT, f"init: {exc}") from exc
    if not declared.channel_declared:
        return channel
    if request.channel_arg and request.channel_arg != declared.channel:
        raise InitError(
            FAILURE_EXIT,
            f"init: {layout} already declares channel = "
            f"'{declared.channel}' — init never flips a "
            "declaration; edit the file to switch channels (adoption "
            "guide § Distribution channels)",
        )
    return declared.channel


def scaffold(plan: Plan) -> Tally:
    """Write every project-owned file the target lacks and return the tally."""
    tally = Tally()
    with write_guard.write_scope(plan.target):
        _overlay_skeletons(plan, tally)
        _refresh_chapters(plan.target)
        _inject_harness_table(plan, tally)
        _normalize_fresh_layout(plan)
        _scaffold_briefs(plan, tally)
        _append_gitignore(plan, tally)
    return tally


def _overlay_skeletons(plan: Plan, tally: Tally) -> None:
    for layer in ("core", f"stacks/{plan.request.stack}"):
        src = INIT_SRC / layer
        if not src.is_dir():
            continue
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            rel = path.relative_to(src).as_posix()
            if rel == GITIGNORE_BLOCK:
                continue
            dest = plan.target / rel
            if dest.exists():
                tally.skipped += 1
                continue
            write_guard.mkdir(dest.parent, parents=True, exist_ok=True)
            write_guard.copy(path, dest)
            if plan.channel == "marketplace" and rel == ".claude/settings.json":
                _drop_hook_matchers(dest)
            tally.leaks += [(rel, t) for t in fill(dest, plan.replacements)]
            tally.created += 1


def _drop_hook_matchers(settings_path: Path) -> None:
    # On the marketplace channel the plugin registers its hooks through its
    # own hooks.json; a project-side matcher would invoke a script that never
    # exists on disk there.
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings.pop("hooks", None)
    write_guard.write_text(settings_path, json.dumps(settings, indent=2) + "\n")


def _refresh_chapters(target: Path) -> None:
    # The skeleton ships each managed heading with an empty body; the single
    # source fills them, and materialize refreshes them on every upgrade.
    if not (target / "CLAUDE.md").is_file():
        return
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
        # The child's diagnostic is the only thing a broken tree leaves to debug with.
        raise InitError(refresh.returncode, refresh.stderr, verbatim=True)


def _inject_harness_table(plan: Plan, tally: Tally) -> None:
    # A kept layout may predate the channel declaration. Appending the table
    # is the one exception to never modifying a project file: a key the
    # doctor requires, added without touching the project's own rules.
    if not plan.layout.is_file():
        return
    layout_text = plan.layout.read_text(encoding="utf-8")
    if re.search(r"^\[harness\]", layout_text, re.MULTILINE):
        return
    layout_text += (
        "\n# Harness identity (added by init): distribution channel + "
        "harness-project API revision.\n"
        f'[harness]\nchannel = "{plan.channel}"\nspec_version = "{_skeleton_spec_version(plan)}"\n'
        f"tools = {plan.toml_array}\nextensions = []\n"
    )
    write_guard.write_text(plan.layout, layout_text, encoding="utf-8")
    tally.harness_injected = 1


def _skeleton_spec_version(plan: Plan) -> str:
    skeleton = INIT_SRC / "stacks" / plan.request.stack / "scripts" / "layout.toml"
    if not skeleton.is_file():
        return DEFAULT_SPEC_VERSION
    match = re.search(
        r'^spec_version = "(.*)"', skeleton.read_text(encoding="utf-8"), re.MULTILINE
    )
    return match.group(1) if match else DEFAULT_SPEC_VERSION


def _normalize_fresh_layout(plan: Plan) -> None:
    # The skeleton ships channel="copy" and every tool; the request wins on a
    # fresh file, while a pre-existing project owns these lines.
    if plan.layout_preexisting or not plan.layout.is_file():
        return
    replace_first_line(plan.layout, "channel = ", f'channel = "{plan.channel}"')
    replace_first_line(plan.layout, "tools = ", f"tools = {plan.toml_array}")


def _scaffold_briefs(plan: Plan, tally: Tally) -> None:
    for template, rel in BRIEFS:
        src = plan.templates / template
        if not src.is_file():
            raise InitError(FAILURE_EXIT, f"init: missing brief template {template}")
        dest = plan.target / rel
        if dest.exists():
            tally.skipped += 1
            continue
        write_guard.mkdir(dest.parent, parents=True, exist_ok=True)
        write_guard.copy(src, dest)
        tally.leaks += [(rel, t) for t in fill(dest, plan.replacements)]
        tally.created += 1


def _append_gitignore(plan: Plan, tally: Tally) -> None:
    # Manifest and marketplace deliver the runtime out-of-band, so it is never
    # committed; copy commits it, so only the handoff ledger is ignored.
    gitignore = plan.target / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    addition = _gitignore_addition(plan.channel, text)
    if addition is None:
        return
    write_guard.write_text(gitignore, text + addition, encoding="utf-8")
    tally.appended = 1


def _gitignore_addition(channel: str, text: str) -> str | None:
    if channel != DEFAULT_CHANNEL:
        if GITIGNORE_SENTINEL in text.lower():
            return None
        return "\n" + (INIT_SRC / "core" / GITIGNORE_BLOCK).read_text(encoding="utf-8")
    if ".scratch/" in text.splitlines():
        return None
    return LEDGER_IGNORE


def tracked_runtime_note(plan: Plan) -> str:
    """Print the untrack hint for a migrating repository and return the summary's note."""
    # A new .gitignore does not untrack what is already committed. Git is
    # never run against the user's repository beyond the read; the report
    # carries the exact command.
    if plan.channel == DEFAULT_CHANNEL or not _inside_git_worktree(plan.target):
        return ""
    runtime_paths = _runtime_paths(INIT_SRC / "core" / GITIGNORE_BLOCK)
    if not runtime_paths:
        return ""
    excludes = _extension_excludes(plan.target)
    result = subprocess.run(
        ["git", "-C", str(plan.target), "ls-files", "--", *runtime_paths, *excludes],
        capture_output=True,
        text=True,
        check=False,
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    if not tracked:
        return ""
    report(
        f"init: NOTE {len(tracked)} harness runtime file(s) are git-tracked; "
        f"untrack them for the {plan.channel} channel:"
    )
    # --ignore-unmatch: a partial-tool project lacks some runtime paths, and
    # git rm fails atomically on the first non-matching pathspec.
    hint = "".join(f' "{p}"' for p in runtime_paths + excludes)
    report(f'  git -C "{plan.target}" rm -r --cached --ignore-unmatch{hint}')
    return f", {len(tracked)} tracked-runtime-file(s)-need-untracking"


def _runtime_paths(block: Path) -> list[str]:
    return [
        line.removesuffix("/*")
        for line in block.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and line != ".scratch/"
    ]


def _extension_excludes(target: Path) -> list[str]:
    # Declared extensions are project-owned and stay tracked. The layout is
    # valid by now; a best-effort read keeps a malformed edit from crashing a
    # migration hint.
    try:
        return [f":!{e}" for e in read_harness_layout(target).extensions]
    except LayoutError:
        return []


def _inside_git_worktree(target: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main(argv: list[str]) -> int:
    """Scaffold the target from the command line and return the exit code."""
    try:
        plan = resolve_plan(parse_request(argv))
        tally = scaffold(plan)
    except InitError as exc:
        if exc.verbatim:
            sys.stderr.write(exc.message)
        else:
            report(exc.message)
        return exc.code
    tracked_note = tracked_runtime_note(plan)
    # A token init was asked to fill must not survive into a consumer's docs.
    if tally.leaks:
        for rel, token in tally.leaks:
            report(f"init: FAIL unfilled placeholder {{{{{token}}}}} in {rel}")
        return FAILURE_EXIT
    print(
        f"init stack={plan.request.stack} channel={plan.channel} tools={plan.toml_array}: "
        f"{tally.created} created, {tally.skipped} pre-existing kept, "
        f"gitignore-block-appended={tally.appended}, "
        f"harness-table-injected={tally.harness_injected}{tracked_note} → {plan.target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
