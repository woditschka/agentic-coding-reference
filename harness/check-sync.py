#!/usr/bin/env python3
"""Local deterministic gate for the harness + samples: the mechanical,
no-judgment half of an audit-harness review. This header is the authoritative
step list — docs reference it rather than re-enumerating:
  1  shellcheck (harness/ + tools/)      3f  verdict-enum sync (schemas)
  1b bandit (python security lint)       3g  stack-agnostic core
  2  python syntax                       3h  root link integrity
  2b agent body parity (per-tool copies) 4   sample test suites
  2c agent-body renderer self-test       4b  sample build-file script refs
  3  materialization faithfulness        5   sample doctors
  3b sample layout invariants            6   harness unit suites
  3c project-owned roster sync           6b  generic-stack self-test
  3d placeholder gate                    7   marketplace faithfulness
  3e handbook delta + self-containment   8   marketplace acceptance
                                         9   real plugin install (claude CLI)
Aggregates failures (does not stop at the first) and exits non-zero if any
check fails. Sole exception: a bootstrap crash in step 3 aborts the run —
the sample checks that follow read the tree it produces.
Tier 0 of the maintainer loop (root CLAUDE.md): run it after
every edit — via release-prep.sh after a /harness edit, or as a git pre-push
hook. This project is local-only — there is no server-side CI.

    harness/check-sync.py [--quick]

--quick is tier 0 for an edit that touches none of harness/, samples/,
plugins/, .claude-plugin/ (i.e. docs, root skills, tools/). It REFUSES to
run while any of those trees is dirty vs HEAD; only then does it skip — with
a loud SKIP line each — the steps that re-render or execute those trees
(2c, 3, 4, 5, 6, 6b, 7, 8, 9). Every static check still runs, so --quick can
never skip a check the pending edit could affect. A /harness edit takes the
full battery via release-prep.sh, unchanged; an /audit-harness run always
uses the full battery.

Needs git and python3; bash for the shell sub-suites; shellcheck and bandit
if present (each skipped with a note if not). No Go/Java toolchain required.
The faithfulness
step re-materializes the samples in place: it is dirty-tree-safe — it flags
only changes the re-materialize *introduces* (a /harness edit you forgot to
materialize, or a hand-edited sample), never your already-pending work.

Pure helpers are unit-tested by test_check_sync.py (battery step 6).
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import helpers  # noqa: E402
from helpers import STACKS, TOOLS  # noqa: E402

FENCE = re.compile(r"^---[ \t]*$")
SKILL_ROW = re.compile(r"^\| `([a-z0-9-]*)`")

# The PROJECT_NAME / PROJECT_DESCRIPTION template tokens, built by
# concatenation so this script never matches itself.
PH_TOKENS = tuple("{{" + t + "}}" for t in ("PROJECT_NAME", "PROJECT_DESCRIPTION"))
PH_ALLOW = re.compile(
    r"^(\.claude/skills/(init|harvest)/SKILL\.md$"
    r"|harness/init/"
    r"|harness/core/\.claude/skills/doctor/"
    r"|harness/core/scripts/test_brief_doctor\.py$"
    r"|plugins/[a-z-]+/skills/doctor/"
    r"|plugins/[a-z-]+/_engine/scripts/test_brief_doctor\.py$"
    r"|samples/[a-z-]+/\.claude/skills/doctor/"
    r"|samples/[a-z-]+/scripts/test_brief_doctor\.py$"
    r"|samples/[a-z-]+/CLAUDE\.md$"
    r"|samples/[a-z-]+/docs/(prd|system-design)\.md$"
    r"|samples/go/Makefile$)"
)

CORE_STACK_TOKENS = re.compile(
    r"\bgo\.mod\b|gradlew|build\.gradle|pom\.xml|\.go\b|\.java\b"
    r"|golangci|spotless|JUnit|com/example"
)

DESIGN_BLOCK_VERDICTS = {"covered", "minor", "new", "refactor-first",
                         "foundational", "conflicting"}
REVIEW_FEEDBACK_VERDICTS = {"approved", "changes_requested", "blocked"}

# Mirror surfaces and their file suffixes — the same helpers.TOOLS-derived
# data the renderer uses (the parsing logic stays independent on purpose).
MIRROR_SURFACES = helpers.mirror_surfaces()

# Per-stack build-binding file and its minimum .py-ref count. A stack absent
# from this table fails step 4b loudly. Generic's stack.sh is an
# unfilled-by-design skeleton (the consumer binds it), so its zero is expected.
BUILD_BINDINGS = {
    "go": ("Makefile", 1),
    "java-spring-boot": ("build.gradle", 1),
    "generic": ("scripts/stack.sh", 0),
}

# Sample suites shipped by every stack (step 4). A missing file is a FAIL,
# not a skip — a silent [ -f ] guard once let the generic stack run without
# test_score_change.py while the battery stayed green.
SAMPLE_SUITES = (
    "scripts/test_brief_doctor.py",
    "scripts/test_handoff.py",
    "scripts/test_score_change.py",
    ".claude/hooks/test_handoff_allow.py",
    ".claude/hooks/test_handoff_log_guard.py",
    ".claude/hooks/test_sendmessage_continue_only.py",
)


# --- pure helpers (unit-tested by test_check_sync.py) -----------------------

def strip_frontmatter(text):
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


def norm_links(lines):
    """Sibling link form → the base form (the one documented body difference)."""
    return [l.replace("../../.claude/skills/", "../skills/") for l in lines]


def section_rows(text, heading_pattern):
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


def is_binary(path):
    """grep -I semantics: a NUL byte in the head marks a binary file."""
    try:
        return b"\0" in path.read_bytes()[:8192]
    except OSError:
        return True


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


# --- the battery -------------------------------------------------------------

class Battery:
    def __init__(self, quick):
        self.quick = quick
        self.failed = False

    def note(self, title):
        print(f"== {title} ==")

    def fail(self, message):
        print(f"FAIL: {message}", file=sys.stderr)
        self.failed = True

    def show_fail(self, output):
        """A failed sub-suite's output with the passing noise dropped."""
        lines = [l for l in output.splitlines() if not l.startswith("ok")]
        for line in lines[-40:]:
            print(f"    {line}", file=sys.stderr)

    def skip(self, message):
        print(f"  SKIP ({message})")

    def run_suite(self, label, script, skip_re=None, skip_label=None):
        """Run a battery sub-suite, aggregating its failure like every step."""
        runner = [sys.executable] if script.endswith(".py") else ["bash"]
        self.note(label)
        if self.quick:
            self.skip("--quick: inputs proven untouched by the guard")
            return
        result = subprocess.run(runner + [str(ROOT / script)],
                                capture_output=True, text=True, cwd=ROOT, check=False)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            self.fail(f"{script} did not pass:")
            self.show_fail(output)
        elif skip_re and re.search(skip_re, output, re.M):
            print(f"  {skip_label}")
        else:
            print("  pass")


