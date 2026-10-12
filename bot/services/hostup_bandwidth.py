"""Owner-only hosting allowance monitor; no customer quota changes."""
import asyncio
import json
import logging
import math
import os
import time
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)
INTERVAL = 12 * 3600
THRESHOLD_GB = 150
STATE_KEY = 'hostup_bandwidth_monitor_state'
BASE_URL = 'https://cloud.hostup.se/api/v2'


def credentials():
    path = Path(os.environ.get('HOSTUP_MONITOR_ENV', Path(__file__).resolve().parents[2] / '.secrets/hostup-monitor.env'))
    if not path.exists():
        return None
    values = dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line and not line.startswith('#'))
    return values


def allowance_state(payload, previous):
    period = payload.get('period') or {}
    start = period.get('startAt')
    if not start:
        raise ValueError('Missing allowance period')
    allowance = payload['allowance']
    used, limit = float(allowance['usedGb']), float(allowance['limitGb'])
    if not all(math.isfinite(x) for x in (used, limit)) or used < 0 or limit <= 0:
        raise ValueError('Invalid allowance')
    remaining = max(0, limit - used)
    state = dict(previous)
    if state.get('period') != start or remaining > THRESHOLD_GB:
        state['notified'] = False
    state.update(period=start, used_gb=used, limit_gb=limit, remaining_gb=remaining)
    return state, remaining <= THRESHOLD_GB and not state.get('notified', False)


async def fetch_allowance(values):
    headers = {'Authorization': 'Bearer ' + values['HOSTUP_API_KEY'], 'Accept': 'application/json',
               'User-Agent': 'ArcVPN-Bandwidth-Monitor/1.0'}
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get(BASE_URL + '/vps', params={'primaryIp': values['HOSTUP_SERVER_IP']}) as response:
            response.raise_for_status()
            items = (await response.json())['data']
        matches = [item for item in items if item.get('primaryIp') == values['HOSTUP_SERVER_IP']]
        if len(matches) != 1:
            raise ValueError('Expected one VPS matching configured IP')
        async with session.get(BASE_URL + '/vps/' + matches[0]['id'] + '/bandwidth') as response:
            response.raise_for_status()
            return await response.json()


async def check_once(bot, values, previous, now):
    state = dict(previous)
    state['next_check'] = now + INTERVAL
    try:
        payload = await fetch_allowance(values)
        state, notify = allowance_state(payload, state)
        state.update(last_success=now, failure_since=None, failure_notified=False)
        if notify:
            await bot.send_message(int(values['HOSTUP_NOTIFICATION_CHAT_ID']),
                f"🇸🇪 Швеция: осталось {state['remaining_gb']:.1f} ГБ из {state['limit_gb']:g} ГБ.\n"
                "Пора докупить трафик.\nИсточник: HostUp. Проверка каждые 12 часов.", parse_mode=None)
            state['notified'] = True
        logger.info('HostUp allowance checked: remaining %.1f GB', state['remaining_gb'])
    except Exception as error:
        # Error bodies/headers may contain provider or authentication details.
        logger.warning('HostUp allowance check failed (%s)', type(error).__name__)
        if state.get('failure_since') is None:
            state['failure_since'] = now
        if now - state['failure_since'] >= 24 * 3600 and not state.get('failure_notified'):
            try:
                await bot.send_message(int(values['HOSTUP_NOTIFICATION_CHAT_ID']),
                    '⚠️ Не удалось проверить остаток трафика Швеции в HostUp более суток. Проверьте кабинет хостинга.',
                    parse_mode=None)
                state['failure_notified'] = True
            except Exception:
                logger.warning('HostUp monitor notification delivery failed')
    return state


async def run_hostup_bandwidth_monitor(bot):
    from database.db_settings import get_setting, set_setting
    values = credentials()
    if not values:
        logger.info('HostUp bandwidth monitor disabled: no credentials file')
        return
    logger.info('HostUp bandwidth monitor started: interval=12h threshold=150GB')
    while True:
        try:
            raw = get_setting(STATE_KEY)
            state = json.loads(raw) if raw else {}
            now = time.time()
            delay = float(state.get('next_check', 0)) - now
            if delay > 0:
                await asyncio.sleep(min(delay, INTERVAL))
                continue
            state = await check_once(bot, values, state, now)
            set_setting(STATE_KEY, json.dumps(state))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning('HostUp monitor state failed (%s)', type(error).__name__)
            await asyncio.sleep(INTERVAL)
