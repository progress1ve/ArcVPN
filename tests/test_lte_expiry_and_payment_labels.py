from datetime import datetime, timezone
import pytest
from bot.services.lte_identity import lte_expiry_patch
from bot.services.payment_labels import payment_label

NOW = datetime(2026, 10, 4, tzinfo=timezone.utc)

def test_expired_lte_restored_without_resetting_quota_or_uuid():
    identity = {"subscription_expires_at": "2026-12-01 00:00:00", "lte_quota_gb": 5}
    user = {"id": "test", "expireAt": "2026-09-01T00:00:00Z", "status": "EXPIRED", "trafficLimitBytes": 500, "userTraffic": {"usedTrafficBytes": 300}}
    assert lte_expiry_patch(identity, user, NOW) == {"id": "test", "expireAt": "2026-12-01T00:00:00+00:00", "status": "ACTIVE"}

@pytest.mark.parametrize("status,used,quota,banned,expiry", [("DISABLED",0,5,False,"2026-12-01"),("LIMITED",0,5,False,"2026-12-01"),("EXPIRED",500,5,False,"2026-12-01"),("EXPIRED",0,0,False,"2026-12-01"),("EXPIRED",0,5,True,"2026-12-01"),("EXPIRED",0,5,False,"2026-09-01")])
def test_never_reactivates_revoked_exhausted_or_expired_access(status,used,quota,banned,expiry):
    patch = lte_expiry_patch({"subscription_expires_at":expiry,"lte_quota_gb":quota,"is_banned":banned}, {"id":"test","expireAt":"2026-09-01T00:00:00Z","status":status,"trafficLimitBytes":500,"userTraffic":{"usedTrafficBytes":used}}, NOW)
    assert "status" not in patch

@pytest.mark.parametrize("row,expected", [
 ({"operation_type":"addon_device","addon_device_units":1,"tariff_name":"Стандарт"},"Докупка · 1 устр."),
 ({"operation_type":"addon_lte","addon_kind":"lte","addon_units":10},"Докупка · 10 ГБ обхода"),
 ({"operation_type":"addon_combined","addon_lte_gb":5,"addon_device_units":2},"Докупка · 2 устр. + 5 ГБ обхода"),
 ({"operation_type":"topup"},"Пополнение баланса"),
 ({"tariff_name":"Стандарт","requested_device_limit":3,"tariff_device_limit":2,"requested_lte_quota_gb":15,"tariff_lte_quota_gb":45,"period_days":90},"Свой тариф · 90 дн. · 3 устр. · 15 ГБ обхода"),
 ({"is_custom_tariff":1,"tariff_name":"Стандарт"},"Свой тариф"),
 ({"requested_device_limit":2,"tariff_device_limit":2,"tariff_name":"Стандарт"},"Стандарт"),
])
def test_payment_labels(row,expected):
    assert payment_label(row)==expected
