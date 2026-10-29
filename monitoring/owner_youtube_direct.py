"""Owner-only trial: Lithuania for ordinary traffic, direct Moscow for YouTube."""
import copy
import json
from pathlib import Path

OWNER = 2075630349
NAME = '🇱🇹 Литва · YouTube напрямую'
STATE = Path(__file__).resolve().parents[1] / '.secrets/youtube-direct-owner-20261029.json'


def load():
    try:
        value = json.loads(STATE.read_text())
        return value if value.get('enabled') else None
    except (OSError, ValueError):
        return None


def apply(profiles, user_id, state=None):
    if user_id != OWNER:
        return profiles
    state = load() if state is None else state
    if not state or not state.get('enabled'):
        return profiles
    for index, source in enumerate(profiles):
        if source.get('remarks') != '🇱🇹 Литва':
            continue
        profile = copy.deepcopy(source)
        original = next((o for o in profile.get('outbounds', []) if o.get('protocol') == 'vless'
                         and o.get('streamSettings', {}).get('security') == 'reality'), None)
        if original is None:
            return profiles
        youtube = copy.deepcopy(original)
        youtube['tag'] = 'youtube-direct-ru'
        youtube['settings']['vnext'][0].update(address=state['address'], port=state['port'])
        youtube['streamSettings'].pop('finalmask', None)
        youtube['streamSettings']['realitySettings'].update({
            key: state[key] for key in ('serverName', 'publicKey', 'shortId')})
        youtube['streamSettings']['realitySettings']['fingerprint'] = 'firefox'
        changed = False
        for rule in profile.get('routing', {}).get('rules', []):
            domains = rule.get('domain', [])
            if any(term in domain for domain in domains for term in ('youtube', 'googlevideo', 'ytimg')):
                rule.pop('balancerTag', None)
                rule['outboundTag'] = youtube['tag']
                changed = True
        if not changed:
            return profiles
        profile['outbounds'].append(youtube)
        profile['remarks'] = NAME
        return profiles[:index+1] + [profile] + profiles[index+1:]
    return profiles
