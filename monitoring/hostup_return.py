"""Restore the authorized Sweden peer without changing customer identities."""
import copy
import json
import urllib.parse
from pathlib import Path

STATE = Path(__file__).resolve().parents[1] / '.secrets/hostup-return-20261029.json'


def apply_links(links):
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        return links
    if not state.get('enabled'):
        return links
    output = []
    sweden = None
    for link in links:
        parsed = urllib.parse.urlsplit(link)
        name = urllib.parse.unquote(parsed.fragment)
        if 'Литва' in name and parsed.scheme == 'vless' and sweden is None:
            sweden = link
        if any(label in name for label in ('Эстония', 'Нидерланды', 'Нейросети', 'Игровой сервер')):
            query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            port = 8444 if 'Нейросети' in name else 443
            query['sni'] = state['serverName']
            if parsed.scheme == 'vless':
                query.update(pbk=state['publicKey'], sid=state['shortId'], fp='firefox')
            authority = parsed.netloc.rsplit('@', 1)[0] + '@' + state['address'] + ':' + str(port)
            link = urllib.parse.urlunsplit((parsed.scheme, authority, parsed.path, urllib.parse.urlencode(query), parsed.fragment))
        output.append(link)
    if sweden:
        parsed = urllib.parse.urlsplit(sweden)
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        query.update(sni=state['serverName'], pbk=state['publicKey'], sid=state['shortId'], fp='firefox')
        link = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc.rsplit('@', 1)[0] + '@' + state['address'] + ':443', parsed.path, urllib.parse.urlencode(query), urllib.parse.quote('🇸🇪 Швеция')))
        index = next((i + 1 for i, value in enumerate(output) if 'Ютуб' in urllib.parse.unquote(urllib.parse.urlsplit(value).fragment)), 0)
        output.insert(index, link)
    return output


def apply(profiles):
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        return profiles
    if not state.get('enabled'):
        return profiles
    result = list(profiles)
    for index, source in enumerate(profiles):
        if 'Автовыбор' not in source.get('remarks', ''):
            continue
        main = next((o for o in source.get('outbounds', []) if o.get('tag') == 'lt-primary'), None)
        if main is None:
            continue
        profile = copy.deepcopy(source)
        se = copy.deepcopy(main)
        se['tag'] = 'se-primary'
        se['settings']['vnext'][0].update(address=state['address'], port=state['port'])
        stream = se['streamSettings']
        stream.pop('finalmask', None)
        stream['realitySettings'].update({key: state[key] for key in ('serverName', 'publicKey', 'shortId')})
        profile['outbounds'].insert(2, se)
        balancer = profile['routing']['balancers'][0]
        balancer['selector'] = ['lt-primary', 'se-primary']
        balancer['strategy'] = {'type': 'leastLoad', 'settings': {
            'expected': 2, 'maxRTT': '3s', 'baselines': ['1s'], 'tolerance': 0.2}}
        profile['burstObservatory']['subjectSelector'] = ['lt-primary', 'se-primary']
        result[index] = profile
    auto = next((p for p in result if 'Автовыбор' in p.get('remarks', '')), None)
    if auto is None:
        return result
    output = []
    for source in result:
        name = source.get('remarks', '')
        if 'Ютуб' in name:
            profile = copy.deepcopy(auto)
            profile['remarks'] = name
            profile['outbounds'] = [o for o in profile['outbounds'] if o.get('streamSettings', {}).get('network') != 'xhttp']
            profile['routing']['balancers'][0]['fallbackTag'] = 'lt-primary-fragment'
            output.append(profile)
            continue
        if any(label in name for label in ('Эстония', 'Нидерланды', 'Нейросети', 'Игровой сервер')):
            profile = copy.deepcopy(source)
            for outbound in profile.get('outbounds', []):
                stream = outbound.get('streamSettings', {})
                if stream.get('security') == 'reality':
                    for target in outbound['settings']['vnext']:
                        target.update(address=state['address'], port=8444 if 'Нейросети' in name else 443)
                    stream['realitySettings'].update({key: state[key] for key in ('serverName', 'publicKey', 'shortId')})
                elif outbound.get('protocol') == 'hysteria':
                    outbound['settings'].update(address=state['address'], port=443)
                    stream['tlsSettings'].update(serverName=state['serverName'], allowInsecure=False)
            output.append(profile)
        else:
            output.append(source)
    manual = next((p for p in output if 'Литва' in p.get('remarks', '')), None)
    if manual:
        sweden = copy.deepcopy(manual)
        sweden['remarks'] = '🇸🇪 Швеция'
        for outbound in sweden.get('outbounds', []):
            if outbound.get('streamSettings', {}).get('security') == 'reality':
                outbound['settings']['vnext'][0].update(address=state['address'], port=443)
                outbound['streamSettings']['realitySettings'].update({key: state[key] for key in ('serverName', 'publicKey', 'shortId')})
        youtube_index = next((i for i, p in enumerate(output) if 'Ютуб' in p.get('remarks', '')), 0)
        output.insert(youtube_index + 1, sweden)
    return output
