---
name: arcvpn-stage
description: Plan and execute a non-trivial ArcVPN stage with explicit acceptance, component mapping, risks, evidence, and a bounded handoff. Use for production, migration, cross-component, security, or substantial UI work.
---

# ArcVPN Stage

1. Read `AGENTS.md`, `.codex/handoff.md`, `.codex/project-index.md`, and `.codex/orchestrator.toml` completely.
2. Search `AI_CONTEXT.md` only for named missing facts.
3. Before edits, write `.codex/stages/current.md` with goal, non-goals, affected components, acceptance criteria, risks, rollback, and verification matrix.
4. Inspect only mapped components. For independent work, use subagents only when the user explicitly authorized them in this chat.
5. Implement the smallest coherent stage. Do not redefine acceptance after seeing the implementation.
6. Record commands and concise evidence in the stage file; keep secrets and verbose logs out.
7. Finish with `$arcvpn-closeout`.
