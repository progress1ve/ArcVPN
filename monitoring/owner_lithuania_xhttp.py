"""Owner-only direct XHTTP experiment, outside automatic selection."""
import copy
import json
import urllib.parse

OWNER = 2075630349
NAME = '🇱🇹 Литва XHTTP · тест'


def stream():
    return {'network': 'xhttp', 'security': 'tls',
            'tlsSettings': {'serverName': 'lt.arccnet.space', 'fingerprint': 'firefox',
                            'allowInsecure': False, 'alpn': ['h2', 'http/1.1']},
            'xhttpSettings': {'host': 'lt.arccnet.space', 'path': '/api-lt-direct', 'mode': 'packet-up',
             'extra': {'uplinkHTTPMethod': 'GET', 'uplinkDataPlacement': 'header',
                       'uplinkDataKey': 'X-Session-Token', 'scMaxEachPostBytes': 24000,
                       'scMinPostsIntervalMs': 10, 'xPaddingBytes': '100-1000',
                       'xPaddingKey': 'dc', 'xPaddingHeader': 'X-Cache', 'xPaddingMethod': 'tokenish',
                       'xPaddingObfsMode': True, 'xPaddingPlacement': 'queryInHeader'}}}


def apply(profiles, user_id):
    if user_id != OWNER:
        return profiles
    for i, source in enumerate(profiles):
        if source.get('remarks') == '🇱🇹 Литва':
            profile = copy.deepcopy(source)
            profile['remarks'] = NAME
            outbound = next(o for o in profile['outbounds'] if o.get('protocol') == 'vless')
            outbound['settings']['vnext'][0].update(address='88.216.62.135', port=443)
            for user in outbound['settings']['vnext'][0]['users']:
                user.pop('flow', None)
            outbound['streamSettings'] = stream()
            outbound.pop('mux', None)
            return profiles[:i+1] + [profile] + profiles[i+1:]
    return profiles


def apply_links(links, user_id):
    if user_id != OWNER:
        return links
    for i, link in enumerate(links):
        parsed = urllib.parse.urlsplit(link)
        if parsed.scheme == 'vless' and urllib.parse.unquote(parsed.fragment) == '🇱🇹 Литва':
            settings = stream()
            query = dict(security='tls', type='xhttp', sni='lt.arccnet.space', fp='firefox',
                         alpn='h2,http/1.1', host='lt.arccnet.space', path='/api-lt-direct', mode='packet-up',
                         extra=json.dumps(settings['xhttpSettings']['extra'], separators=(',', ':')))
            new = urllib.parse.urlunsplit(('vless', parsed.netloc.rsplit('@', 1)[0]+'@88.216.62.135:443',
                                          '', urllib.parse.urlencode(query), urllib.parse.quote(NAME)))
            return links[:i+1] + [new] + links[i+1:]
    return links
