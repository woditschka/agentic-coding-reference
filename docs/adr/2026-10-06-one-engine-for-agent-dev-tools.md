# One Confinement Engine Hosts Every Agent Tool

**Status:** Accepted

## Context

claude-dev confines Claude Code in a container whose only route out is a squid proxy ([ADR 2026-07-29](2026-07-29-proxy-enforced-egress.md)). The launcher was one 853-line bash script and one 679-line config module. About 90 launcher lines named Claude Code: the `~/.claude` mounts, the `--settings` flag, the credential store, the permission mode and the `/v1/messages` path. The remaining lines were the confinement: networks, proxy, hardening, `access` and `cleanup`.

OpenCode is the second tool to run this way, and the operator expects others. [`docs/open-weight-models.md`](../open-weight-models.md) already maps the harness's model pins onto OpenCode, and the cross-tool strategy names it as a supported tool. The question was how a second tool reuses the confinement.

A measurement run on 2026-10-06 settled what OpenCode needs. It used opencode-ai 1.18.34 in throwaway `node:24-slim` containers on an internal Docker network, with a stub peer that logged each request:

- The inline `OPENCODE_CONFIG_CONTENT` outranks the project's `opencode.json`. A project entry that pointed the provider at another base URL and model id lost on both.
- Overriding the built-in `openrouter` provider with `@ai-sdk/openai-compatible` and a `baseURL` works. The peer received the mapped `id` in place of the pinned name.
- The title request names a separate small model. Unpinned, it reached the peer as `google/gemini-3.8-flash`, a name no map covers. Pinned through `small_model`, it carried the mapped name.
- With `HTTP_PROXY` set, OpenCode sent the plain-HTTP model call to the forward proxy, which refuses plaintext. The run ended with `Forbidden`. With `HTTPS_PROXY` alone, the catalog fetch went through `CONNECT` and the model call reached the peer directly.
- OpenCode read the global `~/.claude/CLAUDE.md`, a global skill under `~/.claude/skills` and the project `CLAUDE.md`. All three appeared in the system prompt.
- It fetches `https://models.opencode.ai/api.json` at startup and survives a refusal. A background `npm` install of `@opencode-ai/plugin` into `~/.config/opencode` also fails harmlessly. A seeded copy of that package suppressed the fetch.
- A read-only config directory fails: OpenCode writes `.gitignore` into it at startup.
- Its state lives in `~/.config/opencode`, `~/.local/share/opencode` (database, log, `auth.json`) and `~/.local/state/opencode`.

The measurements used a stub peer, not a model, and one OpenCode version.

## Options Considered

1. **Copy the launcher per tool.** Rejected: two scripts of about 850 lines would carry the same security-critical rule order. A fix to one drifts from the other, and the repository counts hand-maintained source duplication as debt.
2. **Sourced bash profile files.** Rejected: the per-tool facts would be host-run shell outside the typed, tested modules, and the mount logic would stay untestable in bash.
3. **Profiles as TOML data.** Rejected: the facts ship with the code and are not operator policy. Each tool also needs a function, the settings emitter, that a data file cannot hold. A typed object gets mypy and unit tests.
4. **One engine, a typed profile per tool, and a thin command per tool** (chosen).

## Decision

**The confinement is one engine, `agent-dev`. Each tool is a profile plus a command.** A command script such as `claude-dev` names its tool, carries its usage text as its header, and execs the engine. The engine asks the profile for every fact that differs between tools. A `profile` verb prints `KEY=VALUE` lines that the launcher reads and never evaluates.

The profile is a frozen, typed dataclass in `agent_dev_profiles.py`. It holds the command and the image stage. It holds the state roots with their lifetimes and shares, and the protected host paths. It holds the credential mechanism, the proxy variables and the one inference path the reverse port admits. A function in it renders the session's settings document. `agent_dev_config.py` keeps the policy reader and the squid rules and knows no tool. `agent_dev.py` is the CLI that binds the two.

**Names follow the command.** The data directory, image tag, container and network names carry the command's name, and so do the cleanup labels. claude-dev keeps its data directory, image tag and labels, and opencode-dev gets its own. `install.sh <tool>` installs one command with its own copy of the engine files and touches no other tool. The source directory is `tools/agent-dev`, formerly `tools/claude-dev`.

