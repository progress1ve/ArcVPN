import asyncio
from unittest.mock import AsyncMock
import subscription_api as api
from bot.handlers.user import start

def test_support_deeplink_uses_configured_bot(monkeypatch):
    monkeypatch.setattr(api, '_get_bot_username', lambda: 'ArcVPN_test_bot')
    assert api._subscription_support_url() == 'https://t.me/ArcVPN_test_bot?start=help'

def test_help_callback_and_deeplink_share_same_menu(monkeypatch):
    editor = AsyncMock()
    monkeypatch.setattr(start, 'safe_edit_or_send', editor)
    asyncio.run(start.show_fallback_help(object()))
    assert 'Помощь ArcVPN' in editor.call_args.args[1]
    keyboard = editor.call_args.kwargs['reply_markup']
    assert keyboard.inline_keyboard[0][0].callback_data == 'bot_faq:connect'
