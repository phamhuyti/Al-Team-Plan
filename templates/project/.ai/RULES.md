# Rules

1. Shared project state in `.ai/` is the source of truth.
2. Agents must follow their contracts.
3. SAFE actions may run automatically.
4. MODERATE actions require Manager approval.
5. DANGEROUS actions always require user approval (`git push`, volume deletes, destructive migrations).
6. Record every important decision in `DECISIONS.md`.
7. Do not dump the entire codebase into a prompt.
8. Red Team must try to break the plan, not rubber-stamp it.
