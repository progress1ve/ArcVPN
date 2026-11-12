"""Short-lived direct Royale XHTTP profiles for the owner."""
import copy
import json
import re
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlencode, urlsplit
from uuid import UUID

from monitoring.royale_owner import DOMAIN, OWNER, PUBLIC_NAME

STATE = Path(__file__).resolve().parents[1] / '.secrets/owner-xhttp-trial.json'
PORT = 18447
MODES = {
    '🇳🇱 NL · XHTTP Stream Up': 'stream-up',
    '🇳🇱 NL · XHTTP Stream One': 'stream-one',
}


def links_for_owner(telegram_id):
    if telegram_id != OWNER:
        return {}
    try:
        state = json.loads(STATE.read_text(encoding='utf-8'))
        if state.get('enabled') is not True:
            return {}
        expiry = state['expires_at']
        if type(expiry) is not int or not 0 < expiry - time.time() <= 86460:
            return {}
        path = state['path']
        if not re.fullmatch(r'/arc-diag-[0-9a-f]{32}/', path):
            return {}
        identity = UUID(state['uuid'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {}
    params = {
        'encryption': 'none', 'type': 'xhttp', 'security': 'tls',
        'sni': DOMAIN, 'host': DOMAIN, 'alpn': 'h2', 'fp': 'firefox', 'path': path,
    }
    return {
        name: f'vless://{identity}@{DOMAIN}:{PORT}?{urlencode({**params, "mode": mode})}#{quote(name)}'
        for name, mode in MODES.items()
    }


def apply_links(links, telegram_id):
    variants = links_for_owner(telegram_id)
    if not variants or not any(unquote(urlsplit(link).fragment) == PUBLIC_NAME for link in links):
        return links
    return [link for link in links if unquote(urlsplit(link).fragment) not in variants] + list(variants.values())


def apply(profiles, telegram_id, parse_outbound):
    variants = links_for_owner(telegram_id)
    source = next((profile for profile in profiles if profile.get('remarks') == PUBLIC_NAME), None)
    if not variants or source is None or not any(outbound.get('tag') == 'proxy' for outbound in source['outbounds']):
        return profiles
    result = [profile for profile in profiles if profile.get('remarks') not in variants]
    for name, link in variants.items():
        profile = copy.deepcopy(source)
        profile['remarks'] = name
        profile['outbounds'] = [
            parse_outbound(link, 'proxy') if outbound.get('tag') == 'proxy' else outbound
            for outbound in profile['outbounds']
        ]
        result.append(profile)
    return result
