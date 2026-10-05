# ArcVPN handoff — partner cabinet, 2026-10-05

token-mode: economy; persists until user switches.
Deployed on Poland 217.60.33.38 at runtime commit 4530766 (migration75). Bot, subscription API and nginx active; partner TLS issued and dedicated virtual host installed. Normal commit/push/ff-only production pull completed.

Partner cabinet: partners.arccnet.space/partner, admin: panel.arccnet.space/admin/partners. Owner created DNS A to Poland. Dedicated Svelte cabinet and existing React admin; separate secure partner login and owner-only administration.
Exact 30% confirmed SBP/card purchases including renewals/add-ons; paid/free trials/topups excluded. Client terms immutable, future-client rate editable, access/recruitment independent. Existing clients need explicit preview confirmation, no historical paid-order accruals. Manual transfers only; immutable payout/correction/reversal journal with concurrency and idempotency protection. Exceptional refunds use owner-defined correction; negative balance requires explicit form consent.

439 Python tests and both production builds pass; browser checks waived by owner. Stage: .codex/stages/partner-cabinet.md. Guide: docs/operations/partner-cabinet.md. Private primary checkout changes preserved in a separate managed worktree.

Earlier operational history preserved in docs/archive/handoffs/pre-partner-cabinet-2026-10-05.md; outstanding device bans and actual restricted-mobile CDN validation were not part of this stage.

Production evidence: HTTPS partner/admin pages and generated assets return200; guest cabinet401, partner-domain admin endpoints404; owner admin API200. Valid-origin invalid login401, foreign Origin403 after removing duplicate nginx Host headers. Private pre-migration SQLite backup/snapshot in production .secrets; after-check confirms preserved existing customer identities, subscription identifiers and referral attribution. No partner clients imported or ledger records created. No live purchase/transfer or browser QA performed.
