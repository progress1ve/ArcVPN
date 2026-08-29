from unittest.mock import patch

import subscription_api as api
from subscription_api import _happ_add_url, _happ_subscription_target
from subscription_pages import render_silent_import_page


def test_happ_provider_id_is_attached_as_client_only_fragment():
    source = "https://sub.arccnet.space/sub/stable?format=json&device=browser"
    with patch("subscription_api.HAPP_PROVIDER_ID", "Ab12_-Cd"):
        target = _happ_subscription_target(source)
        deeplink = _happ_add_url(source)

    assert target == f"{source}#?providerid=Ab12_-Cd"
    assert deeplink == f"happ://add/{source}#?providerid=Ab12_-Cd"


def test_happ_provider_fragment_is_omitted_for_invalid_id():
    source = "https://sub.arccnet.space/sub/stable?format=json"
    with patch("subscription_api.HAPP_PROVIDER_ID", "not valid"):
        assert _happ_subscription_target(source) == source
        assert _happ_add_url(source) == f"happ://add/{source}"


def test_browser_import_bridge_carries_provider_id_into_fallback_target():
    sub_id = "master_subscription_123"
    with patch("subscription_api.HAPP_PROVIDER_ID", "Ab12_-Cd"):
        response = api.app.test_client().get(f"/import/{sub_id}")

    assert response.status_code == 200
    assert b"#?providerid=Ab12_-Cd" in response.data


def test_device_scoped_import_url_carries_provider_id():
    sub_id = "master_subscription_123"
    device_sub_id = "device_subscription_456"
    with patch("subscription_api.HAPP_PROVIDER_ID", "Ab12_-Cd"), patch(
        "subscription_api.register_import_device", return_value=device_sub_id
    ):
        response = api.app.test_client().post(
            f"/api/device/import/{sub_id}",
            json={"device_token": "device_token_1234567890"},
        )

    assert response.status_code == 200
    assert response.get_json()["import_url"].endswith(
        f"/sub/{device_sub_id}?format=json#?providerid=Ab12_-Cd"
    )


def test_silent_import_uses_registered_device_subscription_url():
    page = render_silent_import_page(
        js_subscription_url='"https://sub.arccnet.space/sub/master?format=plain"',
        js_device_registration_url='"https://sub.arccnet.space/api/device/import/master"',
    )

    assert "await register()" in page
    assert "result?.import_url?.startsWith('happ://add/')" in page
    assert "target.searchParams.set('device', deviceToken())" in page
    assert "target.pathname = `/sub/" not in page
    assert "xhr.open('POST', registrationUrl, false)" not in page
