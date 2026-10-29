import copy
from monitoring import lithuania_canary as m

STATE = {'public_key': 'node-public-key', 'short_id': '00112233', 'tls_name': 'lt.example'}


def reality(tag='proxy', port=443):
    return {'tag': tag, 'protocol': 'vless', 'settings': {'vnext': [
        {'address': 'ee.example', 'port': port, 'users': [{'id': 'keep-owner-uuid'}]}]},
        'streamSettings': {'network': 'tcp', 'security': 'reality', 'realitySettings': {'publicKey': 'ee-key'}}}


def test_other_customers_get_overlay_only_when_globally_enabled(monkeypatch, tmp_path):
    import json
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({**STATE, 'delivery_enabled': True}))
    monkeypatch.setattr(m, 'STATE', path)
    assert m.load(12345) is None
    path.write_text(json.dumps({**STATE, 'delivery_enabled': True, 'global_enabled': True}))
    assert m.load(12345) is not None


def test_auto_without_lte_selects_both_main_variants_and_preserves_input():
    profiles = [{'remarks': '🇸🇴 Автовыбор', 'outbounds': [reality('proxy-main-1'),
        {'tag': 'direct', 'protocol': 'freedom'}], 'routing': {'rules': [
        {'type': 'field', 'domain': ['example.ru'], 'outboundTag': 'direct'},
        {'type': 'field', 'network': 'tcp,udp', 'balancerTag': 'old'}]}}]
    old = copy.deepcopy(profiles)
    p = m.apply(profiles, STATE)[0]
    assert profiles == old
    assert p['outbounds'][0]['settings']['vnext'][0]['address'] == '88.216.62.135'
    assert p['outbounds'][0]['settings']['vnext'][0]['port'] == 443
    assert p['outbounds'][0]['tag'] == 'lt-primary'
    assert 'finalmask' not in p['outbounds'][0]['streamSettings']
    assert p['outbounds'][1]['streamSettings']['finalmask']['tcp'][0]['settings'] == {'packets': 'tlshello', 'length': '10-20', 'delay': '10-20'}
    assert p['routing']['balancers'][0]['fallbackTag'] == 'lt-primary-fragment'
    assert p['routing']['rules'][-1]['balancerTag'] == 'lt-first'
    assert not any(o.get('tag') == 'cdn-safe' for o in p['outbounds'])
    assert p['routing']['rules'][0]['outboundTag'] == 'direct'


def test_alias_uuid_and_ai_port_preserved():
    profiles = [{'remarks': '🇸🇪 Нейросети 🤖', 'outbounds': [reality(port=8444)]}]
    p = m.apply(profiles, STATE)[0]
    assert p['remarks'] == '🇸🇪 Нейросети 🤖'
    target = p['outbounds'][0]['settings']['vnext'][0]
    assert target['address'] == '88.216.62.135'
    assert target['port'] == 8444
    assert target['users'][0]['id'] == 'keep-owner-uuid'


