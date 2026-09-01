---
name: arcvpn-repo-hygiene
description: Audit and clean the ArcVPN checkout without losing owner files, runtime secrets, deployment artifacts, or useful project history. Use for repository dirt, stale files, duplicate outputs, archives, caches, and context-maintenance work.
---

# ArcVPN Repository Hygiene

1. Read `AGENTS.md`, `.codex/handoff.md`, `.codex/project-index.md`, `.gitignore`, and the current `git status`.
2. Audit read-only first. Do not open or print secret contents. Use file metadata, Git tracking state, references, age, size, and build provenance.
3. Classify every candidate before proposing deletion:
   - generated and safely reproducible;
   - intentional tracked source, distribution, evidence, or archive;
   - obsolete with caller/reference evidence;
   - unknown or owner-owned.
4. Never delete or restore the unknown/owner-owned class. Empty directories, ignored caches, and build outputs are not authorization to remove them.
5. Keep cleanup separate from runtime, migration, node, and UI commits. Require the owner to approve the exact deletion class; show recoverability and expected impact first.
6. Treat contradictory active instructions as higher risk than disk clutter. Reconcile the current contract in skills/references and preserve superseded material only in a clearly marked archive.
7. Keep `.codex/stages/current.md` bounded to the active stage, `.codex/handoff.md` to current operational state, and `AI_CONTEXT.md` to stable searchable decisions. Do not append entire completed stage logs indefinitely.
8. Validate the resulting Git diff and rerun only checks affected by cleanup. Finish with `$arcvpn-closeout` when files actually change.
