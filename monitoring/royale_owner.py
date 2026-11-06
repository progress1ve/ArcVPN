"""Owner-only delivery of the direct RoyaleHosting Netherlands node."""
import copy
import json
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

STATE = Path(__file__).resolve().parents[1] / '.secrets/royale-owner-nl.json'
OWNER = 2075630349
NAME = '🇳🇱 Нидерланды · Royale'
DOMAIN = 'nl.arccnet.space'


def load(telegram_id):
    if telegram_id != OWNER:
        return None
    try:
        state = json.loads(STATE.read_text())
        if state.get('enabled') and state.get('public_key') and state.get('short_id'):
            return state
    except (OSError, ValueError):
        pass
    return None


def apply(profiles, state):
    if not state:
        return profiles
    for index, source in enumerate(profiles):
        if source.get('remarks') != '🇸🇪 Швеция':
            continue
        profile = copy.deepcopy(source)
        outbound = next((o for o in profile['outbounds'] if o.get('protocol') == 'vless'), None)
        if not outbound or outbound.get('streamSettings', {}).get('security') != 'reality':
            return profiles
        profile['remarks'] = NAME
        outbound['settings']['vnext'][0].update(address=DOMAIN, port=443)
        outbound['streamSettings']['realitySettings'].update(
            serverName=DOMAIN, publicKey=state['public_key'], shortId=state['short_id'], fingerprint='firefox')
        return profiles[:index] + [profile] + profiles[index:]
    return profiles


def apply_links(links, state):
    if not state:
        return links
    for index, link in enumerate(links):
        parsed = urlsplit(link)
        if parsed.scheme != 'vless' or unquote(parsed.fragment) != '🇸🇪 Швеция':
            continue
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if query.get('security') != 'reality':
            return links
        query.update(sni=DOMAIN, pbk=state['public_key'], sid=state['short_id'], fp='firefox')
        authority = parsed.netloc.rsplit('@', 1)[0] + '@' + DOMAIN + ':443'
        replacement = urlunsplit(('vless', authority, parsed.path, urlencode(query), quote(NAME)))
        return links[:index] + [replacement] + links[index:]
    return links
