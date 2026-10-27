import copy
from monitoring import lithuania_canary as m

STATE = {'public_key': 'node-public-key', 'short_id': '00112233', 'tls_name': 'lt.example'}


def reality(tag='proxy', port=443):
    return {'tag': tag, 'protocol': 'vless', 'settings': {'vnext': [
        {'address': 'ee.example', 'port': port, 'users': [{'id': 'keep-owner-uuid'}]}]},
        'streamSettings': {'network': 'tcp', 'security': 'reality', 'realitySettings': {'publicKey': 'ee-key'}}}


def test_owner_gate_never_reads_state_for_other_customers(monkeypatch):
    class Forbidden:
        def read_text(self):
            raise AssertionError('Other customers must not read owner state')
    monkeypatch.setattr(m, 'STATE', Forbidden())
    assert m.load(12345) is None


def test_auto_lt_primary_ee_only_failure_fallback_preserves_input():
    profiles = [{'remarks': '🇸🇴 Автовыбор', 'outbounds': [reality('proxy-main-1'),
        {'tag': 'direct', 'protocol': 'freedom'}], 'routing': {'rules': [
        {'type': 'field', 'domain': ['example.ru'], 'outboundTag': 'direct'},
        {'type': 'field', 'network': 'tcp,udp', 'balancerTag': 'old'}]}}]
    old = copy.deepcopy(profiles)
    p = m.apply(profiles, STATE)[0]
    assert profiles == old
    assert p['outbounds'][0]['settings']['vnext'][0]['address'] == m.IP
    assert p['outbounds'][1]['settings']['vnext'][0]['address'] == 'ee.example'
    assert p['routing']['balancers'][0]['selector'] == ['lt-primary']
    assert p['routing']['balancers'][0]['fallbackTag'] == 'ee-reserve'
    assert p['routing']['rules'][0]['outboundTag'] == 'direct'


def test_alias_uuid_and_ai_port_preserved():
    profiles = [{'remarks': '🇸🇪 Нейросети 🤖', 'outbounds': [reality(port=8444)]}]
    p = m.apply(profiles, STATE)[0]
    assert p['remarks'] == '🇱🇹 Нейросети 🤖'
    target = p['outbounds'][0]['settings']['vnext'][0]
    assert target['port'] == 8444
    assert target['users'][0]['id'] == 'keep-owner-uuid'


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
