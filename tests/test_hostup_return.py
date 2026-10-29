import copy
import json
from monitoring import hostup_return as m


def test_disabled_does_not_change_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'STATE', tmp_path / 'missing')
    profiles = [{'remarks': 'Автовыбор'}]
    assert m.apply(profiles) is profiles


def test_sweden_identity_selection_and_other_profiles_preserved(tmp_path, monkeypatch):
    state = tmp_path / 'state.json'
    state.write_text(json.dumps(dict(enabled=True, address='sweden.example', port=443,
                                    serverName='sweden.example', publicKey='public', shortId='00')))
    monkeypatch.setattr(m, 'STATE', state)
    main = {'tag': 'lt-primary', 'settings': {'vnext': [{'address': 'lt.example', 'port': 443,
            'users': [{'id': 'unchanged-main'}]}]}, 'streamSettings': {'realitySettings': {}}}
    auto = {'remarks': 'Автовыбор', 'outbounds': [main], 'routing': {'balancers': [
            {'fallbackTag': 'cdn-safe'}]}, 'burstObservatory': {'pingConfig': {'timeout': '5s'}}}
    profiles = [auto, {'remarks': 'Manual'}]
    original = copy.deepcopy(profiles)
    result = m.apply(profiles)
    assert profiles == original
    assert result[1] is profiles[1]
    se = result[0]['outbounds'][1]
    assert se['settings']['vnext'][0]['users'] == main['settings']['vnext'][0]['users']
    balancer = result[0]['routing']['balancers'][0]
    assert balancer['strategy']['type'] == 'leastLoad'
    assert balancer['selector'] == ['lt-primary', 'se-primary']
    assert balancer['fallbackTag'] == 'cdn-safe'
    assert result[0]['burstObservatory']['pingConfig'] == auto['burstObservatory']['pingConfig']
