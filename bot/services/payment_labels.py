"""Human payment purpose, independent of its payment method/base tariff."""

def payment_label(row: dict) -> str:
    operation = row.get("operation_type") or ""
    lte = int(row.get("addon_lte_gb") or (row.get("addon_units") if row.get("addon_kind") == "lte" else 0) or 0)
    devices = int(row.get("addon_device_units") or (row.get("addon_units") if row.get("addon_kind") == "device" else 0) or 0)
    if operation.startswith("addon_") or row.get("addon_kind"):
        parts = ([f"{devices} устр." ] if devices else []) + ([f"{lte} ГБ обхода"] if lte else [])
        return "Докупка · " + (" + ".join(parts) or {"addon_device":"устройств", "addon_lte":"обхода"}.get(operation,"устройств и обхода"))
    if operation == "topup":
        return "Пополнение баланса"
    if row.get("offer_code") == "email_paid_trial" or row.get("payment_type") == "trial":
        return "Пробная подписка"
    custom = bool(row.get("is_custom_tariff")) or any(
        row.get(requested) is not None and row.get(base) is not None and int(row[requested]) != int(row[base])
        for requested, base in [("requested_device_limit", "tariff_device_limit"), ("requested_lte_quota_gb", "tariff_lte_quota_gb")]
    )
    if custom:
        parts = ["Свой тариф"]
        if row.get("period_days"): parts.append(f"{int(row['period_days'])} дн.")
        if row.get("requested_device_limit") is not None: parts.append(f"{int(row['requested_device_limit'])} устр.")
        if row.get("requested_lte_quota_gb") is not None: parts.append(f"{int(row['requested_lte_quota_gb'])} ГБ обхода")
        return " · ".join(parts)
    return str(row.get("tariff_name") or "Подписка")
