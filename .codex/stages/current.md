# Active stage: support human handoff — 2026-10-25

Contract/evidence: `.codex/stages/support-human-handoff.md`. Economy; no subagents (owner instructions). Latest production baseline7bbc0a4 and Telegram safearea release preserved.

Accepted behavior: manager reply pauses AI until explicit per-ticket resume; admin has pause/resume button; only future user messages start resumed AI. DB transaction protects against late provider results and pause/resume races. Account-specific purchases/compensation/promises, explicit human requests and repeated failed diagnostics hand off before model calls. No customer messages, refunds or entitlements changed by this work. Reported thread23 paused as immediate containment, root-only before snapshot retained.

Acceptance: backend concurrency/permissions/handoff tests; TS/build; frontend control test; authenticated live pause/resume without sending messages; four responsive widths and preserved old chunks. Production commit/push/FFpull/restart bot+subscription/health. Rollback code/assets with human pauses retained, no customer DB restore. Status: implementation and checks in progress.
