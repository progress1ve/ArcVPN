"""Restore verified physical Lithuania/Sweden peers after regional recovery."""
import copy
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, unquote

STATE = Path(__file__).resolve().parents[1] / '.secrets/restored-lt-se-20261108.json'
PEERS = {'🇱🇹 Литва': 'lt-primary', '🇸🇪 Швеция': 'se-primary'}


def load():
    try:
        state = json.loads(STATE.read_text())
        if state.get('enabled') is True:
            for name in PEERS:
                assert all(state[name].get(k) for k in ('address', 'serverName', 'publicKey', 'shortId'))
            return state
    except (OSError, ValueError, KeyError, TypeError, AttributeError, AssertionError):
        pass
    return None


def retarget(outbound, peer):
    outbound['settings']['vnext'][0].update(address=peer['address'], port=443)
    outbound['streamSettings']['realitySettings'].update(
        **{k: peer[k] for k in ('serverName', 'publicKey', 'shortId')}, fingerprint='firefox')
    return outbound


def apply(profiles):
    state = load()
    if not state:
        return profiles
    result = copy.deepcopy(profiles)
    lt = next((p for p in result if p.get('remarks') == '🇱🇹 Литва'), None)
    youtube_rule = next((r for r in (lt or {}).get('routing', {}).get('rules', [])
                         if r.get('outboundTag') == 'youtube-nl'), None)
    youtube = next((o for o in (lt or {}).get('outbounds', []) if o.get('tag') == 'youtube-nl'), None)
    for p in result:
        name = p.get('remarks', '')
        if name in PEERS:
            retarget(next(o for o in p['outbounds'] if o.get('tag') == 'proxy'), state[name])
            if name == '🇸🇪 Швеция' and youtube and youtube_rule:
                if not any(o.get('tag') == 'youtube-nl' for o in p['outbounds']):
                    p['outbounds'].append(copy.deepcopy(youtube))
                    p['routing']['rules'].insert(0, copy.deepcopy(youtube_rule))
        if 'Автовыбор' in name:
            nl = next(o for o in p['outbounds'] if o.get('tag') == 'nl-primary')
            tags = list(PEERS.values())
            p['outbounds'] = [o for o in p['outbounds'] if o.get('tag') not in tags]
            for peer_name, tag in PEERS.items():
                o = retarget(copy.deepcopy(nl), state[peer_name]); o['tag'] = tag
                p['outbounds'].append(o)
            primary = next(b for b in p['routing']['balancers'] if b['tag'] == 'lt-first')
            primary['selector'] = ['nl-primary'] + tags
            primary['strategy'] = {'type': 'leastLoad', 'settings': {
                'expected': 2, 'maxRTT': '3s', 'baselines': ['1s'], 'tolerance': 0.2}}
            observer = p['burstObservatory']
            observer['subjectSelector'] = list(dict.fromkeys(observer['subjectSelector'] + tags))
            if youtube and youtube_rule:
                if not any(o.get('tag') == 'youtube-nl' for o in p['outbounds']):
                    p['outbounds'].append(copy.deepcopy(youtube))
                rule = next((r for r in p['routing'].get('rules', [])
                             if r.get('domain') == youtube_rule.get('domain')), None)
                if rule is None:
                    p['routing']['rules'].insert(0, copy.deepcopy(youtube_rule))
                else:
                    rule.pop('balancerTag', None)
                    rule['outboundTag'] = 'youtube-nl'
    return result


def apply_links(links):
    state = load()
    if not state:
        return links
    result = []
    for link in links:
        p = urlsplit(link); name = unquote(p.fragment)
        if name in PEERS and p.scheme == 'vless':
            peer = state[name]; q = dict(parse_qsl(p.query, keep_blank_values=True))
            q.update(sni=peer['serverName'], pbk=peer['publicKey'], sid=peer['shortId'], fp='firefox')
            link = urlunsplit(p._replace(netloc=p.netloc.rsplit('@', 1)[0] + '@' + peer['address'] + ':443', query=urlencode(q)))
        result.append(link)
    return result
