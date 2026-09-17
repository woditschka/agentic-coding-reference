"""Hold the rendered trees to their sources and the cross-file content invariants."""

import json
import re
import subprocess
import sys
import tomllib
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import registry
import retired_paths
from registry import STACKS, TOOLS

from verify_harness.battery import Battery, RenderCheck, check_render_faithful
from verify_harness.text import (
    FENCE,
    FENCE_PAIR,
    HERE,
    LOCAL_SKILL_LINK,
    ROOT,
    SIBLING_SKILL_LINK,
    fence_state,
    frontmatter_block,
    frontmatter_scalar,
    frontmatter_top_keys,
    h2_headings,
    heading_anchors,
    is_binary,
    norm_links,
    read_text,
    rel,
    section_rows,
    severity_headings,
    strip_frontmatter,
    tag_findings,
)

# The template tokens are built by concatenation so this package never
# matches itself.
PH_TOKENS = tuple("{{" + t + "}}" for t in ("PROJECT_NAME", "PROJECT_DESCRIPTION"))
PH_ALLOW = re.compile(
    r"^(\.claude/skills/(init|harvest)/SKILL\.md$"
    r"|harness/init/"
    r"|plugins/[a-z-]+/init/"
    r"|harness/core/\.claude/skills/doctor/"
    r"|harness/core/scripts/tests/test_doctor\.py$"
    r"|plugins/[a-z-]+/skills/doctor/"
    r"|plugins/[a-z-]+/_engine/scripts/tests/test_doctor\.py$"
    r"|samples/[a-z-]+/\.claude/skills/doctor/"
    r"|samples/[a-z-]+/scripts/tests/test_doctor\.py$"
    r"|samples/[a-z-]+/CLAUDE\.md$"
    r"|samples/[a-z-]+/docs/(prd|system-design)\.md$"
    r"|samples/go/Makefile$"
    # The eval runner fills the init skeletons' tokens per arm; it and its
    # tests name them literally.
    r"|evals/run_eval\.py$"
    r"|evals/tests/test_run_eval\.py$)"
)

CORE_STACK_TOKENS = re.compile(
    r"\bgo\.mod\b|gradlew|build\.gradle|pom\.xml|\.go\b|\.java\b"
    r"|golangci|spotless|JUnit|com/example"
)
SHOWN_STACK_TOKEN_HITS = 10

DESIGN_BLOCK_VERDICTS = {
    "covered",
    "minor",
    "new",
    "refactor-first",
    "foundational",
    "conflicting",
}
REVIEW_FEEDBACK_VERDICTS = {"approved", "changes_requested", "blocked"}
GATE_VERBS_KEY = "gate.verbs"

CLAUDE_AGENTS = TOOLS["claude"]["agents_dir"]
COPILOT_AGENTS = TOOLS["copilot"]["agents_dir"]
OPENCODE_AGENTS = TOOLS["opencode"]["agents_dir"]
# The checker parses the mirror surfaces on its own so one parsing bug
# cannot pass both it and the renderer.
MIRROR_SURFACES = registry.mirror_surfaces()
AGENT_SURFACES = ((CLAUDE_AGENTS, TOOLS["claude"]["suffix"]), *MIRROR_SURFACES)
LAYERS = (HERE / "core", *(HERE / "stacks" / stack for stack in STACKS))

# Claude Code's bundled skill and command names. Bare-name skill resolution
# walks enterprise > personal > project > bundled, so a preloaded frontmatter
# name on this list loads the bundled skill instead of the harness one, and
# does so silently. update-research refreshes this pin.
CLAUDE_CODE_BUNDLED_SKILLS = frozenset(
    {
        "batch",
        "claude-api",
        "code-review",
        "dataviz",
        "debug",
        "design-sync",
        "doctor",
        "fewer-permission-prompts",
        "find-skills",
        "init",
        "keybindings-help",
        "loop",
        "run",
        "schedule",
        "security-review",
        "simplify",
        "update-config",
        "verify",
    }
)

# Per-surface frontmatter vocabularies, pinned from each tool's agent
# documentation and restated in docs/cross-tool-strategy.md. toolCallBudget is
# the harness's own cross-tool key and is valid on every surface; variant-of
# is its render key on the .claude surface only.
HARNESS_FRONTMATTER_KEYS = frozenset({"toolCallBudget"})
FRONTMATTER_VOCABULARY: dict[str, frozenset[str]] = {
    CLAUDE_AGENTS: frozenset(
        {
            "name",
            "description",
            "tools",
            "disallowedTools",
            "model",
            "effort",
            "maxTurns",
            "hooks",
            "skills",
            "isolation",
            "background",
            "variant-of",
        }
    ),
    COPILOT_AGENTS: frozenset(
        {"name", "description", "tools", "model", "hooks", "mcp-servers", "handoffs"}
    ),
    OPENCODE_AGENTS: frozenset(
        {
            "description",
            "mode",
            "model",
            "temperature",
            "top_p",
            "steps",
            "permission",
            "hidden",
            "color",
            "prompt",
            "disable",
        }
    ),
}
OPENCODE_PERMISSION_KEYS = frozenset(
    {
        "read",
        "edit",
        "glob",
        "grep",
        "bash",
        "task",
        "skill",
        "lsp",
        "question",
        "webfetch",
        "websearch",
        "external_directory",
        "doom_loop",
    }
)
OPENCODE_PERMISSION_VALUES = frozenset({"allow", "ask", "deny"})

ADOPTION_TRIO = ("init", "materialize", "harvest")
ADOPTION_CHAPTER = "## Adopt in a Project"
VERBATIM_OWNED_FILES = frozenset({"scripts/backlog.sh", "scripts/stack.sh"})

# The hand-owned parallel file pairs, gated on rosters and vocabulary, never
# prose.
IDE_SKILL_PAIRS = (
    (
        "stacks/go/.claude/skills/goland/SKILL.md",
        "stacks/java-spring-boot/.claude/skills/intellij-idea/SKILL.md",
    ),
    (
        "stacks/go/.claude/skills/goland/goland-mcp-integration.md",
        "stacks/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md",
    ),
    (
        "stacks/go/.claude/skills/goland-doctor/SKILL.md",
        "stacks/java-spring-boot/.claude/skills/intellij-idea-doctor/SKILL.md",
    ),
)
# Product-prose H2 pairs pinned as expected divergence, scoped per pair; a
# pin never licenses the same divergence in another file.
IDE_HEADING_DELTA = {
    IDE_SKILL_PAIRS[0]: {
        ("The Go toolchain stays canonical", "Gradle Stays Canonical")
    },
}
STACK_PARALLEL_FLOOR = 10


def _stack_parallel_files() -> tuple[str, ...]:
    """Derive the roster of .claude markdown files every stack carries."""
    per_stack = [
        {
            path.relative_to(HERE / "stacks" / stack).as_posix()
            for path in (HERE / "stacks" / stack / ".claude").rglob("*.md")
        }
        for stack in STACKS
    ]
    common = set.intersection(*per_stack)
    if len(common) < STACK_PARALLEL_FLOOR:
        raise RuntimeError(
            f"derived stack-parallel roster holds {len(common)} three-way "
            f"files — below the {STACK_PARALLEL_FLOOR}-file floor; stacks tree broken?"
        )
    return tuple(sorted(common))


