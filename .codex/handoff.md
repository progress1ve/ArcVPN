# ArcVPN handoff — partner cabinet, 2026-10-05

token-mode: economy; persists until user switches.
Production baseline verified 83e4634 on Poland; partner implementation is locally checked and awaiting the normal commit/push/ff-only pull workflow.

Partner cabinet: partners.arccnet.space/partner, admin: panel.arccnet.space/admin/partners. Owner created DNS A to Poland. Dedicated Svelte cabinet and existing React admin; separate secure partner login and owner-only administration.
Exact 30% confirmed SBP/card purchases including renewals/add-ons; paid/free trials/topups excluded. Client terms immutable, future-client rate editable, access/recruitment independent. Existing clients need explicit preview confirmation, no historical paid-order accruals. Manual transfers only; immutable payout/correction/reversal journal with concurrency and idempotency protection. Exceptional refunds use owner-defined correction; negative balance requires explicit form consent.

439 Python tests and both production builds pass; browser checks waived by owner. Stage: .codex/stages/partner-cabinet.md. Guide: docs/operations/partner-cabinet.md. Private primary checkout changes preserved in a separate managed worktree.

Earlier operational history preserved in docs/archive/handoffs/pre-partner-cabinet-2026-10-05.md; outstanding device bans and actual restricted-mobile CDN validation were not part of this stage.
