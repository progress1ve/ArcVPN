import json
from urllib.parse import urlsplit, parse_qs
from monitoring.admin_node_topology import cdn_edges, connection_schemes, SWEDEN, ESTONIA
from monitoring.cdn_fallbacks import HOST, VARIANTS, cdn_only
from monitoring.lte_operator_worker import variant_links
from monitoring.remnawave_fleet_monitor import tcp_ports
from monitoring.cdn_connections import classify


def test_estonia_edges_and_direct_profiles_match_delivered_variants():
    nodes=[{'address':SWEDEN,'name':'Sweden','connected':False,'disabled':True,'inbounds':[]},
           {'address':ESTONIA,'name':'Estonia','connected':True,'inbounds':[{'tag':v['tag'].replace('SE_', 'EE_', 1)} for v in VARIANTS.values()]}]
    edges=cdn_edges(nodes)
    assert len(edges)==4 and all(e['healthy'] and e['origin']==ESTONIA for e in edges)
    schemes=connection_schemes(nodes,{},edges)
    assert [s['kind'] for s in schemes[1:]]==['client_cdn_fallback','client_cdn_fallback','direct_cdn','direct_cdn','client_cdn_fallback','direct_cdn','direct_cdn','client_cdn_fallback']
    assert [m['weight'] for m in schemes[0]['members']]==[100]
    assert all(not e['healthy'] for e in cdn_edges([]))


def test_operator_links_preserve_identity_and_exact_transport():
    source = {'tag': 'proxy', 'protocol': 'vless', 'settings': {'vnext': [
        {'address': HOST, 'port': 443, 'users': [{'id': 'test-user'}]}]},
        'streamSettings': {'network': 'xhttp'}}
    profile = cdn_only({'outbounds': [source]}, source)
    for outbound in profile['outbounds']:
        transport = outbound['streamSettings']['xhttpSettings']
        transport['path'] = transport['path'].replace('/api-se-', '/api-lt-')
    links = variant_links([profile, profile])
    assert len(links) == 4
    for probe, uri in links.items():
        parsed = urlsplit(uri)
        query = parse_qs(parsed.query)
        path, _, edge = probe.partition('@')
        assert parsed.username == 'test-user' and parsed.hostname == (edge or HOST)
        assert query['sni'] == query['host'] == [HOST] and query['path'] == [path]
        delivered = next(o['streamSettings']['xhttpSettings'] for o in profile['outbounds']
                         if o['settings']['vnext'][0]['address'] == parsed.hostname
                         and o['streamSettings']['xhttpSettings']['path'] == path)
        assert json.loads(query['extra'][0]) == delivered['extra']


def test_sweden_diagnostics_skip_loopback_and_peer_only_ports():
    node={'address':SWEDEN,'configProfile':{'activeInbounds':[
        {'port':443,'network':'tcp','tag':'SE_REALITY'}, {'port':2443,'protocol':'shadowsocks'},
        *[{'port':v['port'],'network':'xhttp','tag':v['tag']} for v in VARIANTS.values()]]}}
    assert tcp_ports(node)==[443]
    assert classify('accepted tcp:example.com:443 [EE_OWNER_DIRECT_XHTTP -> DIRECT] email: test') is None


def test_paused_sweden_has_no_current_cdn_probes(monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api,'_admin_authorized',lambda _:True)
    r=api.app.test_client().get('/api/admin/nodes/operator-probes?host='+SWEDEN)
    assert r.status_code==200 and r.get_json()['results']==[]


def test_royale_attribution_requires_confirmation(monkeypatch):
    from monitoring import cdn_origin
    monkeypatch.setattr(cdn_origin, '_read_state', lambda: {'global_enabled': True})
    assert cdn_origin.active_origin() == cdn_origin.LITHUANIA
    monkeypatch.setattr(cdn_origin, '_read_state', lambda: {'cdn_origin_confirmed': True})
    assert cdn_origin.active_origin() == cdn_origin.ROYALE
    edges = cdn_edges([{'address': cdn_origin.ROYALE_PUBLIC, 'connected': True,
                       'inbounds': [{'tag': v['tag'].replace('SE_', 'NL_', 1)} for v in VARIANTS.values()]}],
                     cdn_origin.active_origin())
    assert all(e['healthy'] and e['origin'] == cdn_origin.ROYALE_PUBLIC for e in edges)
