"""Subprocess suite runners (ADR 2026-07-18 check-sync-decomposition): the
steps whose evidence is another process's verdict — sample test suites and
doctors, harness and tools unit suites, the install-completeness and
toolchain-pin gates, and the marketplace re-render."""

import re
import subprocess
import sys

from registry import STACKS

from verify_harness.battery import Battery, check_render_faithful
from verify_harness.text import HERE, ROOT, read_text, rel

# Control bytes minus newline and tab: what gets stripped from subprocess
# output before this battery re-prints it (terminal-escape hygiene).
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def _printable(text: str) -> str:
    return _CTRL_RE.sub("", text)


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
# its grading suite while the battery stayed green. The scripts suites are
# a package tree under scripts/tests/ (ADR 2026-07-17 runtime-package-layout),
# run via `unittest discover` from the scripts dir; the hook suites are
# standalone scripts run from the sample root.
SAMPLE_SCRIPT_SUITES = (
    "scripts/tests/test_handoff.py",
    "scripts/tests/handoff/test_schema.py",
    "scripts/tests/handoff/test_records.py",
    "scripts/tests/handoff/test_routing.py",
    "scripts/tests/handoff/test_view.py",
    "scripts/tests/test_doctor.py",
    "scripts/tests/test_accounting.py",
    "scripts/tests/changeset/test_config.py",
    "scripts/tests/changeset/test_git_facts.py",
    "scripts/tests/changeset/test_emit.py",
    "scripts/tests/grading/test_config.py",
    "scripts/tests/grading/test_config_layout.py",
    "scripts/tests/grading/test_features.py",
    "scripts/tests/grading/test_features_layout.py",
    "scripts/tests/grading/test_handoff_facts.py",
    "scripts/tests/grading/test_planner.py",
)
SAMPLE_HOOK_SUITES = (
    ".claude/hooks/test_handoff_allow.py",
    ".claude/hooks/test_handoff_log_guard.py",
    ".claude/hooks/test_sendmessage_continue_only.py",
)
SAMPLE_SUITES = SAMPLE_SCRIPT_SUITES + SAMPLE_HOOK_SUITES


def check_sample_suites(b: Battery) -> None:
    """4. Sample test suites. The scripts suites are a package tree run via
    `unittest discover` from each sample's scripts dir (where layout.toml +
    schemas colocate); the hook suites are standalone scripts run from the
    sample root. Every sample ships every suite — a missing file is a FAIL,
    not a skip."""
    b.note("sample test suites")
    if b.quick:
        b.skip("--quick: samples/ proven untouched by the guard")
        return
    ok = True
    for s in STACKS:
        sample = ROOT / "samples" / s
        for t in SAMPLE_SUITES:
            if not (sample / t).is_file():
                b.fail(
                    f"samples/{s}/{t} missing — every sample ships all "
                    f"{len(SAMPLE_SUITES)} suites"
                )
                ok = False
        # The scripts suites run as one discovery over scripts/tests, from the
        # scripts dir (top-level "." so `import handoff` and `import tests.*`
        # resolve, ADR 2026-07-17 runtime-package-layout).
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
            capture_output=True,
            text=True,
            cwd=sample / "scripts",
            check=False,
        )
        if result.returncode != 0:
            b.fail(f"samples/{s}/scripts test discovery")
            b.show_fail(result.stdout + result.stderr)
            ok = False
        # The hook suites are standalone; each runs from the sample root.
        for t in SAMPLE_HOOK_SUITES:
            if not (sample / t).is_file():
                continue
            result = subprocess.run(
                [sys.executable, t],
                capture_output=True,
                text=True,
                cwd=sample,
                check=False,
            )
            if result.returncode != 0:
                b.fail(f"samples/{s}/{t}")
                b.show_fail(result.stdout + result.stderr)
                ok = False
    if ok:
        print("  all suites pass")


def check_build_file_refs(b: Battery) -> None:
    """4b. Sample build files carry no dangling .py references. Project
    builds run no harness suites (ADR 2026-07-13 — the runtime is verified
    once at materialize time), so zero refs is the norm; a build file that
    does name a script must name one that exists."""
    b.note("sample build-file script refs")
    ok = True
    for s in STACKS:
        if s not in BUILD_BINDINGS:
            b.fail(
                f"stack '{s}' has no build-binding file declared — extend "
                "BUILD_BINDINGS in step 4b"
            )
            ok = False
            continue
        binding = BUILD_BINDINGS[s]
        bf = ROOT / "samples" / s / binding
        if not bf.is_file():
            b.fail(
                f"samples/{s}/{binding} missing — the stack's declared "
                "build-binding file"
            )
            ok = False
            continue
        refs = sorted(set(re.findall(r"[A-Za-z0-9_./-]+\.py", read_text(bf))))
        for p in refs:
            if not (ROOT / "samples" / s / p).is_file():
                b.fail(f"samples/{s}/{binding} references missing script '{p}'")
                ok = False
        if not refs:
            print(
                f"  {s}: 0 .py refs in {binding} — project builds carry no "
                "harness wiring"
            )
    if ok:
        print("  build-file script paths resolve")