# Any .claude/**/*.md present in all three stacks is stack-parallel by
# construction; a new three-way file joins the gate without registration.
# The contract-bearing level is the H2 roster; prose below the headings
# diverges per stack freely. A heading only some stacks carry is pinned with
# its exact carrier set, so a carrier dropping it still fails.
STACK_PARALLEL_FILES = _stack_parallel_files()
STACK_PARALLEL_PINNED: dict[str, dict[str, tuple[str, ...]]] = {
    # The agents README names its stack's IDE oracle in the MCP heading;
    # generic binds no oracle and carries no MCP section.
    ".claude/agents/README.md": {
        "MCP Tools (GoLand oracle)": ("go",),
        "MCP Tools (IntelliJ oracle)": ("java-spring-boot",),
    },
    # go/java bind an IDE oracle; only java binds a config surface; generic
    # binds neither.
    ".claude/skills/code-quality-gate/SKILL.md": {
        "IDE Static Analysis (optional)": ("go", "java-spring-boot"),
        "Configuration Sync": ("java-spring-boot",),
    },
    # Each stack names its own checks slot.
    ".claude/skills/security-checks/SKILL.md": {
        "Go-Specific Security Checks": ("go",),
        "Java-Specific Security Checks": ("java-spring-boot",),
        "Stack-Specific Security Checks": ("generic",),
        "IDE-Assisted Checks (optional)": ("go", "java-spring-boot"),
    },
    ".claude/skills/code-quality-review/SKILL.md": {
        "IDE-Assisted Review (optional)": ("go", "java-spring-boot"),
    },
}

_VARIANT_OF = re.compile(r"^variant-of:[ \t]*([A-Za-z0-9_-]+)[ \t]*$")
_FOLDED_SCALAR_MARKERS = (">", ">-", "|", "|-")


def _frontmatter_description(text: str) -> str | None:
    """Return the frontmatter description, folded when block-style, or None when absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    collected: list[str] | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if collected is not None:
            if not line.strip() or line.startswith((" ", "\t")):
                collected.append(line.strip())
                continue
            break
        if line.startswith("description:"):
            value = line[len("description:") :].strip()
            if value in _FOLDED_SCALAR_MARKERS:
                collected = []
            else:
                return value
    return " ".join(collected) if collected is not None else None


def _frontmatter_variant_of(text: str) -> str | None:
    """Return the `variant-of:` target inside the frontmatter block, or None."""
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None
    for line in lines[1:]:
        if line.rstrip() == "---":
            return None
        match = _VARIANT_OF.match(line)
        if match:
            return match.group(1)
    return None


def _frontmatter_skills(text: str) -> list[str]:
    """Return the block-list values of the frontmatter `skills:` key, or [] when absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    names: list[str] | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if names is not None:
            item = line.strip()
            if item.startswith("- "):
                names.append(item[2:].strip().strip("'\""))
                continue
            break
        if line.rstrip() == "skills:":
            names = []
    return names or []


@dataclass(frozen=True, slots=True)
class _AgentFile:
    """One agent surface file with its text read once."""

    path: Path
    text: str

    @classmethod
    def load(cls, path: Path) -> "_AgentFile":
        """Read the agent file at path."""
        return cls(path, read_text(path))

    @property
    def body(self) -> list[str]:
        """Return the lines below the frontmatter."""
        return strip_frontmatter(self.text)

    def scalar(self, key: str) -> str:
        """Return the frontmatter scalar under key, or an empty string."""
        return frontmatter_scalar(self.text, key)


def _surface_files(layer: Path, agents_dir: str, suffix: str) -> list[Path]:
    """List the agent files of one surface in one layer, docs excluded."""
    directory = layer / agents_dir
    if not directory.is_dir():
        return []
    return [
        path
        for path in sorted(directory.glob(f"*{suffix}"))
        if path.stem not in registry.AGENT_DOC_STEMS
    ]


def _agent_files() -> Iterator[Path]:
    """Yield every agent file on every surface of every layer."""
    for layer in LAYERS:
        for agents_dir, suffix in AGENT_SURFACES:
            yield from _surface_files(layer, agents_dir, suffix)


def check_bundled_skill_collision(b: Battery) -> None:
    """Refuse a `skills:` preload that names a Claude Code bundled skill."""
    b.note("bundled-skill-name collision (frontmatter preloads)")
    scanned = 0
    collisions: list[str] = []
    for path in _agent_files():
        names = _frontmatter_skills(read_text(path))
        if not names:
            continue
        scanned += 1
        collisions.extend(
            f"{rel(path)}: skills entry {name!r} collides with a "
            "Claude Code bundled skill — the bundled copy wins the bare name "
            "on the plugin channel"
            for name in names
            if name in CLAUDE_CODE_BUNDLED_SKILLS
        )
    if scanned == 0:
        b.fail("bundled-skill collision check scanned zero skills lists")
        return
    b.report(collisions, f"{scanned} skills lists carry no bundled-skill name")


def _variant_drift(variant: _AgentFile, target: _AgentFile) -> str | None:
    """Return the first rule an effort variant breaks against its target, or None."""
    target_name = target.path.stem
    effort = variant.scalar("effort")
    rules = (
        (
            _frontmatter_variant_of(target.text) is not None,
            f"{rel(variant.path)} chains variant-of onto variant {target_name}",
        ),
        (
            variant.path.stem != f"{target_name}-routine",
            f"{rel(variant.path)} carries variant-of {target_name} but is not "
            f"named {target_name}-routine — the only sanctioned variant shape",
        ),
        (
            variant.body != target.body,
            f"variant body drift: {rel(variant.path)} != {rel(target.path)} "
            "— run render-agent-mirrors, never hand-edit a variant",
        ),
        (
            variant.scalar("model") != target.scalar("model"),
            f"variant model pin drift: {rel(variant.path)} != {rel(target.path)} "
            "— an effort variant keeps its base's model",
        ),
        # A variant shipping its base's effort is a no-op every other gate
        # would pass.
        (
            not effort or effort == target.scalar("effort"),
            f"variant effort pin missing or equal to its base's in "
            f"{rel(variant.path)} — a no-op variant",
        ),
    )
    return next((message for broken, message in rules if broken), None)


def _variant_problems(layer: Path, base: _AgentFile) -> list[str]:
    """Gate a base carrying `variant-of:` against the target it names."""
    target_name = _frontmatter_variant_of(base.text)
    if target_name is None:
        return []
    target_path = layer / CLAUDE_AGENTS / f"{target_name}.md"
    if not target_path.is_file():
        return [
            f"{rel(base.path)} names variant-of {target_name}, "
            "which has no base in this layer"
        ]
    drift = _variant_drift(base, _AgentFile.load(target_path))
    return [drift] if drift else []


def _description_drift(base: _AgentFile, mirror: _AgentFile) -> list[str]:
    """Compare the whitespace-folded frontmatter descriptions of a base and a mirror."""
    base_description = _frontmatter_description(base.text)
    mirror_description = _frontmatter_description(mirror.text)
    if base_description is None:
        return [f"no frontmatter description parsed in {rel(base.path)}"]
    if mirror_description is None:
        return [f"no frontmatter description parsed in {rel(mirror.path)}"]
    if " ".join(base_description.split()) != " ".join(mirror_description.split()):
        return [
            f"agent description drift: {rel(mirror.path)} != {rel(base.path)} "
            "— mirror descriptions restate the base verbatim"
        ]
    return []