def git_status(*paths):
    result = subprocess.run(["git", "status", "--porcelain", "--", *paths],
                            capture_output=True, text=True, cwd=ROOT, check=True)
    return result.stdout


def check_shellcheck(b):
    """1. Shell lint (harness source scripts + the shipped user-level tooling)."""
    b.note("shellcheck (harness/ + tools/)")
    if shutil.which("shellcheck") is None:
        print("  SKIP: shellcheck not installed (brew install shellcheck)")
        return
    ok = True
    for f in sorted(list((ROOT / "harness").rglob("*.sh"))
                    + list((ROOT / "tools").rglob("*.sh"))):
        result = subprocess.run(["shellcheck", "-S", "warning", str(f)],
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(result.stdout, end="")
            b.fail(f"shellcheck flagged {rel(f)}")
            ok = False
    if ok:
        print("  clean")


def check_bandit(b):
    """1b. Python security lint (medium+ severity), same contract as
    shellcheck: run when installed, loud SKIP when not. Gates the mechanical
    findings; trust-boundary judgment belongs to audit-harness Layer 3.
    --ignore-nosec so an in-tree `# nosec` comment cannot silently disarm a
    finding — suppression is a review decision, not a source-file one."""
    b.note("bandit (python security, harness/ + tools/)")
    if shutil.which("bandit") is None:
        print("  SKIP: bandit not installed (pip install bandit)")
        return
    result = subprocess.run(
        ["bandit", "-q", "-r", "-ll", "--ignore-nosec",
         str(ROOT / "harness"), str(ROOT / "tools")],
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        b.fail("bandit flagged python security findings (medium+ severity)")
    else:
        print("  clean")


def check_python_syntax(b):
    """2. Python syntax (compile in memory — no __pycache__ left behind)."""
    b.note("python syntax")
    ok = True
    for f in sorted((ROOT / "harness").rglob("*.py")):
        if "__pycache__" in f.parts:
            continue
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            # ValueError: NUL byte in source; UnicodeDecodeError: not UTF-8.
            # Both aggregate as FAILs — a traceback would abort the battery.
            b.fail(f"python syntax error in {rel(f)}: {exc}")
            ok = False
    if ok:
        print("  ok")


def check_agent_body_parity(b):
    """2b. Agent body parity — every agent's four per-tool source copies must
    carry byte-identical bodies; only the frontmatter differs. One documented
    exception is normalized away: skill links are location-correct per
    directory (../skills/ from .claude/agents/, ../../.claude/skills/ from the
    other three). The mirror bodies are rendered from the .claude base by
    refresh-agent-bodies.py (via release-prep); this step gates a forgotten
    render or a hand-edited mirror. Faithfulness (step 3) cannot see either: a
    drifted mirror sits identically in source and sample. A drifted copy ships
    a weaker agent to that tool's users."""
    b.note("agent body parity (per-tool copies)")
    ok = True

    def fail(msg):
        nonlocal ok
        b.fail(msg)
        ok = False

    layers = [HERE / "core"] + [HERE / "stacks" / s for s in STACKS]
    for layer in layers:
        bases = 0
        for base in sorted((layer / ".claude/agents").glob("*.md")):
            name = base.stem
            if name == "README":
                continue
            bases += 1
            base_body = strip_frontmatter(read_text(base))
            if not any(l.strip() for l in base_body):
                fail(f"empty body (or missing frontmatter fence) in {rel(base)}")
            # Each link form is asserted, not just normalized: the claude copy
            # uses the local form, siblings the rewritten one. Without this, a
            # sibling whose link was never rewritten is byte-equal to the base
            # and would pass while shipping a link broken from its directory.
            if any("../../.claude/skills/" in l for l in base_body):
                fail(f"sibling link form (../../.claude/skills/) in {rel(base)} "
                     "— the claude copy uses ../skills/")
            for mirror_dir, suffix in MIRROR_SURFACES:
                mirror = layer / mirror_dir / f"{name}{suffix}"
                if not mirror.is_file():
                    fail(f"missing per-tool agent copy {rel(mirror)}")
                    continue
                mirror_body = strip_frontmatter(read_text(mirror))
                if any("../skills/" in l.replace("../../.claude/skills/", "")
                       for l in mirror_body):
                    fail(f"un-rewritten skill link (../skills/) in {rel(mirror)} "
                         "— broken from this directory")
                if norm_links(mirror_body) != base_body:
                    fail(f"agent body drift (frontmatter aside): {rel(mirror)} != {rel(base)}")
        if bases == 0:
            fail(f"no agent bases under {rel(layer)}/.claude/agents/ "
                 "— roster empty or path renamed")
        # Reverse sweep: an agent file present only in a sibling dir has no
        # base above and would otherwise never be compared — it would ship to
        # that tool unchecked. It also enforces each tool's file suffix.
        for mirror_dir, suffix in MIRROR_SURFACES:
            d = layer / mirror_dir
            if not d.is_dir():
                continue
            for f in sorted(p for p in d.iterdir() if p.is_file()):
                if f.name == "README.md":
                    continue
                if not f.name.endswith(suffix) or f.name == suffix:
                    kind = ("copilot agents must be <name>.agent.md"
                            if mirror_dir == ".github/agents"
                            else "unexpected non-.md file in a tool agents dir")
                    fail(f"{rel(f)} — {kind}")
                    continue
                name = f.name[: -len(suffix)]
                if not (layer / ".claude/agents" / f"{name}.md").is_file():
                    fail(f"{rel(f)} has no .claude/agents/{name}.md base "
                         "— sibling-only agent, never parity-checked")
    if ok:
        print("  all per-tool bodies identical")


def check_faithfulness(b):
    """3. Materialization faithfulness — dirty-tree-safe. Snapshot the working
    tree, re-materialize, and flag only what the re-materialize *changes*
    (forgotten materialize or a drifted hand-edit), plus any orphan extra."""
    b.note("materialization faithfulness")
    if b.quick:
        b.skip("--quick: harness/ and samples/ proven untouched by the guard")
        return
    before = git_status("samples/")
    result = subprocess.run(["bash", str(HERE / "bootstrap.sh")],
                            capture_output=True, text=True, cwd=ROOT, check=False)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        # The header-documented abort exception: the sample checks that follow
        # read the tree this bootstrap produces.
        print("FAIL: harness/bootstrap.sh failed:", file=sys.stderr)
        print(output, file=sys.stderr)
        raise SystemExit(1)
    extras = re.findall(r"extras: (\d+) file", output)
    for n in extras:
        if n != "0":
            b.fail(f"materialize reported {n} orphan extra(s) — a committed "
                   "file /harness no longer produces. git rm it.")
    # Committed orphans are invisible to the porcelain diff (bootstrap never
    # deletes them) — the extras count is their only guard. No extras line
    # parsed means the output format changed; fail loud rather than pass an
    # unchecked tree.
    if not extras:
        b.fail("no 'extras:' line parsed from bootstrap output — output format "
               "changed; orphan detection is not running.")
        print(output, file=sys.stderr)
    after = git_status("samples/")
    if before != after:
        b.fail("re-materialize changed the samples — a /harness edit was not "
               "materialized, or a sample was hand-edited:")
        before_set, after_set = set(before.splitlines()), set(after.splitlines())
        for line in sorted(before_set - after_set):
            print(f"  < {line}", file=sys.stderr)
        for line in sorted(after_set - before_set):
            print(f"  > {line}", file=sys.stderr)
        print("Fix: review the change, then commit the re-materialized samples "
              "with the /harness edit.", file=sys.stderr)
    else:
        print("  samples == materialize(/harness)")


def check_layout_invariants(b):
    """3b. Sample layout invariants — the cross-tool compatibility rules from
    docs/cross-tool-strategy.md as a gate: CLAUDE.md is the single rules file,
    skills live in .claude/skills/ only, every tool surface is present."""
    b.note("sample layout invariants (cross-tool rules, copy channel)")
    ok = True

    def fail(msg):
        nonlocal ok
        b.fail(msg)
        ok = False

    # Derived from the helpers.TOOLS registry: skills may exist only under
    # .claude/skills/ (no per-tool sibling), and every tool's agents dir must
    # be present in a sample.
    mirror_skill_dirs = tuple(
        row["agents_dir"].rsplit("/", 1)[0] + "/skills"
        for tool, row in TOOLS.items() if tool != "claude")
    agent_dirs = tuple(row["agents_dir"] for row in TOOLS.values())
    for s in STACKS:
        sample = ROOT / "samples" / s
        for p in ("AGENTS.md", ".github/copilot-instructions.md",
                  *mirror_skill_dirs):
            if (sample / p).exists():
                fail(f"samples/{s}/{p} exists — CLAUDE.md is the single rules "
                     "file and skills live in .claude/skills/ only")
        for p in ("CLAUDE.md", ".junie/config.json", *agent_dirs,
                  ".claude/skills"):
            if not (sample / p).exists():
                fail(f"samples/{s}/{p} missing — required by the cross-tool "
                     "compatibility rules")
        # Copy-channel rule: declared in layout.toml, no silent extension
        # creep, the runtime git-tracked, the ledger ignored but never the
        # runtime.
        lt = sample / "scripts/layout.toml"
        lt_text = read_text(lt) if lt.is_file() else ""
        if not re.search(r'channel *= *"copy"', lt_text):
            fail(f'samples/{s}/scripts/layout.toml does not declare channel = "copy"')
        if not re.search(r"extensions *= *\[\]", lt_text):
            fail(f"samples/{s}/scripts/layout.toml extensions is not [] — the "
                 "samples declare none; a non-empty list weakens orphan detection")
        tracked = subprocess.run(
            ["git", "ls-files", f"samples/{s}/.claude/skills"],
            capture_output=True, text=True, cwd=ROOT, check=False).stdout
        if not tracked.strip():
            fail(f"samples/{s} runtime is untracked — the copy channel commits it")
        gitignore = sample / ".gitignore"
        gi_text = read_text(gitignore) if gitignore.is_file() else ""
        if not re.search(r"^\.scratch/", gi_text, re.M):
            fail(f"samples/{s}/.gitignore does not ignore .scratch/")
        if ".claude/skills" in gi_text:
            fail(f"samples/{s}/.gitignore ignores the runtime — the copy "
                 "channel commits it")
    if ok:
        print("  cross-tool rules and channel invariants hold")


def check_roster_sync(b):
    """3c. Project-owned roster sync. Faithfulness (step 3) covers only the
    runtime; the project-owned committed files drift silently when the shipped
    roster changes. Gates: skills table both directions (scoped to its two
    chapters), agents README roster, init skeleton coverage, brief roster, ADR
    placement, and the ROOT skill table (CLAUDE.md "Root-Level Skills") plus
    the adoption trio's mentions in docs/adoption-guide.md. Row *descriptions*
    stay judgment (/audit-harness Layer 2 check 5)."""
    b.note("project-owned roster sync (skills tables incl. root, agents README, init coverage)")
    ok = True

    def fail(msg):
        nonlocal ok
        b.fail(msg)
        ok = False

    for s in STACKS:
        claude_md = read_text(ROOT / "samples" / s / "CLAUDE.md")
        shipped = set()
        for skills_root in (HERE / "core/.claude/skills",
                            HERE / "stacks" / s / ".claude/skills"):
            if not skills_root.is_dir():
                continue
            for d in sorted(p for p in skills_root.iterdir() if p.is_dir()):
                shipped.add(d.name)
                if f"| `{d.name}`" not in claude_md:
                    fail(f"samples/{s}/CLAUDE.md skills table has no row for "
                         f"shipped skill '{d.name}'")
        # Vacuous-pass backstop, same reason as step 2b's bases counter: a
        # renamed skills root would otherwise let this loop check nothing.
        if not shipped:
            fail(f"no shipped skills found for stack {s} — roster empty or path renamed")
        for row in section_rows(claude_md, r"^## (Agent Usage|Stack-specific skills)"):
            if row not in shipped:
                fail(f"samples/{s}/CLAUDE.md skills table row '{row}' names no "
                     "shipped skill — ghost row")
        agents_readme = read_text(ROOT / "samples" / s / ".claude/agents/README.md")
        for agents_root in (HERE / "core/.claude/agents",
                            HERE / "stacks" / s / ".claude/agents"):
            if not agents_root.is_dir():
                continue
            for f in sorted(agents_root.glob("*.md")):
                if f.stem == "README":
                    continue
                if f"**{f.stem}**" not in agents_readme:
                    fail(f"samples/{s}/.claude/agents/README.md has no roster "
                         f"row for shipped agent '{f.stem}'")
        for target, source in (
            ("CLAUDE.md", HERE / "init/stacks" / s / "CLAUDE.md"),
            (".claude/settings.json", HERE / "init/core/.claude/settings.json"),
            ("scripts/layout.toml", HERE / "init/stacks" / s / "scripts/layout.toml"),
            (".gitignore", HERE / "init/core/gitignore-runtime.txt"),
        ):
            if not (ROOT / "samples" / s / target).is_file():
                fail(f"samples/{s}/{target} missing (project-owned committed file)")
            if not source.is_file():
                fail(f"{rel(source)} missing — no init skeleton source for {target}")
        for t in sorted((HERE / "core/.claude/skills/doctor/templates").glob("*.md")):
            brief = "docs/adr/README.md" if t.name == "adr-README.md" else f"docs/{t.name}"
            if not (ROOT / "samples" / s / brief).is_file():
                fail(f"samples/{s}/{brief} missing — the doctor template "
                     f"{t.name} has no sample brief")
        # ADR placement: a sample's decision log starts empty — README.md only.
        adr_dir = ROOT / "samples" / s / "docs/adr"
        entries = sorted(p.name for p in adr_dir.iterdir()) if adr_dir.is_dir() else []
        if entries != ["README.md"]:
            fail(f"samples/{s}/docs/adr must contain only README.md — no "
                 "harness ADR is materialized")

    # Root skill table. Same drift mode as the samples' tables: a skill added
    # or retired at the root must reach the root CLAUDE.md table the same
    # session; the CLAUDE.md table is the single gated home (the README carries
    # no table by design — it links out instead, unenforced). The adoption trio
    # (init, materialize, harvest) is additionally mention-guarded in the
    # adoption guide's "Adopt in Your Own Project" chapter.
    root_claude = read_text(ROOT / "CLAUDE.md")
    root_rows = section_rows(root_claude, r"^## Root-Level Skills$")
    adoption = read_text(ROOT / "docs/adoption-guide.md")
    adopt_section = []
    in_section = False
    for line in adoption.splitlines():
        if line.startswith("## "):
            in_section = line == "## Adopt in Your Own Project"
        if in_section:
            adopt_section.append(line)
    adopt_text = "\n".join(adopt_section)

    root_shipped = set()
    for d in sorted(p for p in (ROOT / ".claude/skills").iterdir() if p.is_dir()):
        root_shipped.add(d.name)
        if d.name not in root_rows:
            fail(f"root CLAUDE.md Root-Level Skills table has no row for skill '{d.name}'")
        if d.name in ("init", "materialize", "harvest"):
            # The trio's documented home; the chapter names them as user-typed
            # commands (`/init`) or bare (`init`) — accept both.
            if f"`{d.name}`" not in adopt_text and f"`/{d.name}`" not in adopt_text:
                fail("docs/adoption-guide.md Adopt in Your Own Project chapter "
                     f"never mentions '{d.name}'")
    if not root_shipped:
        fail("no root skills found under .claude/skills/ — roster empty or path renamed")
    for row in root_rows:
        if row not in root_shipped:
            fail(f"CLAUDE.md table row '{row}' names no root skill — ghost row")
    if ok:
        print("  tables and skeleton coverage in sync")


def check_placeholder_gate(b):
    """3d. Placeholder gate — the PROJECT_NAME / PROJECT_DESCRIPTION template
    tokens may appear only in the documented template locations. The go and
    java samples stay deliberately in template state (they double as readable
    demos); the generic sample ships init-filled — the allowlist permits both.
    The allowlist is per-file; token *placement* inside an allowed brief stays
    judgment. A hit anywhere else is a leak into runtime content."""
    b.note("placeholder gate (template tokens outside documented locations)")
    ok = True
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relpath = path.relative_to(ROOT).as_posix()
        if relpath.startswith(".git/") or "__pycache__" in path.parts:
            continue
        if is_binary(path):
            continue
        text = read_text(path)
        if any(tok in text for tok in PH_TOKENS) and not PH_ALLOW.match(relpath):
            b.fail(f"template placeholder leaked into {relpath} — outside the "
                   "documented template locations")
            ok = False
    # Canary against a vacuous pass: the init skeletons must carry the token —
    # if the token format ever changes, this fails instead of the gate
    # scanning for a string nothing contains.
    for s in STACKS:
        skeleton = HERE / "init/stacks" / s / "CLAUDE.md"
        if not skeleton.is_file() or PH_TOKENS[0] not in read_text(skeleton):
            b.fail(f"{PH_TOKENS[0]} not found in harness/init/stacks/{s}/CLAUDE.md "
                   "— token format changed; the placeholder gate is scanning for nothing")
            ok = False
    if ok:
        print("  placeholders only in documented template locations")


def check_handbook_delta(b):
    """3e. Handbook delta + sample self-containment. The root handbook and its
    installed core copy differ only by the pinned delta (links + doc-form
    pointers) recorded in harness/handbook-delta.expected — any other
    divergence is content drift. Sample docs must stand alone: no reference to
    another sample or to the monorepo samples/ tree."""
    b.note("handbook delta (root vs core copy) + sample self-containment")
    ok = True
    core_hb = HERE / "core/.claude/skills/handoff-routing/agentic-harness.md"
    # diff -U0, not difflib: the pinned expected file was generated by diff,
    # and difflib may group hunks differently for the same logical delta.
    result = subprocess.run(
        ["diff", "-U0", "docs/agentic-harness.md", str(core_hb)],
        capture_output=True, text=True, cwd=ROOT, check=False)
    actual = "\n".join(
        l for l in result.stdout.splitlines()
        if l.startswith(("-", "+")) and not l.startswith(("---", "+++")))
    expected_file = HERE / "handbook-delta.expected"
    if not expected_file.is_file():
        b.fail("harness/handbook-delta.expected missing — the pinned handbook "
               "delta has no reference")
        ok = False
    else:
        expected = "\n".join(l for l in read_text(expected_file).splitlines()
                             if not l.startswith("#"))
        if actual != expected:
            b.fail("docs/agentic-harness.md vs its core copy diverged beyond "
                   "harness/handbook-delta.expected:")
            expected_set = set(expected.splitlines())
            actual_set = set(actual.splitlines())
            for line in sorted(expected_set - actual_set):
                print(f"    - {line}", file=sys.stderr)
            for line in sorted(actual_set - expected_set):
                print(f"    + {line}", file=sys.stderr)
            print("Fix: reconcile the two copies (owner: docs/agentic-harness.md). "
                  "Regenerating the\nexpected delta is an explicit decision — a diff "
                  "touching it needs the same review as content drift.", file=sys.stderr)
            ok = False

    # Self-containment: each pattern scans the docs of the samples that must
    # not mention it.
    hits = set()
    sweeps = (
        (re.compile(r"java-spring-boot"), ("go", "generic")),
        (re.compile(r"\bgo/"), ("java-spring-boot", "generic")),
        (re.compile(r"\bgeneric/"), ("go", "java-spring-boot")),
        (re.compile(r"samples/"), ("go", "java-spring-boot", "generic")),
    )
    for pattern, samples in sweeps:
        for s in samples:
            docs = ROOT / "samples" / s / "docs"
            if not docs.is_dir():
                continue
            for f in sorted(p for p in docs.rglob("*") if p.is_file()):
                if pattern.search(read_text(f)):
                    hits.add(f.relative_to(ROOT).as_posix())
    for h in sorted(hits):
        b.fail(f"{h} references another sample or the samples/ tree — sample "
               "docs must be self-contained")
        ok = False
    if ok:
        print("  delta pinned, samples self-contained")


def check_verdict_enums(b):
    """3f. Verdict-enum sync — the schema enums the routing contract depends
    on. This pins the schemas to a literal copy of the canonical names, so a
    schema edit cannot silently widen or narrow a verdict space. Prose drift in
    the skills that document the sets stays judgment (/audit-harness Layer 2)."""
    b.note("verdict-enum sync (design-block, review-feedback)")

    def verdicts(name):
        schema = json.loads(read_text(HERE / "core/schemas/scratch" / name))
        return set(schema["properties"]["verdict"]["enum"])

    problems = []
    try:
        db = verdicts("design-block.schema.json")
        rf = verdicts("review-feedback.schema.json")
        if db != DESIGN_BLOCK_VERDICTS:
            problems.append(f"design-block verdict enum is {sorted(db)}")
        if rf != REVIEW_FEEDBACK_VERDICTS:
            problems.append(f"review-feedback verdict enum is {sorted(rf)}")
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        problems.append(f"could not read verdict enums: {exc}")
    if problems:
        b.fail(f"verdict-enum sync: {'; '.join(problems)}")
    else:
        print("  enums match the documented verdict sets")


def check_stack_agnostic_core(b):
    """3g. Stack-agnostic core — no stack-specific fact in harness/core/ (the
    invariant from harness/README.md). The token list is the canonical set of
    stack facts; a hit means the fact belongs in stacks/<stack>/, a brief, or
    scripts/layout.toml."""
    b.note("stack-agnostic core (no stack token in harness/core)")
    core = HERE / "core"
    if not core.is_dir():
        b.fail(f"{core} missing — cannot scan for stack tokens")
        return
    hits = []
    try:
        for f in sorted(p for p in core.rglob("*") if p.is_file()):
            if "__pycache__" in f.parts:
                continue
            for i, line in enumerate(read_text(f).splitlines(), 1):
                if CORE_STACK_TOKENS.search(line):
                    hits.append(f"{rel(f)}:{i}:{line}")
    except OSError as exc:
        # A broken scan is a FAIL, not a pass — an unreadable directory must
        # not report "no stack token" without having looked.
        b.fail(f"could not scan harness/core/ for stack tokens: {exc}")
        return
    if hits:
        b.fail("stack-specific tokens in harness/core/ — move to stacks/<stack>/:")
        for h in hits[:10]:
            print(f"    {h}", file=sys.stderr)
    else:
        print("  core carries no stack token")


def check_root_links(b):
    """3h. Root link integrity — every markdown link target in the root-level
    files (README, CLAUDE.md, docs/, root skills, tools/, harness/README.md)
    must resolve. Fenced code blocks are skipped (they carry illustrative
    paths); anchors are not checked (judgment work, /audit-harness Layer 2)."""
    b.note("root link integrity (markdown links resolve)")
    files = [ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "harness/README.md"]
    for pattern in ("docs/**/*.md", ".claude/skills/**/*.md", "tools/**/*.md"):
        files.extend(ROOT.glob(pattern))
    link = re.compile(r"\]\(([^)\s]+)\)")
    bad = []
    for f in sorted(set(files)):
        if not f.is_file():
            continue
        fence = False
        for i, line in enumerate(read_text(f).splitlines(), 1):
            if line.lstrip().startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            for target in link.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if "{{" in target or "<" in target:
                    continue
                path = target.split("#")[0]
                if path and not (f.parent / path).exists():
                    bad.append(f"{rel(f)}:{i} -> {target}")
    if bad:
        b.fail("broken markdown links in root-level files:")
        for line in bad:
            print(f"    {line}", file=sys.stderr)
    else:
        print("  links resolve")


def check_sample_suites(b):
    """4. Sample test suites (run from each sample, where layout.toml + schemas
    colocate). Every sample ships every suite — a missing file is a FAIL, not
    a skip."""
    b.note("sample test suites")
    if b.quick:
        b.skip("--quick: samples/ proven untouched by the guard")
        return
    ok = True
    for s in STACKS:
        sample = ROOT / "samples" / s
        for t in SAMPLE_SUITES:
            if not (sample / t).is_file():
                b.fail(f"samples/{s}/{t} missing — every sample ships all "
                       f"{len(SAMPLE_SUITES)} suites")
                ok = False
                continue
            result = subprocess.run([sys.executable, t], capture_output=True,
                                    text=True, cwd=sample, check=False)
            if result.returncode != 0:
                b.fail(f"samples/{s}/{t}")
                b.show_fail(result.stdout + result.stderr)
                ok = False
    if ok:
        print("  all suites pass")


def check_build_file_refs(b):
    """4b. Sample build files reference live scripts. The battery runs the
    script tests directly (step 4), not through each sample's own make/gradle
    gate, so a script that moves can leave a sample's build target dangling
    while this stays green. Each stack declares its build-binding file and its
    expected minimum .py-ref count, so the check cannot go vacuous."""
    b.note("sample build-file script refs")
    ok = True
    for s in STACKS:
        if s not in BUILD_BINDINGS:
            b.fail(f"stack '{s}' has no build-binding file declared — extend "
                   "BUILD_BINDINGS in step 4b")
            ok = False
            continue
        binding, min_refs = BUILD_BINDINGS[s]
        bf = ROOT / "samples" / s / binding
        if not bf.is_file():
            b.fail(f"samples/{s}/{binding} missing — the stack's declared "
                   "build-binding file")
            ok = False
            continue
        refs = sorted(set(re.findall(r"[A-Za-z0-9_./-]+\.py", read_text(bf))))
        for p in refs:
            if not (ROOT / "samples" / s / p).is_file():
                b.fail(f"samples/{s}/{binding} references missing script '{p}'")
                ok = False
        if len(refs) < min_refs:
            b.fail(f"samples/{s}/{binding} references {len(refs)} .py scripts "
                   f"(expected >= {min_refs}) — step 4b went vacuous for '{s}'")
            ok = False
        elif not refs:
            print(f"  {s}: 0 .py refs in {binding} — consumer-bound stack, "
                  "vacuous by design")
    if ok:
        print("  build-file script paths resolve")


def check_sample_doctors(b):
    """5. Sample doctors (the live docs contract)."""
    b.note("sample doctors")
    if b.quick:
        b.skip("--quick: samples/ proven untouched by the guard")
        return
    ok = True
    for s in STACKS:
        result = subprocess.run(
            [sys.executable, "scripts/brief_doctor.py", "check"],
            capture_output=True, text=True, cwd=ROOT / "samples" / s, check=False)
        if result.returncode != 0:
            b.fail(f"doctor failed in samples/{s}:")
            b.show_fail(result.stdout + result.stderr)
            ok = False
    if ok:
        print("  green")


def check_unit_suites(b):
    """6. Harness unit suites — every maintainer-side test_*.py outside the
    shipped runtime layers (core/, stacks/, and init/ ship their suites into
    consumers; those run inside each sample in step 4).
    test_refresh_agent_bodies.py is excluded here only because it already ran
    as step 2c. Zero suites found is a FAIL, not an empty loop."""
    b.note("harness unit suites")
    if b.quick:
        b.skip("--quick: harness/ proven untouched by the guard")
        return
    suites = [
        f for f in sorted(HERE.glob("test_*.py")) + sorted(HERE.glob("*/test_*.py"))
        if not any(part in ("core", "stacks", "init", "__pycache__") for part in
                   f.relative_to(HERE).parts)
        and f.name != "test_refresh_agent_bodies.py"
    ]
    if not suites:
        b.fail("no harness unit suites found — the step went vacuous")
        return
    ok = True
    for t in suites:
        result = subprocess.run([sys.executable, str(t)], capture_output=True,
                                text=True, cwd=ROOT, check=False)
        if result.returncode != 0:
            b.fail(f"{rel(t)} did not pass:")
            b.show_fail(result.stdout + result.stderr)
            ok = False
    if ok:
        print(f"  {len(suites)} suites pass")


def check_marketplace_faithfulness(b):
    """7. Marketplace faithfulness — dirty-tree-safe. Re-render the plugin
    marketplace in place and flag only what the re-render *changes* (a /harness
    edit that was not repackaged). The render is deterministic, so an in-sync
    tree is unchanged."""
    b.note("marketplace faithfulness")
    if b.quick:
        b.skip("--quick: harness/ and plugins/ proven untouched by the guard")
        return
    before = git_status("plugins/", ".claude-plugin/marketplace.json")
    result = subprocess.run(
        [sys.executable, str(HERE / "package-marketplace.py")],
        capture_output=True, text=True, cwd=ROOT, check=False)
    if result.returncode != 0:
        b.fail("harness/package-marketplace.py failed:")
        print(result.stdout + result.stderr, file=sys.stderr)
    after = git_status("plugins/", ".claude-plugin/marketplace.json")
    if before != after:
        b.fail("re-render changed the marketplace — a /harness edit was not repackaged:")
        before_set, after_set = set(before.splitlines()), set(after.splitlines())
        for line in sorted(before_set - after_set):
            print(f"  < {line}", file=sys.stderr)
        for line in sorted(after_set - before_set):
            print(f"  > {line}", file=sys.stderr)
        print("Fix: run harness/package-marketplace.py and commit the result "
              "with the /harness edit.", file=sys.stderr)
    else:
        print("  marketplace == package-marketplace(/harness)")


def main(argv):
    # Line-buffer both streams so step headers (stdout) and FAIL details
    # (stderr) interleave in true order when the battery is redirected to a
    # file or a pipe — block-buffered stdout would otherwise reorder them.
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    quick = False
    if len(argv) == 2 and argv[1] == "--quick":
        quick = True
    elif len(argv) != 1:
        print("usage: harness/check-sync.py [--quick]", file=sys.stderr)
        return 2

    # The --quick guard. Quick mode is sound only while the derived-surface
    # inputs are untouched: any pending change under them — staged, unstaged,
    # or untracked — means a skipped step could be the one that catches it.
    # Refuse rather than weaken the gate.
    if quick:
        dirty = git_status("harness/", "samples/", "plugins/", ".claude-plugin/")
        if dirty:
            print("FAIL: --quick refused — pending changes touch the derived "
                  "surfaces it would skip:", file=sys.stderr)
            for line in dirty.splitlines()[:10]:
                print(f"    {line}", file=sys.stderr)
            print("Run the full battery: harness/check-sync.py (or "
                  "harness/release-prep.sh after a /harness edit).", file=sys.stderr)
            return 1

    b = Battery(quick)
    check_shellcheck(b)
    check_bandit(b)
    check_python_syntax(b)
    check_agent_body_parity(b)
    b.run_suite("agent-body renderer self-test", "harness/test_refresh_agent_bodies.py")
    check_faithfulness(b)
    check_layout_invariants(b)
    check_roster_sync(b)
    check_placeholder_gate(b)
    check_handbook_delta(b)
    check_verdict_enums(b)
    check_stack_agnostic_core(b)
    check_root_links(b)
    check_sample_suites(b)
    check_build_file_refs(b)
    check_sample_doctors(b)
    check_unit_suites(b)
    b.run_suite("generic-stack self-test", "harness/test-generic-stack.sh")
    check_marketplace_faithfulness(b)
    b.run_suite("marketplace acceptance", "harness/test-marketplace.sh")
    b.run_suite("real plugin install (claude CLI)", "harness/test-plugin-install.sh",
                skip_re=r"^SKIP", skip_label="skip (no claude CLI)")

    print()
    if b.failed:
        print("FAIL check-sync: see failures above", file=sys.stderr)
        return 1
    if quick:
        print("PASS check-sync --quick: static checks green (re-render and "
              "sub-suite steps skipped — guard proved their inputs untouched)")
    else:
        print("PASS check-sync: lint, syntax, parity, faithfulness, invariants, "
              "tests, doctors, marketplace all green")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