def test_auto_excludes_hysteria_and_estonia_but_keeps_game_profile():
    auto = {'remarks': '🇸🇴 Автовыбор', 'outbounds': [reality('old'),
        {'tag': 'direct', 'protocol': 'freedom'}], 'routing': {'rules': [
            {'domain': ['example.ru'], 'outboundTag': 'direct'},
            {'network': 'tcp,udp', 'balancerTag': 'old'}]}}
    game = {'remarks': '🇱🇹 Игровой сервер 🎮', 'outbounds': [
        {'tag': 'proxy', 'protocol': 'hysteria', 'settings': {'address': 'ee.example', 'port': 443, 'version': 2},
         'streamSettings': {'network': 'hysteria', 'security': 'tls',
             'hysteriaSettings': {'auth': 'user-hysteria-auth'}, 'tlsSettings': {'serverName': 'ee.example'}}}]}
    original = copy.deepcopy([auto, game])
    result = m.apply([auto, game], STATE)
    assert [auto, game] == original
    p = result[0]
    primary = p['outbounds'][0]
    assert primary['protocol'] == 'vless' and primary['tag'] == 'lt-primary'
    assert primary['settings']['vnext'][0]['address'] == '88.216.62.135'
    assert primary['settings']['vnext'][0]['port'] == 443
    assert not any(o.get('protocol') in ('hysteria', 'loopback') for o in p['outbounds'])
    assert p['routing']['balancers'][0]['fallbackTag'] == 'lt-primary-fragment'
    assert p['routing']['rules'][-1]['balancerTag'] == 'lt-first'
    assert any(r.get('outboundTag') == 'direct' for r in p['routing']['rules'])
    assert result[1]['outbounds'][0]['protocol'] == 'hysteria'
    assert result[1]['outbounds'][0]['settings']['address'] == '88.216.62.135'
    assert result[1]['outbounds'][0]['settings']['port'] == 443
    assert result[1]['outbounds'][0]['streamSettings']['hysteriaSettings']['auth'] == 'user-hysteria-auth'
    assert result[1]['remarks'] == '🇸🇪 Игровой сервер 🎮'


def test_plain_link_special_flags_are_swedish():
    import urllib.parse
    link = 'vless://test@ee.example:8444?security=reality#' + urllib.parse.quote('🇱🇹 Нейросети 🤖')
    assert urllib.parse.unquote(m.apply_links([link], STATE)[0].split('#', 1)[1]) == '🇸🇪 Нейросети 🤖'


def test_cdn_endpoint_and_identity_retained_only_owner_path_changes():
    o = reality()
    o['streamSettings'] = {'network': 'xhttp', 'security': 'tls', 'xhttpSettings': {
        'path': '/api-se-test-24000', 'extra': {'scMaxEachPostBytes': 24000, 'scMinPostsIntervalMs': 10}}}
    o['settings']['vnext'][0]['address'] = 'cdn-de.arccnet.space'
    r = m.rewrite(o, STATE)
    assert r['settings']['vnext'][0]['address'] == 'cdn-de.arccnet.space'
    assert r['streamSettings']['xhttpSettings']['path'] == '/api-lt-test-24000'
    assert r['streamSettings']['xhttpSettings']['extra']['scMinPostsIntervalMs'] == 10


def test_plain_link_preserves_owner_identity():
    link = 'vless://keep-owner-uuid@ee.example:8444?security=reality&type=tcp&pbk=old#%F0%9F%87%B8%F0%9F%87%AA%20AI'
    result = m.apply_links([link], STATE)[0]
    assert 'keep-owner-uuid@88.216.62.135:8444' in result
    assert 'pbk=node-public-key' in result


def test_auto_fragmentation_does_not_add_test_profile():
    auto = {'remarks': '🇸🇴 Автовыбор', 'outbounds': [reality('old'), {'tag': 'direct', 'protocol': 'freedom'}], 'routing': {'rules': []}}
    profiles = m.apply([auto], STATE)
    assert len(profiles) == 1
    assert profiles[0]['remarks'] == auto['remarks']
    assert profiles[0]['outbounds'][1]['streamSettings']['finalmask']['tcp'][0]['settings'] == {'packets': 'tlshello', 'length': '10-20', 'delay': '10-20'}


