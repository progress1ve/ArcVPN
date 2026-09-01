from unittest.mock import patch

import subscription_api as api
from subscription_api import _happ_add_url, _happ_subscription_target
from subscription_pages import render_silent_import_page, render_silent_incy_import_page


def test_happ_import_url_has_no_external_provider_binding():
    source = "https://sub.arccnet.space/sub/stable?format=json&device=browser"
    target = _happ_subscription_target(source)
    deeplink = _happ_add_url(source)

    assert target == source + "&arc-order=manual-v2"
    assert deeplink == f"happ://add/{target}"
    assert "providerid" not in target.lower()


def test_happ_import_order_revision_is_idempotent():
    source = "https://sub.arccnet.space/sub/stable?format=json&arc-order=old"

    target = _happ_subscription_target(source)

    assert target.count("arc-order=") == 1
    assert target.endswith("arc-order=manual-v2")


def test_browser_import_bridge_has_no_provider_id():
    sub_id = "master_subscription_123"
    response = api.app.test_client().get(f"/import/{sub_id}")

    assert response.status_code == 200
    assert b"providerid" not in response.data.lower()


def test_device_scoped_import_url_has_no_provider_id():
    sub_id = "master_subscription_123"
    device_sub_id = "device_subscription_456"
    with patch("subscription_api.register_import_device", return_value=device_sub_id):
        response = api.app.test_client().post(
            f"/api/device/import/{sub_id}",
            json={"device_token": "device_token_1234567890"},
        )

    assert response.status_code == 200
    import_url = response.get_json()["import_url"]
    assert import_url.endswith(f"/sub/{device_sub_id}?format=json&arc-order=manual-v2")
    assert "providerid" not in import_url.lower()


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


def test_incy_import_bridge_is_black_and_opens_fragment_payload():
    page = render_silent_incy_import_page()

    assert "background:#02060c" in page
    assert "location.hash.slice(1)" in page
    assert "incy://crypt1/${payload}" in page
    assert "setTimeout(openIncy, 40)" in page

    response = api.app.test_client().get("/import/incy")
    assert response.status_code == 200
    assert response.headers["Cache-Control"].startswith("private, no-store")
