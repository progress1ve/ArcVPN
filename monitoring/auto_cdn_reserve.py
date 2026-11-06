"""Keep ordinary node selection, reserve the existing authorized CDN pool."""
import copy

from monitoring.cdn_connections import HTTPS_PROBE_URL


def apply(profiles):
    bypass = next((p for p in profiles if 'Лучший обход' in p.get('remarks', '')), None)
    if not bypass:
        return profiles
    candidates = [o for o in bypass.get('outbounds', [])
                  if o.get('streamSettings', {}).get('network') == 'xhttp']
    if not candidates:
        return profiles
    result = list(profiles)
    for index, source in enumerate(profiles):
        if 'Автовыбор' not in source.get('remarks', ''):
            continue
        p = copy.deepcopy(source)
        routing = p.get('routing', {})
        primary = next((b for b in routing.get('balancers', [])
                        if b.get('tag') == 'lt-first'), None)
        if any(b.get('tag') == 'auto-cdn-ping' for b in routing.get('balancers', [])):
            continue
        if not primary or not any(o.get('tag') == 'cdn-safe' for o in p.get('outbounds', [])):
            continue  # Never add CDN entitlement where none was already granted.
        tags = []
        for i, original in enumerate(candidates):
            o = copy.deepcopy(original)
            o['tag'] = 'auto-cdn-' + str(i)
            tags.append(o['tag'])
            p['outbounds'].append(o)
        p['outbounds'].append({'tag': 'auto-cdn-stage', 'protocol': 'loopback',
                              'settings': {'inboundTag': 'auto-cdn-reserve'}})
        primary['fallbackTag'] = 'auto-cdn-stage'
        routing['balancers'].append({'tag': 'auto-cdn-ping', 'selector': tags,
                                     'strategy': {'type': 'leastPing'}, 'fallbackTag': 'cdn-safe'})
        routing.setdefault('rules', []).insert(0, {'type': 'field',
            'inboundTag': ['auto-cdn-reserve'], 'balancerTag': 'auto-cdn-ping'})
        obs = p['burstObservatory']
        obs['subjectSelector'] = list(dict.fromkeys(obs['subjectSelector'] + tags))
        obs['pingConfig'].update(destination=HTTPS_PROBE_URL,
                                 interval='15s', sampling=2, timeout='5s')
        result[index] = p
    return result
