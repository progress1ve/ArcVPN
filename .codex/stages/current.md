# Delete broadcast drafts — 2026-09-29

Owner request: add draft deletion; do not attach screenshots in replies.
Contract: delete buttons in history and saved-draft editor; confirmation names
that draft; cancel has no effect. Only draft status can be deleted atomically;
queued/running/stopped/completed campaign histories cannot be deleted. Soft
status deletion hides the draft, retains ledger and prevents test/edit/start.
Components: db_admin_broadcasts, owner API DELETE, ArcBroadcasts UI/demo.
Acceptance: status guard and API RBAC/origin tests; build; browser deletion of
agent-created demo draft, cancel and four responsive sizes; production visible
controls without deleting owner's drafts. No campaigns sent or bonuses granted.
Rollback: scoped revert, retained draft data can be restored operationally.

Passed: 37 campaign tests (delete, status guard, no re-test/edit/start, retained
ledger, owner/origin guards), TypeScript/Vite build, scoped Biome check.
Browser: agent-created demo draft cancellation and deletion verified; production
confirmation/cancellation verified at 390/768/1280/1600 without overflow. Local
evidence delete-draft-*.png / delete-production-*.png; not attached per owner.
Runtime d992578 pushed and Poland ff-only pulled. Subscription API service
restarted; both services active; public admin HTTP 200, anonymous DELETE 403.
No rollback needed. No owner drafts deleted; no sends/grants initiated by agent.
Latest live UI: outage campaign is stopped with 22 delivered of 24; earlier
compensation campaign remains a draft (63). These are owner-controlled actions,
not agent sends. Next: owner refreshes admin and deletes any unwanted draft.
# Netherlands alias follow-up — 2026-09-29

Owner-approved display-only Netherlands -> existing EE Reality/443, same
hostname/SNI/inbound, no CDN, multiplier1, unchanged URLs/UUIDs. No additional
automatic candidate. Release4d5049e deployed;286 tests, live equality and real
NL tunnel exit87.251.19.197 HTTP200 passed. Exact evidence/rollback:
`.codex/stages/netherlands-alias.md`. Future Poland/NL -> replacement FI deferred
until new node and direct Moscow route pass. Preserve existing broadcast work.