**Code runs from beside the engine.** Every code file sits in the engine's own directory, installed or in a checkout. A command prefers the engine beside it. An engine therefore never runs another version's modules, and a source checkout never runs an installed engine.

**One Dockerfile builds a stage per tool.** A shared `base` stage holds the toolchains and the confinement runtime. Each tool's stage comes last and carries its own label, so `update` rebuilds one tool layer. Every stage also carries one shared label. `cleanup --all` spares all tool images through that label, because Docker spares an object only when it carries every label the `label!=` filters name. It refuses to prune when any agent-dev tool image present on the engine lacks the label, and it names the image and the `update` that rebuilds it.

**The fences cover every tool and judge the path a mount resolves to.** A symlink or a trailing `..` is resolved before any comparison, and the comparison uses the directory entry's own spelling. A path typed in another letter case on a case-insensitive filesystem therefore resolves to the same protected path and is refused. A `--rw`, `--ro` or `[mounts]` entry that is a symlink to a file mounts the resolved target at the path as typed. A `statusLine` or hook path therefore keeps working inside the session, and the fences judge the resolved target.

- No session mounts any tool's data directory, read-write or read-only, at its default place or where its variable points.
- Every tool's protected host paths, `~/.claude.json` among them, are refused as writable mounts by every command; read-only they stay shareable.
- `~/.local/bin` and a checkout the engine runs from are refused as writable mounts.
- A project that is, or contains, any of these is refused, and so is the filesystem root.
- A command or engine inside the project is refused. `help` answers first.

**State roots have lifetimes.** A root a tool loads code or configuration from is never shared across projects, and a session on a peer never shares a shadow with a credentialed one. Otherwise one hostile project could plant code that every later session runs, and a peer session could read a stored login. Every shipped root's shadow is therefore per-project or per-run. A per-project shadow is keyed by a hash of the project's physical path and has a separate shadow under the open-weight flag.

claude-dev's `~/.claude` shadow is per-project: `state/claude-state/<key>` in the data directory, and `<key>.ow` under `--ow`. Its host-shared session paths and its read-only behavior config stay shares of the host's own files. A read-only share exists only for a config file the host has. Where the host has none, the session can create that name inside its own project's shadow, and it reaches later sessions of that project only.

The state directory is owner-only, and a killed launcher's run directory is reaped by the next launch. A liveness probe that cannot run counts the launcher as alive, so nothing is reaped.

**Open-weight runs follow the reverse-port ADR.** The flag is `--ow`, with `--open-weight` as its long form. The [reverse-port ADR](2026-10-06-open-weight-reverse-port.md) owns the peer, the shipped default map and the cost of its cloud tags; both policy files carry that default. A test holds each map's keys equal to the pins in the harness agents' frontmatter. The preflight reads Ollama's listing and falls back to the OpenAI one, so the peer need not be Ollama.

**The engine split itself changes neither claude-dev's squid rules nor its settings document.** The engine library generates the rules, the profile renders the document, and the suites pin both. claude-dev differs on purpose in these places:

- The `~/.claude` shadow is per-project, with a separate one under `--ow`.
- `build` and `update` pass `--target`, and each image carries the shared label beside its own.
- Under `--ow` the `~/.claude.json` replica drops `primaryApiKey` and every `mcpServers` entry but a bare loopback endpoint.
- The fences compare the directory entry's own spelling, and `~/.claude.json` is a protected host path.
- A mount entry that is a symlink to a file mounts the resolved target at the path as typed.
- The reverse port's admitted query string is limited to letters, digits and `_ = & -`.

**OpenCode is the second profile.**

