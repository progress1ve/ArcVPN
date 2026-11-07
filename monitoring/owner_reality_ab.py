"""Expiring standalone Reality A/B profiles, delivered only to the owner."""
import copy
import json
import math
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit
from uuid import UUID

from monitoring.royale_owner import DOMAIN, OWNER, PUBLIC_NAME

STATE = Path(__file__).resolve().parents[1] / '.secrets/owner-reality-ab.json'
VARIANTS = (('🇳🇱 Тест A', 9443), ('🇳🇱 Тест B', 9445))


def load(telegram_id):
    if telegram_id != OWNER:
        return None
    try:
        state = json.loads(STATE.read_text())
        expires = state['expires_at']
        if (state.get('enabled') is not True or isinstance(expires, bool)
                or not isinstance(expires, (int, float)) or not math.isfinite(expires)
                or not 0 < expires - time.time() <= 86460):
            return None
        UUID(state['uuid'])
        if (not re.fullmatch(r'[A-Za-z0-9_-]{43}', state['public_key'])
                or not re.fullmatch(r'[a-f0-9]{16}', state['short_id'])):
            return None
        return state
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def apply(profiles, telegram_id):
    state = load(telegram_id)
    source = next((p for p in profiles if p.get('remarks') == PUBLIC_NAME), None)
    if not state or source is None:
        return profiles
    names = {name for name, _ in VARIANTS}
    result = [p for p in profiles if p.get('remarks') not in names]
    for name, port in VARIANTS:
        profile = copy.deepcopy(source)
        proxy = next(o for o in profile['outbounds'] if o.get('tag') == 'proxy')
        target = proxy['settings']['vnext'][0]
        target.update(address=DOMAIN, port=port)
        target['users'][0]['id'] = state['uuid']
        proxy['streamSettings']['realitySettings'].update(
            serverName=DOMAIN, publicKey=state['public_key'], shortId=state['short_id'])
        profile['remarks'] = name
        result.append(profile)
    return result


def apply_links(links, telegram_id):
    state = load(telegram_id)
    source = next((urlsplit(link) for link in links
                   if unquote(urlsplit(link).fragment) == PUBLIC_NAME), None)
    if not state or source is None:
        return links
    names = {name for name, _ in VARIANTS}
    result = [link for link in links if unquote(urlsplit(link).fragment) not in names]
    query = dict(parse_qsl(source.query, keep_blank_values=True))
    query.update(sni=DOMAIN, pbk=state['public_key'], sid=state['short_id'])
    for name, port in VARIANTS:
        result.append(urlunsplit(('vless', f"{state['uuid']}@{DOMAIN}:{port}",
                                  source.path, urlencode(query), quote(name))))
    return result
