"""Read-only operational profile; unknown telemetry stays unknown."""
from decimal import Decimal


def payment_amounts(row):
    kind = row.get('payment_type') or ''
    amount = Decimal(str(row.get('amount_cents') or 0))
    provider = bool(row.get('yookassa_payment_id'))
    rub = amount / 100 if provider else amount if kind in ('yookassa', 'yookassa_qr', 'cards', 'balance') else Decimal(0)
    return {'rub': float(rub), 'usd': float(amount / 100) if kind == 'crypto' else 0,
            'stars': int(row.get('amount_stars') or 0)}


def profile_facts(conn, user_id, subscriptions):
    """Totals use all successful purchases, never the truncated detail page."""
    totals = {'rub': Decimal(0), 'usd': Decimal(0), 'stars': 0, 'count': 0}
    latest_by_key = {}
    columns = {row[1] for row in conn.execute('PRAGMA table_info(payments)')}
    fields = ['payment_type', 'yookassa_payment_id', 'amount_cents', 'amount_stars',
              'status', 'operation_type', 'offer_code', 'paid_at', 'tariff_id', 'id']
    fields += [field for field in ('vpn_key_id', 'is_custom_tariff', 'requested_device_limit',
                                 'requested_lte_quota_gb', 'period_days') if field in columns]
    date_sql = 'COALESCE(p.paid_at,p.fulfilled_at)' if 'fulfilled_at' in columns else 'p.paid_at'
    payments = conn.execute('SELECT ' + ','.join('p.' + field for field in fields) + ',t.device_limit AS tariff_device_limit,t.lte_quota_gb AS tariff_lte_quota_gb FROM payments p LEFT JOIN tariffs t ON t.id=p.tariff_id WHERE p.user_id=? ORDER BY ' + date_sql + ' DESC,p.id DESC', (user_id,))
    for source in payments:
        row = dict(source)
        if row['status'] not in ('paid', 'succeeded'):
            continue
        operation = row.get('operation_type') or ''
        if operation != 'topup' and row['payment_type'] != 'trial':
            values = payment_amounts(row)
            if any(values.values()):
                for currency in ('rub', 'usd'):
                    totals[currency] += Decimal(str(values[currency]))
                totals['stars'] += values['stars']
                totals['count'] += 1
        if operation in ('new', 'renew', 'renewal', 'subscription'):
            target = row.get('vpn_key_id')
            # Legacy new purchases have no key FK. A sole retained key of the
            # same tariff is the only safe local association; multiple keys
            # remain unclassified rather than borrowing another key's plan.
            if not target and operation == 'new' and len(subscriptions) == 1 and row.get('tariff_id') == subscriptions[0].get('tariff_id'):
                target = subscriptions[0]['id']
            if target:
                latest_by_key.setdefault(int(target), row)
    for sub in subscriptions:
        purchase = latest_by_key.get(int(sub['id']))
        if not purchase and conn.execute('SELECT 1 FROM trial_entitlements WHERE vpn_key_id=?', (sub['id'],)).fetchone():
            sub['is_trial'] = True
        custom = purchase and (purchase.get('is_custom_tariff') or any(
            purchase.get(requested) is not None and purchase.get(base) is not None
            and int(purchase[requested]) != int(purchase[base])
            for requested, base in [('requested_device_limit','tariff_device_limit'),('requested_lte_quota_gb','tariff_lte_quota_gb')]))
        sub['plan_kind'] = 'trial' if sub.get('is_trial') else 'custom' if custom else 'standard' if sub.get('tariff_name') else 'unknown'
        sub['plan_name'] = 'Триал' if sub['plan_kind'] == 'trial' else 'Кастомный тариф' if sub['plan_kind'] == 'custom' else sub.get('tariff_name') or 'Название тарифа не сохранено'
        sub['plan_purchase'] = {key: purchase.get(key) for key in ('requested_device_limit', 'requested_lte_quota_gb', 'period_days')} if purchase else None
        if sub.get('panel_disabled_at'):
            sub['active'] = 0
    dates = [str(sub['created_at']) for sub in subscriptions if sub.get('created_at')]
    return {'first_subscription_at': min(dates) if dates else None,
            'purchase_totals': {**totals, 'rub': float(totals['rub']), 'usd': float(totals['usd'])}}
