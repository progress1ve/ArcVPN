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
    try:
        d = json.loads(STATE.read_text())
        allowed = d.get('global_enabled') or (int(telegram_id) == OWNER and d.get('delivery_enabled'))
        return d if allowed and d.get('public_key') and d.get('short_id') else None
    except (OSError, ValueError):
        return None


def rename(name):
    if 'Нейросети' in name or 'Игровой сервер' in name:
        return name.replace('🇱🇹', '🇸🇪')
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
            target['address'] = '95.182.120.237'
            target['port'] = 9444 if int(target.get('port', 443)) == 8444 else 1443
        stream['realitySettings'].update(serverName=state['tls_name'], publicKey=state['public_key'], shortId=state['short_id'], fingerprint='firefox')
    elif o.get('protocol') == 'hysteria':
        o['settings'].update(address='95.182.120.237', port=443)
        stream['tlsSettings'].update(serverName=state['tls_name'], allowInsecure=False)
    return o


def apply(profiles, state, *, include_fragment=False):
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
            primary['tag'] = 'lt-primary'
            primary.setdefault('streamSettings', {})['finalmask'] = {
                'tcp': [{'type': 'fragment', 'settings': {
                    'packets': 'tlshello', 'length': '10-20', 'delay': '10-20',
                }}]
            }
            retained = [o for o in p['outbounds'] if o.get('protocol') in ('freedom', 'blackhole', 'dns')]
            removed = {o['tag'] for o in p['outbounds'] if o not in retained}
            loops = {o.get('settings', {}).get('inboundTag') for o in p['outbounds'] if o.get('protocol') == 'loopback'}
            rules = []
            for r in p.get('routing', {}).get('rules', []):
                if set(r.get('inboundTag', [])) & loops:
                    continue
                if 'balancerTag' in r or r.get('outboundTag') in removed:
                    r.pop('balancerTag', None)
                    r['outboundTag'] = 'lt-primary'
                rules.append(r)
            rules.append({'type': 'field', 'network': 'tcp,udp', 'outboundTag': 'lt-primary'})
            p['outbounds'] = [primary] + retained
            p['routing']['rules'] = rules
            p['routing'].pop('balancers', None)
            p.pop('observatory', None)
            p.pop('burstObservatory', None)
    if include_fragment:
        auto = next((p for p in result if 'Автовыбор' in p.get('remarks', '')), None)
        if auto:
            candidate = copy.deepcopy(auto)
            primary = next((o for o in candidate.get('outbounds', []) if o.get('tag') == 'lt-primary'), None)
            if primary:
                primary.setdefault('streamSettings', {})['finalmask'] = {
                    'tcp': [{'type': 'fragment', 'settings': {
                        'packets': 'tlshello', 'length': '10-20', 'delay': '10-20',
                    }}]
                }
                candidate['remarks'] = '🇱🇹 Литва — тест фрагментации'
                result.insert(result.index(auto) + 1, candidate)
    return result


def apply_links(links, state):
    result = []
    for link in links:
        p = urllib.parse.urlsplit(link)
        q = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
        host = p.hostname; port = p.port
        if p.scheme == 'vless' and q.get('security') == 'reality':
            host = '95.182.120.237'; port = 9444 if port == 8444 else 1443
            q.update(sni=state['tls_name'], pbk=state['public_key'], sid=state['short_id'], fp='firefox')
        elif q.get('type') == 'xhttp':
            for field in ('path', 'extra'):
                if field in q:q[field] = q[field].replace('/api-se', '/api-lt').replace('/api-ee', '/api-lt').replace('/api-test', '/api-lt-test')
        elif p.scheme in ('hysteria2', 'hy2'):
            host = '95.182.120.237'; port = 443; q.update(sni=state['tls_name'], insecure='0')
        if host:
            authority = p.netloc.rsplit('@', 1)[0] + '@' + host + (':'+str(port) if port else '')
            link = urllib.parse.urlunsplit((p.scheme, authority, p.path, urllib.parse.urlencode(q), urllib.parse.quote(rename(urllib.parse.unquote(p.fragment)))))
        result.append(link)
    return result