- Its config, state, cache and `~/.claude` shadows are per-run. Its data shadow, which holds `auth.json`, the session database and logs, is per-project. One project's state never reaches another's, and a session on a peer starts apart from any provider login. The cost is one `/connect` in each project, which a first run names.
- Each parent directory of a nested root is its own tmpfs with the home's options. The engine would otherwise create `~/.cache` and `~/.local` owned by root, and other tools could not write beside OpenCode's directories.
- Host rules, agents, commands, plugins, skills, `tui.json` and `opencode.json` share read-only under `~/.config/opencode`. From `~/.claude` only `CLAUDE.md` and `skills` cross, read-only.
- The settings document travels as `OPENCODE_CONFIG_CONTENT`. It disables session sharing, which uploads a transcript, and auto-update. Under `--ow` it overrides the `openrouter` provider with the reverse port, maps each pin to the peer's tag, and pins `model` and `small_model` to mapped names. The lowest Claude tier among the mapped names serves titles.
- The session receives `HTTPS_PROXY` only. The reverse port admits `POST /v1/chat/completions` and nothing else.
- The image stage installs `opencode-ai` from the npm registry as the unprivileged account, into directories only that account owns, last on `PATH`. Package scripts therefore cannot alter squid, which starts from the same image. The stage also installs the plugin SDK at the same version into a seed directory, and a step inside the session copies it into the per-run config shadow.
- The default allow-list names `models.opencode.ai` and no model provider, and it leaves `opencode.ai` off: that origin accepts authenticated uploads.
- No IDE bridge and no permission-mode injection. The reader refuses a `[telemetry]` table for this tool, since the launcher declares nothing about OpenCode's opt-in telemetry.

## Consequences

Positive:

- A further tool is a profile, a seven-line command script under its usage header, a policy file, an installer arm, an install skill and an image stage. The proxy, mounts, fences, hardening, `access`, `cleanup` and the reaper stay in one place.
- The proxy rules have one source. The suite that pins their order runs once for every tool.
- The facts that differ are typed, and invariants hold for every profile by test. Roots stay home-relative, no root sits inside another, overlays sit under read-only shares, and no tool keeps a credential in a persistent shared root.
- Installing one tool never changes the other's files, data or image, and neither tool's session can mount the other's.

Negative:

- The engine files install once per tool, so a fix to the engine reaches a tool only when that tool's install runs again. The installer's `check` mode reports drift per tool.
- Each command carries its own usage text. A test keeps the help in step with the engine's flags and cannot catch stale wording.
- The two policy files share about 90 lines of prose and the toolchain hosts. A test holds the hosts equal; the prose is hand-kept.
- The two install skills run in parallel and are kept in step by hand. No test holds them equal.
- Real Docker behavior rests on one maintainer run, on 2026-10-06, not on a test. The run built both images, started a session in each, ran `--ow` against the host's Ollama daemon and ran `cleanup --all`. The suites drive a stub engine, so they cover the calls, not the engine's behavior.
- The OpenCode measurements cover opencode-ai 1.18.34 and a stub peer. They do not cover HTTPS inference to a real provider through the proxy.
- The `timeout` provider option and the `share` and `autoupdate` keys are checked against OpenCode's published config schema, not against a runtime that rejects them.
- Read-only sharing of a protected path stays the operator's choice and exposes what the path holds. The shared `opencode.json` is readable by the session, as `settings.json` is for Claude Code.
- A project plugin runs in-process and can alter the provider at runtime. It cannot change a route, since the proxy decides every one.
- A command run from a checkout runs that checkout's code on the host, and `install.sh` installs the checkout it lives in. A checkout a confined session has written is session-authored code.
- `cleanup --all` prunes nothing while one agent-dev tool image on the engine lacks the shared label; `update` on the named image clears the refusal.
- A config name the host lacks is writable in a project's own claude-dev shadow, so a plant there reaches that project's later sessions.
- The directory rename changed the path of every link into the tool. The ADRs that name the old path carry the new one, in links and in prose.

## References

- [Egress Is Enforced by an External Proxy, Not by the Workload](2026-07-29-proxy-enforced-egress.md) — extended: the same proxy and rule order confine a second tool.
- [An Open-Weight Peer Is Reached Through a Reverse Port the Proxy Can Read](2026-10-06-open-weight-reverse-port.md) — extended: the inference path is a profile constant, and `/v1/chat/completions` is the second admitted shape. It owns the peer, the shipped default map and its cost.
- [`tools/agent-dev/README.md`](../../tools/agent-dev/README.md) — the operator-facing statement of the structure, the boundary and the OpenCode differences.
- [`docs/open-weight-models.md`](../open-weight-models.md) — the OpenCode model mapping the profile emits.
- OpenCode documentation and config schema, read 2026-10-06: [config](https://opencode.ai/docs/config/) (precedence order, `OPENCODE_CONFIG_CONTENT`), [network](https://opencode.ai/docs/network/) (proxy variables), [providers](https://opencode.ai/docs/providers/) (credential path), and the [config schema](https://opencode.ai/config.json) (`share`, `autoupdate`, `small_model`, provider `timeout`, top-level `additionalProperties: false`).
