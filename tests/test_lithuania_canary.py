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


def test_auto_lt_primary_only_preserves_input():
    profiles = [{'remarks': '🇸🇴 Автовыбор', 'outbounds': [reality('proxy-main-1'),
        {'tag': 'direct', 'protocol': 'freedom'}], 'routing': {'rules': [
        {'type': 'field', 'domain': ['example.ru'], 'outboundTag': 'direct'},
        {'type': 'field', 'network': 'tcp,udp', 'balancerTag': 'old'}]}}]
    old = copy.deepcopy(profiles)
    p = m.apply(profiles, STATE)[0]
    assert profiles == old
    assert p['outbounds'][0]['settings']['vnext'][0]['address'] == '95.182.120.237'
    assert p['outbounds'][0]['settings']['vnext'][0]['port'] == 1443
    assert p['outbounds'][0]['tag'] == 'lt-primary'
    assert 'balancers' not in p['routing']
    assert p['routing']['rules'][-1]['outboundTag'] == 'lt-primary'
    assert p['routing']['rules'][0]['outboundTag'] == 'direct'


def test_alias_uuid_and_ai_port_preserved():
    profiles = [{'remarks': '🇸🇪 Нейросети 🤖', 'outbounds': [reality(port=8444)]}]
    p = m.apply(profiles, STATE)[0]
    assert p['remarks'] == '🇸🇪 Нейросети 🤖'
    target = p['outbounds'][0]['settings']['vnext'][0]
    assert target['port'] == 9444
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
    assert primary['settings']['vnext'][0]['address'] == '95.182.120.237'
    assert primary['settings']['vnext'][0]['port'] == 1443
    assert not any(o.get('protocol') in ('hysteria', 'loopback') for o in p['outbounds'])
    assert 'balancers' not in p['routing'] and 'burstObservatory' not in p
    assert p['routing']['rules'][-1]['outboundTag'] == 'lt-primary'
    assert any(r.get('outboundTag') == 'direct' for r in p['routing']['rules'])
    assert result[1]['outbounds'][0]['protocol'] == 'hysteria'
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
    assert 'keep-owner-uuid@95.182.120.237:9444' in result
    assert 'pbk=node-public-key' in result
