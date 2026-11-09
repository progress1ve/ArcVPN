import copy
import json
import time
from urllib.parse import quote, unquote, urlsplit

import pytest

from monitoring import owner_reality_ab as m


@pytest.fixture
def state(tmp_path, monkeypatch):
    path = tmp_path / 'state.json'
    monkeypatch.setattr(m, 'STATE', path)
    data = {'enabled': True, 'expires_at': time.time() + 3600,
            'uuid': '57c24a09-4e21-410e-a33c-5537841d262f',
            'public_key': 'a' * 43, 'short_id': '0123456789abcdef'}
    path.write_text(json.dumps(data))
    return data


def profile():
    return {'remarks': m.PUBLIC_NAME, 'routing': {'rules': [{'outboundTag': 'direct'}]},
            'outbounds': [{'tag': 'proxy', 'protocol': 'vless', 'settings': {'vnext': [
                {'address': m.DOMAIN, 'port': 443, 'users': [{'id': 'existing',
                 'flow': 'xtls-rprx-vision'}]}]}, 'streamSettings': {'network': 'tcp',
                 'security': 'reality', 'realitySettings': {'fingerprint': 'firefox',
                 'serverName': m.DOMAIN, 'publicKey': 'old', 'shortId': 'old'}}}]}


def test_owner_profiles_preserve_main_and_differ_only_by_port_and_name(state):
    profiles = [profile()]
    before = copy.deepcopy(profiles)
    result = m.apply(profiles, m.OWNER)
    assert profiles == before
    assert result[0] == before[0]
    a, b = result[1:]
    assert a['routing'] == b['routing'] == before[0]['routing']
    target = a['outbounds'][0]['settings']['vnext'][0]
    assert target['users'][0] == {'id': state['uuid'], 'flow': 'xtls-rprx-vision'}
    assert target['port'] == 9443
    b = copy.deepcopy(b)
    b['remarks'] = a['remarks']
    assert b['outbounds'][0]['settings']['vnext'][0]['port'] == 9445
    b['outbounds'][0]['settings']['vnext'][0]['port'] = 9443
    assert a == b
    assert m.apply(result, m.OWNER) == result


def test_other_users_and_missing_source_are_unchanged(state):
    profiles = [profile()]
    assert m.apply(profiles, 123) is profiles
    assert m.apply([], m.OWNER) == []
    assert m.apply_links([], m.OWNER) == []


@pytest.mark.parametrize('override', [
    {'enabled': False}, {'expires_at': time.time() - 1}, {'expires_at': True},
    {'expires_at': float('inf')}, {'expires_at': time.time() + 90000},
    {'uuid': 'invalid'}, {'public_key': None}, {'short_id': 'invalid'},
])
def test_invalid_or_expired_state_hides_profiles(state, override):
    m.STATE.write_text(json.dumps({**state, **override}))
    profiles = [profile()]
    assert m.apply(profiles, m.OWNER) is profiles


def test_plain_links_match_owner_json_and_preserve_other_users(state):
    links = [f'vless://existing@{m.DOMAIN}:443?security=reality&type=tcp'
             '&flow=xtls-rprx-vision&fp=firefox#' + quote(m.PUBLIC_NAME)]
    result = m.apply_links(links, m.OWNER)
    assert len(result) == 3 and result[0] == links[0]
    for link, (name, port) in zip(result[1:], m.VARIANTS):
        parsed = urlsplit(link)
        assert parsed.username == state['uuid']
        assert parsed.hostname == m.DOMAIN and parsed.port == port
        assert unquote(parsed.fragment) == name
    assert m.apply_links(result, m.OWNER) == result
    assert m.apply_links(links, 123) is links


def test_tcp_tuning_uses_only_domain_based_control_and_bbr(state):
    m.STATE.write_text(json.dumps({**state, 'experiment': 'tcp-tuning'}))
    links = [f'vless://existing@{m.DOMAIN}:443?security=reality#' + quote(m.PUBLIC_NAME)]
    rendered = m.apply([profile()], m.OWNER)[1:]
    shares = m.apply_links(links, m.OWNER)[1:]
    assert len(rendered) == len(shares) == 2
    for item, share in zip(rendered, shares):
        outbound = item['outbounds'][0]
        target = outbound['settings']['vnext'][0]
        parsed = urlsplit(share)
        assert (target['address'], target['port']) == (parsed.hostname, parsed.port)
        assert outbound['streamSettings']['realitySettings']['serverName'] == m.DOMAIN
        assert f'sni={m.DOMAIN}' in parsed.query
    assert [(urlsplit(link).hostname, urlsplit(link).port) for link in shares] == [
        (m.DOMAIN, 9443), (m.DOMAIN, 9445),
    ]
    assert m.apply_links(links, 123) is links
