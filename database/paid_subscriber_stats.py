"""Unique active commercial subscribers and first purchases on Moscow dates."""

PAYMENT = """p.status IN ('paid','succeeded')
    AND p.operation_type IN ('new','renew','upgrade')
    AND COALESCE(p.payment_type,'') NOT IN ('trial','demo')
    AND COALESCE(p.offer_code,'')!='email_paid_trial'
    AND CASE WHEN p.payment_type='stars' THEN COALESCE(p.amount_stars,0)
             ELSE COALESCE(p.amount_cents,0) END > 0"""


def paid_subscriber_stats(conn, now_utc='now'):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='payments' AND type='table'").fetchone():
        return {'paid': 0, 'first_paid_today': 0}
    trials = conn.execute("SELECT 1 FROM sqlite_master WHERE name='trial_entitlements' AND type='table'").fetchone()
    exclude_trial = """AND NOT EXISTS(SELECT 1 FROM trial_entitlements te
        WHERE te.vpn_key_id=k.id AND te.status='active')""" if trials else ''
    active = conn.execute(f"""SELECT COUNT(DISTINCT k.user_id) FROM vpn_keys k
        WHERE datetime(k.expires_at)>datetime(?) {exclude_trial}
          AND EXISTS(SELECT 1 FROM payments p WHERE p.user_id=k.user_id AND {PAYMENT})""",
        (now_utc,)).fetchone()[0]
    first = conn.execute(f"""WITH first_payment AS (
        SELECT p.user_id,MIN(datetime(p.paid_at)) AS first_at FROM payments p
        WHERE {PAYMENT} GROUP BY p.user_id)
        SELECT COUNT(*) FROM first_payment
        WHERE date(first_at,'+3 hours')=date(?,'+3 hours')""", (now_utc,)).fetchone()[0]
    return {'paid': int(active), 'first_paid_today': int(first)}
