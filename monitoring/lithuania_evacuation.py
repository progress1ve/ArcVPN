"""Retire unreachable Lithuanian delivery paths without changing identities."""
import copy
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from monitoring.royale_owner import DOMAIN, _royale_outbound

HOSTS = {'88.216.62.135', 'lt.arccnet.space', '88-216-62-135.sslip.io'}


def apply(profiles, state):
    if not state or not state.get('global_enabled'):
        return profiles
    result = copy.deepcopy(profiles)
    for p in result:
        retired = set()
        for o in p.get('outbounds', []):
            targets = o.get('settings', {}).get('vnext', [])
            if any(t.get('address') in HOSTS for t in targets):
                if any(word in p.get('remarks', '') for word in ('Автовыбор', 'Ютуб без рекламы')):
                    retired.add(o['tag'])
                else:
                    _royale_outbound(o, state)
        if retired:
            p['outbounds'] = [o for o in p['outbounds'] if o.get('tag') not in retired]
            def replace(value):
                if isinstance(value, dict):
                    return {k: ([x for x in v if x not in retired] if k in ('selector', 'subjectSelector')
                                else replace(v)) for k, v in value.items()}
                if isinstance(value, list):
                    return [replace(x) for x in value]
                return 'nl-primary' if isinstance(value, str) and value in retired else value
            p['routing'] = replace(p['routing'])
            p['burstObservatory'] = replace(p['burstObservatory'])
    return result


def apply_links(links, state):
    if not state or not state.get('global_enabled'):
        return links
    result = []
    for link in links:
        p = urlsplit(link)
        if p.hostname in HOSTS and p.scheme == 'vless':
            q = dict(parse_qsl(p.query, keep_blank_values=True))
            q.update(sni=DOMAIN, pbk=state['public_key'], sid=state['short_id'], fp='firefox')
            p = p._replace(netloc=p.netloc.rsplit('@', 1)[0] + '@' + DOMAIN + ':443', query=urlencode(q))
            link = urlunsplit(p)
        result.append(link)
    return result
