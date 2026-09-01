from pathlib import Path


SOURCE = Path("webapp/src/views/HomeFlowPreview.svelte")


def test_incy_import_keeps_custom_scheme_navigation_inside_user_click():
    source = SOURCE.read_text(encoding="utf-8")

    assert "@incy/link-encoder/sync" in source
    assert "@incy/link-encoder/web" not in source
    assert "const incyUrl = encryptIncyLink(subKey.sub_url" in source
    assert "await encryptIncyLink" not in source
    assert "function incyBridgeUrl(incyUrl)" in source
    assert "`${origin}/import/incy#${encodeURIComponent(payload)}`" in source
    assert "openExternal(incyBridgeUrl(incyUrl))" in source
    assert "intent://" not in source


def test_both_client_cards_use_supported_badge():
    source = SOURCE.read_text(encoding="utf-8")

    assert "<em>Поддерживается</em>" in source
    assert "'Рекомендуем'" not in source


def test_desktop_connection_flow_is_vertically_centered():
    source = SOURCE.read_text(encoding="utf-8")

    assert ".connect-page { display: flex; flex-direction: column; justify-content: center;" in source
    assert "<span>Назад</span>" in source
