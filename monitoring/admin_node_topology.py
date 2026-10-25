"""Safe admin view of the current fleet and delivered Estonia CDN variants."""
from monitoring.cdn_fallbacks import HOST, VARIANTS

SWEDEN = '136.148.220.228'
ESTONIA = '87.251.19.197'
DIRECT = {3:4096, 4:24000, 6:65536, 7:32768}

def cdn_edges(nodes):
    parent = next((n for n in nodes if n.get('address') == ESTONIA), {})
    result = []
    for number, size in DIRECT.items():
        variant = VARIANTS[size]
        inbound = next((i for i in parent.get('inbounds', []) if i.get('tag') == variant['tag'].replace('SE_', 'EE_', 1)), None)
        result.append({
            'id': f'lte-se-{size}', 'name': f'Эстония CDN · {size}/{variant["interval"]}',
            'country_code': 'EE', 'origin_host': ESTONIA, 'origin_domain': 'ee.arccnet.space',
            'public_host': HOST, 'path': variant['path'],
            'profile_name': f'🇪🇺 Обход глушилок #{number}',
            'origin': parent.get('address'), 'node_uuid': parent.get('uuid'),
            'connected': bool(parent.get('connected')), 'inbound_active': inbound is not None,
            'network': 'xhttp', 'port': variant['port'], 'traffic_factor': 1,
            'users_online': int(parent.get('users_online') or 0),
            'traffic_used_gb': float(parent.get('traffic_used_gb') or 0),
            'diagnostic': parent.get('diagnostic'),
            'healthy': bool(parent.get('connected') and not parent.get('disabled') and inbound is not None),
        })
    return result

def connection_schemes(nodes, distribution, edges):
    members = [{'name': n.get('name') or n.get('address'), 'online': int(n.get('users_online') or 0),
                'connected': bool(n.get('connected')), 'weight': 100}
               for n in nodes if n.get('address') == ESTONIA and not n.get('disabled')]
    fallback = 'Эстония 100% → CDN 4096/7 + XMUX → CDN 24000/10'
    schemes = [{'id':'auto', 'name':'🇸🇴 Автовыбор | Самый быстрый', 'kind':'client_balancer',
                'probe_interval_seconds':10, 'probe_url':'http://sub.arccnet.space:18080/generate_204',
                'failover':fallback, 'selection_observable':False,
                'online_distribution':distribution, 'members':members}]
    for number in range(1,9):
        edge = next((e for e in edges if DIRECT.get(number) and e['id'] == f'lte-se-{DIRECT[number]}'), None)
        schemes.append({'id':f'fallback-{number}',
            'name':'🇪🇺 Лучший обход' if number == 1 else f'🇪🇺 Обход глушилок #{number}',
            'kind':'direct_cdn' if edge else 'client_cdn_fallback', 'traffic_factor':1,
            'active_only_as_fallback':edge is None, 'strategy':'XHTTP без балансировщика' if edge else fallback,
            'public_host':HOST, 'origin':ESTONIA, 'path':edge['path'] if edge else None,
            'origins':[HOST], 'healthy':bool(edge['healthy']) if edge else any(e['healthy'] for e in edges)})
    return schemes
