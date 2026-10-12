import asyncio
import pytest
from bot.services import hostup_bandwidth as monitor


def payload(used=874, limit=1024, period='2026-10-06'):
    return {'period': {'startAt': period}, 'allowance': {'usedGb': used, 'limitGb': limit}}


def test_threshold_dedup_and_new_period():
    state, send = monitor.allowance_state(payload(873.9), {})
    assert not send
    state, send = monitor.allowance_state(payload(), state)
    assert send and state['remaining_gb'] == 150
    state['notified'] = True
    restored = __import__('json').loads(__import__('json').dumps(state))
    assert not monitor.allowance_state(payload(900), restored)[1]
    assert monitor.allowance_state(payload(900, period='2026-11-06'), restored)[1]


def test_topup_rearms_and_invalid_values_are_not_zero():
    state, _ = monitor.allowance_state(payload(900), {})
    state['notified'] = True
    state, send = monitor.allowance_state(payload(900, 2024), state)
    assert not send and not state['notified']
    assert monitor.allowance_state(payload(1900, 2024), state)[1]
    for data in (payload(float('nan')), payload(-1), payload(limit=0), {'period': None}):
        with pytest.raises((ValueError, KeyError)):
            monitor.allowance_state(data, {})


def test_delivery_only_once_and_persistent_schedule(monkeypatch):
    async def fetch(_): return payload()
    monkeypatch.setattr(monitor, 'fetch_allowance', fetch)
    class Bot:
        messages = []
        async def send_message(self, recipient, message, **kwargs): self.messages.append((recipient, message))
    bot = Bot()
    values = {'HOSTUP_NOTIFICATION_CHAT_ID': '123'}
    state = asyncio.run(monitor.check_once(bot, values, {}, 100))
    assert state['next_check'] == 100 + 43200 and state['notified']
    asyncio.run(monitor.check_once(bot, values, state, 43300))
    assert len(bot.messages) == 1 and bot.messages[0][0] == 123


def test_failed_delivery_retries_and_api_outage_warns_once(monkeypatch):
    async def fetch(_): return payload()
    monkeypatch.setattr(monitor, 'fetch_allowance', fetch)
    class Bot:
        fail = True
        messages = []
        async def send_message(self, recipient, message, **kwargs):
            if self.fail: raise RuntimeError('delivery failed')
            self.messages.append(message)
    bot = Bot()
    values = {'HOSTUP_NOTIFICATION_CHAT_ID': '123'}
    state = asyncio.run(monitor.check_once(bot, values, {}, 100))
    assert not state.get('notified')
    bot.fail = False
    state = asyncio.run(monitor.check_once(bot, values, state, 43300))
    assert state['notified'] and len(bot.messages) == 1
    async def broken(_): raise RuntimeError('provider unavailable')
    monkeypatch.setattr(monitor, 'fetch_allowance', broken)
    for now in (50000, 93200, 136400, 179600):
        state = asyncio.run(monitor.check_once(bot, values, state, now))
    assert len(bot.messages) == 2 and state['failure_notified']
