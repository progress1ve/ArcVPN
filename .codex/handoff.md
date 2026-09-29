# ArcVPN handoff — admin broadcasts MVP (2026-09-29)

## Latest production incident fix

Runtime `a5efeb4`: unbound generic subscription GETs without stable HWID cannot
allocate or reactivate recovery slots. Bound device URLs and recognized clients
keep existing access. 279 tests passed, including 18 probe regression checks.
Poland pulled ff-only; subscription service restarted and active; public health
200. Three real public probes left all device rows unchanged. One verified
synthetic active slot was deactivated after a restricted DB backup; zero active
synthetic generic rows remain. @sso095 has one active INCY iPhone 14 Pro and its
public subscription returns the existing UUID. Key URLs/UUIDs are unchanged.
No rollback needed. Unrecognized unbound clients use the existing reimport
response; use explicit import for those clients. Broadcast owner test below
remains pending. Evidence: `.codex/stages/device-generic-fix.md`.

MVP runtime: `e2d3892` (with UI release `48b006f` and order guards `7e634ed`), based on `e810aae`.
Poland remains the control plane. This release preserves the latest Germany
retirement/Estonia CDN changes. Primary checkout has unrelated owner changes;
continue broadcasts in the attached managed `admin-broadcasts` worktree.

## Current behavior

`https://arccnet.space/admin/broadcasts` is the working owner-only campaign UI.
Drafts, recipient snapshots, test revisions, deliveries and reward state are
stored in SQLite (migrations 67/68). HTML and length are validated; preview is
sanitized. Tests go only to a configured Telegram admin and never grant bonuses.
Editing invalidates test; start needs the tested revision and recipient count.
Days are atomically extended once and externally synced before notification.
New shared/private campaign codes reserve order capacity atomically; private
codes are recipient-bound. Ambiguous Telegram deliveries are marked uncertain
for manual review, rather than automatically duplicated.

## Owner review / pending action

Latest UI verification: owner's “Проблема с серверами решена” is stopped,
22 deliveries out of 24. The earlier compensation draft still has 63 recipients.
Those state changes were performed outside the agent's workflow; the agent did
not send or grant rewards. Any further agent sending requires owner instruction.

## Evidence and rollback

257 baseline full-suite tests passed; 67 after latest-main rebase; 38 broadcast/
promocode tests and 2 payment-storage tests after final order guards. Admin
build, type-check and scoped Biome passed. Authenticated production browser QA
at 390x844, 768x1024, 1280x900, 1600x900 found no horizontal overflow. Screenshots
are local `.codex/evidence/broadcasts/production-*-top.png` / `*-launch.png`.
Backup: `/root/ArcVPN/backups/broadcasts-20260929-pre-mvp.sqlite3`, mode 0600.
Existing subscription UUIDs/URLs match the backup. Stop jobs before reverting
runtime commits; retain ledger and additive tables, and never blindly undo days.
See `.codex/stages/current.md` for exact deployment status and residual limits.

## Day-bonus copy correction — 2026-09-29

Runtime ee7c079 removes the automatic gift sentence from preview and Telegram;
owner authors the bonus copy. Actual reward grants are unchanged. 31 campaign
checks and admin build passed; production four-width browser check passed.
There are now two drafts: owner's outage message for 24 active subscribers and
previous compensation draft for 63. Both untested after invalidating one old
successful day test; neither started or delivered. Repeat the test before any
mass confirmation. Generic-device repair from 83976e6 is preserved.

## Draft deletion — 2026-09-29

Runtime d992578 deployed. Delete buttons in history and saved-draft editor use
explicit named confirmation. Only drafts can be soft-deleted atomically; deleted
rows are hidden, retained for recovery, and cannot be edited/tested/started.
Started/stopped/completed histories cannot be deleted. 37 focused tests, build,
Biome and four-width demo/production UI checks passed. Only subscription API
restarted; both services healthy. Agent deleted no owner draft and sent nothing.
Owner prefers no screenshot attachments in replies. Next: refresh admin to use.
