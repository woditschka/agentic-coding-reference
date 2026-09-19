"""changeset — the change set under review: what is judged, independent of grading.

The change set — the working-tree delta a reviewer and the grader both judge —
is defined here, not inside the grader that was once its only caller. The
`changeset.py` launcher and the reviewer roster resolve their view through this
package; the grading engine composes it too (ADR 2026-07-17 runtime-package-layout).
The layer map is the tree — config is the exclude-filter ACL, git_facts the git
gateway (canonical env, ref/tree hardening, the worktree snapshot), emit the
base/head resolution and the emit verb.

Like grading/, this package declares no re-export surface: its consumers — the
`changeset.py` launcher, the grading package, and the test suites — all import
submodule-form (`from changeset.git_facts import …`). Each module's public names
are its API; underscore names stay module-internal.
"""
