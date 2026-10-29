import copy
from monitoring import owner_youtube_direct as m

STATE = dict(enabled=True, address='moscow.example', port=443, serverName='ru.example', publicKey='public', shortId='00')


def profile():
    return {'remarks': '🇱🇹 Литва', 'outbounds': [{'tag': 'proxy', 'protocol': 'vless',
        'settings': {'vnext': [{'address': 'lt.example', 'port': 443, 'users': [{'id': 'unchanged'}]}]},
        'streamSettings': {'security': 'reality', 'realitySettings': {}}}],
        'routing': {'rules': [{'domain': ['geosite:youtube', 'domain:googlevideo.com'], 'outboundTag': 'proxy'},
                             {'domain': ['geosite:telegram'], 'outboundTag': 'proxy'},
                             {'network': 'tcp,udp', 'outboundTag': 'proxy'}]}}


def test_only_owner_can_receive_trial():
    p = [profile()]
    assert m.apply(p, 123, STATE) is p
    assert m.apply(p, m.OWNER, {'enabled': False}) is p


def test_only_youtube_changes_and_credentials_and_other_profiles_stay_intact():
    p = [profile(), {'remarks': 'Other'}]; before = copy.deepcopy(p)
    result = m.apply(p, m.OWNER, STATE)
    assert p == before and result[0] is p[0] and result[2] is p[1]
    trial = result[1]
    assert trial['remarks'] == m.NAME
    assert trial['outbounds'][0] == p[0]['outbounds'][0]
    assert trial['outbounds'][-1]['settings']['vnext'][0]['users'] == [{'id': 'unchanged'}]
    assert trial['routing']['rules'][0]['outboundTag'] == 'youtube-direct-ru'
    assert trial['routing']['rules'][1:] == p[0]['routing']['rules'][1:]


def test_missing_youtube_rule_does_not_create_incomplete_trial():
    p = profile(); p['routing']['rules'] = []
    profiles = [p]
    assert m.apply(profiles, m.OWNER, STATE) is profiles
