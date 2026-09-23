"""Account-bound, time-limited offer for a connected trial that never converted."""

from .connection import get_db

OFFER_CODE = "ARCTRIAL20"
OFFER_KEY = "trial_winback_20"


def offer_discount(user_id: int, tariff: dict, *, custom: bool = False) -> bool:
    """The same check is used for a quote and for creating an order."""
    months = int(tariff.get("period_months") or round(int(tariff.get("duration_days") or 0) / 30))
    if custom or months != 3:
        return False
    with get_db() as conn:
        row = conn.execute("""
            SELECT 1 FROM trial_winback_offers offer
            WHERE offer.user_id=? AND offer.sent_at IS NOT NULL
              AND offer.sent_at>datetime('now','-48 hours')
              AND offer.claimed_order_id IS NULL
              AND EXISTS (SELECT 1 FROM trial_entitlements te WHERE te.user_id=offer.user_id)
              AND NOT EXISTS (
                SELECT 1 FROM payments p WHERE p.user_id=offer.user_id
                  AND p.status IN ('paid','succeeded')
                  AND COALESCE(p.payment_type,'')!='trial'
                  AND COALESCE(p.operation_type,'')!='trial_start'
                  AND COALESCE(p.offer_code,'')!='email_paid_trial'
              )
        """, (int(user_id),)).fetchone()
        return bool(row)


def claim_offer(user_id: int, order_id: str, discount_rub: int) -> bool:
    """Seal the single checkout; provider failures can explicitly release it."""
    with get_db() as conn:
        cur = conn.execute("""
            UPDATE trial_winback_offers SET claimed_order_id=?
            WHERE user_id=? AND claimed_order_id IS NULL
              AND sent_at>datetime('now','-48 hours')
              AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.user_id=?
                  AND p.status IN ('paid','succeeded')
                  AND COALESCE(p.payment_type,'')!='trial'
                  AND COALESCE(p.operation_type,'')!='trial_start'
                  AND COALESCE(p.offer_code,'')!='email_paid_trial')
        """, (order_id, int(user_id), int(user_id)))
        if cur.rowcount != 1:
            return False
        conn.execute("UPDATE payments SET offer_code=?,discount_rub=? WHERE order_id=? AND user_id=?",
                     (OFFER_KEY, int(discount_rub), order_id, int(user_id)))
        return True


def release_offer(user_id: int, order_id: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE trial_winback_offers SET claimed_order_id=NULL WHERE user_id=? AND claimed_order_id=?",
                     (int(user_id), order_id))
        conn.execute("UPDATE payments SET status='canceled' WHERE order_id=? AND user_id=? AND status='pending'",
                     (order_id, int(user_id)))
