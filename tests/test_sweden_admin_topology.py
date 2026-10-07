import json
from urllib.parse import urlsplit, parse_qs
from monitoring.admin_node_topology import cdn_edges, connection_schemes, SWEDEN, ESTONIA
from monitoring.cdn_fallbacks import VARIANTS
from monitoring.lte_operator_worker import variant_links
from monitoring.remnawave_fleet_monitor import tcp_ports
from monitoring.cdn_connections import classify


def test_sweden_edges_and_direct_profiles_match_delivered_variants():
    nodes=[{'address':SWEDEN,'name':'Sweden','connected':True,'inbounds':[{'tag':v['tag']} for v in VARIANTS.values()]},
           {'address':ESTONIA,'name':'Estonia','connected':True,'inbounds':[]}]
    edges=cdn_edges(nodes)
    assert len(edges)==4 and all(e['healthy'] and e['origin']==SWEDEN for e in edges)
    schemes=connection_schemes(nodes,{},edges)
    assert [s['kind'] for s in schemes[1:]]==['client_cdn_fallback','client_cdn_fallback','direct_cdn','direct_cdn','client_cdn_fallback','direct_cdn','direct_cdn','client_cdn_fallback']
    assert [m['weight'] for m in schemes[0]['members']]==[61,39]
    assert all(not e['healthy'] for e in cdn_edges([]))


def test_operator_links_preserve_identity_and_exact_transport():
    uri='vless://test-user@cdn-de.arccnet.space:443?type=xhttp&path=%2Fapi-test&encryption=none#test'
    links=variant_links(uri)
    assert set(links)=={v['path'] for v in VARIANTS.values()}
    for size,v in VARIANTS.items():
        p=urlsplit(links[v['path']]);q=parse_qs(p.query);extra=json.loads(q['extra'][0])
        assert p.username=='test-user' and p.hostname=='cdn-de.arccnet.space'
        assert q['path']==[v['path']] and q['fp']==['firefox']
        assert extra['scMaxEachPostBytes']==size and extra['scMinPostsIntervalMs']==v['interval']
        assert extra['uplinkDataPlacement']=='header' and extra['uplinkHTTPMethod']=='GET'


def test_sweden_diagnostics_skip_loopback_and_peer_only_ports():
    node={'address':SWEDEN,'configProfile':{'activeInbounds':[
        {'port':443,'network':'tcp','tag':'SE_REALITY'}, {'port':2443,'protocol':'shadowsocks'},
        *[{'port':v['port'],'network':'xhttp','tag':v['tag']} for v in VARIANTS.values()]]}}
    assert tcp_ports(node)==[443]
    assert classify('accepted tcp:example.com:443 [EE_OWNER_DIRECT_XHTTP -> DIRECT] email: test') is None


def test_estonia_has_no_current_cdn_probes(monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api,'_admin_authorized',lambda _:True)
    r=api.app.test_client().get('/api/admin/nodes/operator-probes?host='+ESTONIA)
    assert r.status_code==200 and r.get_json()['results']==[]