def _mirror_problems(base: _AgentFile, mirror_path: Path) -> list[str]:
    """Compare one rendered mirror against its base body and description."""
    if not mirror_path.is_file():
        return [f"missing per-tool agent copy {rel(mirror_path)}"]
    mirror = _AgentFile.load(mirror_path)
    problems = []
    # Each link form is asserted, not just normalized: a sibling whose link
    # was never rewritten is byte-equal to the base and would otherwise pass
    # while shipping a link broken from its directory.
    if any(
        LOCAL_SKILL_LINK in line.replace(SIBLING_SKILL_LINK, "") for line in mirror.body
    ):
        problems.append(
            f"un-rewritten skill link ({LOCAL_SKILL_LINK}) in {rel(mirror_path)} "
            "— broken from this directory"
        )
    if norm_links(mirror.body) != base.body:
        problems.append(
            f"agent body drift (frontmatter aside): {rel(mirror_path)} != {rel(base.path)}"
        )
    problems.extend(_description_drift(base, mirror))
    return problems


def _agent_base_problems(layer: Path, base: _AgentFile) -> list[str]:
    """Gate one .claude base: its body, its variant target, and its mirrors."""
    problems = []
    if not any(line.strip() for line in base.body):
        problems.append(
            f"empty body (or missing frontmatter fence) in {rel(base.path)}"
        )
    problems.extend(_variant_problems(layer, base))
    if any(SIBLING_SKILL_LINK in line for line in base.body):
        problems.append(
            f"sibling link form ({SIBLING_SKILL_LINK}) in {rel(base.path)} "
            f"— the claude copy uses {LOCAL_SKILL_LINK}"
        )
    for mirror_dir, suffix in MIRROR_SURFACES:
        mirror_path = layer / mirror_dir / f"{base.path.stem}{suffix}"
        problems.extend(_mirror_problems(base, mirror_path))
    return problems


def _stray_mirror_problem(
    layer: Path, mirror_dir: str, suffix: str, file: Path
) -> str | None:
    """Name why a file in a mirror directory has no base, or None when it has one."""
    if file.stem in registry.AGENT_DOC_STEMS:
        # The tool loads every matching file as an agent and the renderer's
        # prune never deletes a doc, so a stray doc would ship live.
        return (
            f"{rel(file)} — doc file in a tool agents dir; docs "
            f"live in {CLAUDE_AGENTS}/ only"
        )
    if not file.name.endswith(suffix) or file.name == suffix:
        kind = (
            "copilot agents must be <name>.agent.md"
            if mirror_dir == COPILOT_AGENTS
            else "unexpected non-.md file in a tool agents dir"
        )
        return f"{rel(file)} — {kind}"
    name = file.name[: -len(suffix)]
    if not (layer / CLAUDE_AGENTS / f"{name}.md").is_file():
        return (
            f"{rel(file)} has no {CLAUDE_AGENTS}/{name}.md base "
            "— sibling-only agent, never parity-checked"
        )
    return None


def _stray_mirror_problems(layer: Path) -> list[str]:
    """Sweep the mirror directories for files no base would ever compare."""
    problems = []
    for mirror_dir, suffix in MIRROR_SURFACES:
        directory = layer / mirror_dir
        if not directory.is_dir():
            continue
        for file in sorted(path for path in directory.iterdir() if path.is_file()):
            problem = _stray_mirror_problem(layer, mirror_dir, suffix, file)
            if problem:
                problems.append(problem)
    return problems


def check_agent_body_parity(b: Battery) -> None:
    """Hold every agent's per-tool copies to the body and description of its .claude base."""
    b.note("agent body parity (per-tool copies)")
    problems: list[str] = []
    for layer in LAYERS:
        bases = _surface_files(layer, CLAUDE_AGENTS, ".md")
        if not bases:
            problems.append(
                f"no agent bases under {rel(layer)}/{CLAUDE_AGENTS}/ "
                "— roster empty or path renamed"
            )
        for path in bases:
            problems.extend(_agent_base_problems(layer, _AgentFile.load(path)))
        problems.extend(_stray_mirror_problems(layer))
    b.report(problems, "all per-tool bodies and descriptions identical")


def _compatibility_problems(layer: Path) -> list[str]:
    """Check every skill's `compatibility:` list against the registry's tool names."""
    problems: list[str] = []
    known = ", ".join(sorted(registry.COMPATIBILITY_NAMES))
    for skill in sorted((layer / ".claude/skills").glob("*/SKILL.md")):
        block = re.search(
            r"^compatibility:\n((?:  - .+\n)+)", read_text(skill), re.MULTILINE
        )
        if not block:
            continue
        problems.extend(
            f"unknown compatibility name `{name.strip()}` in {rel(skill)} — "
            f"the registry knows {known}"
            for name in re.findall(r"^  - (.+)$", block.group(1), re.MULTILINE)
            if name.strip() not in registry.COMPATIBILITY_NAMES
        )
    return problems


def _opencode_permission_problems(file: Path, content: str) -> list[str]:
    """Check an OpenCode agent's block-form `permission` map."""
    problems = []
    if frontmatter_scalar(content, "permission"):
        problems.append(
            f"flow-style or scalar `permission` in {rel(file)} — "
            "the gate reads only the block form"
        )
    for key, value in frontmatter_block(content, "permission"):
        if key not in OPENCODE_PERMISSION_KEYS and "*" not in key:
            problems.append(
                f"unknown OpenCode permission key `{key}` in {rel(file)} — "
                "documented keys or a wildcard pattern only"
            )
        # An empty value opens a nested per-command map.
        if value and value not in OPENCODE_PERMISSION_VALUES:
            problems.append(
                f"OpenCode permission `{key}: {value!r}` in {rel(file)} — "
                "value must be allow/ask/deny"
            )
    return problems


def _frontmatter_problems(file: Path, agents_dir: str) -> list[str]:
    """Check one agent file's top-level keys against its surface's pin."""
    content = read_text(file)
    keys = frontmatter_top_keys(content)
    if not keys:
        return [f"no frontmatter keys parsed in {rel(file)}"]
    vocabulary = FRONTMATTER_VOCABULARY[agents_dir] | HARNESS_FRONTMATTER_KEYS
    problems = [
        f"out-of-vocabulary frontmatter key `{key}` in {rel(file)} — not in "
        f"the {agents_dir} pin (docs/cross-tool-strategy.md § Agents / Subagents)"
        for key in keys
        if key not in vocabulary
    ]
    if agents_dir == OPENCODE_AGENTS:
        problems.extend(_opencode_permission_problems(file, content))
    return problems


def check_frontmatter_vocabulary(b: Battery) -> None:
    """Hold every agent file's frontmatter keys inside its tool's pinned vocabulary."""
    b.note("frontmatter vocabulary (per-tool)")
    problems: list[str] = []
    for layer in LAYERS:
        problems.extend(_compatibility_problems(layer))
    for layer in LAYERS:
        for agents_dir, suffix in AGENT_SURFACES:
            files = _surface_files(layer, agents_dir, suffix)
            if not files:
                problems.append(
                    f"no agent frontmatter scanned under {rel(layer / agents_dir)} — "
                    "renamed directory or suffix"
                )
            for file in files:
                problems.extend(_frontmatter_problems(file, agents_dir))
    b.report(problems, "all agent frontmatter keys inside the per-tool pins")


def check_accounting_sync(b: Battery) -> None:
    """Hold the vendored accounting module byte-identical to its canonical home."""
    b.note("accounting vendored-copy sync")
    canonical = ROOT / "tools/harness-stats/accounting.py"
    vendored = HERE / "core/scripts/accounting.py"
    try:
        identical = canonical.read_bytes() == vendored.read_bytes()
    except OSError as exc:
        b.fail(f"could not compare the accounting copies: {exc}")
        return
    if identical:
        b.record_pass("canonical == vendored")
    else:
        b.fail(
            f"{rel(canonical)} != {rel(vendored)} — decide which copy "
            f"holds the intended edit (canonical home: {rel(canonical)}), "
            "then cp it over the other"
        )


