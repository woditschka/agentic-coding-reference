# Native Sandbox: OS-Level Confinement on the Bare Host

Claude Code ships an OS-level sandbox — Seatbelt on macOS, bubblewrap on Linux — that confines the Bash commands a session runs. Configured strictly, it is the container-free counterpart to [`tools/claude-dev/`](../tools/claude-dev/README.md): reduced approvals on the bare host, with OS-enforced write containment, credential denial, and a network allowlist. This document holds the configuration in use here, states what each layer enforces, and compares the boundary with claude-dev's.

Sources, verified 2026-07-31: the Claude Code [sandboxing](https://code.claude.com/docs/en/sandboxing), [settings](https://code.claude.com/docs/en/settings), [permissions](https://code.claude.com/docs/en/permissions), and [permission modes](https://code.claude.com/docs/en/permission-modes) documentation. `sandbox.network.strictAllowlist` needs Claude Code 2.1.219+ and `sandbox.credentials` 2.1.187+.

## The Configuration

The file belongs at `~/.claude/settings.json` (user scope). Two keys silently degrade elsewhere. `defaultMode: "auto"` is ignored in project and local settings (2.1.142+), so a repo cannot grant itself auto mode. `strictAllowlist` is honored only from user, managed, or CLI settings — a repository copy has no effect.

```json
{
  "permissions": {
    "defaultMode": "auto",
    "deny": [
      "Bash(git push --force *)",
      "Bash(git push -f *)",
      "Bash(gh pr merge *)",
      "Bash(gh release *)",
      "Bash(npm publish *)",
      "Bash(pnpm publish *)",
      "Bash(yarn npm publish *)",
      "Bash(docker *)",
      "Bash(kubectl *)",
      "Bash(terraform apply *)",
      "Bash(terraform destroy *)",
      "Read(~/.ssh/**)",
      "Read(~/.aws/**)",
      "Read(~/.config/gcloud/**)",
      "Read(~/.azure/**)",
      "Read(~/.kube/**)",
      "Read(~/.docker/**)",
      "Read(~/.config/gh/**)",
      "Read(~/.netrc)",
      "Read(~/.npmrc)",
      "Read(~/.gnupg/**)",
      "Write(~/.claude/**)",
      "Edit(~/.claude/**)"
    ]
  },
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "strictAllowlist": true,
      "allowedDomains": [
        "api.anthropic.com",
        "github.com",
        "raw.githubusercontent.com",
        "registry.npmjs.org",
        "pypi.org",
        "files.pythonhosted.org",
        "crates.io",
        "static.crates.io",
        "proxy.golang.org",
        "sum.golang.org",
        "repo.maven.apache.org",
        "services.gradle.org",
        "plugins.gradle.org",
        "rubygems.org"
      ]
    },
    "filesystem": {
      "denyRead": [
        "~/.config/gh",
        "~/.netrc",
        "~/.npmrc",
        "~/.gnupg",
        "~/.zshrc",
        "~/.zprofile",
        "~/.bashrc",
        "~/.bash_profile",
        "~/.profile"
      ],
      "allowWrite": [
        "~/.npm",
        "~/.gradle",
        "~/.m2/repository",
        "~/go/pkg/mod",
        "~/.cache",
        "~/Library/Caches"
      ]
    },
    "credentials": {
      "files": [
        { "path": "~/.ssh", "mode": "deny" },
        { "path": "~/.aws", "mode": "deny" },
        { "path": "~/.config/gcloud", "mode": "deny" },
        { "path": "~/.azure", "mode": "deny" },
        { "path": "~/.kube", "mode": "deny" },
        { "path": "~/.docker", "mode": "deny" }
      ]
    }
  },
  "env": {
    "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1",
    "CLAUDE_CODE_AUTO_CONNECT_IDE": "false"
  }
}
```

## What Each Layer Enforces

The layers differ in enforcement point, and the enforcement point decides what a hostile session can do about them.

| Layer | Enforcement point | Failure direction |
|---|---|---|
| Write containment: project directory plus `allowWrite` entries | Seatbelt, per sandboxed command, inherited by children | Denied write, command fails |
| Credential and `denyRead` file denial | Seatbelt; symlinks resolve to the denied target (2.1.210+) | Denied read |
| Network allowlist | A proxy Claude Code runs outside the sandbox; `strictAllowlist` denies unlisted hosts without prompting | Connection refused |
| Subprocess env scrub | Claude Code, before each spawn; strips Anthropic and cloud-provider credentials | Variable absent |
| `permissions.deny` rules | Claude Code's permission layer, prefix-matched | Tool call refused |
| Auto mode classifier | The session's own process | Prompt, or approval |

Three of the strict choices carry the posture. `failIfUnavailable: true` refuses to start rather than run unconfined. `allowUnsandboxedCommands: false` removes the per-command sandbox escape. `strictAllowlist: true` turns the first unlisted domain from a prompt into a denial, so a low-approval run fails closed instead of waiting. It also means the allowlist must carry every registry a build touches. The Gradle wrapper alone needs `services.gradle.org`; a missing entry surfaces as a failed download, never as an open connection.

Two layers are best-effort and counted as such. `Bash(git push --force *)` is a prefix match: `git push origin --force main` starts differently and passes, as does the same push through a script. The deny list documents intent and catches the common spelling; the load-bearing control is that no push credential is readable. The classifier is behavioral: it runs in the session's process and reads the same context a hostile repo poisons, so every OS-enforced layer above is sized to hold without it. The `Read`/`Write`/`Edit` deny rules exist because the sandbox does not govern the built-in file tools. Without them, the classifier is the only thing between the session and `~/.claude/settings.json` — this same policy file.

## The Two Boundaries Compared

The structural difference is enforcement placement. [ADR 2026-07-29](adr/2026-07-29-proxy-enforced-egress.md) put claude-dev's enforcement outside the workload; here Seatbelt policy and proxy both belong to the Claude Code process being confined. Each posture's properties follow from that placement.

- **Home reads.** The sandbox denies enumerated paths and reads everything else; claude-dev's `~/.claude` and `HOME` are default-deny with enumerated crossings. An unenumerated token — a `~/.config/<tool>` store, an exported key in a dotfile — is readable here and absent there.
- **Host config.** Here `~/.claude` is the live host config: the sandbox blocks Bash writes to it, and two deny rules cover the file tools — both policy in the same file they protect. Claude-dev shadows it, so even a permission-skipped session cannot plant a hook or flip trust for later host runs.
- **Escape surface.** Claude-dev's session has no route out except a proxy in another container; a sandbox escape here is code on the host as the operator.
- **Filesystem lifetime.** Claude-dev's container is deleted after the run; this filesystem is the host.
- **Audit record.** Squid records every verdict outside claude-dev's session, beyond the session's reach; sandbox denials surface only in-session.
- **Credentials.** Claude-dev logs in once inside and forwards no token. Here the session runs with host credentials: the env scrub and file denials are subtractive, and `github.com` on the allowlist is a write channel for whatever survives them.

Shared residuals, in both designs: domain fronting through an allowed CDN name (neither terminates TLS), DNS as a side channel, and the project directory as a writable prompt-injection surface.

## The Split in Use

Here the native sandbox runs trusted repos on machines without a container engine: one settings file, no image, no launch latency, OS-enforced write and read containment. Claude-dev runs untrusted or semi-trusted repos and unattended sessions: the boundary is outside the workload, the host config is unreachable, and the egress log survives the session. Work governed by managed settings stays on the host either way — claude-dev discloses the same rule.
