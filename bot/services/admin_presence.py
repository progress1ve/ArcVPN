"""Resolve multiple VPN identities to one customer for admin counters."""

def unique_customer_presence(presences: list[dict], customers: list[dict]) -> list[dict]:
    by_telegram = {}
    by_name = {}
    for customer in customers:
        by_telegram[str(customer["telegram_id"])] = customer["id"]
        for name in (customer.get("panel_email"), customer.get("lte_panel_username")):
            if name: by_name[str(name)] = customer["id"]
    unique = {}
    for presence in presences:
        customer_id = by_telegram.get(str(presence.get("telegram_id")))
        if customer_id is None:
            customer_id = by_name.get(str(presence.get("username")))
        if customer_id is None: continue
        previous = unique.get(customer_id)
        if previous is None or str(presence.get("online_at") or "") > str(previous.get("online_at") or ""):
            unique[customer_id] = presence
    return list(unique.values())
