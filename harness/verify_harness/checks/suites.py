"""Run the sample, harness, tools, and eval suites and the marketplace re-render."""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

from registry import STACKS

from verify_harness.battery import (
    Battery,
    RenderCheck,
    check_render_faithful,
    git_status,
)
from verify_harness.text import HERE, ROOT, read_text, rel

# Control bytes minus newline and tab, stripped from subprocess output before
# the battery re-prints it.
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
DISCOVER = (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".")
SCRIPT_SUITE_FLOOR = 16
HOOK_SUITE_FLOOR = 4
PINNED_TOOLS = ("mypy", "bandit")
CONFINEMENT_BINARIES = ("squid", "socat")
SANDBOX_OFF_OVERRIDE = (
    '--settings \'{"sandbox":{"enabled":false,"failIfUnavailable":false}}\''
)

# Per-stack build-binding file. Project builds carry no harness suite wiring,
# so zero .py references is the norm; a reference that exists must resolve.
BUILD_BINDINGS = {
    "go": "Makefile",
    "java-spring-boot": "build.gradle",
    "generic": "scripts/stack.sh",
}


def _printable(text: str) -> str:
    """Strip terminal control bytes from subprocess output."""
    return _CTRL_RE.sub("", text)


def _tests_under(scripts: Path) -> set[str]:
    """Return the sample-relative test files under one scripts tree."""
    return {
        "scripts/" + path.relative_to(scripts).as_posix()
        for path in (scripts / "tests").rglob("test_*.py")
    }


def _script_suites() -> tuple[str, ...]:
    """Derive the scripts-suite roster every sample receives from the source tree."""
    # Core ships most suites; the layout-bound pair ships from each stack
    # layer under the same path, so the intersection keeps only what every
    # sample receives. The floor keeps a shrunken source tree loud.
    core = _tests_under(HERE / "core" / "scripts")
    per_stack = [_tests_under(HERE / "stacks" / stack / "scripts") for stack in STACKS]
    suites = tuple(sorted(core | set.intersection(*per_stack)))
    if len(suites) < SCRIPT_SUITE_FLOOR:
        raise RuntimeError(
            f"derived scripts-suite roster holds {len(suites)} files under "
            f"core+stacks scripts/tests — below the {SCRIPT_SUITE_FLOOR}-suite "
            "floor; source tree broken?"
        )
    return suites


def _hook_suites() -> tuple[str, ...]:
    """Derive the hook-suite roster from the test siblings beside the shipped hooks."""
    suites = tuple(
        sorted(
            ".claude/hooks/" + path.name
            for path in (HERE / "core/.claude/hooks").glob("test_*.py")
        )
    )
    if len(suites) < HOOK_SUITE_FLOOR:
        raise RuntimeError(
            f"derived hook-suite roster holds {len(suites)} files under "
            f"core/.claude/hooks — below the {HOOK_SUITE_FLOOR}-suite floor; "
            "source tree broken?"
        )
    return suites


SAMPLE_SCRIPT_SUITES = _script_suites()
SAMPLE_HOOK_SUITES = _hook_suites()
SAMPLE_SUITES = SAMPLE_SCRIPT_SUITES + SAMPLE_HOOK_SUITES


def _run_suite(
    b: Battery, argv: tuple[str, ...], cwd: Path, label: str
) -> subprocess.CompletedProcess[str] | None:
    """Run one suite process, reporting a failure and returning None when it fails."""
    result = subprocess.run(
        list(argv), capture_output=True, text=True, cwd=cwd, check=False
    )
    if result.returncode != 0:
        b.fail(label)
        b.show_fail(result.stdout + result.stderr)
        return None
    return result


