from bot.services import remnawave_stats


def test_environment_authority_has_stable_cache_identity(monkeypatch):
    monkeypatch.setattr(remnawave_stats, "get_all_servers", lambda: [])
    authority = remnawave_stats.remnawave_authority_config()
    assert authority["id"] == -1
    assert authority["panel_type"] == "remnawave"
