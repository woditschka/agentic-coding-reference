# Native Sandbox: OS-Level Confinement on the Bare Host

Claude Code ships an OS-level sandbox (Seatbelt on macOS, bubblewrap on Linux) that confines the Bash commands a session runs. Configured strictly, it is the container-free counterpart to [`tools/claude-dev/`](../tools/claude-dev/README.md): reduced approvals on the bare host, with OS-enforced write containment, credential denial, and a network allowlist for sandboxed commands. This document holds the configuration in use here, states what each layer enforces, and compares the boundary with claude-dev's. It is stated for macOS.

Sources, read 2026-07-31: the Claude Code [sandboxing](https://code.claude.com/docs/en/sandboxing), [settings](https://code.claude.com/docs/en/settings), [permissions](https://code.claude.com/docs/en/permissions), and [permission modes](https://code.claude.com/docs/en/permission-modes) documentation. Version floors, taken from the documentation: `sandbox.network.strictAllowlist` needs Claude Code 2.1.219+ and `sandbox.credentials` 2.1.187+. Further floors appear with the keys they govern. `sandbox.network.allowLocalBinding` has no published floor; it is present and identical in builds 2.1.218 through 2.1.220.

## The Configuration

The file belongs at `~/.claude/settings.json` (user scope). Two keys silently degrade elsewhere. `defaultMode: "auto"` is ignored in project and local settings (2.1.142+), so a repo cannot grant itself auto mode. `strictAllowlist` is honored only from user, managed, or CLI settings. A repository copy has no effect.

The one `env` key, `CLAUDE_CODE_AUTO_CONNECT_IDE: false`, stops the session from auto-connecting to a running IDE.

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
      "Edit(~/.claude/**)"
    ]
  },
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "strictAllowlist": true,
      "allowLocalBinding": true,
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
        "plugins-artifacts.gradle.org",
        "release-assets.githubusercontent.com",
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
| Remote network allowlist for sandboxed commands — localhost exempt, see below | A proxy Claude Code runs outside the sandbox; `strictAllowlist` denies unlisted hosts without prompting | Connection refused |
| Local socket bind, inbound, and localhost outbound | Seatbelt; the three are granted together by `allowLocalBinding` | Allowed here; without the key, `bind` and any non-proxy localhost connect are denied |
| In-process tool network reach, such as WebFetch | Claude Code's permission layer; `strictAllowlist` does not gate it | Tool call refused |
| `permissions.deny` rules | Claude Code's permission layer, prefix-matched | Tool call refused |
| Sandboxed-command approval | `sandbox.autoAllowBashIfSandboxed`, default true, honored at project scope | Approved without a prompt |
| Auto mode classifier | The session's own process | Prompt, or approval |

Three of the strict choices carry the posture. `failIfUnavailable: true` refuses to start rather than run unconfined. `allowUnsandboxedCommands: false` removes the per-command sandbox escape. `strictAllowlist: true` turns the first unlisted domain from a prompt into a denial, so a low-approval run fails closed instead of waiting. It also means the allowlist must carry every registry a build touches, including redirect targets. The Gradle wrapper's download 307-redirects from `services.gradle.org` through `github.com` to `release-assets.githubusercontent.com`, and the plugin portal 303s jars to `plugins-artifacts.gradle.org`. A missing entry surfaces as a failed download, never as an open connection. The enforcement table above splits the scopes: sandboxed commands meet the allowlist, in-process tools meet the `permissions` layer.

Two project-scope settings outside this file still shape the posture. `sandbox.autoAllowBashIfSandboxed` defaults to true, so a sandboxed command is approved without a prompt; setting it false in project settings restores prompting. Project `permissions.allow` entries such as `WebFetch(domain:…)` widen the in-process reach.

One sandbox default is relaxed deliberately, because serving a local port is ordinary work. `allowLocalBinding: true` permits it; the default refuses with `EPERM`, so every dev server and every test that listens fails at `bind`. This repository's own `tools/claude-dev` suite fails 34 of 148 tests without it, each at `bind(("127.0.0.1", 0))`. The key is absent from the Claude Code sandboxing and settings pages. It is documented in the [`@anthropic-ai/sandbox-runtime`](https://github.com/anthropic-experimental/sandbox-runtime) package the sandbox derives from.

