"""Delivery of the direct RoyaleHosting Netherlands node."""
import copy
import json
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

STATE = Path(__file__).resolve().parents[1] / '.secrets/royale-owner-nl.json'
OWNER = 2075630349
NAME = '🇳🇱 Нидерланды · Royale'
PUBLIC_NAME = '🇳🇱 Нидерланды'
DOMAIN = 'nl.arccnet.space'


def load(telegram_id):
    return _read_state() if telegram_id == OWNER else None


def delivery_state(telegram_id):
    state = _read_state()
    if state and (state.get('global_enabled') or telegram_id == OWNER):
        return state
    return None


def _read_state():
    try:
        state = json.loads(STATE.read_text())
        if state.get('enabled') and state.get('public_key') and state.get('short_id'):
            return state
    except (OSError, ValueError):
        pass
    return None


def _royale_outbound(outbound, state):
    outbound['settings']['vnext'][0].update(address=DOMAIN, port=443)
    outbound['streamSettings']['realitySettings'].update(
        serverName=DOMAIN, publicKey=state['public_key'], shortId=state['short_id'], fingerprint='firefox')
    return outbound


def apply(profiles, state, youtube_domains=()):
    if not state:
        return profiles
    for index, source in enumerate(profiles):
        if source.get('remarks') != '🇸🇪 Швеция':
            continue
        profile = copy.deepcopy(source)
        outbound = next((o for o in profile['outbounds'] if o.get('protocol') == 'vless'), None)
        if not outbound or outbound.get('streamSettings', {}).get('security') != 'reality':
            return profiles
        _royale_outbound(outbound, state)
        profile['remarks'] = PUBLIC_NAME if state.get('global_enabled') else NAME
        result = profiles[:index] + [profile] + profiles[index:]
        if state.get('global_enabled'):
            result = [p for p in result if p is profile or p.get('remarks') != PUBLIC_NAME]
            return _update_routes(result, state, youtube_domains)
        return result
    return profiles


def _update_routes(profiles, state, youtube_domains):
    result = []
    for source in profiles:
        name = source.get('remarks', '')
        if 'Автовыбор' in name or 'Ютуб без рекламы' in name:
            profile = copy.deepcopy(source)
            peer = next((o for o in profile['outbounds'] if o['tag'] == 'se-primary'), None)
            if peer is not None:
                _royale_outbound(peer, state)['tag'] = 'nl-primary'
                balancer = profile['routing']['balancers'][0]
                balancer['selector'] = ['nl-primary' if t == 'se-primary' else t for t in balancer['selector']]
                observer = profile['burstObservatory']
                observer['subjectSelector'] = ['nl-primary' if t == 'se-primary' else t
                                               for t in observer['subjectSelector']]
                if 'Автовыбор' in name:
                    balancer['strategy'] = {'type': 'leastPing'}
        elif name == '🇱🇹 Литва':
            profile = copy.deepcopy(source)
            proxy = next(o for o in profile['outbounds'] if o['tag'] == 'proxy')
            youtube = _royale_outbound(copy.deepcopy(proxy), state)
            youtube['tag'] = 'youtube-nl'
            profile['outbounds'].append(youtube)
            rule = next((r for r in profile['routing']['rules'] if r.get('domain') == list(youtube_domains)), None)
            if rule is not None:
                rule['outboundTag'] = 'youtube-nl'
        else:
            profile = source
        result.append(profile)
    return result


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
        name = PUBLIC_NAME if state.get('global_enabled') else NAME
        replacement = urlunsplit(('vless', authority, parsed.path, urlencode(query), quote(name)))
        result = links[:index] + [replacement] + links[index:]
        if state.get('global_enabled'):
            result = [item for item in result if item == replacement or unquote(urlsplit(item).fragment) != PUBLIC_NAME]
        return result
    return links
