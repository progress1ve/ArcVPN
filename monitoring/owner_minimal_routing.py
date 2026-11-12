"""Temporary minimal-routing comparison using the existing Royale tunnel."""

import copy
import json
import time
from pathlib import Path

from monitoring.royale_owner import OWNER, PUBLIC_NAME

STATE = Path(__file__).resolve().parents[1] / '.secrets/owner-minimal-routing.json'
NAME = '🇳🇱 NL · Минимальные правила'


def apply(profiles, telegram_id):
    if telegram_id != OWNER:
        return profiles
    try:
        expiry = json.loads(STATE.read_text(encoding='utf-8'))['expires_at']
    except (OSError, ValueError, TypeError, KeyError):
        return profiles
    if type(expiry) is not int or not 0 < expiry - time.time() <= 86460:
        return profiles
    source = next((profile for profile in profiles if profile.get('remarks') == PUBLIC_NAME), None)
    if source is None or not source.get('outbounds') or source['outbounds'][0].get('tag') != 'proxy':
        return profiles
    trial = copy.deepcopy(source)
    trial['remarks'] = NAME
    trial['routing'] = {
        'domainStrategy': 'IPIfNonMatch',
        'rules': [{'type': 'field', 'protocol': ['bittorrent'], 'outboundTag': 'direct'}],
    }
    return [profile for profile in profiles if profile.get('remarks') != NAME] + [trial]