def check_spec_version_sync(b: Battery) -> None:
    """Hold the docs' stated spec version equal to the doctor expectations."""
    b.note("spec-version sync (docs vs doctor-expectations)")
    expectations = HERE / "core/scripts/doctor-expectations.toml"
    spec_version = tomllib.loads(read_text(expectations))["spec_version"]
    surfaces = {
        ROOT / "docs/harness-project-api.md": f"**Version:** {spec_version} ",
        ROOT / "docs/adoption-guide.md": f"spec {spec_version} ",
    }
    problems = [
        f"{rel(path)} does not state spec {spec_version} — the doc drifted "
        f"from {rel(expectations)} spec_version; update the doc's version statement"
        for path, needle in surfaces.items()
        if needle not in read_text(path)
    ]
    b.report(problems, f"both docs state spec {spec_version}")


def check_faithfulness(b: Battery) -> None:
    """Re-materialize the samples and flag only what the render changes."""
    b.note("materialization faithfulness")
    if b.quick:
        b.skip("--quick: harness/ and samples/ proven untouched by the guard")
        return

    def on_result(result: subprocess.CompletedProcess[str]) -> None:
        output = result.stdout + result.stderr
        if result.returncode != 0:
            # Abort: the sample checks that follow would read the tree this
            # run left half-written.
            b.fail(f"harness/materialize-samples.sh failed:\n{output}")
            raise SystemExit(1)
        # Committed orphans are invisible to the porcelain diff, so the
        # extras count is their only guard; a missing line means the output
        # format changed and orphan detection is not running.
        extras = re.findall(r"extras: (\d+) file", output)
        for count in extras:
            if count != "0":
                b.fail(
                    f"materialize reported {count} orphan extra(s) — a committed "
                    "file /harness no longer produces. git rm it."
                )
        if not extras:
            b.fail(
                "no 'extras:' line parsed from materialize-samples output — output "
                f"format changed; orphan detection is not running.\n{output}"
            )

    render = RenderCheck(
        paths=("samples/",),
        command=("bash", str(HERE / "materialize-samples.sh")),
        changed_message=(
            "re-materialize changed the samples — a /harness edit was not "
            "materialized, or a sample was hand-edited:"
        ),
        fix_message=(
            "Fix: review the change, then commit the re-materialized samples "
            "with the /harness edit."
        ),
    )
    if check_render_faithful(b, render, on_result):
        b.record_pass("samples == materialize(/harness)")


def _surface_presence_problems(stack: str) -> list[str]:
    """Check one sample against the cross-tool layout rules."""
    sample = ROOT / "samples" / stack
    mirror_skill_dirs = tuple(
        row["agents_dir"].rsplit("/", 1)[0] + "/skills"
        for tool, row in TOOLS.items()
        if tool != "claude"
    )
    agent_dirs = tuple(row["agents_dir"] for row in TOOLS.values())
    forbidden = ("AGENTS.md", ".github/copilot-instructions.md", *mirror_skill_dirs)
    required = ("CLAUDE.md", *agent_dirs, ".claude/skills")
    problems = [
        f"samples/{stack}/{path} exists — CLAUDE.md is the single rules "
        "file and skills live in .claude/skills/ only"
        for path in forbidden
        if (sample / path).exists()
    ]
    problems.extend(
        f"samples/{stack}/{path} missing — required by the cross-tool "
        "compatibility rules"
        for path in required
        if not (sample / path).exists()
    )
    return problems


def _tracked_files(path: str) -> str:
    """Return git's listing of the tracked files under path."""
    return subprocess.run(
        ["git", "ls-files", path],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    ).stdout


def _copy_channel_problems(stack: str) -> list[str]:
    """Check one sample's copy-channel declaration, tracking, and gitignore."""
    sample = ROOT / "samples" / stack
    layout = sample / "scripts/layout.toml"
    layout_text = read_text(layout) if layout.is_file() else ""
    gitignore = sample / ".gitignore"
    gitignore_text = read_text(gitignore) if gitignore.is_file() else ""
    rules = (
        (
            not re.search(r'channel *= *"copy"', layout_text),
            f'samples/{stack}/scripts/layout.toml does not declare channel = "copy"',
        ),
        (
            not re.search(r"extensions *= *\[\]", layout_text),
            f"samples/{stack}/scripts/layout.toml extensions is not [] — the "
            "samples declare none; a non-empty list weakens orphan detection",
        ),
        (
            not _tracked_files(f"samples/{stack}/.claude/skills").strip(),
            f"samples/{stack} runtime is untracked — the copy channel commits it",
        ),
        (
            not re.search(r"^\.scratch/", gitignore_text, re.MULTILINE),
            f"samples/{stack}/.gitignore does not ignore .scratch/",
        ),
        (
            ".claude/skills" in gitignore_text,
            f"samples/{stack}/.gitignore ignores the runtime — the copy "
            "channel commits it",
        ),
    )
    return [message for broken, message in rules if broken]


def check_layout_invariants(b: Battery) -> None:
    """Hold every sample to the cross-tool layout rules and the copy channel."""
    b.note("sample layout invariants (cross-tool rules, copy channel)")
    problems: list[str] = []
    for stack in STACKS:
        problems.extend(_surface_presence_problems(stack))
        problems.extend(_copy_channel_problems(stack))
    b.report(problems, "cross-tool rules and channel invariants hold")


def _hook_registration_problems() -> list[str]:
    """Match the hooks the settings skeleton registers against the hooks core ships."""
    skeleton = read_text(HERE / "init/core/.claude/settings.json")
    registered = set(re.findall(r"\.claude/hooks/([A-Za-z0-9_-]+\.py)", skeleton))
    shipped = {
        path.name
        for path in (HERE / "core/.claude/hooks").glob("*.py")
        if not path.name.startswith("test_")
    }
    problems = [
        f"init settings skeleton registers .claude/hooks/{name}, which "
        "core does not ship — a missing hook script blocks its tool"
        for name in sorted(registered - shipped)
    ]
    problems.extend(
        f"core ships .claude/hooks/{name} but the init settings skeleton "
        "never registers it — a delivered-but-unregistered hook never runs"
        for name in sorted(shipped - registered)
    )
    return problems


def _shipped_skills(stack: str) -> list[str]:
    """List the skill names core and the stack ship, in directory order."""
    roots = (HERE / "core/.claude/skills", HERE / "stacks" / stack / ".claude/skills")
    return [
        path.name
        for root in roots
        if root.is_dir()
        for path in sorted(path for path in root.iterdir() if path.is_dir())
    ]


def _skills_table_problems(stack: str, claude_md: str, agents_readme: str) -> list[str]:
    """Hold the sample's two skills tables equal to the shipped skill roster, both ways."""
    sample = f"samples/{stack}"
    # Presence is judged against the parsed rows, not a whole-file substring,
    # so a row under the wrong heading never satisfies the roster.
    readme_rows = set(section_rows(agents_readme, r"^## Skills"))
    shipped = _shipped_skills(stack)
    problems = []
    if not readme_rows:
        problems.append(
            f"{sample}/.claude/agents/README.md: no rows parsed under "
            "'## Skills' — roster empty or heading renamed"
        )
    for name in shipped:
        if f"| `{name}`" not in claude_md:
            problems.append(
                f"{sample}/CLAUDE.md skills table has no row for shipped skill '{name}'"
            )
        if name not in readme_rows:
            problems.append(
                f"{sample}/.claude/agents/README.md Skills table "
                f"has no row for shipped skill '{name}'"
            )
    if not shipped:
        problems.append(
            f"no shipped skills found for stack {stack} — roster empty or path renamed"
        )
    problems.extend(
        f"{sample}/CLAUDE.md skills table row '{row}' names no shipped skill — ghost row"
        for row in section_rows(claude_md, r"^## (Agent Usage|Stack-specific skills)")
        if row not in shipped
    )
    problems.extend(
        f"{sample}/.claude/agents/README.md Skills row '{row}' names no "
        "shipped skill — ghost row"
        for row in readme_rows
        if row not in shipped
    )
    return problems