def check_deps_report(b: Battery) -> None:
    """4c. Pinned-version sync — deps-report.py's local half: every pin the
    deps-upgrade skill tracks (build files, README/CLAUDE.md tables, init
    skeletons, workflow action SHAs) must exist and agree within its item.
    Before this step, a bump that missed one restatement passed every gate
    and waited for the next manual /deps-upgrade (the ADR 2026-07-14 Gradle
    case). Local reads only; --resolve-shas (network) stays in the skill.
    Runs in --quick too: README.md and .github/workflows/ sit outside the
    quick guard's derived trees, so a pin edit there must still be checked."""
    b.note("pinned-version sync (deps-report, local half)")
    result = subprocess.run(
        [sys.executable, str(HERE / "deps-report.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        # deps-report echoes excerpts of agent-editable repo files (README
        # table cells, workflow lines); strip control bytes before they reach
        # the maintainer's terminal or the CI log.
        print(_printable(result.stdout), end="")
        print(_printable(result.stderr), end="", file=sys.stderr)
        b.fail("deps-report found inconsistent version pins (harness/deps-report.py)")
    else:
        print("  all pins consistent")


def check_sample_doctors(b: Battery) -> None:
    """5. Sample doctors (the live docs contract)."""
    b.note("sample doctors")
    if b.quick:
        b.skip("--quick: samples/ proven untouched by the guard")
        return
    ok = True
    for s in STACKS:
        result = subprocess.run(
            [sys.executable, "scripts/doctor.py", "check"],
            capture_output=True,
            text=True,
            cwd=ROOT / "samples" / s,
            check=False,
        )
        if result.returncode != 0:
            b.fail(f"doctor failed in samples/{s}:")
            b.show_fail(result.stdout + result.stderr)
            ok = False
    if ok:
        print("  green")


def check_unit_suites(b: Battery) -> None:
    """6. Harness unit suites — every maintainer-side test_*.py under
    harness/tests/ (the shipped runtime layers core/, stacks/, and init/ ship
    their suites into consumers; those run inside each sample in step 4).
    test_render_agent_mirrors.py is excluded here only because it already ran
    as step 2c. Zero suites found is a FAIL, not an empty loop."""
    b.note("harness unit suites")
    if b.quick:
        b.skip("--quick: harness/ proven untouched by the guard")
        return
    suites = [
        f
        for f in sorted(HERE.glob("tests/**/test_*.py"))
        if not any(
            part in ("core", "stacks", "init", "__pycache__")
            for part in f.relative_to(HERE).parts
        )
        and f.name != "test_render_agent_mirrors.py"
    ]
    if not suites:
        b.fail("no harness unit suites found — the step went vacuous")
        return
    ok = True
    for t in suites:
        result = subprocess.run(
            [sys.executable, str(t)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            b.fail(f"{rel(t)} did not pass:")
            b.show_fail(result.stdout + result.stderr)
            ok = False
    if ok:
        print(f"  {len(suites)} suites pass")


def check_tools_install_complete(b: Battery) -> None:
    """6a. A tool with an install.sh must ship every non-test .py and .sh it has.

    ide_preflight.py once shipped nowhere: the installer copied three named files
    and the two new scripts were not among them, so the feature no-opped for every
    supported install while working from a repo checkout. This guards that
    regression class — every shipped module is named in the installer. Shipped
    .sh modules (e.g. claude-pod's egress_init.sh) are the same class: dropping
    one degrades every install to a runtime warn path the battery never sees."""
    b.note("tools install completeness")
    # A filename that survives only in a comment, an echo, or a printf status row
    # is reporting, not shipping — a whole-file substring test passes on those
    # while the actual copy line is gone, which is the regression this guards.
    reporting = re.compile(r"^\s*(#|echo\b|printf\b)")
    missing = []
    for install_sh in sorted((ROOT / "tools").glob("*/install.sh")):
        code = "\n".join(
            line
            for line in install_sh.read_text().splitlines()
            if not reporting.match(line)
        )
        shipped = sorted(install_sh.parent.glob("*.py")) + sorted(
            install_sh.parent.glob("*.sh")
        )
        for mod in shipped:
            if mod.name.startswith("test_") or mod.name == "install.sh":
                continue  # tests are not shipped; the installer does not ship itself
            if mod.name not in code:
                missing.append(f"{rel(install_sh)} does not ship {mod.name}")
    if missing:
        for m in missing:
            b.fail(m)
        return
    print("  every shipped tools/*/*.py and *.sh is named in its install.sh")


def check_pod_toolchain_pins(b: Battery) -> None:
    """6bb. The pod image's python toolchain pins match their single sources.

    The pod denies egress at runtime (ADR 2026-07-17 default-deny), so the
    strict battery's python tools bake into the image at build time, pinned.
    ruff's pin lives in pyproject.toml (required-version); the Dockerfile's
    copy is a hand-owned parallel and gets this gate (ADR 2026-07-12). mypy
    and bandit have no other repo pin; the gate asserts they are ==-pinned so
    the image cannot float to a drifting toolchain. One supply-chain tripwire
    rides along: the Dockerfile must not pipe into a shell (sh/bash/dash/zsh,
    sudo/env/abs-path variants). It guards the removed curl|bash installer
    idiom returning — Claude Code installs from Anthropic's signed apt repo —
    and is NOT a general remote-execution barrier: download-then-execute or
    process substitution would pass it. A second tripwire guards the launcher:
    the injected sandbox-off --settings override must stay — the image ships
    no bubblewrap/socat, so dropping it would revive the startup refusal a
    host's sandbox.failIfUnavailable setting causes in the pod."""
    import tomllib

    b.note("claude-pod toolchain pins")
    dockerfile = ROOT / "tools/claude-pod/Dockerfile"
    launcher = ROOT / "tools/claude-pod/claude-pod"
    pyproject = ROOT / "pyproject.toml"
    missing = [p for p in (dockerfile, launcher, pyproject) if not p.exists()]
    if missing:
        b.fail(f"pod-toolchain gate: {', '.join(rel(m) for m in missing)} missing")
        return
    try:
        required = tomllib.loads(pyproject.read_text(encoding="utf-8"))["tool"]["ruff"][
            "required-version"
        ]
    except (tomllib.TOMLDecodeError, KeyError) as exc:
        b.fail(f"pyproject.toml lacks tool.ruff.required-version ({exc!r})")
        return
    text = dockerfile.read_text(encoding="utf-8")
    pins = dict(re.findall(r"'(ruff|mypy|bandit)==([0-9][0-9.]*)'", text))
    problems = []
    if pins.get("ruff") != required:
        problems.append(
            f"Dockerfile pins ruff=={pins.get('ruff')} but pyproject "
            f"required-version is {required}"
        )
    problems.extend(
        f"Dockerfile does not ==-pin {tool}"
        for tool in ("mypy", "bandit")
        if tool not in pins
    )
    if re.search(r"\|\s*(sudo\s+|env\s+)?(/usr/bin/|/bin/)?(ba|da|z)?sh\b", text):
        problems.append("Dockerfile pipes into a shell (curl|bash-style idiom)")
    override = '--settings \'{"sandbox":{"enabled":false,"failIfUnavailable":false}}\''
    if override not in launcher.read_text(encoding="utf-8"):
        problems.append(
            "launcher lost the sandbox-off --settings injection "
            "(the image ships no bubblewrap; see README)"
        )
    if problems:
        for p in problems:
            b.fail(p)
        return
    print(
        f"  ruff {required} matches pyproject; mypy/bandit pinned; "
        "no pipe-to-shell idiom; sandbox-off injection present"
    )


def check_tools_suites(b: Battery) -> None:
    """6b. Tools unit suites — every tools/*/tests/ suite tree.

    Not skipped by --quick, unlike step 6: --quick is the tier-0 mode for a
    tools/ edit, so skipping here would leave exactly those edits untested. The
    suites are stdlib-only and run in about a second, so there is nothing to buy
    by skipping them. Each tree runs via unittest discover from its toolbox
    root, so the source module a suite imports resolves from that root — the
    same way it resolves when installed.
    Zero suites found is a FAIL, not an empty loop."""
    b.note("tools unit suites")
    toolboxes = sorted(d.parent for d in (ROOT / "tools").glob("*/tests") if d.is_dir())
    if not toolboxes:
        b.fail("no tools unit suites found — the step went vacuous")
        return
    ok = True
    for box in toolboxes:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
            capture_output=True,
            text=True,
            cwd=box,
            check=False,
        )
        if result.returncode != 0:
            b.fail(f"{rel(box)}/tests did not pass:")
            b.show_fail(result.stdout + result.stderr)
            ok = False
    if ok:
        print(f"  {len(toolboxes)} toolbox suites pass")


def check_marketplace_faithfulness(b: Battery) -> None:
    """7. Marketplace faithfulness — dirty-tree-safe. Re-render the plugin
    marketplace in place and flag only what the re-render *changes* (a /harness
    edit that was not repackaged). The render is deterministic, so an in-sync
    tree is unchanged."""
    b.note("marketplace faithfulness")
    if b.quick:
        b.skip("--quick: harness/ and plugins/ proven untouched by the guard")
        return

    def on_result(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0:
            b.fail("harness/package-marketplace.py failed:")
            print(result.stdout + result.stderr, file=sys.stderr)

    if check_render_faithful(
        b,
        ("plugins/", ".claude-plugin/marketplace.json"),
        [sys.executable, str(HERE / "package-marketplace.py")],
        "re-render changed the marketplace — a /harness edit was not repackaged:",
        "Fix: run harness/package-marketplace.py and commit the result "
        "with the /harness edit.",
        on_result,
    ):
        print("  marketplace == package-marketplace(/harness)")
