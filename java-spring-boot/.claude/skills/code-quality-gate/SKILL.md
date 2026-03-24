---
name: code-quality-gate
description: >-
  Build, test, format, and lint requirements that must pass before
  code review. Load when checking implementation completeness or
  running the quality gate.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Quality Gate

Before invoking reviewers, all checks must pass.

### Required Checks

| Check | Command | What It Verifies |
|---|---|---|
| Build | `./gradlew build` | Project compiles |
| Test | `./gradlew test` | All tests pass |
| Format | `./gradlew checkJavaFormat` | Code follows google-java-format |

### Fix Formatting

```bash
./gradlew formatJava
```

Formats all Java files with google-java-format. Run before `checkJavaFormat`.

## Configuration Sync

After implementing a feature that adds or changes configuration properties, verify:

- [ ] New properties appear in `application.yml`
- [ ] `@ConfigurationProperties` record updated if needed
- [ ] prd.md configuration table updated (if user-facing property)
- [ ] Default values consistent across all locations

## Completion Criteria

A feature is complete when:

- [ ] All TDD cycles finished
- [ ] All tests pass (`./gradlew test`)
- [ ] Code formatted (`./gradlew formatJava`)
- [ ] Format check passes (`./gradlew checkJavaFormat`)
- [ ] Project builds (`./gradlew build`)
- [ ] Configuration synced (if config changed)
- [ ] All four reviewers approve
- [ ] No pending escalations (or human approved)
