# Lint Docs

Validate documentation coherence, structure, and writing quality on demand.

## Instructions

Run the `doc-reviewer` agent against the current documentation:

```
Agent(subagent_type="doc-reviewer", prompt="Full audit of docs/prd.md, docs/system-design.md, and docs/adr/*.md against docs/documentation.md Validation Checklist.")
```

Report results directly to the user. No `.scratch/` files needed for on-demand use.
