#!/usr/bin/env python3
"""Render the route-rule inventory from the routing source.

Usage: harness/render-route-rules.py [--check]

Walks the decision constructors in
harness/core/scripts/handoff/routing.py (_dispatch, _bounce, _blocked,
_escalate) by AST and writes the complete rule inventory to
harness/core/.claude/skills/handoff-routing/route-rules.md: every rule
`route` can print, with its decision kind and dispatch target. --check
compares instead of writing and exits 1 on drift (battery step 3j). A
non-literal rule argument is an error — the inventory must be total, so
the constructors accept only literal rule names.

The default mode writes only when the content changed. Stdlib only.
Tested by tests/test_render_route_rules.py.
"""

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402

ROUTING = HERE / "core" / "scripts" / "handoff" / "routing.py"
RECORDS = HERE / "core" / "scripts" / "handoff" / "records.py"
OUTPUT = HERE / "core" / ".claude" / "skills" / "handoff-routing" / "route-rules.md"

USAGE = "usage: harness/render-route-rules.py [--check]"

# Constructor name -> (rule-argument index, decision-kind label).
CONSTRUCTORS: dict[str, tuple[int, str]] = {
    "_dispatch": (1, "dispatch"),
    "_bounce": (1, "dispatch (bounce)"),
    "_blocked": (0, "blocked"),
    "_escalate": (0, "escalate"),
}

HEADER = """\
# Route Rules — the generated decision inventory

<!-- GENERATED from scripts/handoff/routing.py — do not edit by hand;
     regenerated and drift-gated upstream in the reference. -->

Every rule `scripts/handoff.py route` can print, with its decision kind and
dispatch target. The decision JSON names the matched rule; this inventory is
the lookup. The narrative contract is `route-spec.md`; the judgment-facing
summaries are `SKILL.md`'s. A target of *(computed)* is resolved from the log
at decision time (the roster, the requester, the recorded upstream).

| Rule | Decision | Dispatches |
|---|---|---|
"""


def module_constants(source: str) -> dict[str, str]:
    """Module-level ``NAME = "literal"`` string assignments in one source."""
    constants: dict[str, str] = {}
    for node in ast.parse(source).body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target = node.targets[0]
        value = node.value
        if (
            isinstance(target, ast.Name)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        ):
            constants[target.id] = value.value
    return constants


def _resolve(node: ast.expr, constants: dict[str, str]) -> str | None:
    """One element of a dispatch target as a string, or None if dynamic."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    return None


def _target(call: ast.Call, name: str, constants: dict[str, str]) -> str:
    """The dispatch target of one constructor call, or the computed marker."""
    if name in ("_blocked", "_escalate"):
        return "—"
    if not call.args:
        return "(computed)"
    first = call.args[0]
    if isinstance(first, (ast.List, ast.Tuple)):
        names = [_resolve(element, constants) for element in first.elts]
        if names and all(name is not None for name in names):
            return ", ".join(f"`{name}`" for name in names)
        return "(computed)"
    single = _resolve(first, constants)
    return f"`{single}`" if single is not None else "(computed)"


def _rule(call: ast.Call, index: int) -> ast.expr | None:
    """The rule argument of one constructor call, positional or keyword."""
    if len(call.args) > index:
        return call.args[index]
    for keyword in call.keywords:
        if keyword.arg == "rule":
            return keyword.value
    return None


def extract(source: str, constants: dict[str, str]) -> dict[str, set[tuple[str, str]]]:
    """Map each rule name to its set of (decision kind, dispatch target).

    Raises ValueError naming every constructor call whose rule argument is
    not a string literal — a partial inventory must never render.
    """
    tree = ast.parse(source)
    rules: dict[str, set[tuple[str, str]]] = {}
    errors: list[str] = []
    # A constructor's own body may forward to another constructor (_bounce
    # delegates to _dispatch); those internal calls carry parameters, not
    # rule literals, so calls inside the constructor definitions are skipped.
    internal: list[tuple[int, int]] = [
        (node.lineno, node.end_lineno or node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in CONSTRUCTORS
    ]
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if any(start <= node.lineno <= end for start, end in internal):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id in CONSTRUCTORS):
            continue
        index, kind = CONSTRUCTORS[func.id]
        rule = _rule(node, index)
        if not (isinstance(rule, ast.Constant) and isinstance(rule.value, str)):
            errors.append(f"line {node.lineno}: {func.id} rule is not a literal")
            continue
        rules.setdefault(rule.value, set()).add(
            (kind, _target(node, func.id, constants))
        )
    if errors:
        raise ValueError("non-literal rule arguments:\n" + "\n".join(errors))
    return rules


def render(rules: dict[str, set[tuple[str, str]]]) -> str:
    """The complete inventory as one markdown document."""
    lines = [HEADER]
    for rule in sorted(rules):
        variants = sorted(rules[rule])
        kinds = " · ".join(kind for kind, _ in variants)
        targets = " · ".join(target for _, target in variants)
        lines.append(f"| `{rule}` | {kinds} | {targets} |\n")
    lines.append(f"\n{len(rules)} rules.\n")
    return "".join(lines)


def main(argv: list[str]) -> int:
    check = False
    if len(argv) == 2 and argv[1] == "--check":
        check = True
    elif len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        source = ROUTING.read_text(encoding="utf-8")
        records_source = RECORDS.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read the routing sources: {exc}", file=sys.stderr)
        return 1
    try:
        constants = module_constants(records_source) | module_constants(source)
        content = render(extract(source, constants))
    except (SyntaxError, ValueError) as exc:
        print(f"cannot extract rules: {exc}", file=sys.stderr)
        return 1
    committed = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    shown = (
        str(OUTPUT.relative_to(HERE.parent))
        if OUTPUT.is_relative_to(HERE.parent)
        else str(OUTPUT)
    )
    if check:
        if committed != content:
            print(
                f"{shown} drifted from the routing source — regenerate with "
                "harness/render-route-rules.py",
                file=sys.stderr,
            )
            return 1
        return 0
    if committed != content:
        with write_guard.write_scope(OUTPUT.parent):
            write_guard.write_text(OUTPUT, content)
        print(f"wrote {shown}")
    else:
        print(f"{shown} already current")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
