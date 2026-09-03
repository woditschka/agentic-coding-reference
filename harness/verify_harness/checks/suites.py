"""Subprocess suite runners (ADR 2026-07-18 check-sync-decomposition): the
steps whose evidence is another process's verdict — sample test suites and
doctors, harness and tools unit suites, the install-completeness and
toolchain-pin gates, and the marketplace re-render."""

import re
import subprocess
import sys
from pathlib import Path

from registry import STACKS

from verify_harness.battery import Battery, check_render_faithful, git_status
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


def _script_suites() -> tuple[str, ...]:
    """The scripts-suite roster, derived from the /harness source tree — the
    per-sample presence gate keeps its FAIL-on-missing semantics while the
    hand list retires: a suite added to core/scripts/tests joins the gate
    without a roster edit. A shrunken source tree must fail loudly, never
    shrink the gate — the floor pins the 2026-08-06 roster size."""

    def tests_under(scripts: Path) -> set[str]:
        return {
            "scripts/" + p.relative_to(scripts).as_posix()
            for p in (scripts / "tests").rglob("test_*.py")
        }

    # Core ships most suites; the layout-bound pair (test_config_layout,
    # test_features_layout) ships from each stack layer under the same
    # path — the intersection keeps only what every sample receives.
    core = tests_under(HERE / "core" / "scripts")
    per_stack = [tests_under(HERE / "stacks" / s / "scripts") for s in STACKS]
    suites = tuple(sorted(core | set.intersection(*per_stack)))
    if len(suites) < 16:
        raise SystemExit(
            f"derived scripts-suite roster holds {len(suites)} files under "
            "core+stacks scripts/tests — below the 16-suite floor; source "
            "tree broken?"
        )
    return suites


def _hook_suites() -> tuple[str, ...]:
    """The hook-suite roster, derived from core/.claude/hooks like the
    scripts roster above — a test sibling added beside a hook joins the gate
    without a roster edit. The floor pins the 2026-09-02 roster size (four
    hooks, four suites); a shrunken tree fails loudly."""
    suites = tuple(
        sorted(
            ".claude/hooks/" + p.name
            for p in (HERE / "core/.claude/hooks").glob("test_*.py")
        )
    )
    if len(suites) < 4:
        raise SystemExit(
            f"derived hook-suite roster holds {len(suites)} files under "
            "core/.claude/hooks — below the 4-suite floor; source tree broken?"
        )
    return suites


