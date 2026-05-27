---
name: ship
description: >-
  Commit staged and unstaged changes and push to the remote in one step.
  Load when the user asks to commit and push, or invokes /ship.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

# Ship (Commit and Push)

Stage tracked changes plus any new feature files, write a single conventional commit, and push to `origin`.

## Instructions

1. Run `git status`, `git diff --stat`, and `git log --oneline -10` in parallel to assess the change set and match recent commit style.
2. Run the project's quality gate (`./gradlew build && ./gradlew test && ./gradlew checkJavaFormat`, or `./mvnw verify` on Maven targets) and confirm green. If it fails, stop and report — do not commit broken builds.
3. Draft a commit message following the convention in `CLAUDE.md` (`<type>(<scope>): <subject>`, imperative mood, lowercase, no period, ≤50 chars). Reference the REQ-XX-NNN identifier in the subject when applicable.
4. Stage files explicitly by name. Do not use `git add -A` or `git add .`. Skip `.scratch/` (gitignored) and any file that looks like a secret.
5. Commit using a HEREDOC so the body formats correctly. Always include the `Co-Authored-By` trailer.
6. Run `git push`. If the local branch is ahead by more than one commit, surface that to the user before pushing.
7. Report the resulting commit SHA and the push destination.

## Execution Template

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<optional body — wrap at ~72 chars, explain why, not what>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push
```

## Rules

- Never commit if the quality gate is red.
- Never use `--no-verify`, `--amend`, or `git push --force` unless the user explicitly asks.
- Never stage files that look like secrets (`.env`, credentials, keys). Warn the user if they are present.
- One commit per invocation. If the change set spans unrelated concerns, flag it and ask whether to split before committing.
- If the working tree is clean, report it and stop — do not create empty commits.
