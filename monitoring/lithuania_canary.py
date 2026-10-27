"""Owner-only delivery overlay; inactive for every other customer.

The controller-created state file is root-only. Removing delivery_enabled is
the immediate rollback; no global catalog or customer identity is changed.
"""
import copy
import json
from pathlib import Path
import urllib.parse

OWNER = 2075630349
IP = '88.216.62.135'
STATE = Path(__file__).resolve().parents[1] / '.secrets/lithuania-canary-20261027.json'


def load(telegram_id):
    if int(telegram_id) != OWNER:
        return None
    try:
        d = json.loads(STATE.read_text())
        return d if d.get('delivery_enabled') and d.get('public_key') and d.get('short_id') else None
    except (OSError, ValueError):
        return None


def rename(name):
    return name.replace('🇸🇪', '🇱🇹').replace('Швеция', 'Литва')


def rewrite(o, state):
    stream = o.get('streamSettings', {})
    if stream.get('network') == 'xhttp':
        x = stream.get('xhttpSettings', {})
        for settings in (x, x.get('extra', {})):
            if 'path' in settings:
                settings['path'] = settings['path'].replace('/api-se', '/api-lt').replace('/api-ee', '/api-lt').replace('/api-test', '/api-lt-test')
    elif stream.get('security') == 'reality':
        targets = o.get('settings', {}).get('vnext', [])
        for target in targets:
            target['address'] = IP
            target['port'] = 8444 if int(target.get('port', 443)) == 8444 else 443
        stream['realitySettings'].update(serverName=state['tls_name'], publicKey=state['public_key'], shortId=state['short_id'], fingerprint='firefox')
    elif o.get('protocol') == 'hysteria':
        o['settings'].update(address=IP, port=443)
        stream['tlsSettings'].update(serverName=state['tls_name'], allowInsecure=False)
    return o


def apply(profiles, state):
    result = copy.deepcopy(profiles)
    original_auto = next((p for p in profiles if 'Автовыбор' in p.get('remarks', '')), None)
    ee_backup = next((copy.deepcopy(o) for o in (original_auto or {}).get('outbounds', [])
        if o.get('streamSettings', {}).get('security') == 'reality'), None)
    for p in result:
        p['remarks'] = rename(p.get('remarks', ''))
        for o in p.get('outbounds', []):
            rewrite(o, state)
        if 'Автовыбор' in p['remarks'] and ee_backup:
            primary = rewrite(copy.deepcopy(ee_backup), state)
            primary['tag'] = 'lt-primary'; ee_backup['tag'] = 'ee-reserve'
            retained = [o for o in p['outbounds'] if o.get('protocol') in ('freedom', 'blackhole', 'dns')]
            removed = {o['tag'] for o in p['outbounds'] if o not in retained}
            loops = {o.get('settings', {}).get('inboundTag') for o in p['outbounds'] if o.get('protocol') == 'loopback'}
            rules = []
            for r in p.get('routing', {}).get('rules', []):
                if set(r.get('inboundTag', [])) & loops:
                    continue
                if 'balancerTag' in r or r.get('outboundTag') in removed:
                    r.pop('outboundTag', None); r['balancerTag'] = 'lt-first'
                rules.append(r)
            rules.append({'type': 'field', 'network': 'tcp,udp', 'balancerTag': 'lt-first'})
            p['outbounds'] = [primary, ee_backup] + retained
            p['routing']['rules'] = rules
            p['routing']['balancers'] = [{'tag': 'lt-first', 'selector': ['lt-primary'],
                'strategy': {'type': 'leastPing'}, 'fallbackTag': 'ee-reserve'}]
            p.pop('observatory', None)
            p['burstObservatory'] = {'subjectSelector': ['lt-primary', 'ee-reserve'],
                'pingConfig': {'destination': 'https://www.gstatic.com/generate_204',
                    'interval': '30s', 'sampling': 3, 'timeout': '2s'}}
    ordinary = next((p for p in result if p.get('remarks') == '🇱🇹 Литва'), None)
    if ordinary:
        bridge = copy.deepcopy(ordinary); bridge['remarks'] = '🇷🇺 Москва → Литва (Мост)'
        proxy = next(o for o in bridge['outbounds'] if o.get('protocol') == 'vless')
        proxy['settings']['vnext'][0].update(address='95.182.120.237', port=1443)
        result.insert(result.index(ordinary) + 1, bridge)
    return result


def apply_links(links, state):
    result = []
    for link in links:
        p = urllib.parse.urlsplit(link)
        q = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
        host = p.hostname; port = p.port
        if p.scheme == 'vless' and q.get('security') == 'reality':
            host = IP; port = 8444 if port == 8444 else 443
            q.update(sni=state['tls_name'], pbk=state['public_key'], sid=state['short_id'], fp='firefox')
        elif q.get('type') == 'xhttp':
            for field in ('path', 'extra'):
                if field in q:q[field] = q[field].replace('/api-se', '/api-lt').replace('/api-ee', '/api-lt').replace('/api-test', '/api-lt-test')
        elif p.scheme in ('hysteria2', 'hy2'):
            host = IP; port = 443; q.update(sni=state['tls_name'], insecure='0')
        if host:
            authority = p.netloc.rsplit('@', 1)[0] + '@' + host + (':'+str(port) if port else '')
            link = urllib.parse.urlunsplit((p.scheme, authority, p.path, urllib.parse.urlencode(q), urllib.parse.quote(rename(urllib.parse.unquote(p.fragment)))))
        result.append(link)
    return result
