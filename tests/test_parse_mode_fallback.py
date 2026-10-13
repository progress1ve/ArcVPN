from bot.middlewares.parse_mode_fallback import _plain_text
from bot.middlewares.parse_mode_fallback import _unformatted, SafeParseSession
import asyncio
from types import SimpleNamespace
import pytest
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage, SendPhoto, EditMessageMedia, SendMediaGroup
from aiogram.types import InputMediaPhoto, MessageEntity


def test_invalid_html_fallback_does_not_show_raw_tags():
    assert _plain_text('💙 <b>Спасибо!</b> <code>A&amp;B</code>') == '💙 Спасибо! A&B'


@pytest.mark.parametrize('method', [
    SendMessage(chat_id=1, text='<b>Спасибо</b><br>ArcVPN', parse_mode='HTML'),
    SendPhoto(chat_id=1, photo='fixture', caption='<b>Спасибо</b><br>ArcVPN', parse_mode='HTML'),
    EditMessageMedia(chat_id=1, message_id=2, media=InputMediaPhoto(media='fixture', caption='<b>Спасибо</b><br>ArcVPN', parse_mode='HTML')),
    SendMediaGroup(chat_id=1, media=[InputMediaPhoto(media='fixture', caption='<b>Спасибо</b><br>ArcVPN', parse_mode='HTML')]),
])
def test_transport_retries_text_caption_and_nested_media_as_plain(monkeypatch, method):
    sent = []
    async def request(self, bot, value, timeout=None):
        sent.append(value)
        if len(sent) == 1: raise TelegramBadRequest(method=value, message="can't parse entities: unsupported start tag br")
        return 'delivered'
    monkeypatch.setattr(AiohttpSession, 'make_request', request)
    bot = SimpleNamespace(default=DefaultBotProperties())
    session = SafeParseSession()
    assert asyncio.run(session.make_request(bot, method)) == 'delivered'
    value = sent[1]
    if getattr(value, 'media', None): value = value.media[0] if isinstance(value.media, list) else value.media
    assert (getattr(value, 'text', None) or value.caption) == 'Спасибо\nArcVPN'
    assert value.parse_mode is None
    assert sent[0] is method


def test_entities_default_mode_and_plain_literals_are_preserved():
    bot = SimpleNamespace(default=DefaultBotProperties(parse_mode='HTML'))
    assert _unformatted(SendMessage(chat_id=1, text='<b>A&amp;B</b>'), bot).text == 'A&B'
    value = SendPhoto(chat_id=1, photo='fixture', caption='2 < 3 & <name>', parse_mode=None,
                      caption_entities=[MessageEntity(type='bold', offset=0, length=1)])
    plain = _unformatted(value, bot)
    assert plain.caption == value.caption and plain.caption_entities is None
    assert value.caption_entities  # Do not mutate the original retry input.
    markdown = SendMessage(chat_id=1, text='link <https://example.com>', parse_mode='MarkdownV2')
    assert _unformatted(markdown, bot).text == markdown.text


def test_unrelated_telegram_errors_are_not_retried(monkeypatch):
    calls = []
    async def request(self, bot, value, timeout=None):
        calls.append(value)
        raise TelegramBadRequest(method=value, message='chat not found')
    monkeypatch.setattr(AiohttpSession, 'make_request', request)
    method = SendMessage(chat_id=1, text='<b>Hello</b>', parse_mode='HTML')
    with pytest.raises(TelegramBadRequest):
        asyncio.run(SafeParseSession().make_request(SimpleNamespace(default=DefaultBotProperties()), method))
    assert len(calls) == 1