The key grants three Seatbelt rules together, not one: `network-bind` and `network-inbound` on `(local ip "*:*")`, and `network-outbound` to `(remote ip "localhost:*")`. Two consequences follow, and neither is separable: the rules are emitted as a unit. The bind is not loopback-scoped: a sandboxed command can bind a routable interface and accept connections from any source. And localhost egress leaves the proxy. With the key off, the only permitted localhost outbound is the proxy's own ports, and that funnel is what keeps remote traffic on the allowlist's path. With it on, a host listener that forwards (an `ssh -L` tunnel, a local proxy, an MCP server) is an egress path the allowlist never sees. Remote egress from sandboxed commands is unchanged: a direct connection is denied by the profile's `deny default`, and proxy-routed traffic still meets the allowlist. This residual belongs to the bare-host posture alone, and is recorded in [the local-binding ADR](adr/2026-07-31-local-binding-residual.md).

Two layers are best-effort and counted as such. `Bash(git push --force *)` is a prefix match: `git push origin --force main` starts differently and passes, as does the same push through a script. The deny list documents intent and catches the common spelling; the load-bearing control is that no push credential is readable. The classifier is behavioral: it runs in the session's process and reads the same context a hostile repo poisons, so every OS-enforced layer above is sized to hold without it. The `Read` and `Edit` deny rules exist because the sandbox does not govern the built-in file tools. `Edit(path)` is the rule that covers every file-editing tool; a `Write(path)` rule validates but is never consulted, and Claude Code warns about it at startup. Without these rules, the classifier is the only thing between the session and `~/.claude/settings.json`, this same policy file.

## The Two Boundaries Compared

The structural difference is enforcement placement. [ADR 2026-07-29](adr/2026-07-29-proxy-enforced-egress.md) put claude-dev's enforcement outside the workload; here Seatbelt policy and proxy both belong to the Claude Code process being confined. Each posture's properties follow from that placement.

- **Home reads.** The sandbox denies enumerated paths and reads everything else; claude-dev's `~/.claude` and `HOME` are default-deny with enumerated crossings. An unenumerated token (a `~/.config/<tool>` store, an exported key in a dotfile) is readable here and absent there.
- **Loopback.** `allowLocalBinding` lets a sandboxed command reach any host listener without the proxy, because the boundary and the listener share one machine. Claude-dev runs the in-process sandbox off inside a container whose only route out is the proxy, so its loopback stays inside the boundary and this residual does not arise.
- **Host config.** Here `~/.claude` is the live host config: the sandbox blocks Bash writes to it, and one deny rule covers the file tools. Both are policy in the same file they protect. Claude-dev shadows it, so even a permission-skipped session cannot plant a hook or flip trust for later host runs.
- **Escape surface.** Claude-dev's session has no route out except a proxy in another container; a sandbox escape here is code on the host as the operator.
- **Filesystem lifetime.** Claude-dev's container is deleted after the run; this filesystem is the host.
- **Audit record.** Squid records every verdict outside claude-dev's session, beyond the session's reach; sandbox denials surface only in-session.
- **Credentials.** Claude-dev logs in once inside and forwards no token. Here the session runs with host credentials: the file denials are subtractive, and `github.com` on the allowlist is a write channel for whatever survives them. Subprocesses inherit that environment, Anthropic and cloud-provider variables included. `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` strips them before each spawn, but forces permission mode back to `default`, so it and `defaultMode: "auto"` cannot both take effect. This configuration takes auto mode, so the scrub stays off and subprocesses inherit the variables. Trading auto mode for an explicit allow roster is the other branch, and it keeps the scrub.

Shared residuals, in both designs: domain fronting through an allowed CDN name (neither terminates TLS), DNS as a side channel, and the project directory as a writable prompt-injection surface.

## The Split in Use

Here the native sandbox runs trusted repos on macOS machines without a container engine: one settings file, no image, no launch latency, OS-enforced write and read containment. Claude-dev runs untrusted or semi-trusted repos and unattended sessions: the boundary is outside the workload, the host config is unreachable, and the egress log survives the session. Work governed by managed settings stays on the host either way. Claude-dev discloses the same rule.
