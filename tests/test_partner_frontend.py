import subscription_api as api


def test_partner_serves_own_react_entry_without_admin_fallback(tmp_path, monkeypatch):
    partner = tmp_path / "partner"
    partner.mkdir()
    (partner / "partner.html").write_text('<div id="root">partner-entry</div>')
    admin = tmp_path / "admin"
    admin.mkdir()
    (admin / "index.html").write_text("admin-entry")
    monkeypatch.setattr(api, "PARTNER_WEBAPP_DIST_DIR", str(partner))
    monkeypatch.setattr(api, "ADMIN_WEBAPP_DIST_DIR", str(admin))
    client = api.app.test_client()
    response = client.get("/partner")
    assert response.status_code == 200
    assert b"partner-entry" in response.data and b"admin-entry" not in response.data
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert client.get("/admin").data == b"admin-entry"


def test_partner_assets_only_from_partner_bundle_and_missing_paths_are_404(tmp_path, monkeypatch):
    partner = tmp_path / "partner"
    (partner / "assets").mkdir(parents=True)
    (partner / "assets" / "partner.js").write_text("partner-react")
    (partner / "partner.html").write_text("private-entry")
    monkeypatch.setattr(api, "PARTNER_WEBAPP_DIST_DIR", str(partner))
    client = api.app.test_client()
    assert client.get("/partner-assets/assets/partner.js").data == b"partner-react"
    for path in ("missing.js", "../partner.html", "../../admin_webapp_dist/index.html"):
        assert client.get("/partner-assets/assets/" + path).status_code == 404
    assert client.get("/partner-assets/partner.html").status_code == 404
