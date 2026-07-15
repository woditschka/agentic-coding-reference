#!/usr/bin/env python3
"""Local deterministic gate for the harness + samples: the mechanical,
no-judgment half of an audit-harness review. This header is the authoritative
step list — docs reference it rather than re-enumerating:
  1  shellcheck (harness/ + tools/)      3g  stack-agnostic core
  1b bandit (python security lint)       3h  root link integrity
  1c stdlib-only shipped runtime         3i  parity gates (stacks)
  2  python syntax                       3j  shared test-suite pins (stacks)
  2b agent body parity (per-tool copies) 4   sample test suites
  2c agent-body renderer self-test       4b  sample build-file script refs
  2d cc_accounting vendored-copy sync    5   sample doctors
  3  materialization faithfulness        6   harness unit suites
  3b sample layout invariants            6b  generic-stack self-test
  3c project-owned roster sync           7   marketplace faithfulness
  3d placeholder gate                    8   marketplace acceptance
  3e handbook delta + self-containment   9   real plugin install (claude CLI)
  3f verdict-enum sync (schemas)
Aggregates failures (does not stop at the first) and exits non-zero if any
check fails. Sole exception: a bootstrap crash in step 3 aborts the run —
the sample checks that follow read the tree it produces.
Tier 0 of the maintainer loop (root CLAUDE.md): run it after
every edit — via release-prep.sh after a /harness edit. Two push-time gates
mirror it: the .githooks/pre-push hook blocks an unscanned local push, and the
.github/workflows/battery.yml GitHub Actions workflow attests every push and
pull request. Both invoke --strict. See
docs/adr/2026-07-13-server-side-battery-enforcement.md.

    harness/check-sync.py [--quick] [--strict]

--quick is tier 0 for an edit that touches none of harness/, samples/,
plugins/, .claude-plugin/ (i.e. docs, root skills, tools/). It REFUSES to
run while any of those trees is dirty vs HEAD; only then does it skip — with
a loud SKIP line each — the steps that re-render or execute those trees
(2c, 3, 4, 5, 6, 6b, 7, 8, 9). Every static check still runs, so --quick can
never skip a check the pending edit could affect. A /harness edit takes the
full battery via release-prep.sh, unchanged; an /audit-harness run always
uses the full battery.

--strict makes a missing shellcheck or bandit a FAIL, not a SKIP; the two
push-time gates set it so the SAST steps cannot silently no-op. Without it an
absent linter skips with a note — the dev-machine default.

Needs git and python3; bash for the shell sub-suites; shellcheck and bandit
if present (each skipped with a note if not, or failed under --strict). No
Go/Java toolchain required.
The faithfulness
step re-materializes the samples in place: it is dirty-tree-safe — it flags
only changes the re-materialize *introduces* (a /harness edit you forgot to
materialize, or a hand-edited sample), never your already-pending work.

Pure helpers are unit-tested by test_check_sync.py (battery step 6).
"""

import ast
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
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

# Per-stack build-binding file. A stack absent from this table fails step 4b
# loudly. Project builds carry no harness suite wiring (ADR 2026-07-13:
# runtime verification happens at materialize time), so zero .py refs is the
# norm; the check exists to fail any dangling reference a build file carries.
BUILD_BINDINGS = {
    "go": "Makefile",
    "java-spring-boot": "build.gradle",
    "generic": "scripts/stack.sh",
}

