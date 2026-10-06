"""A shared fixture for the suites that drive the shipped command scripts."""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from agent_dev_profiles import PROFILES

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
LAUNCH_TIMEOUT_S = 60
COMMANDS = tuple(profile.command for profile in PROFILES.values())
# Every code file an install places beside the engine.
ENGINE_FILES = (
    "agent-dev",
    "agent_dev.py",
    "agent_dev_config.py",
    "agent_dev_profiles.py",
    "open_weight_preflight.py",
    "claude_dev_scrub.py",
    "ide_preflight.py",
    "Dockerfile",
)


def home_var(command: str) -> str:
    """Return the data-dir variable a command reads: the upper-cased command plus _HOME."""
    return command.upper().replace("-", "_") + "_HOME"


class CommandFixture(unittest.TestCase):
    """A home, a project and one data dir per tool, each outside the others."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.project = self.tmp / "project"
        self.bin = self.tmp / "bin"
        self.data = {command: self.tmp / f"data-{command}" for command in COMMANDS}
        for d in (self.home, self.project, self.bin, *self.data.values()):
            d.mkdir(parents=True)

    def env(self, **overrides: str) -> dict[str, str]:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "TMPDIR": str(self.tmp),
        }
        env.update({home_var(c): str(d) for c, d in self.data.items()})
        env.update(overrides)
        return env

    def run_script(
        self,
        script: pathlib.Path,
        *args: str,
        cwd: pathlib.Path | None = None,
        env: dict[str, str] | None = None,
    ):
        return subprocess.run(
            [str(script), *args],
            cwd=str(cwd or self.project),
            env=env if env is not None else self.env(),
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
        )

    def access(self, command: str, *flags: str, **kwargs):
        """Run a command's `access` verb from the source checkout."""
        return self.run_script(TOOLS_DIR / command, "access", *flags, **kwargs)

    def assert_refused(self, result, *needles: str):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        for needle in needles:
            self.assertIn(needle, result.stderr)

    def install(self, command: str) -> pathlib.Path:
        """Lay a command out as install.sh does: the script in bin, the code in its data dir."""
        for name in ENGINE_FILES:
            shutil.copy(TOOLS_DIR / name, self.data[command] / name)
        shutil.copy(
            TOOLS_DIR / f"{command}.toml", self.data[command] / f"{command}.toml"
        )
        shutil.copy(TOOLS_DIR / command, self.bin / command)
        return self.bin / command

    def at_default_homes(self) -> None:
        """Move each tool's data dir to ~/.config/<command>, where an unrelocated one lives."""
        for command in list(self.data):
            target = self.home / ".config" / command
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(self.data[command]), str(target))
            self.data[command] = target
