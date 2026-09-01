---
name: arcvpn-stage
description: Plan and execute a non-trivial ArcVPN stage with explicit acceptance, component mapping, risks, evidence, and a bounded handoff. Use for production, migration, cross-component, security, or substantial UI work.
---

# ArcVPN Stage

1. Read `AGENTS.md`, `.codex/handoff.md`, `.codex/project-index.md`, and `.codex/orchestrator.toml` completely.
2. Search `AI_CONTEXT.md` only for named missing facts.
3. Before edits, write `.codex/stages/current.md` with goal, non-goals, affected components, acceptance criteria, risks, rollback, and verification matrix. Treat a rejected proposal as history, never as authority.
4. Turn public contracts into exact tables or examples. For URLs, topology, pricing, callbacks, and visible UI behavior, the assumption budget is zero: if two implementations satisfy the prose differently, record the alternatives and obtain the owner's explicit choice before mutation.
5. Inspect only mapped components. For independent work, use subagents only when the user explicitly authorized them in this chat.
6. Implement the smallest coherent stage. Do not redefine acceptance after seeing the implementation and do not substitute an easier proxy check for the requested observable result.
7. Record commands and concise evidence in the stage file; keep secrets and verbose logs out. Keep only the current stage here; move stable decisions to `AI_CONTEXT.md` and completed history to a bounded closeout/handoff.
8. Finish with `$arcvpn-closeout`.