# Sample suites shipped by every stack (step 4). A missing file is a FAIL,
# not a skip — a silent [ -f ] guard once let the generic stack run without
# test_score_change.py while the battery stayed green.
SAMPLE_SUITES = (
    "scripts/test_brief_doctor.py",
    "scripts/test_handoff.py",
    "scripts/test_cc_accounting.py",
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


FENCE_MARKS = ("```", "~~~")


def _fence_state(line, fence):
    """Track fenced-code state across lines: `fence` is the open marker (None
    = outside). Fences may be indented and use ``` or ~~~; a block closes
    only on its own opening marker, so a ~~~ line inside a ``` block stays
    literal content."""
    s = line.lstrip()
    if fence is None:
        return s[:3] if s.startswith(FENCE_MARKS) else None
    return None if s.startswith(fence) else fence


def h2_headings(body_lines):
    """H2 headings in order, fenced code excluded (indented and ~~~ fences
    included in the exclusion)."""
    out, fence = [], None
    for line in body_lines:
        fence = _fence_state(line, fence)
        if fence is None and line.startswith("## "):
            out.append(line[3:].strip())
    return out


def severity_headings(body_lines):
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
    def __init__(self, quick, strict=False):
        self.quick = quick
        self.strict = strict
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
        if b.strict:
            b.fail("shellcheck required under --strict but not installed "
                   "(the push-time gates run --strict; brew install shellcheck)")
        else:
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
        if b.strict:
            b.fail("bandit required under --strict but not installed "
                   "(the push-time gates run --strict; pipx install bandit)")
        else:
            print("  SKIP: bandit not installed (pipx install bandit)")
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


def check_stdlib_only(b):
    """1c. The shipped runtime is stdlib-only — the contract recorded by
    [logic-in-python] ("Stdlib only, Python 3.11+ for everything") and restated
    by [single-pricing-source]. Enforcement, not a new rule: a third-party
    import would add a dependency the consumer never chose to code that runs on
    their machine. Scope is every tree that reaches a consumer on any channel —
    core/ + stacks/ (copy) plus the two scripts package-marketplace.py copies
    into each plugin and setup.sh executes. Imports resolve against the
    standard library or a module in the importing file's own directory; a
    cross-directory sibling fails here because it also fails at runtime, where
    only that directory is on sys.path. Manifests are the claim's other half:
    a dependency file is a third-party dependency even with no import yet."""
    b.note("stdlib-only shipped runtime (no third-party imports)")
    roots = [HERE / "core", HERE / "stacks", HERE / "claude-md"]
    loose = [HERE / "refresh-gitignore.py"]
    missing = [p for p in roots + loose if not p.exists()]
    if missing:
        # A broken scan is a FAIL, not a pass — an absent tree must not report
        # "no third-party import" without having looked.
        b.fail(f"{', '.join(rel(m) for m in missing)} missing — cannot scan imports")
        return
    try:
        by_root = {r: sorted(f for f in r.rglob("*.py")
                             if "__pycache__" not in f.parts) for r in roots}
        empty = [r for r, fs in by_root.items() if not fs]
        if empty:
            # Roots exist but hold no .py: the scan would look at nothing and
            # report clean. A silent [ -f ] guard once let the generic stack
            # run without test_score_change.py while the battery stayed green.
            b.fail(f"{', '.join(rel(r) for r in empty)} holds no .py — "
                   "refusing to report 'stdlib only' having scanned nothing")
            return
        files = [f for fs in by_root.values() for f in fs] + loose
        manifests = sorted(m for r in roots
                           for pat in ("requirements*.txt", "pyproject.toml",
                                       "Pipfile", "setup.py", "setup.cfg")
                           for m in r.rglob(pat))
        hits = [f"{rel(m)}: dependency manifest" for m in manifests]
        for f in files:
            try:
                tree = ast.parse(read_text(f), str(f))
            except (SyntaxError, ValueError):
                # step 2 owns syntax (it rglobs all of harness/, a superset)
                # and aggregates these as FAILs; a raise here would abort the
                # battery before the steps below ever run.
                continue
            siblings = {p.stem for p in f.parent.glob("*.py")}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [(a.name.split(".")[0], node.lineno) for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level or not node.module:
                        continue  # relative import — local by construction
                    names = [(node.module.split(".")[0], node.lineno)]
                else:
                    continue
                for name, line in names:
                    if name in sys.stdlib_module_names or name in siblings:
                        continue
                    hits.append(f"{rel(f)}:{line}: imports '{name}'")
    except OSError as exc:
        b.fail(f"could not scan the shipped runtime for imports: {exc}")
        return
    if hits:
        b.fail("the shipped runtime is stdlib-only by contract (stdlib or a "
               "module in the same directory; no dependency manifest):")
        for h in hits[:10]:
            print(f"    {h}", file=sys.stderr)
    else:
        print("  shipped runtime imports stdlib only")


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


def check_cc_accounting_sync(b):
    """2d. cc_accounting vendored-copy sync. The module is authored once and
    copied to the other location; the two must stay byte-identical so the
    statusline and the handoff board price from the same code. Canonical home:
    tools/harness-stats/cc_accounting.py (install.sh puts it beside the
    statusline). Vendored copy: harness/core/scripts/cc_accounting.py, which the
    board imports and which materializes into every sample (step 3 covers the
    sample copies; only this canonical↔vendored pair is unguarded otherwise).
    There is no build step — the copy is manual, this gate is automatic."""
    b.note("cc_accounting vendored-copy sync")
    canon = ROOT / "tools/harness-stats/cc_accounting.py"
    vendored = HERE / "core/scripts/cc_accounting.py"
    try:
        if canon.read_bytes() == vendored.read_bytes():
            print("  canonical == vendored")
        else:
            b.fail(f"{rel(canon)} != {rel(vendored)} — decide which copy "
                   f"holds the intended edit (canonical home: {rel(canon)}), "
                   f"then cp it over the other")
    except OSError as exc:
        b.fail(f"could not compare the cc_accounting copies: {exc}")


def check_render_faithful(b, paths, cmd, changed_msg, fix_msg, on_result=None):
    """Shared core of the two faithfulness checks (steps 3 and 7): snapshot
    git status over paths, run the deterministic render, re-snapshot, and fail
    with a before/after set diff plus the fix hint when the render changed the
    tree. on_result(result) runs between render and compare — the per-check
    hook for return-code handling and output parsing; it may b.fail or abort.
    Returns True when the render left the tree unchanged."""
    before = git_status(*paths)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT,
                            check=False)
    if on_result:
        on_result(result)
    after = git_status(*paths)
    if before != after:
        b.fail(changed_msg)
        before_set, after_set = set(before.splitlines()), set(after.splitlines())
        for line in sorted(before_set - after_set):
            print(f"  < {line}", file=sys.stderr)
        for line in sorted(after_set - before_set):
            print(f"  > {line}", file=sys.stderr)
        print(fix_msg, file=sys.stderr)
        return False
    return True


def check_faithfulness(b):
    """3. Materialization faithfulness — dirty-tree-safe. Snapshot the working
    tree, re-materialize, and flag only what the re-materialize *changes*
    (forgotten materialize or a drifted hand-edit), plus any orphan extra."""
    b.note("materialization faithfulness")
    if b.quick:
        b.skip("--quick: harness/ and samples/ proven untouched by the guard")
        return

    def on_result(result):
        output = result.stdout + result.stderr
        if result.returncode != 0:
            # The header-documented abort exception: the sample checks that
            # follow read the tree this bootstrap produces.
            print("FAIL: harness/bootstrap.sh failed:", file=sys.stderr)
            print(output, file=sys.stderr)
            raise SystemExit(1)
        extras = re.findall(r"extras: (\d+) file", output)
        for n in extras:
            if n != "0":
                b.fail(f"materialize reported {n} orphan extra(s) — a committed "
                       "file /harness no longer produces. git rm it.")
        # Committed orphans are invisible to the porcelain diff (bootstrap
        # never deletes them) — the extras count is their only guard. No
        # extras line parsed means the output format changed; fail loud
        # rather than pass an unchecked tree.
        if not extras:
            b.fail("no 'extras:' line parsed from bootstrap output — output "
                   "format changed; orphan detection is not running.")
            print(output, file=sys.stderr)

    if check_render_faithful(
            b, ("samples/",), ["bash", str(HERE / "bootstrap.sh")],
            "re-materialize changed the samples — a /harness edit was not "
            "materialized, or a sample was hand-edited:",
            "Fix: review the change, then commit the re-materialized samples "
            "with the /harness edit.", on_result):
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
    installed core copy differ only by the pinned delta (the installed copy is
    a deliberate trim plus adjusted links) recorded in
    harness/handbook-delta.expected — any other divergence is content drift. Sample docs must stand alone: no reference to
    another sample or to the monorepo samples/ tree."""
    b.note("handbook delta (root vs core copy) + sample self-containment")
    ok = True
    core_hb = HERE / "core/.claude/skills/handoff-routing/agentic-harness.md"
    # diff -U0, filtered to changed lines. The pass/fail compare is on the
    # multiset of those lines, not the raw diff text: `diff -U0` hunk grouping
    # and order are not stable across implementations (Apple/FreeBSD diff and
    # GNU diff group -U0 hunks differently for the same logical delta), so a
    # raw string compare fails on whichever platform did not generate the
    # pinned file. The delta's meaning is the multiset of added/removed lines
    # — order-independent — so comparing counts makes the check portable while
    # still catching real content drift: any changed line changes the multiset.
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
        actual_counts = Counter(actual.splitlines())
        expected_counts = Counter(expected.splitlines())
        if actual_counts != expected_counts:
            b.fail("docs/agentic-harness.md vs its core copy diverged beyond "
                   "harness/handbook-delta.expected:")
            for line in sorted((expected_counts - actual_counts).elements()):
                print(f"    - {line}", file=sys.stderr)
            for line in sorted((actual_counts - expected_counts).elements()):
                print(f"    + {line}", file=sys.stderr)
            print("Fix: reconcile the two copies (owner: docs/agentic-harness.md). "
                  "Regenerating the\nexpected delta is an explicit decision — a diff "
                  "touching it needs the same review as content drift.", file=sys.stderr)
            ok = False

    # Self-containment: each pattern scans the docs of the samples that must
    # not mention it. Derived from STACKS, so a new stack joins the sweep
    # without touching this check. A hyphenated stack name is distinctive
    # enough to match bare; a short one (go, generic) matches only as a path
    # segment, else ordinary prose would false-positive. Limit: a hyphenated
    # name that is a substring of another stack's, or that names a common
    # technology, would over- or under-match — such a stack needs its own
    # pattern here.
    hits = set()
    sweeps = [
        (re.compile(r"\b" + re.escape(s) + ("" if "-" in s else "/")),
         tuple(o for o in STACKS if o != s))
        for s in STACKS
    ]
    sweeps.append((re.compile(r"samples/"), tuple(STACKS)))
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


def github_slug(heading):
    """GitHub's heading→anchor slug: markdown stripped, lowercased, spaces
    to hyphens, everything not alphanumeric/hyphen/underscore dropped."""
    s = heading.strip().lower()
    s = re.sub(r"`([^`]*)`", r"\1", s)               # inline code markers
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)   # links keep their text
    s = "".join(ch for ch in s if ch.isalnum() or ch in " -_")
    return s.replace(" ", "-")


def heading_anchors(text):
    """Every anchor a markdown file exposes: heading slugs (GitHub duplicate
    suffixing: second 'x' is 'x-1') plus explicit <a id> anchors. Fenced
    blocks are skipped — a commented heading is not an anchor."""
    heading_re = re.compile(r"^#{1,6}\s+(\S.*)")
    aid_re = re.compile(r'<a id="([^"]+)"')
    slugs, seen = set(), Counter()
    fence = False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = heading_re.match(ln)
        if m:
            slug = github_slug(m.group(1))
            n = seen[slug]
            seen[slug] += 1
            slugs.add(slug if n == 0 else f"{slug}-{n}")
        slugs.update(aid_re.findall(ln))
    return slugs


def check_root_links(b):
    """3h. Root link integrity — every markdown link target in the root-level
    files (README, CLAUDE.md, docs/, root skills, tools/, harness/README.md)
    must resolve, including the #fragment: a fragment must name a heading slug
    or <a id> anchor in the target file. Fenced code blocks are skipped (they
    carry illustrative paths). Bare path tokens outside link syntax stay
    judgment work (/audit-harness Layer 2, check 5)."""
    b.note("root link integrity (markdown links + anchors resolve)")
    files = [ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "harness/README.md"]
    for pattern in ("docs/**/*.md", ".claude/skills/**/*.md", "tools/**/*.md"):
        files.extend(ROOT.glob(pattern))
    link = re.compile(r"\]\(([^)\s]+)\)")
    anchor_cache = {}

    def anchors_of(path):
        key = path.resolve()
        if key not in anchor_cache:
            anchor_cache[key] = heading_anchors(read_text(path))
        return anchor_cache[key]

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
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                if "{{" in target or "<" in target:
                    continue
                path_part, _, frag = target.partition("#")
                dest = f if not path_part else (f.parent / path_part)
                if path_part and not dest.exists():
                    bad.append(f"{rel(f)}:{i} -> {target}")
                    continue
                if frag and dest.is_file() and dest.suffix == ".md" \
                        and frag not in anchors_of(dest):
                    bad.append(f"{rel(f)}:{i} -> {target} (no anchor '{frag}')")
    if bad:
        b.fail("broken markdown links or anchors in root-level files:")
        for line in bad:
            print(f"    {line}", file=sys.stderr)
    else:
        print("  links and anchors resolve")


# 3i inputs (ADR 2026-07-12-parity-gates-for-hand-owned-parallels): the
# hand-owned parallel file pairs gated on rosters and vocabulary, never prose.
IDE_SKILL_PAIRS = (
    ("stacks/go/.claude/skills/goland/SKILL.md",
     "stacks/java-spring-boot/.claude/skills/intellij-idea/SKILL.md"),
    ("stacks/go/.claude/skills/goland/goland-mcp-integration.md",
     "stacks/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md"),
    ("stacks/go/.claude/skills/goland-doctor/SKILL.md",
     "stacks/java-spring-boot/.claude/skills/intellij-idea-doctor/SKILL.md"),
)
# Product-prose H2 pairs pinned as expected divergence, scoped per pair —
# a pin never licenses the same divergence in another file. Renaming either
# heading fails the gate until its pin is updated — an explicit decision.
IDE_HEADING_DELTA = {
    IDE_SKILL_PAIRS[0]: {("The Go toolchain stays canonical",
                          "Gradle Stays Canonical")},
}
# A candidate tag is any bracketed word, optionally with a (loosely
# captured) :target suffix, so malformed forms reach judgment instead of
# falling out of the scan: a case-variant head ([Blocked]), a spaced colon
# ([CLARIFY :x]), a bad target (uppercase, digits-first, empty,
# whitespace), or a canonical tag styled as a link ([AUTOFIX](note)).
# Regex classes ([A-Z]) and ID placeholders ([REQ-XX-NNN]) carry hyphens
# or stay single-lettered and never match the candidate shape.
TAG_CANDIDATE = re.compile(r"\[([A-Za-z]{2,})(\s*:[^\]]*)?\]")
TAG_TARGET = re.compile(r"^[a-z][a-z0-9-]*$")


def tag_findings(text, canon):
    """Judge every tag-shaped bracket token in text against the canonical
    vocabulary. Returns (judged, problems): judged counts the distinct
    tokens that reached judgment; problems are the defect strings. A token
    reaches judgment when its head is uppercase (tag-shaped) or matches the
    vocabulary case-insensitively; ordinary markdown links and lowercase
    prose brackets never do."""
    judged, problems, seen = 0, [], set()
    for m in TAG_CANDIDATE.finditer(text):
        head, sep = m.group(1), m.group(2)
        linked = text[m.end():m.end() + 1] == "("
        in_vocab = head.lower() in canon
        if not in_vocab and (linked or not head.isupper()):
            continue                    # an ordinary link or prose brackets
        if (head, sep, linked) in seen:
            continue
        seen.add((head, sep, linked))
        judged += 1
        if not in_vocab:
            problems.append(f"tag [{head}] is not in review-workflow's "
                            f"canonical set {sorted(canon)}")
        elif not head.isupper():
            problems.append(f"tag [{head}] has a case-variant head — "
                            "canonical tags are uppercase")
        elif linked:
            problems.append(f"tag [{head}] is immediately followed by '(' "
                            "— styled as a markdown link, not a tag")
        elif sep is not None and not sep.startswith(":"):
            problems.append(f"tag [{head}{sep}] carries whitespace before "
                            "the colon — expected [TAG:target]")
        elif sep is not None and not TAG_TARGET.match(sep[1:]):
            problems.append(f"tag [{head}:…] has a malformed target "
                            f"{sep[1:]!r} — expected a lowercase agent name")
    return judged, problems


def check_parity_gates(b):
    """3i. Parity gates for hand-owned parallel files (ADR
    2026-07-12-parity-gates-for-hand-owned-parallels). Three gates: the IDE
    skill pairs share one H2 roster (one pinned product-prose pair); feedback
    tags used in stack skills belong to review-workflow's canonical set; the
    severity headings match across the security-review copies. Prose stays
    free to diverge per stack — only rosters and vocabulary are gated."""
    b.note("parity gates (IDE rosters, tag vocabulary, severity headings)")
    ok = True

    def body(path):
        # Frontmatter is stripped only when the file opens with a fence — a
        # frontmatter-less companion whose own prose carries "---" rules must
        # not be truncated at the second rule. A missing input aggregates as
        # a FAIL row (None here), never aborts the battery mid-run.
        try:
            text = read_text(path)
        except OSError:
            return None
        lines = text.splitlines()
        if lines and FENCE.match(lines[0]):
            return strip_frontmatter(text)
        return lines

    for pair in IDE_SKILL_PAIRS:
        go_rel, java_rel = pair
        go_body, java_body = body(HERE / go_rel), body(HERE / java_rel)
        if go_body is None or java_body is None:
            b.fail("parity gates: missing input file — "
                   f"{go_rel if go_body is None else java_rel}")
            ok = False
            continue
        a = h2_headings(go_body)
        c = h2_headings(java_body)
        if not a or not c:
            b.fail(f"parity gates: empty H2 roster in {go_rel} or {java_rel}")
            ok = False
            continue
        pinned = IDE_HEADING_DELTA.get(pair, set())
        drift = [f"{x!r} vs {y!r}" for x, y in zip(a, c)
                 if x != y and (x, y) not in pinned]
        if len(a) != len(c) or drift:
            b.fail(f"IDE section-roster drift, {go_rel} vs {java_rel}: "
                   + ("; ".join(drift) or f"{len(a)} vs {len(c)} H2 headings"))
            ok = False

    try:
        rw_text = read_text(HERE / "core/.claude/skills/review-workflow/SKILL.md")
    except OSError:
        rw_text = ""
    canon = set(section_rows(rw_text, r"^## Feedback Tags"))
    if not canon:
        b.fail("parity gates: no canonical tags parsed from review-workflow "
               "§ Feedback Tags — the vocabulary gate would be vacuous")
        ok = False
    total_judged = 0
    for f in sorted((HERE / "stacks").glob("*/.claude/skills/**/*.md")):
        judged, problems = tag_findings(read_text(f), canon)
        total_judged += judged
        for problem in problems:
            b.fail(f"{rel(f)}: {problem}")
            ok = False
    if canon and total_judged == 0:
        # Anti-vacuity floor on the scan's own input: the stack skills carry
        # tags today, so a zero-judged sweep means the glob or the carriers
        # drifted and the gate is checking nothing.
        b.fail("parity gates: zero feedback tags reached judgment across "
               "the stack skills — the vocabulary gate scanned nothing")
        ok = False

    rosters = {}
    for s in STACKS:
        sec_rel = f"stacks/{s}/.claude/skills/security-review/SKILL.md"
        sec_body = body(HERE / sec_rel)
        if sec_body is None:
            b.fail(f"parity gates: missing input file — {sec_rel}")
            ok = False
        else:
            rosters[s] = severity_headings(sec_body)
    if rosters:
        baseline_stack = next(s for s in STACKS if s in rosters)
        if not rosters[baseline_stack]:
            b.fail("parity gates: no H3 headings under '## Severity "
                   "Classification' — the severity gate would be vacuous")
            ok = False
        for s, r in rosters.items():
            if r != rosters[baseline_stack]:
                b.fail(f"severity-heading drift, stacks/{s}/security-review: "
                       f"{r} vs {baseline_stack}'s {rosters[baseline_stack]}")
                ok = False
    if ok:
        print("  rosters and vocabularies match")


# 3j input: engine-pin classes the three stack test suites carry
# byte-identically — the same rationale as 3i (ADR 2026-07-12): a hand-owned
# parallel gets a gate. Fixture classes outside this list diverge freely.
SHARED_TEST_PIN_CLASSES = ("TestReviewConfigValidation", "TestReviewPlan")


def check_shared_test_pins(b):
    """3j. Shared engine-pin classes in stacks/*/scripts/test_score_change.py
    are byte-identical across the three stacks. The suites legitimately
    diverge in stack fixtures; the named classes pin the one engine, so a fix
    landing in a single stack's copy is drift, not variation."""
    b.note("shared test-suite pins (byte-identical across stacks)")
    segments = {}
    ok = True
    for s in STACKS:
        path = HERE / f"stacks/{s}/scripts/test_score_change.py"
        try:
            text = read_text(path)
        except OSError:
            b.fail(f"shared test pins: missing {rel(path)}")
            return
        for cls in SHARED_TEST_PIN_CLASSES:
            # Stop at the next class OR the __main__ trailer, so a stack's
            # legitimate trailer/class divergence after the pinned class
            # never false-fails the byte compare.
            m = re.search(rf"^class {cls}\b.*?(?=^class |^if __name__|\Z)",
                          text, re.M | re.S)
            if m is None:
                b.fail(f"shared test pins: {cls} missing from {rel(path)}")
                ok = False
                continue
            segments.setdefault(cls, {})[s] = m.group(0)
    for cls, per_stack in sorted(segments.items()):
        if len(set(per_stack.values())) > 1:
            b.fail(f"shared test pins: {cls} differs across stacks — a fix "
                   "landed in one copy only; sync all three")
            ok = False
    if ok:
        print("  shared pin classes identical")


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
    """4b. Sample build files carry no dangling .py references. Project
    builds run no harness suites (ADR 2026-07-13 — the runtime is verified
    once at materialize time), so zero refs is the norm; a build file that
    does name a script must name one that exists."""
    b.note("sample build-file script refs")
    ok = True
    for s in STACKS:
        if s not in BUILD_BINDINGS:
            b.fail(f"stack '{s}' has no build-binding file declared — extend "
                   "BUILD_BINDINGS in step 4b")
            ok = False
            continue
        binding = BUILD_BINDINGS[s]
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
        if not refs:
            print(f"  {s}: 0 .py refs in {binding} — project builds carry no "
                  "harness wiring")
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

    def on_result(result):
        if result.returncode != 0:
            b.fail("harness/package-marketplace.py failed:")
            print(result.stdout + result.stderr, file=sys.stderr)

    if check_render_faithful(
            b, ("plugins/", ".claude-plugin/marketplace.json"),
            [sys.executable, str(HERE / "package-marketplace.py")],
            "re-render changed the marketplace — a /harness edit was not repackaged:",
            "Fix: run harness/package-marketplace.py and commit the result "
            "with the /harness edit.", on_result):
        print("  marketplace == package-marketplace(/harness)")


def main(argv):
    # Line-buffer both streams so step headers (stdout) and FAIL details
    # (stderr) interleave in true order when the battery is redirected to a
    # file or a pipe — block-buffered stdout would otherwise reorder them.
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    flags = argv[1:]
    quick = "--quick" in flags
    strict = "--strict" in flags
    if any(f not in ("--quick", "--strict") for f in flags):
        print("usage: harness/check-sync.py [--quick] [--strict]", file=sys.stderr)
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

    b = Battery(quick, strict)
    check_shellcheck(b)
    check_bandit(b)
    check_stdlib_only(b)
    check_python_syntax(b)
    check_agent_body_parity(b)
    b.run_suite("agent-body renderer self-test", "harness/test_refresh_agent_bodies.py")
    check_cc_accounting_sync(b)
    check_faithfulness(b)
    check_layout_invariants(b)
    check_roster_sync(b)
    check_placeholder_gate(b)
    check_handbook_delta(b)
    check_verdict_enums(b)
    check_stack_agnostic_core(b)
    check_root_links(b)
    check_parity_gates(b)
    check_shared_test_pins(b)
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
