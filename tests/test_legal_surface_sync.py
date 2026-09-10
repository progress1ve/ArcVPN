from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_webapp_uses_current_canonical_legal_document():
    source = (ROOT / "webapp/src/views/HomeFlowPreview.svelte").read_text(encoding="utf-8")

    assert "Редакция от 10 сентября 2026" in source
    assert 'href="/legal/user-agreement"' in source
    assert "Политика конфиденциальности" not in source or "Соглашение и конфиденциальность" in source
    assert "29 июля 2026" not in source
    assert "[УКАЖИТЕ" not in source


def test_bot_records_current_legal_version_and_names_both_documents():
    start = (ROOT / "bot/handlers/user/start.py").read_text(encoding="utf-8")
    gate = (ROOT / "bot/middlewares/subscription_check.py").read_text(encoding="utf-8")

    assert "get_setting('legal_consent_version', '2026-09-10')" in start
    assert "Пользовательское соглашение и Политику конфиденциальности" in gate


def test_daily_scheduler_keeps_local_backup_without_telegram_archive():
    source = (ROOT / "bot/services/scheduler.py").read_text(encoding="utf-8")
    daily = source[source.index("async def run_daily_tasks"):source.index("async def check_and_notify_updates")]

    assert "await maintain_local_backups()" in daily
    assert "await send_daily_stats(bot)" not in daily
    assert "send_document" not in daily
    assert "send_backup_archive" not in source
    assert "BufferedInputFile" not in source