def test_auto_restores_authorized_cdn_fallback_without_estonia_or_hysteria():
    from monitoring.cdn_fallbacks import outbound
    lte = reality('lte')
    lte['settings']['vnext'][0]['users'][0]['id'] = 'separate-lte-uuid'
    lte['streamSettings'] = {'network': 'xhttp'}
    auto = {'remarks': '🇸🇴 Автовыбор', 'outbounds': [reality(), outbound(lte,4096,'cdn-fast'), outbound(lte,24000,'cdn-safe'), {'tag':'direct','protocol':'freedom'}], 'routing': {'rules':[{'domain':['example.ru'],'outboundTag':'direct'}]}}
    p=m.apply([auto],STATE)[0]
    b=p['routing']['balancers']
    assert b[0]['selector']==['lt-primary'] and b[0]['fallbackTag']=='cdn-safe'
    assert len(b)==1
    cdn=[o for o in p['outbounds'] if o['tag'] in ('cdn-fast','cdn-safe')]
    assert [o['streamSettings']['xhttpSettings']['path'] for o in cdn]==['/api-lt-test-24000']
    assert all(o['settings']['vnext'][0]['users'][0]['id']=='separate-lte-uuid' for o in cdn)
    assert any(r.get('outboundTag')=='direct' for r in p['routing']['rules'])
    assert not any(o.get('tag')=='ee-reserve' or o.get('protocol')=='hysteria' for o in p['outbounds'])


def test_auto_variants_share_main_authorization_but_are_independent_copies():
    source = reality('old')
    source['streamSettings']['finalmask'] = {'tcp': [{'type': 'obsolete'}]}
    auto = {'remarks': 'Автовыбор', 'outbounds': [source], 'routing': {'rules': []}}
    before = copy.deepcopy(auto)
    p = m.apply([auto], STATE)[0]
    plain, fragmented = p['outbounds'][:2]
    assert plain['settings'] == fragmented['settings']
    assert plain['settings']['vnext'][0]['users'][0]['id'] == 'keep-owner-uuid'
    assert 'finalmask' not in plain['streamSettings']
    assert fragmented['streamSettings']['finalmask']['tcp'][0]['type'] == 'fragment'
    observed = p['burstObservatory']['subjectSelector']
    assert {o['tag'] for o in p['outbounds'] if any(o['tag'].startswith(s) for s in observed)} == {'lt-primary', 'lt-primary-fragment'}
    assert auto == before
    plain['settings']['vnext'][0]['users'][0]['id'] = 'changed-in-test'
    assert fragmented['settings']['vnext'][0]['users'][0]['id'] == 'keep-owner-uuid'


def test_no_lte_failure_never_falls_back_to_unprotected_direct():
    auto = {'remarks': 'Автовыбор', 'outbounds': [reality(),
        {'tag': 'direct', 'protocol': 'freedom'}, {'tag': 'block', 'protocol': 'blackhole'}],
        'routing': {'rules': [{'domain': ['example.ru'], 'outboundTag': 'direct'}]}}
    p = m.apply([auto], STATE)[0]
    b = p['routing']['balancers'][0]
    fallback = next(o for o in p['outbounds'] if o['tag'] == b['fallbackTag'])
    assert fallback['protocol'] == 'vless'
    assert fallback['streamSettings']['security'] == 'reality'
    assert p['routing']['rules'][0]['outboundTag'] == 'direct'


def test_all_ordinary_share_links_bypass_moscow_preserving_auth_and_sni():
    import urllib.parse
    links = [
        'vless://ordinary-auth@95.182.120.237:1443?security=reality&type=tcp#Lithuania',
        'vless://ai-auth@95.182.120.237:9444?security=reality&type=tcp#AI',
        'hysteria2://gaming-auth@95.182.120.237:443?sni=old.example#Games',
        'vless://lte-auth@cdn-de.arccnet.space:443?type=xhttp&security=tls&path=%2Fapi-lt-test-24000#CDN',
    ]
    result = [urllib.parse.urlsplit(s) for s in m.apply_links(links, STATE)]
    assert [(s.hostname, s.port) for s in result] == [
        ('88.216.62.135', 443), ('88.216.62.135', 8444),
        ('88.216.62.135', 443), ('cdn-de.arccnet.space', 443)]
    assert [s.username for s in result] == ['ordinary-auth', 'ai-auth', 'gaming-auth', 'lte-auth']
    assert all(urllib.parse.parse_qs(s.query)['sni'] == ['lt.example'] for s in result[:3])
    assert urllib.parse.parse_qs(result[3].query)['path'] == ['/api-lt-test-24000']
