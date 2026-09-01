from pathlib import Path


SOURCE = Path("webapp/src/views/HomeFlowPreview.svelte")


def test_incy_import_keeps_custom_scheme_navigation_inside_user_click():
    source = SOURCE.read_text(encoding="utf-8")

    assert "@incy/link-encoder/sync" in source
    assert "@incy/link-encoder/web" not in source
    assert "const incyUrl = encryptIncyLink(subKey.sub_url" in source
    assert "await encryptIncyLink" not in source


def test_both_client_cards_use_supported_badge():
    source = SOURCE.read_text(encoding="utf-8")

    assert "<em>Поддерживается</em>" in source
    assert "'Рекомендуем'" not in source
