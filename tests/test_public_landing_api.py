import subscription_api as api


def _client(monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", True)
    return api.app.test_client()


def test_public_tariffs_are_allowlisted_and_conditional(monkeypatch):
    monkeypatch.setattr(api, "get_all_tariffs", lambda: [{
        "id": 7,
        "product_code": "standard",
        "name": "Стандарт 3",
        "period_months": 3,
        "duration_days": 90,
        "price_rub": 399,
        "device_limit": 3,
        "traffic_limit_gb": 0,
        "lte_quota_gb": 45,
        "lte_cycle_days": 30,
        "payment_provider_secret": "must-not-leak",
    }, {
        "id": 99, "product_code": "internal", "period_months": 3, "price_rub": 1,
    }])
    client = _client(monkeypatch)
    response = client.get("/api/public/tariffs")
    assert response.status_code == 200
    tariff = response.get_json()["tariffs"][0]
    assert set(tariff) == {
        "product_code", "name", "period_months", "duration_days",
        "price_rub", "monthly_rub", "device_limit", "traffic_limit_gb",
        "lte_quota_gb", "lte_cycle_days",
    }
    assert tariff["monthly_rub"] == 133
    assert len(response.get_json()["tariffs"]) == 1
    conditional = client.get("/api/public/tariffs", headers={"If-None-Match": response.headers["ETag"]})
    assert conditional.status_code == 304


def test_public_config_hides_non_https_optional_links(monkeypatch):
    monkeypatch.setattr(api, "_get_bot_username", lambda: "arcvpn_bot")
    monkeypatch.setattr(api, "_public_links", lambda: {
        "support_url": "javascript:alert(1)",
        "channel_url": "http://example.test/channel",
        "legal_url": "https://arccnet.space/legal/user-agreement",
    })
    monkeypatch.setattr(api, "get_setting", lambda key, default="": {
        "instagram_url": "https://instagram.com/arcvpn",
        "tiktok_url": "",
        "status_page_url": "/status",
    }.get(key, default))
    config = _client(monkeypatch).get("/api/public/config").get_json()
    assert config["support_url"] == ""
    assert config["channel_url"] == ""
    assert config["status_url"] == ""
    assert config["instagram_url"] == "https://instagram.com/arcvpn"


def test_public_catalog_contains_only_safe_ui_projection(monkeypatch):
    monkeypatch.setattr(api, "SUBSCRIPTION_INBOUND_ORDER", ["EE_VLESS", "LTE_VLESS"])
    monkeypatch.setattr(api, "_catalog_overrides", lambda: {
        "EE_VLESS": {"display_name": "Эстония", "sort_order": 4, "host": "secret.example"},
        "LTE_VLESS": {"display_name": "Лучший обход", "sort_order": 8},
    })
    monkeypatch.setattr(api, "_subscription_protocol_label", lambda _name: "VLESS")
    response = _client(monkeypatch).get("/api/public/subscription-catalog")
    assert response.status_code == 200
    profiles = response.get_json()["profiles"]
    assert profiles[0]["kind"] == "auto"
    assert {profile["kind"] for profile in profiles} == {"auto", "location", "bypass"}
    assert all(set(profile) == {"display_name", "kind", "sort_order"} for profile in profiles)
    serialized = response.get_data(as_text=True).lower()
    assert all(value not in serialized for value in ("protocol", "host", "port", "uuid", "secret.example"))


def test_public_custom_quote_uses_server_calculator(monkeypatch):
    catalog = [{"id": 2, "product_code": "standard", "period_months": 3, "price_rub": 399}]
    monkeypatch.setattr(api, "get_all_tariffs", lambda: catalog)
    monkeypatch.setattr(api, "_custom_tariff_quote", lambda selected, devices, lte, items: {
        "price_rub": 512, "monthly_rub": 171, "device_limit": devices, "lte_quota_gb": lte,
    })
    response = _client(monkeypatch).get(
        "/api/public/custom-tariff-quote?period_months=3&device_limit=5&lte_quota_gb=75"
    )
    assert response.status_code == 200
    assert response.get_json()["price_rub"] == 512
    assert response.get_json()["device_limit"] == 5


def test_public_sitemap_excludes_private_app_routes(monkeypatch):
    response = _client(monkeypatch).get("/sitemap.xml", headers={"Host": "arccnet.space"})
    body = response.get_data(as_text=True)
    assert "https://arccnet.space/" in body
    assert "https://arccnet.space/legal/user-agreement" in body
    assert "/app" not in body and "/admin" not in body and "/import" not in body
