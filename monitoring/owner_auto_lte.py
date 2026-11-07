"""Expiring owner-only JSON Auto trial; CDN remains strict backup."""
import copy
import json
import math
from pathlib import Path
import time
from monitoring.royale_owner import OWNER

STATE = Path(__file__).resolve().parents[1] / '.secrets/owner-auto-lte.json'
NAME = '🇳🇱 Автовыбор · тест LTE'


def apply(profiles, telegram_id):
    if telegram_id != OWNER:
        return profiles
    try:
        state = json.loads(STATE.read_text())
        expires = state['expires_at']
        if (state.get('enabled') is not True or isinstance(expires, bool)
                or not isinstance(expires, (int, float)) or not math.isfinite(expires)
                or not 0 < expires - time.time() <= 86460):
            return profiles
    except (OSError, ValueError, TypeError, KeyError):
        return profiles
    source = next((p for p in profiles if 'Автовыбор' in p.get('remarks', '')
                   and p.get('remarks') != NAME), None)
    if source is None:
        return profiles
    trial = copy.deepcopy(source)
    reserve = next((b for b in trial.get('routing', {}).get('balancers', [])
                    if b.get('tag') == 'auto-cdn-ping'), None)
    if reserve is None:
        return profiles  # No LTE authorization, no fabricated access.
    reserve['strategy'] = {'type': 'leastLoad', 'settings': {
        'expected': 2, 'maxRTT': '3s', 'baselines': ['200ms', '400ms'], 'tolerance': 0.05}}
    trial['burstObservatory']['pingConfig']['httpMethod'] = 'GET'
    trial['remarks'] = NAME
    result = [p for p in profiles if p.get('remarks') != NAME]
    result.insert(result.index(source) + 1, trial)
    return result
