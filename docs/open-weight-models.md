# Open-Weight Models

Every harness agent pins one of two Anthropic models in its frontmatter, `claude-opus-5-5` or `claude-sonnet-5`, and the runtime ships no provider configuration. The same runtime runs on an open-weight model when the agent tool points at a provider that serves it and remaps the pinned names in the tool's own configuration. The pins never change. Claude Code remaps them through the `modelOverrides` settings key and OpenCode through the `id` field of a model entry, so both keep the two-tier split. Copilot CLI takes one provider model for the whole session and loses the split. Every mapping lives in a file the operator owns, never in the materialized runtime, so no harness change is involved. This document carries the mapping per tool, a worked example on Ollama Cloud, and the operating notes that decide whether a run completes.

The gates, the router, the hooks, and the ledger are deterministic and model-agnostic. What varies with the model is prompt discipline. The eval bench is the instrument that measures it: trend rows key on the model pin, and the served model's name lands in every rep's transcript. The mapping per tool follows, then the example, then the operating notes.

Sources, read 2026-09-13: the Claude Code [model configuration](https://code.claude.com/docs/en/model-config), [settings reference](https://code.claude.com/docs/en/settings-reference), [environment variables](https://code.claude.com/docs/en/env-vars), and [subagents](https://code.claude.com/docs/en/sub-agents) pages; Ollama's [Anthropic compatibility](https://docs.ollama.com/api/anthropic-compatibility) and [cloud](https://docs.ollama.com/cloud) pages; the Copilot CLI [own-models](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-byok-models) page; the OpenCode [providers](https://opencode.ai/docs/providers/) page and [config schema](https://opencode.ai/config.json); the vLLM [online serving](https://docs.vllm.ai/en/latest/serving/online_serving/) page; Epoch AI's data insight [Open models lag state-of-the-art closed models by 4 months](https://epoch.ai/data-insights/open-closed-eci-gap) (2026-05-29); the [SWE-bench leaderboards](https://www.swebench.com/). Verified by running Claude Code 2.1.270 against Ollama 0.33.3 on macOS: the `modelOverrides` rewrite of a pinned ID, its effect on a frontmatter-pinned subagent, and its effect under `ANTHROPIC_BASE_URL`. Also verified: the local layer outranking the project layer, a complete `claude -p` run on a local model with both pins mapped, and one API request answered by a cloud model through the signed-in daemon. The Claude Code model-configuration page states the reverse of two observations. It says a subagent's frontmatter model wins over `modelOverrides`, and that the map is bypassed on an LLM gateway. The observation governs here until `update-research` re-checks it. The OpenCode block is verified against the config schema only, and the Copilot, vLLM, llama.cpp, and LM Studio rows transcribe their vendors' pages.

## The Mapping

Three values map: the endpoint URL, the credential, and one provider model per pinned name. [ADR 2026-06-11](adr/2026-06-11-model-tier-assignment.md#decision) fixes the tier split: judgment roles on the opus pin, checklist roles on the sonnet pin. The current IDs per tool are in [cross-tool-strategy.md § Agents / Subagents](cross-tool-strategy.md#agents--subagents).

| Tool | URL and credential | Pinned name to provider model | Tier split |
|---|---|---|---|
| Claude Code | `env` block of `.claude/settings.local.json` | `modelOverrides` map in the same file | Kept |
| OpenCode | Provider override in the operator's `opencode.json` | `id` field per model entry | Kept |
| Copilot CLI | `COPILOT_PROVIDER_BASE_URL`, `COPILOT_PROVIDER_TYPE`, `COPILOT_PROVIDER_API_KEY` in the shell | `COPILOT_MODEL`, one model per session | Lost |

**Claude Code.** `modelOverrides` is a settings map from a model name Claude Code knows to the ID the provider uses. With the two pinned IDs as keys, every specialist dispatch is rewritten on the way out, including a subagent whose frontmatter pins the full ID. The root session follows through the `model` key set to the opus pin. The map applies with `ANTHROPIC_BASE_URL` set to an Ollama daemon. `.claude/settings.local.json` is per-operator, and its `modelOverrides` outranks the same key in the committed `settings.json`. Claude Code ignores the file in git only when it creates the file itself; a hand-written one needs a `.gitignore` line, and the harness's ignore block does not carry it. Removing the `env`, `model`, and `modelOverrides` keys restores the Anthropic defaults; the file also holds the operator's permission allowlist, so it is edited, not deleted. `CLAUDE_CODE_SUBAGENT_MODEL` with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` is the one-model shortcut: every pin runs on one model and the tier split is lost.

**OpenCode.** Agents name `openrouter/anthropic/claude-opus-5.5`. The operator's config overrides the `openrouter` provider's transport and rewrites each model entry's upstream id through the `id` field. The schema describes that field as "send a different upstream model id than its map key". The config lives in `~/.config/opencode/opencode.json` or a file named by `OPENCODE_CONFIG`; both merge under the project's `opencode.json`, and `{env:NAME}` substitution keeps the credential out of the file. OpenCode reads the provider through its OpenAI-compatible endpoint, not the Anthropic one. OpenCode ships on the copy channel only.

**Copilot CLI.** Four shell variables switch the session to an own provider. They are the base URL, the provider type (`openai` by default, `azure`, or `anthropic`), an optional key, and the one model ID. The vendor page names Ollama as a local provider and requires a model with tool calling and streaming, with a context window of at least 128k tokens recommended. The agent frontmatter's list of hosted display names has no documented interaction with the session model, so both tiers run on the one model named.

The server serves the Anthropic Messages API for Claude Code and a Copilot session of type `anthropic`, and the OpenAI-compatible endpoint for OpenCode and a Copilot session of type `openai`:

| Server | Anthropic `/v1/messages` | OpenAI-compatible `/v1` | Two models behind one URL |
|---|---|---|---|
| Ollama, local or cloud-backed | Yes | Yes | Yes, loaded per request |
| vLLM | Yes, with `count_tokens` | Yes | One model per process; two tiers need a gateway such as LiteLLM, which then carries the map |
| llama.cpp `llama-server` | Yes | Yes | Router mode over a models directory |
| LM Studio | Yes | Yes | Yes |

## Worked Example: Ollama Cloud

Ollama Cloud runs open-weight models on Ollama's servers through the local daemon. The configuration is identical to a local model, and the host's memory sets no limit. Sign-in is the whole credential: the daemon holds it, a cloud tag needs no pull, and the token the tool sends is a placeholder. The example puts one model family's two sizes on the two tiers; the pairing is a starting point, not a measured equivalence.

Two public sources bound how far that starting point sits from the pinned models. Epoch AI's data insight finds the leading open-weight models trailing frontier closed models by an average of four months since January 2026, an 8-point gap on its capabilities index. The SWE-bench Verified leaderboard, the closest public proxy to the implementer's job, lists open-weight entries beside Claude's under one submission protocol. Both are external publications the reference neither controls nor re-measures. Their figures change with each model release and are read at the date in the Sources block. A link points at their method, not at a ranking. Neither measures this pipeline; the eval bench does, one trend row per mapped model.

| Pinned name | Tier | Ollama Cloud model in the example |
|---|---|---|
| `claude-opus-5-5` | Judgment: requirements, design, implementation, security, grading | `glm-5.3:cloud` |
| `claude-sonnet-5` | Checklist: coordination, code quality, tests, docs | `glm-5.3-flash:cloud` |

Both tags list `tools` and `thinking` among their capabilities in `ollama show`. With the daemon running:

```sh
ollama signin
```

Claude Code reads the whole mapping from `.claude/settings.local.json` in the project. The file is hand-written here, so the `.gitignore` line comes with it:

```sh
grep -qx '.claude/settings.local.json' .gitignore || echo '.claude/settings.local.json' >> .gitignore
```

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:11434",
    "ANTHROPIC_AUTH_TOKEN": "ollama",
    "API_TIMEOUT_MS": "1800000"
  },
  "model": "claude-opus-5-5",
  "modelOverrides": {
    "claude-opus-5-5": "glm-5.3:cloud",
    "claude-sonnet-5": "glm-5.3-flash:cloud"
  }
}
```

Start `claude` in the project. Every specialist dispatch names its pinned model, the map rewrites it, and the daemon runs the cloud model. The session transcript under `~/.claude/projects/` records the served model's name in each assistant message, which confirms the map took; `ollama ps` lists local models only.

OpenCode reads the same daemon through its OpenAI-compatible endpoint. `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "openrouter": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://localhost:11434/v1",
        "apiKey": "ollama"
      },
      "models": {
        "anthropic/claude-opus-5.5": { "id": "glm-5.3:cloud" },
        "anthropic/claude-sonnet-5": { "id": "glm-5.3-flash:cloud" }
      }
    }
  }
}
```

Copilot CLI takes the shell variables, with the Anthropic-format endpoint and one model:

```sh
export COPILOT_PROVIDER_TYPE=anthropic
export COPILOT_PROVIDER_BASE_URL=http://localhost:11434
export COPILOT_MODEL=glm-5.3:cloud
```

**Local variant.** The same files apply to a model on the host, with the local tag as the map's value. One addition: `OLLAMA_CONTEXT_LENGTH` on the daemon, or `PARAMETER num_ctx 65536` in a Modelfile that derives a tag from the base model. A host that holds one model at a time maps both pins to the same tag; two different local models reload on every dispatch and drop the daemon's prompt cache.

## Operating Notes

Four things decide whether a mapped run completes or fails without an error message: the context window, the endpoint's feature gaps, the request timeout, and where the run executes. A fifth, cost accounting, decides whether the numbers a run reports mean anything. Each is one paragraph.

**Context window.** The material root loads before any work starts, measured on the generic sample with `wc -c` at 4 bytes per token. The Go and Java samples' `CLAUDE.md` differ in size:

| Loaded by root | Tokens |
|---|---|
| `CLAUDE.md` | 4,900 |
| `handoff-routing` skill, `SKILL.md` and `route-rules.md` | 8,300 |
| Handbook copy in the skill | 9,500 |
| `route-spec.md`, read on demand | 10,600 |

The tool's own system prompt and tool schemas add to that, and a reviewer adds a whole change set. A 64k window is the floor, and 128k is the Copilot page's recommendation. A request whose prompt exceeds the daemon's context length is served with tokens dropped. The only trace is the server log line `truncating input prompt`, and the symptom in the session is an agent that lost its rules. `OLLAMA_CONTEXT_LENGTH` sets the daemon's window, and `ollama ps` shows the window in force per loaded model: 4,096 tokens on this host before the variable was set. On the Claude Code side, `CLAUDE_CODE_MAX_CONTEXT_TOKENS` caps the window Claude Code assumes and makes it compact before that cap, in the main session and in subagents. Without it Claude Code sizes compaction for the pinned name, not the served model.

**Endpoint gaps.** Ollama's Anthropic endpoint has no `count_tokens`, ignores `cache_control`, and rejects `tool_choice`. A model without the `tools` capability fails every request with status 400. vLLM needs `--enable-auto-tool-choice` with the parser matching the model family, or tool calls arrive as text and every dispatch ends after one turn. Thinking models need the matching `--reasoning-parser`. The vendor pages in the Sources block carry the full lists.

**Timeouts.** The `API_TIMEOUT_MS` default is 600,000 ms. On this host a 2,000-token request to a local model took 33 s including the model load and 6 s warm. Parallel review fan-out queues on one daemon (`OLLAMA_NUM_PARALLEL` defaults to 1). The example sets 1,800,000 ms.

**Knobs without effect.** The frontmatter `effort` field and `cache_control` markers reach the endpoint and change nothing; the routine effort variant runs at base strength, as on OpenCode. Sampling parameters come from the model's Modelfile.

**Cost accounting.** Claude Code's own cost figure prices the run at the pinned name's rate: the local run reported $0.02 for 2,000 tokens on a free model. The session transcript records the served model's name, `gemma4:latest` in that run. Harness Stats and the eval bench price an unrecognized model at $0.00 by design, and the eval trend lists it as the resolved model. Neither figure is the run's cost.

**Claude Dev.** The container's egress proxy is default-deny, permits port 443 only, and refuses the host apart from the `--ide` pinhole. A daemon on the host is unreachable from inside it. Open-weight runs execute on the host.