def _agents_readme_problems(stack: str, agents_readme: str) -> list[str]:
    """Hold the sample's agents README roster to the shipped agents."""
    roots = (HERE / "core/.claude/agents", HERE / "stacks" / stack / ".claude/agents")
    return [
        f"samples/{stack}/.claude/agents/README.md has no roster "
        f"row for shipped agent '{path.stem}'"
        for root in roots
        if root.is_dir()
        for path in sorted(root.glob("*.md"))
        if path.stem not in registry.AGENT_DOC_STEMS
        and f"**{path.stem}**" not in agents_readme
    ]


def _owned_file_problems(stack: str) -> list[str]:
    """Check presence of every project-owned file and byte-identity of the verbatim ones."""
    owned = [
        ("CLAUDE.md", HERE / "init/stacks" / stack / "CLAUDE.md"),
        (".claude/settings.json", HERE / "init/core/.claude/settings.json"),
        ("scripts/layout.toml", HERE / "init/stacks" / stack / "scripts/layout.toml"),
        ("scripts/backlog.sh", HERE / "init/core/scripts/backlog.sh"),
        (".gitignore", HERE / "init/core/gitignore-runtime.txt"),
    ]
    stack_sh = HERE / "init/stacks" / stack / "scripts/stack.sh"
    if stack_sh.is_file():
        owned.append(("scripts/stack.sh", stack_sh))
    problems = []
    for target, source in owned:
        sample_file = ROOT / "samples" / stack / target
        if not sample_file.is_file():
            problems.append(
                f"samples/{stack}/{target} missing (project-owned committed file)"
            )
        elif not source.is_file():
            problems.append(
                f"{rel(source)} missing — no init skeleton source for {target}"
            )
        elif (
            target in VERBATIM_OWNED_FILES
            and sample_file.read_bytes() != source.read_bytes()
        ):
            problems.append(
                f"samples/{stack}/{target} differs from its init skeleton "
                f"{rel(source)} — copy the skeleton over it"
            )
    return problems


def _brief_problems(stack: str) -> list[str]:
    """Check that every doctor template has its brief in the sample."""
    templates = sorted((HERE / "core/.claude/skills/doctor/templates").glob("*.md"))
    problems = []
    for template in templates:
        brief = (
            "docs/adr/README.md"
            if template.name == "adr-README.md"
            else f"docs/{template.name}"
        )
        if not (ROOT / "samples" / stack / brief).is_file():
            problems.append(
                f"samples/{stack}/{brief} missing — the doctor template "
                f"{template.name} has no sample brief"
            )
    return problems


def _adr_placement_problems(stack: str) -> list[str]:
    """Check that the sample's decision log holds only its README."""
    adr_dir = ROOT / "samples" / stack / "docs/adr"
    entries = (
        sorted(path.name for path in adr_dir.iterdir()) if adr_dir.is_dir() else []
    )
    if entries == ["README.md"]:
        return []
    return [
        f"samples/{stack}/docs/adr must contain only README.md — no "
        "harness ADR is materialized"
    ]


def _stack_roster_problems(stack: str) -> list[str]:
    """Gate one sample's project-owned rosters against the shipped runtime."""
    claude_md = read_text(ROOT / "samples" / stack / "CLAUDE.md")
    agents_readme = read_text(ROOT / "samples" / stack / ".claude/agents/README.md")
    return [
        *_skills_table_problems(stack, claude_md, agents_readme),
        *_agents_readme_problems(stack, agents_readme),
        *_owned_file_problems(stack),
        *_brief_problems(stack),
        *_adr_placement_problems(stack),
    ]


def _chapter(text: str, heading: str) -> str:
    """Return the lines of one H2 chapter, heading included."""
    lines = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line == heading
        if inside:
            lines.append(line)
    return "\n".join(lines)


def _root_skill_table_problems() -> list[str]:
    """Hold the root CLAUDE.md skill table and the adoption chapter to the root skills."""
    root_rows = section_rows(read_text(ROOT / "CLAUDE.md"), r"^## Root-Level Skills$")
    adoption = _chapter(read_text(ROOT / "docs/adoption-guide.md"), ADOPTION_CHAPTER)
    root_skills = sorted(
        path.name for path in (ROOT / ".claude/skills").iterdir() if path.is_dir()
    )
    problems = [
        f"root CLAUDE.md Root-Level Skills table has no row for skill '{name}'"
        for name in root_skills
        if name not in root_rows
    ]
    # The chapter names the trio as typed commands (`/init`) or bare (`init`).
    problems.extend(
        f"docs/adoption-guide.md Adopt in a Project chapter never mentions '{name}'"
        for name in root_skills
        if name in ADOPTION_TRIO
        and f"`{name}`" not in adoption
        and f"`/{name}`" not in adoption
    )
    if not root_skills:
        problems.append(
            "no root skills found under .claude/skills/ — roster empty or path renamed"
        )
    problems.extend(
        f"CLAUDE.md table row '{row}' names no root skill — ghost row"
        for row in root_rows
        if row not in root_skills
    )
    return problems


def check_roster_sync(b: Battery) -> None:
    """Hold the project-owned rosters and skeleton copies in sync with the shipped runtime."""
    b.note(
        "project-owned roster sync (skills tables incl. root, agents README, init coverage)"
    )
    problems = _hook_registration_problems()
    for stack in STACKS:
        problems.extend(_stack_roster_problems(stack))
    problems.extend(_root_skill_table_problems())
    b.report(problems, "tables and skeleton coverage in sync")


def _placeholder_leaks() -> list[str]:
    """Find template tokens outside the documented template locations."""
    problems = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relpath = path.relative_to(ROOT).as_posix()
        # evals/.runs holds whole repo copies whose tokens belong to sources
        # the gate already scans.
        if relpath.startswith((".git/", "evals/.runs/")) or "__pycache__" in path.parts:
            continue
        if is_binary(path):
            continue
        text = read_text(path)
        if any(token in text for token in PH_TOKENS) and not PH_ALLOW.match(relpath):
            problems.append(
                f"template placeholder leaked into {relpath} — outside the "
                "documented template locations"
            )
    return problems


def _placeholder_canary_problems() -> list[str]:
    """Confirm the init skeletons still carry the token the gate scans for."""
    problems = []
    for stack in STACKS:
        skeleton = HERE / "init/stacks" / stack / "CLAUDE.md"
        if not skeleton.is_file() or PH_TOKENS[0] not in read_text(skeleton):
            problems.append(
                f"{PH_TOKENS[0]} not found in harness/init/stacks/{stack}/CLAUDE.md "
                "— token format changed; the placeholder gate is scanning for nothing"
            )
    return problems


def check_placeholder_gate(b: Battery) -> None:
    """Confine the template tokens to the documented template locations."""
    b.note("placeholder gate (template tokens outside documented locations)")
    problems = [*_placeholder_leaks(), *_placeholder_canary_problems()]
    b.report(problems, "placeholders only in documented template locations")


