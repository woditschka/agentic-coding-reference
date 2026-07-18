"""Shared path-loader for the harness test suites.

The producer-side toolbox is not a package (see ADR
2026-07-18-producer-side-tests-subdir): source scripts keep their
hyphenated CLI names and are loaded by path. This module centralizes
that path-load. ``ROOT`` is the toolbox root — the ``harness/``
directory containing ``helpers.py`` — resolved by walking up from this
file, so it works at any test depth.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "helpers.py").is_file():
            return parent
    raise RuntimeError("toolbox root (dir containing helpers.py) not found")


ROOT: Path = _find_root()


def load(name: str, relpath: str) -> ModuleType:
    """Load ``ROOT / relpath`` as module ``name`` and return it."""
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
