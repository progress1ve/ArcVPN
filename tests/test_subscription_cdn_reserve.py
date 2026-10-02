from unittest.mock import patch

import subscription_api as api
from bot.handlers.user.keys import _reserve_subscription_url, _subscription_urls


def test_reserve_uses_same_identifier_and_keeps_primary_import_path():
    primary, import_url = _subscription_urls("example-device-alias")
    reserve = _reserve_subscription_url("example-device-alias")

    assert primary == "https://sub.arccnet.space/sub/example-device-alias"
    assert import_url == "https://sub.arccnet.space/import/example-device-alias"
    assert reserve == "https://cdn-de.arccnet.space/sub/example-device-alias"


def test_authenticated_status_exposes_only_get_reserve_for_existing_subscription():
    keys = [
        {"id": 1, "sub_id": "existing-id", "is_active": True},
        {"id": 2, "sub_id": None, "is_active": False},
    ]
    with (
        api.app.test_request_context("/api/status"),
        patch.object(api, "_webapp_telegram_id", return_value=42),
        patch.object(api, "get_user_entitlements", return_value={}),
        patch.object(api, "get_user_keys_for_display", return_value=keys),
        patch.object(api, "_public_links", return_value={}),
    ):
        response = api.api_status()

    published = response.get_json()["keys"]
    assert published[0]["sub_url"] == "https://sub.arccnet.space/sub/existing-id"
    assert published[0]["reserve_sub_url"] == "https://cdn-de.arccnet.space/sub/existing-id"
    assert published[0]["import_url"] == "https://sub.arccnet.space/import/existing-id"
    assert published[1]["reserve_sub_url"] is None
    assert "no-store" in response.headers["Cache-Control"]
