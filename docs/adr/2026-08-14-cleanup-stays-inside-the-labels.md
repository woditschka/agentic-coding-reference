# Cleanup Removes Only What the Tool Labeled; Engine-Wide Is a Separate Consent

**Status:** Accepted

## Context

Every `build`/`update` retags `claude-dev:latest` and strands the predecessor image — an `update --all` predecessor is a multi-GB object. A SIGKILLed launcher leaves its session container and networks behind; each launch reaps them, but only a launch does. On macOS the engine's disk is a fixed-size VM image, and a full VM fails sessions with `ENOSPC`. Docker's own `prune` family cannot cover the gap: it never removes a *running* container, and an orphaned session's placeholder keeps running until something with the liveness picture kills it.

Two removal problems, two blast radii: the tool's own leftovers (safe to remove mechanically), and everything else on the engine (removable only on the operator's explicit word).

## Options Considered

1. **No verb — point the operator at `docker system prune`** — rejected: prune cannot reap a running orphaned session, and the unscoped command destroys unrelated projects' state to fix a claude-dev leak.
2. **Track the predecessor image by ID around each build** — rejected: it adds per-build state the launcher must persist and reconcile, where a label rides on the object itself and survives crashes between build and record.
3. **Name the verb `prune` for docker familiarity** — rejected: docker's prune contract never touches anything running or in use, while this verb force-removes running orphaned sessions, and `--all` would collide with `prune -a`'s narrower meaning (include non-dangling images, nothing more). Importing the name imports a safety promise the verb deliberately breaks; `cleanup` names the broader action honestly.
4. **Two attribution labels, a scoped verb, and a filtered engine-wide escalation** (chosen).

## Decision

**`claude-dev cleanup` removes exactly what the tool's two labels attribute to it, and nothing else.** Session containers and networks carry `claude-dev.launcher=<install-id>:<pid>`; the reaper — the same one every launch runs — force-removes objects whose recorded launcher PID is dead, judged only within the install that issued it. Images carry `claude-dev.image=1` from the Dockerfile's last instruction; the verb prunes dangling images under that label, and each successful build prunes its own superseded predecessors the same way.

**`cleanup --all` crosses the lane on the operator's word:** after the scoped pass it runs `docker system prune -a --volumes` with a `label!=claude-dev.image` filter, so the current image survives and the next launch pays no rebuild. The launcher refuses `--all` while `claude-dev:latest` predates the label — an unlabeled image is exactly what the filter cannot spare, and the refusal message names the fix (`claude-dev update` first).

The label sits after every build layer, so introducing it invalidated no cache. Stub-docker tests pin the whole engine surface: reap by label and liveness, no prune outside the label, the exact `--all` argv, and the unlabeled-image refusal.

## Consequences

Positive:

- The engine stays leftover-free within the tool's lane without a launch, and full-disk recovery needs no rebuild afterward.
- A running orphaned session — invisible to every docker prune — is removed by the only party holding the liveness picture.
- The migration window is fail-closed: `--all` refuses rather than deleting the tool's own pre-label image.

Negative:

- Containers inherit the image's label, so `--all` spares claude-dev's own stopped containers; another install's crash leftovers wait for that install's reap.
- `--volumes` removes anonymous unused volumes on Engine 23+, named ones too on older engines — the README states the split because the blast radius is the point.
- The build cache is not spared: the first `update` after `--all` rebuilds every layer once. Launches pay nothing.
- A pre-label predecessor image is removable only by `--all` or a manual `docker image prune` — the scoped verb's filter cannot see it.
- A synced or restored data dir clones the install id across hosts, letting one host's reaper judge another's PIDs; deleting `host-id` on the clone restores the boundary.

## References

- [Egress Is Enforced by an External Proxy, Not by the Workload](2026-07-29-proxy-enforced-egress.md) — the per-session networks this verb's reaper owns by label.
- [`tools/claude-dev/README.md`](../../tools/claude-dev/README.md) — the operator-facing statement of the verb's scope and the `--all` consent line.