SAMPLE_SCRIPT_SUITES = _script_suites()
SAMPLE_HOOK_SUITES = _hook_suites()
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
        # resolve, ADR 2026-07-17 runtime-package-layout). Discovery skips a
        # non-package directory without error, so a run that collects zero
        # tests is a FAIL, not a green — the vacuity guard the install-time
        # exact-module run no longer needs but discovery still does.
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
        elif not re.search(r"Ran [1-9][0-9]* tests?", result.stderr):
            b.fail(
                f"samples/{s}/scripts test discovery ran zero tests — "
                "suites silently skipped?"
            )
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
    upgrade-deps skill tracks (build files, README/CLAUDE.md tables, init
    skeletons, workflow action SHAs) must exist and agree within its item.
    Before this step, a bump that missed one restatement passed every gate
    and waited for the next manual /upgrade-deps (the ADR 2026-07-14 Gradle
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
    .sh modules are the same class: dropping
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
    """6bb. The dev image's python toolchain pins match their single sources.

    The session container's egress is default-denied at runtime (ADR 2026-07-29
    proxy-enforced-egress), so the strict battery's python tools bake into the
    image at build time, pinned. ruff's pin lives in pyproject.toml
    (required-version); the Dockerfile's copy is a hand-owned parallel and gets
    this gate (ADR 2026-07-12). mypy and bandit have no other repo pin; the gate
    asserts they are ==-pinned so the image cannot float to a drifting
    toolchain. One supply-chain tripwire rides along: the Dockerfile must not
    pipe into a shell (sh/bash/dash/zsh, sudo/env/abs-path variants). It guards
    the removed curl|bash installer idiom returning — Claude Code installs from
    Anthropic's signed apt repo — and is NOT a general remote-execution barrier:
    download-then-execute or process substitution would pass it.

    Two tripwires guard the confinement itself. The image must install squid
    (the session's only path to the internet) and socat (the --ide tunnel) — a
    dev-tool cleanup dropping either would degrade a control silently. And the
    launcher must keep the sandbox-off --settings injection: Claude's in-process
    sandbox needs bubblewrap, which cannot create a user namespace under
    Docker's default seccomp profile (measured on docker 29.5.2, 2026-07-29 —
    it works only with seccomp=unconfined). Dropping the injection would revive
    the startup refusal a host's sandbox.failIfUnavailable setting causes."""
    import tomllib

    b.note("claude-dev toolchain and confinement pins")
    dockerfile = ROOT / "tools/claude-dev/Dockerfile"
    launcher = ROOT / "tools/claude-dev/claude-dev"
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
    problems.extend(
        f"Dockerfile does not install {binary} — a confinement control, not a dev tool"
        for binary in ("squid", "socat")
        if not re.search(rf"^\s*(?!#).*\b{binary}\b", text, re.MULTILINE)
    )
    override = '--settings \'{"sandbox":{"enabled":false,"failIfUnavailable":false}}\''
    if override not in launcher.read_text(encoding="utf-8"):
        problems.append(
            "launcher lost the sandbox-off --settings injection (bubblewrap "
            "cannot create a user namespace under the default seccomp profile; "
            "see the Dockerfile)"
        )
    # The eval runner restates the build-egress hosts deliberately (runtime
    # independence from operator config); this keeps the restated knowledge a
    # subset of the shipped default policy, so a host rename is a one-place
    # edit that this gate fans out.
    run_eval = ROOT / "evals" / "run_eval.py"
    policy = ROOT / "tools/claude-dev/claude-dev.toml"
    if run_eval.exists() and policy.exists():
        bench_hosts = set(
            re.findall(r'"--allow",\s*"([^"]+)"', run_eval.read_text(encoding="utf-8"))
        )
        try:
            allowed = set(
                tomllib.loads(policy.read_text(encoding="utf-8"))["egress"]["allow"]
            )
        except (tomllib.TOMLDecodeError, KeyError) as exc:
            allowed = set()
            problems.append(f"claude-dev.toml lacks egress.allow ({exc!r})")
        stray = sorted(bench_hosts - allowed)
        if stray and allowed:
            problems.append(
                "eval runner --allow hosts missing from claude-dev.toml "
                f"egress.allow: {', '.join(stray)}"
            )
    if problems:
        for p in problems:
            b.fail(p)
        return
    print(
        f"  ruff {required} matches pyproject; mypy/bandit pinned; "
        "no pipe-to-shell idiom; squid/socat present; sandbox-off injection "
        "present; eval --allow hosts within the shipped egress policy"
    )


def _quick_skip_proof(b: Battery) -> str | None:
    """Steps 6b/6bc quick-mode proof: in --quick, when tools/ and evals/ are
    both clean vs HEAD (staged, unstaged, and untracked), the pending edit
    cannot reach what these suites execute — the same git-proof mechanism the
    --quick guard already trusts for the derived trees, and the push-time
    gates still run the full battery. The proof is joint over both trees, and
    both steps skip on it or neither does: the eval suites are the only
    executable coverage of tools/harness-stats/accounting.py (run_eval.py
    loads it dynamically), so a per-tree skip would leave a tools/ edit
    untested. Returns the proof line, or None when the steps must run."""
    if not b.quick:
        return None
    if git_status("tools/", "evals/"):
        return None
    return "tools/ and evals/ clean vs HEAD (joint proof; full battery at push)"


def _dev_artifacts() -> list[str]:
    """The gitignored dev-run artifacts (TREND-dev.md, results/runs/dev-*).

    Local-only by contract, so the clean-tree proof cannot see them — the one
    input class step 6bc validates that git status does not cover."""
    results = ROOT / "evals" / "results"
    candidates = [results / "TREND-dev.md", *sorted((results / "runs").glob("dev-*"))]
    return [p.relative_to(ROOT).as_posix() for p in candidates if p.exists()]


def _summarize_check(b: Battery) -> bool:
    """The derived-view gate: `summarize.py --check` re-renders every view
    (TREND.md, run-page READMEs, and TREND-dev.md when dev runs exist) and
    fails on drift. Returns False after reporting the failure."""
    trend = subprocess.run(
        [sys.executable, "evals/summarize.py", "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if trend.returncode != 0:
        b.fail("eval derived views drifted from the run folders:")
        b.show_fail(trend.stdout + trend.stderr)
        return False
    return True


def _discovered_suite_passes(b: Battery, cwd: Path, label: str) -> str | None:
    """`unittest discover` from `cwd` with the shared vacuity guard: a failing
    run or a zero-test collection reports a FAIL and returns None; a passing
    run returns the collected-test count."""
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )
    ran = re.search(r"Ran (\d+) tests?", result.stderr)
    if result.returncode != 0:
        b.fail(f"{label} did not pass:")
        b.show_fail(result.stdout + result.stderr)
        return None
    if ran is None or int(ran.group(1)) == 0:
        b.fail(f"{label} collected zero tests — the suite went vacuous")
        return None
    return ran.group(1)


def check_tools_suites(b: Battery) -> None:
    """6b. Tools unit suites — every tools/*/tests/ suite tree.

    --quick runs this step whenever tools/ or evals/ carries a pending change
    — --quick is the tier-0 mode for a tools/ edit — and skips it only on the
    joint clean-tree proof (_quick_skip_proof; measured 2026-08-20: the
    claude-dev suite alone costs ~7s of wall-clock socket waits, so the skip
    buys real latency on the docs-edit path). Each tree runs via unittest
    discover from its toolbox root, so the source module a suite imports
    resolves from that root — the same way it resolves when installed.
    Zero suites found is a FAIL, not an empty loop."""
    b.note("tools unit suites")
    proof = _quick_skip_proof(b)
    if proof:
        b.skip(f"--quick: {proof}")
        return
    toolboxes = sorted(d.parent for d in (ROOT / "tools").glob("*/tests") if d.is_dir())
    if not toolboxes:
        b.fail("no tools unit suites found — the step went vacuous")
        return
    ok = True
    for box in toolboxes:
        if _discovered_suite_passes(b, box, f"{rel(box)}/tests") is None:
            ok = False
    if ok:
        print(f"  {len(toolboxes)} toolbox suites pass")


def check_eval_suites(b: Battery) -> None:
    """6bc. Eval bench unit suites — evals/tests/ via unittest discover —
    plus the derived-view gate — results/TREND.md and every run folder's
    README.md must match a fresh render (`summarize.py --check`) — the
    host-identity gate over the committed run folders
    (`run_eval.py --leak-scan`), and the dev-run commit gate: `dev-*` run
    folders and TREND-dev.md are local-only by contract (gitignored), so a
    tracked one means a forced add slipped through.

    --quick runs this step whenever tools/ or evals/ carries a pending change
    — --quick is the tier-0 mode for an evals/ edit — and skips it only on
    the joint clean-tree proof (_quick_skip_proof; measured 2026-08-20:
    `summarize.py --check` re-renders every committed run folder in ~13s).
    One input class is git-invisible: the gitignored dev-run artifacts. When
    any exists, the derived-view gate still runs before the rest skips, so a
    stale or orphaned TREND-dev.md is caught in exactly the pre-release
    dev-sweep window. The skip does forgo the leak-scan and tracked-dev
    gates until the push-time full battery — both read committed state, and
    a bad commit is exactly what the push gates re-check. Discovery runs with the evals root as the top level, so
    `import summarize` resolves the way the scripts themselves do. Zero
    suites found is a FAIL, and so is a discovery that collects zero tests —
    file presence alone proves nothing."""
    b.note("eval bench unit suites")
    proof = _quick_skip_proof(b)
    if proof:
        dev = _dev_artifacts()
        if not dev:
            b.skip(f"--quick: {proof}")
            return
        if _summarize_check(b):
            b.skip(
                f"--quick: {proof}; derived views validated first for the "
                f"git-invisible dev artifacts: {', '.join(dev)}"
            )
        return
    tests_dir = ROOT / "evals" / "tests"
    suites = (
        [
            f
            for f in sorted(tests_dir.rglob("test_*.py"))
            if "__pycache__" not in f.parts
        ]
        if tests_dir.is_dir()
        else []
    )
    if not suites:
        b.fail("no eval bench suites found — the step went vacuous")
        return
    ran = _discovered_suite_passes(b, ROOT / "evals", "evals/tests")
    if ran is None:
        return
    if not _summarize_check(b):
        return
    leak = subprocess.run(
        [sys.executable, "evals/run_eval.py", "--leak-scan"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if leak.returncode != 0:
        b.fail("committed eval run folders carry host identity:")
        b.show_fail(leak.stdout + leak.stderr)
        return
    tracked = subprocess.run(
        ["git", "ls-files", "--", "evals/results"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    dev_tracked = [
        path
        for path in tracked.stdout.splitlines()
        if path.startswith("evals/results/runs/dev-")
        or path == "evals/results/TREND-dev.md"
    ]
    if dev_tracked:
        b.fail("dev eval runs are local-only but git tracks:")
        b.show_fail("\n".join(dev_tracked))
        return
    print(
        f"  {len(suites)} suites pass ({ran} tests), derived views current,"
        " run folders leak-free, no dev run tracked"
    )


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
