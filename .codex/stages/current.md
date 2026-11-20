# Recurring payments
Acceptance: derive the next collection window from the same owned key as the scheduler, revoke independently for every user, and avoid starving eligible renewals behind already claimed cycles. Verify in isolated SQLite and on production read-only. Preserve the single-attempt policy. Rollback by reverting this commit.

Local verification: 5 tests passed against isolated SQLite, including two payment methods, queue pagination, repeated scheduling, expiry changes and independent revocations. First actual automatic collection remains pending its normal window.
