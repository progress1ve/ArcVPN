---
name: arcvpn-closeout
description: Close an ArcVPN stage with exact verification, Git/deployment evidence, residual risks, durable context updates, and a concise next-chat handoff.
---

# ArcVPN Closeout

1. Re-read acceptance criteria and mark each as passed, failed, or deferred with evidence.
2. Run proportional local checks and inspect `git diff --staged` before committing.
3. For runtime changes: commit, push, production `git pull --ff-only`, restart only affected services, and verify public behavior. For docs-only changes: push and production pull; do not restart services without need.
4. Update `.codex/handoff.md` with only current durable state. Add stable historical facts to `AI_CONTEXT.md` without logs or secrets.
5. Finish `.codex/stages/current.md` with commit, deployment, verification, rollback status, residual risks, and one next step.
6. Report cause, changes, verification, commit, deployment, and next step. Do not claim completion where acceptance is missing.