def _sample_suite_passes(b: Battery, stack: str) -> bool:
    """Run one sample's scripts discovery and hook suites, reporting each failure."""
    sample = ROOT / "samples" / stack
    passing = True
    for suite in SAMPLE_SUITES:
        if not (sample / suite).is_file():
            b.fail(
                f"samples/{stack}/{suite} missing — every sample ships all "
                f"{len(SAMPLE_SUITES)} suites"
            )
            passing = False
    # Discovery skips a non-package directory without error, so a run that
    # collects zero tests is a failure, not a pass.
    result = _run_suite(
        b, DISCOVER, sample / "scripts", f"samples/{stack}/scripts test discovery"
    )
    if result is None:
        passing = False
    elif not re.search(r"Ran [1-9][0-9]* tests?", result.stderr):
        b.fail(
            f"samples/{stack}/scripts test discovery ran zero tests — "
            "suites silently skipped?"
        )
        passing = False
    for suite in SAMPLE_HOOK_SUITES:
        if not (sample / suite).is_file():
            continue
        if (
            _run_suite(b, (sys.executable, suite), sample, f"samples/{stack}/{suite}")
            is None
        ):
            passing = False
    return passing


def check_sample_suites(b: Battery) -> None:
    """Run every shipped suite inside every sample."""
    b.note("sample test suites")
    if b.quick:
        b.skip("--quick: samples/ proven untouched by the guard")
        return
    passing = [_sample_suite_passes(b, stack) for stack in STACKS]
    if all(passing):
        b.record_pass("all suites pass")


def _build_file_references(build_file: Path) -> list[str]:
    """List the distinct .py paths a build file names."""
    return sorted(set(re.findall(r"[A-Za-z0-9_./-]+\.py", read_text(build_file))))


def _build_file_problems(b: Battery, stack: str) -> list[str]:
    """Check that one sample's build file exists and names only scripts that exist."""
    binding = BUILD_BINDINGS.get(stack)
    if binding is None:
        return [
            f"stack '{stack}' has no build-binding file declared — extend "
            "BUILD_BINDINGS in the sample build-file check"
        ]
    build_file = ROOT / "samples" / stack / binding
    if not build_file.is_file():
        return [
            f"samples/{stack}/{binding} missing — the stack's declared "
            "build-binding file"
        ]
    references = _build_file_references(build_file)
    if not references:
        b.record_pass(
            f"{stack}: 0 .py refs in {binding} — project builds carry no harness wiring"
        )
    return [
        f"samples/{stack}/{binding} references missing script '{reference}'"
        for reference in references
        if not (ROOT / "samples" / stack / reference).is_file()
    ]


def check_build_file_refs(b: Battery) -> None:
    """Refuse a dangling .py reference in any sample's build file."""
    b.note("sample build-file script refs")
    problems = [
        problem for stack in STACKS for problem in _build_file_problems(b, stack)
    ]
    b.report(problems, "build-file script paths resolve")


