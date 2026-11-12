"""Temporary M3T routing comparison using the existing Royale tunnel."""

import copy
import json
import time
from pathlib import Path

from monitoring.royale_owner import OWNER, PUBLIC_NAME

STATE = Path(__file__).resolve().parents[1] / '.secrets/owner-m3t-routing.json'
NAME = '🇳🇱 NL · Reality M3T'
RULE_FIELDS = {'domain', 'ip', 'outboundTag', 'port', 'protocol', 'ruleTag', 'type'}


def apply(profiles, telegram_id):
    if telegram_id != OWNER:
        return profiles
    try:
        state = json.loads(STATE.read_text(encoding='utf-8'))
        expiry = state['expires_at']
        routing = state['routing']
        rules = routing['rules']
    except (OSError, ValueError, TypeError, KeyError):
        return profiles
    if type(expiry) is not int or not 0 < expiry - time.time() <= 86460:
        return profiles
    if (set(routing) != {'domainStrategy', 'rules'} or routing['domainStrategy'] != 'IPOnDemand'
            or not isinstance(rules, list) or not rules
            or any(not isinstance(rule, dict) or set(rule) - RULE_FIELDS
                   or rule.get('outboundTag') not in ('direct', 'block')
                   for rule in rules)):
        return profiles
    source = next((profile for profile in profiles if profile.get('remarks') == PUBLIC_NAME), None)
    if source is None or not source.get('outbounds') or source['outbounds'][0].get('tag') != 'proxy':
        return profiles
    trial = copy.deepcopy(source)
    trial['remarks'] = NAME
    trial['routing'] = routing
    return [profile for profile in profiles if profile.get('remarks') != NAME] + [trial]