def _handbook_delta() -> Counter[str]:
    """Count the changed lines between the root handbook and its core copy."""
    core_copy = HERE / "core/.claude/skills/handoff-routing/agentic-harness.md"
    result = subprocess.run(
        ["diff", "-U0", "docs/agentic-harness.md", str(core_copy)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    return Counter(
        line
        for line in result.stdout.splitlines()
        if line.startswith(("-", "+")) and not line.startswith(("---", "+++"))
    )


def _handbook_delta_problems() -> list[str]:
    """Compare the handbook delta against its pinned multiset of changed lines."""
    expected_file = HERE / "handbook-delta.expected"
    if not expected_file.is_file():
        return [
            "harness/handbook-delta.expected missing — the pinned handbook "
            "delta has no reference"
        ]
    # The compare is on the multiset of changed lines, not the diff text:
    # Apple and GNU diff group -U0 hunks differently for the same delta.
    expected = Counter(
        line
        for line in read_text(expected_file).splitlines()
        if not line.startswith("#")
    )
    actual = _handbook_delta()
    if actual == expected:
        return []
    detail = [
        *(f"    - {line}" for line in sorted((expected - actual).elements())),
        *(f"    + {line}" for line in sorted((actual - expected).elements())),
        "Fix: reconcile the two copies (owner: docs/agentic-harness.md). "
        "Regenerating the\nexpected delta is an explicit decision — a diff "
        "touching it needs the same review as content drift.",
    ]
    return [
        "docs/agentic-harness.md vs its core copy diverged beyond "
        "harness/handbook-delta.expected:\n" + "\n".join(detail)
    ]


def _self_containment_problems() -> list[str]:
    """Find sample docs that reference another sample or the samples/ tree."""
    # A hyphenated stack name is distinctive enough to match bare; a short
    # one matches only as a path segment, else ordinary prose would match.
    sweeps = [
        (
            re.compile(r"\b" + re.escape(stack) + ("" if "-" in stack else "/")),
            tuple(other for other in STACKS if other != stack),
        )
        for stack in STACKS
    ]
    sweeps.append((re.compile(r"samples/"), tuple(STACKS)))
    hits: set[str] = set()
    for pattern, stacks in sweeps:
        for stack in stacks:
            docs = ROOT / "samples" / stack / "docs"
            if not docs.is_dir():
                continue
            hits.update(
                path.relative_to(ROOT).as_posix()
                for path in sorted(docs.rglob("*"))
                if path.is_file() and pattern.search(read_text(path))
            )
    return [
        f"{hit} references another sample or the samples/ tree — sample "
        "docs must be self-contained"
        for hit in sorted(hits)
    ]


def check_handbook_delta(b: Battery) -> None:
    """Pin the handbook's core-copy delta and keep the sample docs self-contained."""
    b.note("handbook delta (root vs core copy) + sample self-containment")
    problems = [*_handbook_delta_problems(), *_self_containment_problems()]
    b.report(problems, "delta pinned, samples self-contained")


def _schema(name: str) -> Any:  # noqa: ANN401
    """Load one core scratch schema, the parse boundary of the enum gates."""
    return json.loads(read_text(HERE / "core/schemas/scratch" / name))


def _verdict_enum(name: str) -> set[str]:
    """Return the verdict enum of one core scratch schema."""
    return set(_schema(name)["properties"]["verdict"]["enum"])


def _verdict_enum_problems() -> list[str]:
    """Pin the design-block and review-feedback verdict enums to their canonical names."""
    problems = []
    try:
        design_block = _verdict_enum("design-block.schema.json")
        review_feedback = _verdict_enum("review-feedback.schema.json")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        # TypeError: valid JSON of the wrong shape aggregates, never aborts.
        return [f"could not read verdict enums: {exc}"]
    if design_block != DESIGN_BLOCK_VERDICTS:
        problems.append(f"design-block verdict enum is {sorted(design_block)}")
    if review_feedback != REVIEW_FEEDBACK_VERDICTS:
        problems.append(f"review-feedback verdict enum is {sorted(review_feedback)}")
    return problems


def _build_record_problems() -> list[str]:
    """Check that both core build-record schemas defer to the layout's gate verbs."""
    try:
        failure = _schema("build-failure.schema.json")["properties"]
        passing = _schema("build-pass.schema.json")["properties"]
        failed_source = failure["failed_check"].get("enumFrom")
        ran_source = passing["gate_checks_run"]["items"].get("enumFrom")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [f"could not read core build-record schemas: {exc}"]
    if failed_source == GATE_VERBS_KEY and ran_source == GATE_VERBS_KEY:
        return []
    return [
        "core build-record schemas must both defer to layout "
        f"{GATE_VERBS_KEY} via enumFrom (got {failed_source!r} and {ran_source!r})"
    ]


def _gate_skeleton_problems(stack: str) -> list[str]:
    """Check that a stack's layout skeleton declares non-empty gate verbs and a command."""
    skeleton = HERE / "init" / "stacks" / stack / "scripts" / "layout.toml"
    try:
        gate = tomllib.loads(read_text(skeleton)).get("gate", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"{stack}: could not read skeleton layout.toml: {exc}"]
    verbs = gate.get("verbs")
    command = gate.get("command")
    problems = []
    if (
        not isinstance(verbs, list)
        or not verbs
        or not all(isinstance(v, str) for v in verbs)
    ):
        problems.append(
            f"{stack}: skeleton layout.toml [gate] verbs missing or empty — "
            "the build-record vocabulary check would be vacuous"
        )
    if not isinstance(command, str) or not command.strip():
        problems.append(f"{stack}: skeleton layout.toml [gate] command missing")
    return problems


def check_verdict_enums(b: Battery) -> None:
    """Pin the schema enums the routing contract depends on."""
    b.note("verdict-enum sync (design-block, review-feedback, build stages)")
    problems = [*_verdict_enum_problems(), *_build_record_problems()]
    for stack in STACKS:
        problems.extend(_gate_skeleton_problems(stack))
    b.report(problems, "verdict and gate-stage enums in sync")


def check_stack_agnostic_core(b: Battery) -> None:
    """Refuse any stack-specific token under harness/core."""
    b.note("stack-agnostic core (no stack token in harness/core)")
    core = HERE / "core"
    if not core.is_dir():
        b.fail(f"{core} missing — cannot scan for stack tokens")
        return
    try:
        hits = [
            f"{rel(path)}:{number}:{line}"
            for path in sorted(core.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
            for number, line in enumerate(read_text(path).splitlines(), 1)
            if CORE_STACK_TOKENS.search(line)
        ]
    except OSError as exc:
        # An unreadable directory must not report "no stack token" without
        # having looked.
        b.fail(f"could not scan harness/core/ for stack tokens: {exc}")
        return
    if hits:
        shown = "\n".join(f"    {hit}" for hit in hits[:SHOWN_STACK_TOKEN_HITS])
        b.fail(
            f"stack-specific tokens in harness/core/ — move to stacks/<stack>/:\n{shown}"
        )
    else:
        b.record_pass("core carries no stack token")


_LINK = re.compile(r"\]\(([^)\s]+)\)")
_EXTERNAL_LINK_SCHEMES = ("http://", "https://", "mailto:")


def _link_sources() -> list[Path]:
    """List the root-level markdown files whose links are checked."""
    files = [ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "harness/README.md"]
    for pattern in ("docs/**/*.md", ".claude/skills/**/*.md", "tools/**/*.md"):
        files.extend(ROOT.glob(pattern))
    # Run pages under evals/results/runs/ embed agent-authored findings whose
    # links name another repo's tree; links to the pages remain checked.
    run_pages = ROOT / "evals" / "results" / "runs"
    files.extend(
        path
        for path in ROOT.glob("evals/**/*.md")
        if ".runs" not in path.parts and run_pages not in path.parents
    )
    return sorted(set(files))


@cache
def _anchors_of(path: Path) -> set[str]:
    """Return the heading slugs and explicit anchors of one markdown file."""
    return heading_anchors(read_text(path))


def _link_problem(source: Path, target: str) -> str | None:
    """Name why a link target does not resolve from source, or None when it does."""
    if target.startswith(_EXTERNAL_LINK_SCHEMES) or "{{" in target or "<" in target:
        return None
    path_part, _, fragment = target.partition("#")
    destination = source.parent / path_part if path_part else source
    if path_part and not destination.exists():
        return f"-> {target}"
    if (
        fragment
        and destination.is_file()
        and destination.suffix == ".md"
        and fragment not in _anchors_of(destination.resolve())
    ):
        return f"-> {target} (no anchor '{fragment}')"
    return None


def _broken_links(source: Path) -> list[str]:
    """List the unresolved links of one markdown file, fenced blocks skipped."""
    problems = []
    fence = None
    for number, line in enumerate(read_text(source).splitlines(), 1):
        fence = fence_state(line, fence)
        if fence is not None:
            continue
        for target in _LINK.findall(line):
            problem = _link_problem(source, target)
            if problem:
                problems.append(f"{rel(source)}:{number} {problem}")
    return problems


def check_root_links(b: Battery) -> None:
    """Resolve every markdown link and anchor in the root-level files."""
    b.note("root link integrity (markdown links + anchors resolve)")
    broken = [
        problem
        for source in _link_sources()
        if source.is_file()
        for problem in _broken_links(source)
    ]
    if broken:
        shown = "\n".join(f"    {line}" for line in broken)
        b.fail(f"broken markdown links or anchors in root-level files:\n{shown}")
    else:
        b.record_pass("links and anchors resolve")


def _body(path: Path) -> list[str] | None:
    """Return a file's lines below its frontmatter, or None when it is unreadable."""
    # Frontmatter is stripped only when the file opens with a fence, so a
    # frontmatter-less file whose prose carries "---" rules stays whole.
    try:
        text = read_text(path)
    except OSError:
        return None
    lines = text.splitlines()
    if lines and FENCE.match(lines[0]):
        return strip_frontmatter(text)
    return lines


def _ide_pair_problems(pair: tuple[str, str]) -> list[str]:
    """Compare the H2 rosters of one go/java IDE skill pair, pinned pairs aside."""
    go_rel, java_rel = pair
    go_body, java_body = _body(HERE / go_rel), _body(HERE / java_rel)
    if go_body is None or java_body is None:
        missing = go_rel if go_body is None else java_rel
        return [f"parity gates: missing input file — {missing}"]
    go_headings, java_headings = h2_headings(go_body), h2_headings(java_body)
    if not go_headings or not java_headings:
        return [f"parity gates: empty H2 roster in {go_rel} or {java_rel}"]
    pinned = IDE_HEADING_DELTA.get(pair, set())
    drift = [
        f"{go_heading!r} vs {java_heading!r}"
        for go_heading, java_heading in zip(go_headings, java_headings, strict=False)
        if go_heading != java_heading and (go_heading, java_heading) not in pinned
    ]
    if len(go_headings) == len(java_headings) and not drift:
        return []
    detail = "; ".join(drift) or (
        f"{len(go_headings)} vs {len(java_headings)} H2 headings"
    )
    return [f"IDE section-roster drift, {go_rel} vs {java_rel}: {detail}"]


def _pin_problems(
    rel_path: str, pins: dict[str, tuple[str, ...]], headings: dict[str, list[str]]
) -> list[str]:
    """Hold each pinned heading's presence per stack equal to its carrier set."""
    problems = []
    for heading, carriers in pins.items():
        for stack, stack_headings in sorted(headings.items()):
            count = stack_headings.count(heading)
            if (count > 0) != (stack in carriers):
                verb = "lacks" if stack in carriers else "carries"
                problems.append(
                    f"pinned stack-parallel heading '{heading}' ({rel_path}): "
                    f"stacks/{stack} {verb} it, the pin names {sorted(carriers)} "
                    "— sync the file or update the pin"
                )
            elif count > 1:
                # Pinned headings sit outside the ordered roster compare.
                problems.append(
                    f"pinned stack-parallel heading '{heading}' ({rel_path}): "
                    f"stacks/{stack} carries it {count} times — deduplicate"
                )
    return problems


def _stack_parallel_problems(rel_path: str) -> list[str]:
    """Compare one three-way file's H2 rosters across the stacks."""
    pins = STACK_PARALLEL_PINNED.get(rel_path, {})
    problems = []
    headings: dict[str, list[str]] = {}
    rosters: dict[str, list[str]] = {}
    for stack in STACKS:
        lines = _body(HERE / "stacks" / stack / rel_path)
        if lines is None:
            problems.append(
                f"parity gates: missing input file — stacks/{stack}/{rel_path}"
            )
            continue
        headings[stack] = h2_headings(lines)
        roster = [heading for heading in headings[stack] if heading not in pins]
        if not roster:
            problems.append(
                f"parity gates: empty H2 roster in stacks/{stack}/{rel_path}"
            )
            continue
        rosters[stack] = roster
    problems.extend(_pin_problems(rel_path, pins, headings))
    if len(rosters) > 1:
        baseline = next(stack for stack in STACKS if stack in rosters)
        problems.extend(
            f"stack-parallel H2 roster drift, stacks/{stack}/{rel_path}: "
            f"{roster} vs {baseline}'s {rosters[baseline]} — an edit "
            "landed one-sided; sync all three or pin the heading"
            for stack, roster in sorted(rosters.items())
            if roster != rosters[baseline]
        )
    return problems


def _tag_vocabulary_problems() -> list[str]:
    """Hold the feedback tags in the stack skills to review-workflow's canonical set."""
    try:
        review_workflow = read_text(
            HERE / "core/.claude/skills/review-workflow/SKILL.md"
        )
    except OSError:
        review_workflow = ""
    canon = set(section_rows(review_workflow, r"^## Feedback Tags"))
    if not canon:
        return [
            "parity gates: no canonical tags parsed from review-workflow "
            "§ Feedback Tags — the vocabulary gate would be vacuous"
        ]
    problems: list[str] = []
    total_judged = 0
    for path in sorted((HERE / "stacks").glob("*/.claude/skills/**/*.md")):
        judged, findings = tag_findings(read_text(path), canon)
        total_judged += judged
        problems.extend(f"{rel(path)}: {finding}" for finding in findings)
    if total_judged == 0:
        # The stack skills carry tags, so a zero-judged sweep means the glob
        # or the carriers drifted.
        problems.append(
            "parity gates: zero feedback tags reached judgment across "
            "the stack skills — the vocabulary gate scanned nothing"
        )
    return problems


def _severity_problems() -> list[str]:
    """Compare the severity headings across the security-checks copies."""
    problems = []
    rosters: dict[str, list[str]] = {}
    for stack in STACKS:
        security_rel = f"stacks/{stack}/.claude/skills/security-checks/SKILL.md"
        body = _body(HERE / security_rel)
        if body is None:
            problems.append(f"parity gates: missing input file — {security_rel}")
        else:
            rosters[stack] = severity_headings(body)
    if not rosters:
        return problems
    baseline = next(stack for stack in STACKS if stack in rosters)
    if not rosters[baseline]:
        problems.append(
            "parity gates: no H3 headings under '## Severity "
            "Classification' — the severity gate would be vacuous"
        )
    problems.extend(
        f"severity-heading drift, stacks/{stack}/security-checks: "
        f"{roster} vs {baseline}'s {rosters[baseline]}"
        for stack, roster in rosters.items()
        if roster != rosters[baseline]
    )
    return problems


def check_parity_gates(b: Battery) -> None:
    """Gate the hand-owned parallel files on their rosters and vocabulary, never prose."""
    b.note(
        "parity gates (IDE + stack-parallel rosters, tag vocabulary, severity headings)"
    )
    problems: list[str] = []
    for pair in IDE_SKILL_PAIRS:
        problems.extend(_ide_pair_problems(pair))
    for rel_path in STACK_PARALLEL_FILES:
        problems.extend(_stack_parallel_problems(rel_path))
    problems.extend(_tag_vocabulary_problems())
    problems.extend(_severity_problems())
    b.report(problems, "rosters and vocabularies match")


def _check_rendered(b: Battery, script: str, drift: str, passed: str) -> None:
    """Run a renderer's --check mode and report its drift."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "harness" / script), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode:
        detail = "\n".join(
            f"    {line}" for line in (proc.stdout + proc.stderr).strip().splitlines()
        )
        b.fail(f"{drift}\n{detail}")
    else:
        b.record_pass(passed)


# A decision-record citation carries a date; the schema's `2026-01-01-...md`
# placeholder does not. A requirement id whose letters are XX or YY is the
# documented placeholder form.
DECISION_RECORD_CITATION = re.compile(r"docs/adr/\d{4}-\d{2}-\d{2}-(?!\.\.\.)[^\s)`]+")
REQUIREMENT_CITATION = re.compile(r"\bREQ-(?!XX-|YY-)[A-Z]+-\d{3}\b")
RUNTIME_NUMBER = re.compile(
    r"\b(?:toolCallBudget|maxTurns)\b[^\n\d]{0,20}\d+|\b\d+ tool calls\b"
)
PROSE_SUFFIXES = (".md", ".json")


def _shipped_prose_files() -> list[Path]:
    """List the markdown and schema files every layer ships to a consumer."""
    return [
        path
        for layer in LAYERS
        for root in (layer / ".claude", layer / "schemas")
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in PROSE_SUFFIXES
    ]


def _prose_lines(path: Path) -> Iterator[tuple[int, str]]:
    """Yield the numbered lines of a file outside its frontmatter block."""
    lines = read_text(path).splitlines()
    fences_left = FENCE_PAIR if lines and FENCE.match(lines[0]) else 0
    for number, line in enumerate(lines, 1):
        if fences_left and FENCE.match(line):
            fences_left -= 1
            continue
        if fences_left:
            continue
        yield number, line


def _citation_problems(files: list[Path]) -> list[str]:
    """Find decision-record and requirement citations in shipped prose."""
    kinds = (
        (DECISION_RECORD_CITATION, "decision record"),
        (REQUIREMENT_CITATION, "requirement id"),
    )
    return [
        f"{rel(path)}:{number}: cites a {kind} ({match.group()}) — shipped "
        "prose stays self-contained"
        for path in files
        for number, line in _prose_lines(path)
        for pattern, kind in kinds
        if (match := pattern.search(line))
    ]


def check_prose_self_containment(b: Battery) -> None:
    """Refuse a decision-record or requirement citation in the shipped prose."""
    b.note(
        "shipped prose self-containment (no decision-record or requirement citation)"
    )
    files = _shipped_prose_files()
    if not files:
        b.fail("no shipped prose found under the layers — roster empty or path renamed")
        return
    b.report(
        _citation_problems(files),
        f"{len(files)} shipped prose files cite no decision record or requirement",
    )


def _runtime_number_problems(files: list[Path]) -> list[str]:
    """Find a numeric budget or turn cap in shipped prose outside frontmatter."""
    return [
        f"{rel(path)}:{number}: names a runtime number ({match.group().strip()}) — "
        "budgets live in agent frontmatter, prose names the key"
        for path in files
        if path.suffix == ".md"
        for number, line in _prose_lines(path)
        if (match := RUNTIME_NUMBER.search(line))
    ]


def check_runtime_number_free_prose(b: Battery) -> None:
    """Refuse a numeric tool-call budget or turn cap in the shipped prose."""
    b.note("runtime-number-free prose (budgets in frontmatter only)")
    files = _shipped_prose_files()
    if not files:
        b.fail("no shipped prose found under the layers — roster empty or path renamed")
        return
    b.report(
        _runtime_number_problems(files),
        f"{len(files)} shipped prose files name no runtime number",
    )


def check_route_rules(b: Battery) -> None:
    """Hold the committed route-rule inventory equal to the routing source."""
    b.note("route-rule inventory sync (generated from the routing source)")
    _check_rendered(
        b,
        "render-route-rules.py",
        "route-rules.md drifted from the routing source",
        "route-rules.md matches the routing source",
    )


def check_gitignore_block(b: Battery) -> None:
    """Hold the consumer .gitignore runtime block equal to the doctor roster."""
    b.note("gitignore-block sync (generated from the doctor roster)")
    _check_rendered(
        b,
        "render-gitignore-block.py",
        "init/core/gitignore-runtime.txt drifted from doctor.RUNTIME_PATHS",
        "block matches the doctor roster",
    )


def check_adr_index(b: Battery) -> None:
    """Hold the ADR index table equal to the ADR files' status lines."""
    b.note("adr-index sync (generated from the ADR files)")
    _check_rendered(
        b,
        "render-adr-index.py",
        "docs/adr/README.md § Index drifted from the ADR files",
        "index matches the ADR files",
    )


def _latest_release_tag() -> str | None:
    """Return the nearest reachable v* tag, or None when there is none."""
    proc = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v*"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def _live_manifest_entries(entries: list[str], produced: set[str]) -> list[str]:
    """List the manifest entries the current source produces again."""
    return sorted(
        entry
        for entry in entries
        if entry in produced
        or (entry.endswith("/") and any(path.startswith(entry) for path in produced))
    )


def check_retired_paths(b: Battery) -> None:
    """Hold the retired-paths manifest current in both directions."""
    b.note("retired-paths manifest (deletions covered; no live entry)")
    if not retired_paths.MANIFEST.is_file():
        b.fail("harness/retired-paths.txt missing")
        return
    entries, problems = retired_paths.parse_manifest(
        retired_paths.MANIFEST.read_text(encoding="utf-8")
    )
    if problems:
        for problem in problems:
            b.fail(f"retired-paths.txt: {problem}")
        return
    live = _live_manifest_entries(entries, retired_paths.produced_paths(None))
    for entry in live:
        b.fail(
            f"retired-paths.txt entry '{entry}' is produced by the current source — "
            "a reintroduced path must be removed from the manifest (setup.sh "
            "prunes listed paths)"
        )
    tag = _latest_release_tag()
    if tag is None:
        if b.strict:
            b.fail(
                "no v* tag reachable — deletion coverage cannot run. The "
                "push-time gates need tags (CI: checkout fetch-depth: 0)"
            )
        else:
            b.skip("no v* tag reachable — deletion coverage not checked")
        return
    missing = sorted(
        path
        for path in retired_paths.retired_since(tag)
        if not retired_paths.covered(path, entries)
    )
    for path in missing:
        b.fail(
            f"runtime path '{path}' was produced at {tag} but is gone from the "
            "source and missing from harness/retired-paths.txt — record it: "
            f"python3 harness/retired_paths.py update {tag} <label>"
        )
    if not live and not missing:
        b.record_pass(
            f"{len(entries)} entries; deletions since {tag} covered; no entry produced"
        )