def check_deps_report(b: Battery) -> None:
    """Hold every tracked version pin consistent across its restatements."""
    b.note("pinned-version sync (deps-report, local half)")
    result = subprocess.run(
        [sys.executable, str(HERE / "deps-report.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        # deps-report echoes excerpts of agent-editable repo files.
        output = _printable(result.stdout + result.stderr).rstrip()
        b.fail(
            "deps-report found inconsistent version pins "
            f"(harness/deps-report.py)\n{output}"
        )
    else:
        b.record_pass("all pins consistent")


def check_sample_doctors(b: Battery) -> None:
    """Run the doctor inside every sample."""
    b.note("sample doctors")
    if b.quick:
        b.skip("--quick: samples/ proven untouched by the guard")
        return
    results = [
        _run_suite(
            b,
            (sys.executable, "scripts/doctor.py", "check"),
            ROOT / "samples" / stack,
            f"doctor failed in samples/{stack}:",
        )
        for stack in STACKS
    ]
    if all(result is not None for result in results):
        b.record_pass("green")


def _harness_unit_suites() -> list[Path]:
    """List the maintainer-side test files under harness/tests, the renderer self-test aside."""
    return [
        path
        for path in sorted(HERE.glob("tests/**/test_*.py"))
        if not any(
            part in ("core", "stacks", "init", "__pycache__")
            for part in path.relative_to(HERE).parts
        )
        and path.name != "test_render_agent_mirrors.py"
    ]


def check_unit_suites(b: Battery) -> None:
    """Run every maintainer-side unit suite."""
    b.note("harness unit suites")
    if b.quick:
        b.skip("--quick: harness/ proven untouched by the guard")
        return
    suites = _harness_unit_suites()
    if not suites:
        b.fail("no harness unit suites found — the step went vacuous")
        return
    results = [
        _run_suite(b, (sys.executable, str(suite)), ROOT, f"{rel(suite)} did not pass:")
        for suite in suites
    ]
    if all(result is not None for result in results):
        b.record_pass(f"{len(suites)} suites pass")


def _unshipped_modules(install_sh: Path) -> list[str]:
    """List the tool's modules its installer never names in a copy line."""
    # A filename surviving only in a comment, echo, or printf row is
    # reporting, not shipping.
    reporting = re.compile(r"^\s*(#|echo\b|printf\b)")
    code = "\n".join(
        line
        for line in install_sh.read_text().splitlines()
        if not reporting.match(line)
    )
    shipped = [
        *sorted(install_sh.parent.glob("*.py")),
        *sorted(install_sh.parent.glob("*.sh")),
    ]
    return [
        f"{rel(install_sh)} does not ship {module.name}"
        for module in shipped
        if not module.name.startswith("test_")
        and module.name != "install.sh"
        and module.name not in code
    ]


def check_tools_install_complete(b: Battery) -> None:
    """Hold every tool's installer to shipping each of its non-test modules."""
    b.note("tools install completeness")
    problems = [
        problem
        for install_sh in sorted((ROOT / "tools").glob("*/install.sh"))
        for problem in _unshipped_modules(install_sh)
    ]
    b.report(problems, "every shipped tools/*/*.py and *.sh is named in its install.sh")


def _toolchain_pin_problems(dockerfile_text: str, required_ruff: str) -> list[str]:
    """Check the dev image's Python toolchain pins and its confinement binaries."""
    pins = dict(re.findall(r"'(ruff|mypy|bandit)==([0-9][0-9.]*)'", dockerfile_text))
    problems = []
    if pins.get("ruff") != required_ruff:
        problems.append(
            f"Dockerfile pins ruff=={pins.get('ruff')} but pyproject "
            f"required-version is {required_ruff}"
        )
    problems.extend(
        f"Dockerfile does not ==-pin {tool}"
        for tool in PINNED_TOOLS
        if tool not in pins
    )
    # The tripwire guards the removed curl|bash installer idiom returning; it
    # is not a general remote-execution barrier.
    if re.search(
        r"\|\s*(sudo\s+|env\s+)?(/usr/bin/|/bin/)?(ba|da|z)?sh\b", dockerfile_text
    ):
        problems.append("Dockerfile pipes into a shell (curl|bash-style idiom)")
    problems.extend(
        f"Dockerfile does not install {binary} — a confinement control, not a dev tool"
        for binary in CONFINEMENT_BINARIES
        if not re.search(rf"^\s*(?!#).*\b{binary}\b", dockerfile_text, re.MULTILINE)
    )
    return problems


def _workflow_pin_problems(dockerfile_text: str) -> list[str]:
    """Hold the CI workflow's Python tool pins equal to the dev image's."""
    workflow = ROOT / ".github/workflows/checks.yml"
    if not workflow.is_file():
        return [f"{rel(workflow)} missing — the push-time gate has no workflow to pin"]
    image = dict(re.findall(r"'(ruff|mypy|bandit)==([0-9][0-9.]*)'", dockerfile_text))
    ci = dict(
        re.findall(
            r'"(ruff|mypy|bandit)==([0-9][0-9.]*)"',
            workflow.read_text(encoding="utf-8"),
        )
    )
    problems = [
        f"checks.yml does not ==-pin {tool}"
        for tool in ("ruff", *PINNED_TOOLS)
        if tool not in ci
    ]
    problems.extend(
        f"checks.yml pins {tool}=={ci[tool]} but the Dockerfile pins {image.get(tool)}"
        for tool in ci
        if tool in image and ci[tool] != image[tool]
    )
    return problems


def _egress_subset_problems() -> list[str]:
    """Check that the eval runner's --allow hosts sit inside the shipped egress policy."""
    run_eval = ROOT / "evals" / "run_eval.py"
    policy = ROOT / "tools/claude-dev/claude-dev.toml"
    if not (run_eval.exists() and policy.exists()):
        return []
    bench_hosts = set(
        re.findall(r'"--allow",\s*"([^"]+)"', run_eval.read_text(encoding="utf-8"))
    )
    try:
        allowed = set(
            tomllib.loads(policy.read_text(encoding="utf-8"))["egress"]["allow"]
        )
    except (tomllib.TOMLDecodeError, KeyError) as exc:
        return [f"claude-dev.toml lacks egress.allow ({exc!r})"]
    stray = sorted(bench_hosts - allowed)
    if stray and allowed:
        return [
            "eval runner --allow hosts missing from claude-dev.toml "
            f"egress.allow: {', '.join(stray)}"
        ]
    return []


def check_pod_toolchain_pins(b: Battery) -> None:
    """Hold the dev image's toolchain pins and confinement controls to their sources."""
    b.note("claude-dev toolchain and confinement pins")
    dockerfile = ROOT / "tools/claude-dev/Dockerfile"
    launcher = ROOT / "tools/claude-dev/claude-dev"
    pyproject = ROOT / "pyproject.toml"
    missing = [path for path in (dockerfile, launcher, pyproject) if not path.exists()]
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
    problems = _toolchain_pin_problems(dockerfile.read_text(encoding="utf-8"), required)
    problems.extend(_workflow_pin_problems(dockerfile.read_text(encoding="utf-8")))
    # Claude's in-process sandbox needs bubblewrap, which cannot create a user
    # namespace under Docker's default seccomp profile.
    if SANDBOX_OFF_OVERRIDE not in launcher.read_text(encoding="utf-8"):
        problems.append(
            "launcher lost the sandbox-off --settings injection (bubblewrap "
            "cannot create a user namespace under the default seccomp profile; "
            "see the Dockerfile)"
        )
    problems.extend(_egress_subset_problems())
    b.report(
        problems,
        f"ruff {required} matches pyproject; mypy/bandit pinned; checks.yml pins "
        "match the image; no pipe-to-shell idiom; squid/socat present; sandbox-off "
        "injection present; eval --allow hosts within the shipped egress policy",
    )


def _quick_skip_proof(b: Battery) -> str | None:
    """Return the joint clean-tree proof that lets the tools and eval suites skip, or None."""
    # The proof is joint: the eval suites are the only executable coverage of
    # tools/harness-stats/accounting.py, so a per-tree skip would leave a
    # tools/ edit untested.
    if not b.quick:
        return None
    if git_status("tools/", "evals/"):
        return None
    return "tools/ and evals/ clean vs HEAD (joint proof; full battery at push)"


def _dev_artifacts() -> list[str]:
    """List the gitignored dev-run artifacts, the one input class git status cannot see."""
    results = ROOT / "evals" / "results"
    candidates = [results / "TREND-dev.md", *sorted((results / "runs").glob("dev-*"))]
    return [path.relative_to(ROOT).as_posix() for path in candidates if path.exists()]


def _summarize_check(b: Battery) -> bool:
    """Re-render every derived eval view and report drift."""
    return (
        _run_suite(
            b,
            (sys.executable, "evals/summarize.py", "--check"),
            ROOT,
            "eval derived views drifted from the run folders:",
        )
        is not None
    )


def _discovered_suite_passes(b: Battery, cwd: Path, label: str) -> str | None:
    """Run unittest discovery from cwd, returning the test count or None on failure or vacuity."""
    result = _run_suite(b, DISCOVER, cwd, f"{label} did not pass:")
    if result is None:
        return None
    ran = re.search(r"Ran (\d+) tests?", result.stderr)
    if ran is None or int(ran.group(1)) == 0:
        b.fail(f"{label} collected zero tests — the suite went vacuous")
        return None
    return ran.group(1)


def check_tools_suites(b: Battery) -> None:
    """Run every toolbox's suite tree by discovery from its root."""
    b.note("tools unit suites")
    proof = _quick_skip_proof(b)
    if proof:
        b.skip(f"--quick: {proof}")
        return
    toolboxes = sorted(d.parent for d in (ROOT / "tools").glob("*/tests") if d.is_dir())
    if not toolboxes:
        b.fail("no tools unit suites found — the step went vacuous")
        return
    results = [
        _discovered_suite_passes(b, box, f"{rel(box)}/tests") for box in toolboxes
    ]
    if all(result is not None for result in results):
        b.record_pass(f"{len(toolboxes)} toolbox suites pass")


def _tracked_dev_runs() -> list[str]:
    """List the dev-run artifacts git tracks despite their local-only contract."""
    tracked = subprocess.run(
        ["git", "ls-files", "--", "evals/results"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    return [
        path
        for path in tracked.stdout.splitlines()
        if path.startswith("evals/results/runs/dev-")
        or path == "evals/results/TREND-dev.md"
    ]


def _eval_gates_pass(b: Battery) -> str | None:
    """Run the eval suites and the three gates over the committed run folders."""
    tests_dir = ROOT / "evals" / "tests"
    suites = (
        [
            path
            for path in sorted(tests_dir.rglob("test_*.py"))
            if "__pycache__" not in path.parts
        ]
        if tests_dir.is_dir()
        else []
    )
    if not suites:
        b.fail("no eval bench suites found — the step went vacuous")
        return None
    ran = _discovered_suite_passes(b, ROOT / "evals", "evals/tests")
    if ran is None or not _summarize_check(b):
        return None
    leak = _run_suite(
        b,
        (sys.executable, "evals/run_eval.py", "--leak-scan"),
        ROOT,
        "committed eval run folders carry host identity:",
    )
    if leak is None:
        return None
    dev_tracked = _tracked_dev_runs()
    if dev_tracked:
        b.fail("dev eval runs are local-only but git tracks:")
        b.show_fail("\n".join(dev_tracked))
        return None
    return (
        f"{len(suites)} suites pass ({ran} tests), derived views current,"
        " run folders leak-free, no dev run tracked"
    )


def check_eval_suites(b: Battery) -> None:
    """Run the eval bench suites and the derived-view, leak, and dev-run gates."""
    b.note("eval bench unit suites")
    proof = _quick_skip_proof(b)
    if proof:
        # The dev artifacts are git-invisible, so the derived-view gate still
        # runs over them before the rest skips.
        dev = _dev_artifacts()
        if not dev:
            b.skip(f"--quick: {proof}")
        elif _summarize_check(b):
            b.skip(
                f"--quick: {proof}; derived views validated first for the "
                f"git-invisible dev artifacts: {', '.join(dev)}"
            )
        return
    verdict = _eval_gates_pass(b)
    if verdict:
        b.record_pass(verdict)


def check_marketplace_faithfulness(b: Battery) -> None:
    """Re-render the marketplace and flag only what the render changes."""
    b.note("marketplace faithfulness")
    if b.quick:
        b.skip("--quick: harness/ and plugins/ proven untouched by the guard")
        return

    def on_result(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0:
            b.fail(
                f"harness/package-marketplace.py failed:\n{result.stdout}{result.stderr}"
            )

    render = RenderCheck(
        paths=("plugins/", ".claude-plugin/marketplace.json"),
        command=(sys.executable, str(HERE / "package-marketplace.py")),
        changed_message=(
            "re-render changed the marketplace — a /harness edit was not repackaged:"
        ),
        fix_message=(
            "Fix: run harness/package-marketplace.py and commit the result "
            "with the /harness edit."
        ),
    )
    if check_render_faithful(b, render, on_result):
        b.record_pass("marketplace == package-marketplace(/harness)")
