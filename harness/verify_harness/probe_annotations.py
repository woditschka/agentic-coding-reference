"""Import the shipped runtime and evaluate every annotation it declares.

Usage: python3 -I -B probe_annotations.py SCRIPTS_ROOT FILE...

A signature annotation is evaluated when the function is defined on every
Python before 3.14, and only on demand from 3.14 on. A name that exists in
the type stubs alone, such as a subscripted argparse action, therefore
passes a 3.14 developer's battery and raises on a consumer's 3.12 at
import. Touching every annotation here forces the evaluation on the
interpreter at hand. Prints one line per failure and exits 1 on any.
Stdlib only.
"""

import importlib
import importlib.util
import inspect
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType


def load(scripts_root: Path, path: Path, index: int) -> ModuleType:
    """Import a package module by its dotted name and a loose script by path."""
    if (path.parent / "__init__.py").is_file():
        dotted = ".".join(path.relative_to(scripts_root).with_suffix("").parts)
        return importlib.import_module(dotted)
    spec = importlib.util.spec_from_file_location(f"annotation_probe_{index}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(module: ModuleType) -> int:
    """Force every annotation the module declares and return how many objects carried one."""
    count = 0
    for _name, obj in inspect.getmembers(module):
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        if inspect.isclass(obj):
            count += _evaluate_class(obj)
        elif inspect.isroutine(obj):
            count += _evaluate_routine(obj)
    return count


def _evaluate_class(cls: type) -> int:
    count = 1 if inspect.get_annotations(cls) is not None else 0
    for _name, member in inspect.getmembers(cls):
        if (
            inspect.isroutine(member)
            and getattr(member, "__module__", None) == cls.__module__
        ):
            count += _evaluate_routine(member)
    return count


def _evaluate_routine(routine: Callable[..., object]) -> int:
    inspect.get_annotations(inspect.unwrap(routine))
    return 1


def main(argv: list[str]) -> int:
    """Probe every file; print each failure and exit 1 when any annotation fails to evaluate."""
    scripts_root = Path(argv[1]).resolve()
    sys.path.insert(0, str(scripts_root))
    failures = 0
    evaluated = 0
    for index, argument in enumerate(argv[2:]):
        path = Path(argument).resolve()
        try:
            evaluated += evaluate(load(scripts_root, path, index))
        except Exception as exc:  # noqa: BLE001 — every failure is reported, never hidden
            failures += 1
            print(f"{path.relative_to(scripts_root)}: {type(exc).__name__}: {exc}")
    print(f"{evaluated} annotated objects across {len(argv) - 2} modules")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
