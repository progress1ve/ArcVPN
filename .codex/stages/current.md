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
