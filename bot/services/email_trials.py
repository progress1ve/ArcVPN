"""Website trial policy; amounts and eligibility are owned by the server."""
from database.connection import get_db
from database.db_trials import get_trial_entitlement, get_standard_monthly_tariff
from database.db_webapp import email_paid_trial_state


def free_trial_available(account):
    if account.get('identity_source') != 'email' or not account.get('email_verified_at'):
        return False
    entitlement = get_trial_entitlement(int(account['id']))
    if account.get('used_trial') or entitlement and entitlement['status'] not in {'failed', 'provisioning'}:
        return False
    if email_paid_trial_state(int(account['id'])) not in {'available', 'canceled', 'failed'}:
        return False
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM payments WHERE user_id=? AND status IN ('paid','succeeded') LIMIT 1", (account['id'],)).fetchone():
            return False
        return bool(entitlement) or not conn.execute('SELECT 1 FROM vpn_keys WHERE user_id=? LIMIT 1', (account['id'],)).fetchone()


def offer_details():
    tariff = get_standard_monthly_tariff()
    return {'free_days': 1, 'paid_days': 7, 'paid_amount_rub': 10,
            'renewal_amount_rub': int(tariff['price_rub']) if tariff else None,
            'renewal_period_days': 30}


def paid_trial_eligible(account):
    if account.get('identity_source') != 'email' or not account.get('email_verified_at'):
        return False
    with get_db() as conn:
        if conn.execute("""SELECT 1 FROM payments WHERE user_id=? AND status IN ('paid','succeeded')
            AND COALESCE(offer_code,'')!='email_paid_trial' AND COALESCE(payment_type,'')!='trial' LIMIT 1""", (account['id'],)).fetchone():
            return False
        has_key = conn.execute('SELECT 1 FROM vpn_keys WHERE user_id=? LIMIT 1', (account['id'],)).fetchone()
    return not has_key or bool(get_trial_entitlement(int(account['id'])))


def recurring_terms(order):
    if order.get('offer_code') == 'email_paid_trial':
        # Old checkouts did not agree to the new monthly amount. Do not infer consent.
        amount, days = order.get('renewal_amount_cents'), order.get('renewal_period_days')
        if not amount or not days:
            return None
        return {'amount_cents': int(amount), 'period_days': int(days)}
    return {'amount_cents': order.get('amount_cents'), 'period_days': order.get('period_days')}
