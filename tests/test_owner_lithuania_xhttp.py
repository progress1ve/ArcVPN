import copy
import urllib.parse
from monitoring import owner_lithuania_xhttp as m


def profile():
    return {'remarks': '🇱🇹 Литва', 'outbounds': [{'protocol': 'vless', 'settings': {'vnext': [
        {'address': 'lt.example', 'port': 443, 'users': [{'id': 'keep-main-identity', 'flow': 'xtls-rprx-vision'}]}]},
        'streamSettings': {'network': 'tcp', 'security': 'reality'}}], 'routing': {'rules': []}}


def test_other_user_unchanged():
    p = [profile()]
    assert m.apply(p, 123) is p
    links = ['unmodified']
    assert m.apply_links(links, 123) is links


def test_owner_separate_profile_preserves_original_identity_and_rules():
    lte = profile(); lte['remarks'] = 'Bypass'
    lte['outbounds'][0]['streamSettings'] = {'network': 'xhttp'}
    lte['outbounds'][0]['settings']['vnext'][0]['users'] = [{'id': 'separate-lte-identity'}]
    p = [profile(), lte]; before = copy.deepcopy(p)
    result = m.apply(p, m.OWNER)
    assert p == before and result[0] is p[0]
    test = result[1]; out = test['outbounds'][0]
    assert test['remarks'] == m.NAME
    assert out['settings']['vnext'][0]['users'] == [{'id': 'separate-lte-identity'}]
    assert out['streamSettings']['network'] == 'xhttp'
    assert test['routing'] == p[0]['routing']
    assert out['streamSettings']['tlsSettings']['allowInsecure'] is False


def test_share_link_preserves_owner_uuid_without_reality_flow():
    link = 'vless://keep-main-identity@lt.example:443?flow=xtls-rprx-vision#'+urllib.parse.quote('🇱🇹 Литва')
    lte = 'vless://separate-lte-identity@cdn.example:443?type=xhttp'
    result = m.apply_links([link, lte], m.OWNER)
    p = urllib.parse.urlsplit(result[1]); query = urllib.parse.parse_qs(p.query)
    assert p.username == 'separate-lte-identity' and p.hostname == '88.216.62.135'
    assert 'flow' not in query and query['type'] == ['xhttp']
    assert urllib.parse.unquote(p.fragment) == m.NAME


def test_owner_without_lte_does_not_gain_access():
    p = [profile()]
    assert m.apply(p, m.OWNER) is p
    links = ['vless://main@lt.example:443?type=tcp#'+urllib.parse.quote('🇱🇹 Литва')]
    assert m.apply_links(links, m.OWNER) is links
