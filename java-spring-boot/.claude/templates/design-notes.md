# Design Notes - REQ-XX-NNN

## Architectural Fit

[How this feature integrates with existing design]

## Reliability Assessment

### Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|------------|
| [failure] | [impact] | [how handled] |

### Idempotency Impact

[Does this change affect idempotency? How?]

## Package Placement

- Primary: `src/main/java/com/example/project/{package}/{Class}.java`
- Supporting: `src/main/java/com/example/project/model/{Record}.java`

## Pipeline Integration

- Fits at step N of the pipeline
- Inputs: [what it receives]
- Outputs: [what it produces]

## Integration Points

1. [Component A] connects to [Component B] via [mechanism]

## Patterns to Follow

- See `src/main/java/com/example/project/{package}/{Class}.java:45` for similar pattern

## Risks

- [Risk]: [Mitigation]

## Recommendation

APPROVED | NEEDS_CHANGES | BLOCKED

[If NEEDS_CHANGES or BLOCKED, specific actions required]
