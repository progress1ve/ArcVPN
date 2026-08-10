from subscription_pages import render_silent_import_page


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
