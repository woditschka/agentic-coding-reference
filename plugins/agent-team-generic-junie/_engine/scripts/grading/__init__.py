"""grading — the change-grading engine's domain package.

The entry point grading.py composes these modules over the change-set layer
(the changeset package) (ADR 2026-07-17 runtime-package-layout). The layer map
is the tree — config is the grading layout-config ACL, features the feature
model, handoff_facts the handoff-log gateway, planner the pure risk ladder. The
git gateway and the change set's definition live in the changeset package,
composed here — the feature model reads every diff through changeset.git_facts.

Unlike handoff/, this package declares no re-export surface: it has no
cross-context consumer — only the entry launcher and the test suites compose
it, and both import submodule-form (`from grading.planner import …`). Each
module's public names are its API; underscore names stay module-internal.
"""
