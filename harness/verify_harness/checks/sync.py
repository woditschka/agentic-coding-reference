"""Rendered-tree parity and content-invariant checks (ADR 2026-07-18
check-sync-decomposition): the steps that compare re-rendered trees against
the committed ones or hold cross-file content invariants — agent-body parity,
the accounting vendored copy, materialization faithfulness, the sample layout
and roster invariants, the placeholder and handbook gates, verdict enums, the
stack-agnostic core, root links, and the parity gates."""

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import registry
from registry import STACKS, TOOLS

from verify_harness.battery import Battery, check_render_faithful
from verify_harness.text import (
    FENCE,
    HERE,
    ROOT,
    _fence_state,
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

# The PROJECT_NAME / PROJECT_DESCRIPTION template tokens, built by
# concatenation so this package never matches itself.
PH_TOKENS = tuple("{{" + t + "}}" for t in ("PROJECT_NAME", "PROJECT_DESCRIPTION"))
PH_ALLOW = re.compile(
    r"^(\.claude/skills/(init|harvest)/SKILL\.md$"
    r"|harness/init/"
    r"|harness/core/\.claude/skills/doctor/"
    r"|harness/core/scripts/tests/test_doctor\.py$"
    r"|plugins/[a-z-]+/skills/doctor/"
    r"|plugins/[a-z-]+/_engine/scripts/tests/test_doctor\.py$"
    r"|samples/[a-z-]+/\.claude/skills/doctor/"
    r"|samples/[a-z-]+/scripts/tests/test_doctor\.py$"
    r"|samples/[a-z-]+/CLAUDE\.md$"
    r"|samples/[a-z-]+/docs/(prd|system-design)\.md$"
    r"|samples/go/Makefile$)"
)

CORE_STACK_TOKENS = re.compile(
    r"\bgo\.mod\b|gradlew|build\.gradle|pom\.xml|\.go\b|\.java\b"
    r"|golangci|spotless|JUnit|com/example"
)

DESIGN_BLOCK_VERDICTS = {
    "covered",
    "minor",
    "new",
    "refactor-first",
    "foundational",
    "conflicting",
}
REVIEW_FEEDBACK_VERDICTS = {"approved", "changes_requested", "blocked"}

# Mirror surfaces and their file suffixes — the same registry.TOOLS-derived
# data the renderer uses (the parsing logic stays independent on purpose).
MIRROR_SURFACES = registry.mirror_surfaces()


def check_agent_body_parity(b: Battery) -> None:
    """2b. Agent body parity — every agent's four per-tool source copies must
    carry byte-identical bodies; only the frontmatter differs. One documented
    exception is normalized away: skill links are location-correct per
    directory (../skills/ from .claude/agents/, ../../.claude/skills/ from the
    other three). The mirror bodies are rendered from the .claude base by
    render-agent-mirrors.py (via propagate-harness); this step gates a forgotten
    render or a hand-edited mirror. Faithfulness (step 3) cannot see either: a
    drifted mirror sits identically in source and sample. A drifted copy ships
    a weaker agent to that tool's users."""
    b.note("agent body parity (per-tool copies)")
    ok = True

    def fail(msg: str) -> None:
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
                fail(
                    f"sibling link form (../../.claude/skills/) in {rel(base)} "
                    "— the claude copy uses ../skills/"
                )
            for mirror_dir, suffix in MIRROR_SURFACES:
                mirror = layer / mirror_dir / f"{name}{suffix}"
                if not mirror.is_file():
                    fail(f"missing per-tool agent copy {rel(mirror)}")
                    continue
                mirror_body = strip_frontmatter(read_text(mirror))
                if any(
                    "../skills/" in l.replace("../../.claude/skills/", "")
                    for l in mirror_body
                ):
                    fail(
                        f"un-rewritten skill link (../skills/) in {rel(mirror)} "
                        "— broken from this directory"
                    )
                if norm_links(mirror_body) != base_body:
                    fail(
                        f"agent body drift (frontmatter aside): {rel(mirror)} != {rel(base)}"
                    )
        if bases == 0:
            fail(
                f"no agent bases under {rel(layer)}/.claude/agents/ "
                "— roster empty or path renamed"
            )
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
                    kind = (
                        "copilot agents must be <name>.agent.md"
                        if mirror_dir == ".github/agents"
                        else "unexpected non-.md file in a tool agents dir"
                    )
                    fail(f"{rel(f)} — {kind}")
                    continue
                name = f.name[: -len(suffix)]
                if not (layer / ".claude/agents" / f"{name}.md").is_file():
                    fail(
                        f"{rel(f)} has no .claude/agents/{name}.md base "
                        "— sibling-only agent, never parity-checked"
                    )
    if ok:
        print("  all per-tool bodies identical")


def check_accounting_sync(b: Battery) -> None:
    """2d. accounting vendored-copy sync. The module is authored once and
    copied to the other location; the two must stay byte-identical so the
    statusline and the handoff board price from the same code. Canonical home:
    tools/harness-stats/accounting.py (install.sh puts it beside the
    statusline). Vendored copy: harness/core/scripts/accounting.py, which the
    board imports and which materializes into every sample (step 3 covers the
    sample copies; only this canonical↔vendored pair is unguarded otherwise).
    There is no build step — the copy is manual, this gate is automatic."""
    b.note("accounting vendored-copy sync")
    canon = ROOT / "tools/harness-stats/accounting.py"
    vendored = HERE / "core/scripts/accounting.py"
    try:
        if canon.read_bytes() == vendored.read_bytes():
            print("  canonical == vendored")
        else:
            b.fail(
                f"{rel(canon)} != {rel(vendored)} — decide which copy "
                f"holds the intended edit (canonical home: {rel(canon)}), "
                f"then cp it over the other"
            )
    except OSError as exc:
        b.fail(f"could not compare the accounting copies: {exc}")


def check_faithfulness(b: Battery) -> None:
    """3. Materialization faithfulness — dirty-tree-safe. Snapshot the working
    tree, re-materialize, and flag only what the re-materialize *changes*
    (forgotten materialize or a drifted hand-edit), plus any orphan extra."""
    b.note("materialization faithfulness")
    if b.quick:
        b.skip("--quick: harness/ and samples/ proven untouched by the guard")
        return

    def on_result(result: subprocess.CompletedProcess[str]) -> None:
        output = result.stdout + result.stderr
        if result.returncode != 0:
            # The header-documented abort exception: the sample checks that
            # follow read the tree this materialize-samples run produces.
            print("FAIL: harness/materialize-samples.sh failed:", file=sys.stderr)
            print(output, file=sys.stderr)
            raise SystemExit(1)
        extras = re.findall(r"extras: (\d+) file", output)
        for n in extras:
            if n != "0":
                b.fail(
                    f"materialize reported {n} orphan extra(s) — a committed "
                    "file /harness no longer produces. git rm it."
                )
        # Committed orphans are invisible to the porcelain diff (materialize-
        # samples never deletes them) — the extras count is their only guard. No
        # extras line parsed means the output format changed; fail loud
        # rather than pass an unchecked tree.
        if not extras:
            b.fail(
                "no 'extras:' line parsed from materialize-samples output — output "
                "format changed; orphan detection is not running."
            )
            print(output, file=sys.stderr)

    if check_render_faithful(
        b,
        ("samples/",),
        ["bash", str(HERE / "materialize-samples.sh")],
        "re-materialize changed the samples — a /harness edit was not "
        "materialized, or a sample was hand-edited:",
        "Fix: review the change, then commit the re-materialized samples "
        "with the /harness edit.",
        on_result,
    ):
        print("  samples == materialize(/harness)")


def check_layout_invariants(b: Battery) -> None:
    """3b. Sample layout invariants — the cross-tool compatibility rules from
    docs/cross-tool-strategy.md as a gate: CLAUDE.md is the single rules file,
    skills live in .claude/skills/ only, every tool surface is present."""
    b.note("sample layout invariants (cross-tool rules, copy channel)")
    ok = True

    def fail(msg: str) -> None:
        nonlocal ok
        b.fail(msg)
        ok = False

    # Derived from the registry.TOOLS table: skills may exist only under
    # .claude/skills/ (no per-tool sibling), and every tool's agents dir must
    # be present in a sample.
    mirror_skill_dirs = tuple(
        row["agents_dir"].rsplit("/", 1)[0] + "/skills"
        for tool, row in TOOLS.items()
        if tool != "claude"
    )
    agent_dirs = tuple(row["agents_dir"] for row in TOOLS.values())
    for s in STACKS:
        sample = ROOT / "samples" / s
        for p in ("AGENTS.md", ".github/copilot-instructions.md", *mirror_skill_dirs):
            if (sample / p).exists():
                fail(
                    f"samples/{s}/{p} exists — CLAUDE.md is the single rules "
                    "file and skills live in .claude/skills/ only"
                )
        for p in ("CLAUDE.md", ".junie/config.json", *agent_dirs, ".claude/skills"):
            if not (sample / p).exists():
                fail(
                    f"samples/{s}/{p} missing — required by the cross-tool "
                    "compatibility rules"
                )
        # Copy-channel rule: declared in layout.toml, no silent extension
        # creep, the runtime git-tracked, the ledger ignored but never the
        # runtime.
        lt = sample / "scripts/layout.toml"
        lt_text = read_text(lt) if lt.is_file() else ""
        if not re.search(r'channel *= *"copy"', lt_text):
            fail(f'samples/{s}/scripts/layout.toml does not declare channel = "copy"')
        if not re.search(r"extensions *= *\[\]", lt_text):
            fail(
                f"samples/{s}/scripts/layout.toml extensions is not [] — the "
                "samples declare none; a non-empty list weakens orphan detection"
            )
        tracked = subprocess.run(
            ["git", "ls-files", f"samples/{s}/.claude/skills"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        ).stdout
        if not tracked.strip():
            fail(f"samples/{s} runtime is untracked — the copy channel commits it")
        gitignore = sample / ".gitignore"
        gi_text = read_text(gitignore) if gitignore.is_file() else ""
        if not re.search(r"^\.scratch/", gi_text, re.M):
            fail(f"samples/{s}/.gitignore does not ignore .scratch/")
        if ".claude/skills" in gi_text:
            fail(
                f"samples/{s}/.gitignore ignores the runtime — the copy "
                "channel commits it"
            )
    if ok:
        print("  cross-tool rules and channel invariants hold")


def check_roster_sync(b: Battery) -> None:
    """3c. Project-owned roster sync. Faithfulness (step 3) covers only the
    runtime; the project-owned committed files drift silently when the shipped
    roster changes. Gates: skills table both directions (scoped to its two
    chapters), agents README roster, init skeleton coverage, brief roster, ADR
    placement, and the ROOT skill table (CLAUDE.md "Root-Level Skills") plus
    the adoption trio's mentions in docs/adoption-guide.md. Row *descriptions*
    stay judgment (/audit-harness Layer 2 check 5)."""
    b.note(
        "project-owned roster sync (skills tables incl. root, agents README, init coverage)"
    )
    ok = True

    def fail(msg: str) -> None:
        nonlocal ok
        b.fail(msg)
        ok = False

    for s in STACKS:
        claude_md = read_text(ROOT / "samples" / s / "CLAUDE.md")
        agents_readme = read_text(ROOT / "samples" / s / ".claude/agents/README.md")
        # Presence is judged against the parsed '## Skills' rows, not a
        # whole-file substring — a row under the wrong heading, or the name
        # embedded mid-cell elsewhere, must not satisfy the roster.
        readme_rows = set(section_rows(agents_readme, r"^## Skills"))
        if not readme_rows:
            fail(
                f"samples/{s}/.claude/agents/README.md: no rows parsed under "
                "'## Skills' — roster empty or heading renamed"
            )
        shipped = set()
        for skills_root in (
            HERE / "core/.claude/skills",
            HERE / "stacks" / s / ".claude/skills",
        ):
            if not skills_root.is_dir():
                continue
            for d in sorted(p for p in skills_root.iterdir() if p.is_dir()):
                shipped.add(d.name)
                if f"| `{d.name}`" not in claude_md:
                    fail(
                        f"samples/{s}/CLAUDE.md skills table has no row for "
                        f"shipped skill '{d.name}'"
                    )
                if d.name not in readme_rows:
                    fail(
                        f"samples/{s}/.claude/agents/README.md Skills table "
                        f"has no row for shipped skill '{d.name}'"
                    )
        # Vacuous-pass backstop, same reason as step 2b's bases counter: a
        # renamed skills root would otherwise let this loop check nothing.
        if not shipped:
            fail(
                f"no shipped skills found for stack {s} — roster empty or path renamed"
            )
        for row in section_rows(claude_md, r"^## (Agent Usage|Stack-specific skills)"):
            if row not in shipped:
                fail(
                    f"samples/{s}/CLAUDE.md skills table row '{row}' names no "
                    "shipped skill — ghost row"
                )
        for row in readme_rows:
            if row not in shipped:
                fail(
                    f"samples/{s}/.claude/agents/README.md Skills row "
                    f"'{row}' names no shipped skill — ghost row"
                )
        for agents_root in (
            HERE / "core/.claude/agents",
            HERE / "stacks" / s / ".claude/agents",
        ):
            if not agents_root.is_dir():
                continue
            for f in sorted(agents_root.glob("*.md")):
                if f.stem == "README":
                    continue
                if f"**{f.stem}**" not in agents_readme:
                    fail(
                        f"samples/{s}/.claude/agents/README.md has no roster "
                        f"row for shipped agent '{f.stem}'"
                    )
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
            brief = (
                "docs/adr/README.md" if t.name == "adr-README.md" else f"docs/{t.name}"
            )
            if not (ROOT / "samples" / s / brief).is_file():
                fail(
                    f"samples/{s}/{brief} missing — the doctor template "
                    f"{t.name} has no sample brief"
                )
        # ADR placement: a sample's decision log starts empty — README.md only.
        adr_dir = ROOT / "samples" / s / "docs/adr"
        entries = sorted(p.name for p in adr_dir.iterdir()) if adr_dir.is_dir() else []
        if entries != ["README.md"]:
            fail(
                f"samples/{s}/docs/adr must contain only README.md — no "
                "harness ADR is materialized"
            )

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
            fail(
                f"root CLAUDE.md Root-Level Skills table has no row for skill '{d.name}'"
            )
        # The trio's documented home; the chapter names them as user-typed
        # commands (`/init`) or bare (`init`) — accept both.
        if (
            d.name in ("init", "materialize", "harvest")
            and f"`{d.name}`" not in adopt_text
            and f"`/{d.name}`" not in adopt_text
        ):
            fail(
                "docs/adoption-guide.md Adopt in Your Own Project chapter "
                f"never mentions '{d.name}'"
            )
    if not root_shipped:
        fail(
            "no root skills found under .claude/skills/ — roster empty or path renamed"
        )
    for row in root_rows:
        if row not in root_shipped:
            fail(f"CLAUDE.md table row '{row}' names no root skill — ghost row")
    if ok:
        print("  tables and skeleton coverage in sync")


def check_placeholder_gate(b: Battery) -> None:
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
            b.fail(
                f"template placeholder leaked into {relpath} — outside the "
                "documented template locations"
            )
            ok = False
    # Canary against a vacuous pass: the init skeletons must carry the token —
    # if the token format ever changes, this fails instead of the gate
    # scanning for a string nothing contains.
    for s in STACKS:
        skeleton = HERE / "init/stacks" / s / "CLAUDE.md"
        if not skeleton.is_file() or PH_TOKENS[0] not in read_text(skeleton):
            b.fail(
                f"{PH_TOKENS[0]} not found in harness/init/stacks/{s}/CLAUDE.md "
                "— token format changed; the placeholder gate is scanning for nothing"
            )
            ok = False
    if ok:
        print("  placeholders only in documented template locations")


def check_handbook_delta(b: Battery) -> None:
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
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    actual = "\n".join(
        l
        for l in result.stdout.splitlines()
        if l.startswith(("-", "+")) and not l.startswith(("---", "+++"))
    )
    expected_file = HERE / "handbook-delta.expected"
    if not expected_file.is_file():
        b.fail(
            "harness/handbook-delta.expected missing — the pinned handbook "
            "delta has no reference"
        )
        ok = False
    else:
        expected = "\n".join(
            l for l in read_text(expected_file).splitlines() if not l.startswith("#")
        )
        actual_counts = Counter(actual.splitlines())
        expected_counts = Counter(expected.splitlines())
        if actual_counts != expected_counts:
            b.fail(
                "docs/agentic-harness.md vs its core copy diverged beyond "
                "harness/handbook-delta.expected:"
            )
            for line in sorted((expected_counts - actual_counts).elements()):
                print(f"    - {line}", file=sys.stderr)
            for line in sorted((actual_counts - expected_counts).elements()):
                print(f"    + {line}", file=sys.stderr)
            print(
                "Fix: reconcile the two copies (owner: docs/agentic-harness.md). "
                "Regenerating the\nexpected delta is an explicit decision — a diff "
                "touching it needs the same review as content drift.",
                file=sys.stderr,
            )
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
        (
            re.compile(r"\b" + re.escape(s) + ("" if "-" in s else "/")),
            tuple(o for o in STACKS if o != s),
        )
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
        b.fail(
            f"{h} references another sample or the samples/ tree — sample "
            "docs must be self-contained"
        )
        ok = False
    if ok:
        print("  delta pinned, samples self-contained")


def check_verdict_enums(b: Battery) -> None:
    """3f. Verdict-enum sync — the schema enums the routing contract depends
    on. Two gates. The core verdict enums are pinned to a literal copy of the
    canonical names, so a schema edit cannot silently widen or narrow a
    verdict space. Per stack, build-failure's `failed_check` enum must equal
    build-pass's `gate_checks_run` items enum — one quality gate, one verb
    vocabulary, two schemas. A one-sided rename would ship and fail loudly
    only at the consumer's first append. Prose drift in the skills that
    document the sets stays judgment (/audit-harness Layer 2)."""
    b.note("verdict-enum sync (design-block, review-feedback, build stages)")

    def verdicts(name: str) -> set[str]:
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
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        # TypeError: valid JSON of the wrong shape (non-dict properties,
        # non-iterable enum) must aggregate, never abort the battery.
        problems.append(f"could not read verdict enums: {exc}")
    for s in STACKS:
        scratch = HERE / "stacks" / s / "schemas/scratch"
        try:
            bf = json.loads(read_text(scratch / "build-failure.schema.json"))
            bp = json.loads(read_text(scratch / "build-pass.schema.json"))
            failed = set(bf["properties"]["failed_check"]["enum"])
            ran = set(bp["properties"]["gate_checks_run"]["items"]["enum"])
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            problems.append(f"{s}: could not read build-stage enums: {exc}")
            continue
        if not failed or not ran:
            problems.append(f"{s}: empty build-stage enum — the gate would be vacuous")
        elif failed != ran:
            problems.append(
                f"{s}: build-failure failed_check {sorted(failed)} != "
                f"build-pass gate_checks_run {sorted(ran)} — sync both schemas"
            )
    if problems:
        b.fail(f"verdict-enum sync: {'; '.join(problems)}")
    else:
        print("  verdict and gate-stage enums in sync")


def check_stack_agnostic_core(b: Battery) -> None:
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


def check_root_links(b: Battery) -> None:
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
    anchor_cache: dict[Path, set[str]] = {}

    def anchors_of(path: Path) -> set[str]:
        key = path.resolve()
        if key not in anchor_cache:
            anchor_cache[key] = heading_anchors(read_text(path))
        return anchor_cache[key]

    bad = []
    for f in sorted(set(files)):
        if not f.is_file():
            continue
        fence = None
        for i, line in enumerate(read_text(f).splitlines(), 1):
            fence = _fence_state(line, fence)
            if fence is not None:
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
                if (
                    frag
                    and dest.is_file()
                    and dest.suffix == ".md"
                    and frag not in anchors_of(dest)
                ):
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
# Product-prose H2 pairs pinned as expected divergence, scoped per pair —
# a pin never licenses the same divergence in another file. Renaming either
# heading fails the gate until its pin is updated — an explicit decision.
IDE_HEADING_DELTA = {
    IDE_SKILL_PAIRS[0]: {
        ("The Go toolchain stays canonical", "Gradle Stays Canonical")
    },
}
# 3i inputs, same ADR: the per-stack agent bodies and skill parallels are
# hand-owned three-way copies whose contract-bearing level is the H2 roster;
# prose below the headings stays free to diverge per stack. A heading only
# some stacks legitimately carry is pinned in STACK_PARALLEL_PINNED with the
# exact carrier set and excluded from the cross-compare; the gate then checks
# presence per stack against that set, so a carrier dropping a pinned heading
# still fails. Adding a pin is an explicit decision, same as IDE_HEADING_DELTA.
STACK_PARALLEL_FILES = (
    ".claude/agents/README.md",
    ".claude/agents/system-design-expert.md",
    ".claude/agents/feature-implementer.md",
    ".claude/agents/security-reviewer.md",
    ".claude/agents/test-reviewer.md",
    ".claude/agents/code-quality-reviewer.md",
    ".claude/skills/design-validation/SKILL.md",
    ".claude/skills/doc-sync/SKILL.md",
    ".claude/skills/code-quality-gate/SKILL.md",
    ".claude/skills/document-writing/review-checks.md",
    ".claude/skills/test-review/SKILL.md",
    ".claude/skills/code-quality-review/SKILL.md",
    ".claude/skills/security-review/SKILL.md",
)
STACK_PARALLEL_PINNED: dict[str, dict[str, tuple[str, ...]]] = {
    # The agents README names its stack's IDE oracle in the MCP heading;
    # generic binds no oracle and carries no MCP section.
    ".claude/agents/README.md": {
        "MCP Tools (GoLand oracle)": ("go",),
        "MCP Tools (IntelliJ oracle)": ("java-spring-boot",),
    },
    # go/java bind an IDE oracle; only java binds a config surface
    # (application.yml / @ConfigurationProperties); generic binds neither.
    ".claude/skills/code-quality-gate/SKILL.md": {
        "IDE Static Analysis (optional)": ("go", "java-spring-boot"),
        "Configuration Sync": ("java-spring-boot",),
    },
    # Each stack names its own checks slot (Go-/Java-/Stack-Specific); java
    # additionally carries a grep-pattern table no sibling has; go/java bind
    # an IDE oracle, generic binds none.
    ".claude/skills/security-review/SKILL.md": {
        "Go-Specific Security Checks": ("go",),
        "Java-Specific Security Checks": ("java-spring-boot",),
        "Stack-Specific Security Checks": ("generic",),
        "Detection Patterns": ("java-spring-boot",),
        "IDE-Assisted Checks (optional)": ("go", "java-spring-boot"),
    },
    ".claude/skills/code-quality-review/SKILL.md": {
        "IDE-Assisted Review (optional)": ("go", "java-spring-boot"),
    },
}


def check_parity_gates(b: Battery) -> None:
    """3i. Parity gates for hand-owned parallel files (ADR
    2026-07-12-parity-gates-for-hand-owned-parallels). Four gates: the IDE
    skill pairs share one H2 roster (one pinned product-prose pair); the
    stack-parallel agent bodies and skill trios share one H2 roster per file
    (stack-specific headings pinned); feedback tags used in stack skills
    belong to review-workflow's canonical set; the severity headings match
    across the security-review copies. Prose stays free to diverge per
    stack — only rosters and vocabulary are gated."""
    b.note(
        "parity gates (IDE + stack-parallel rosters, tag vocabulary, severity headings)"
    )
    ok = True

    def body(path: Path) -> list[str] | None:
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
            b.fail(
                "parity gates: missing input file — "
                f"{go_rel if go_body is None else java_rel}"
            )
            ok = False
            continue
        a = h2_headings(go_body)
        c = h2_headings(java_body)
        if not a or not c:
            b.fail(f"parity gates: empty H2 roster in {go_rel} or {java_rel}")
            ok = False
            continue
        pinned = IDE_HEADING_DELTA.get(pair, set())
        drift = [
            f"{x!r} vs {y!r}"
            for x, y in zip(a, c, strict=False)
            if x != y and (x, y) not in pinned
        ]
        if len(a) != len(c) or drift:
            b.fail(
                f"IDE section-roster drift, {go_rel} vs {java_rel}: "
                + ("; ".join(drift) or f"{len(a)} vs {len(c)} H2 headings")
            )
            ok = False

    for rel_path in STACK_PARALLEL_FILES:
        pins = STACK_PARALLEL_PINNED.get(rel_path, {})
        rosters, headings = {}, {}
        for s in STACKS:
            lines = body(HERE / "stacks" / s / rel_path)
            if lines is None:
                b.fail(f"parity gates: missing input file — stacks/{s}/{rel_path}")
                ok = False
                continue
            headings[s] = h2_headings(lines)
            roster = [h for h in headings[s] if h not in pins]
            if not roster:
                b.fail(f"parity gates: empty H2 roster in stacks/{s}/{rel_path}")
                ok = False
                continue
            rosters[s] = roster
        # A pin is exact, not an exclusion: presence per stack must equal the
        # declared carrier set, so a carrier dropping a pinned heading fails
        # instead of hiding behind the pin.
        for heading, carriers in pins.items():
            for s, hs in sorted(headings.items()):
                if (heading in hs) != (s in carriers):
                    verb = "lacks" if s in carriers else "carries"
                    b.fail(
                        f"pinned stack-parallel heading '{heading}' "
                        f"({rel_path}): stacks/{s} {verb} it, the pin "
                        f"names {sorted(carriers)} — sync the file or "
                        "update the pin"
                    )
                    ok = False
        if len(rosters) < 2:
            continue
        baseline = next(s for s in STACKS if s in rosters)
        for s, r in sorted(rosters.items()):
            if r != rosters[baseline]:
                b.fail(
                    f"stack-parallel H2 roster drift, stacks/{s}/{rel_path}: "
                    f"{r} vs {baseline}'s {rosters[baseline]} — an edit "
                    "landed one-sided; sync all three or pin the heading"
                )
                ok = False

    try:
        rw_text = read_text(HERE / "core/.claude/skills/review-workflow/SKILL.md")
    except OSError:
        rw_text = ""
    canon = set(section_rows(rw_text, r"^## Feedback Tags"))
    if not canon:
        b.fail(
            "parity gates: no canonical tags parsed from review-workflow "
            "§ Feedback Tags — the vocabulary gate would be vacuous"
        )
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
        b.fail(
            "parity gates: zero feedback tags reached judgment across "
            "the stack skills — the vocabulary gate scanned nothing"
        )
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
            b.fail(
                "parity gates: no H3 headings under '## Severity "
                "Classification' — the severity gate would be vacuous"
            )
            ok = False
        for s, r in rosters.items():
            if r != rosters[baseline_stack]:
                b.fail(
                    f"severity-heading drift, stacks/{s}/security-review: "
                    f"{r} vs {baseline_stack}'s {rosters[baseline_stack]}"
                )
                ok = False
    if ok:
        print("  rosters and vocabularies match")
