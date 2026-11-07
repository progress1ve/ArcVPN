import copy

from monitoring.auto_cdn_reserve import apply


def profiles(entitled=True):
    cdn = [{'tag': tag, 'protocol': 'vless',
            'settings': {'vnext': [{'users': [{'id': 'test-lte-identity'}]}]},
            'streamSettings': {'network': 'xhttp'}}
           for tag in ['cdn-fast', 'cdn-medium', 'cdn-safe']]
    auto = {'remarks': 'Автовыбор', 'outbounds': copy.deepcopy(cdn[-1:]) if entitled else [],
            'routing': {'rules': [{'type': 'field', 'balancerTag': 'lt-first'}],
                        'balancers': [{'tag': 'lt-first', 'strategy': {'type': 'leastLoad'},
                                       'selector': ['lt-primary', 'se-primary'], 'fallbackTag': 'cdn-safe'}]},
            'burstObservatory': {'subjectSelector': ['lt-primary', 'se-primary'], 'pingConfig': {}}}
    return [auto, {'remarks': 'Лучший обход', 'outbounds': cdn}, {'remarks': 'Литва'}]


def test_reserve_preserves_authorization_and_primary_strategy():
    original = profiles()
    before = copy.deepcopy(original)
    result = apply(original)
    assert original == before
    assert result[1:] == before[1:]
    main, reserve = result[0]['routing']['balancers']
    assert main['strategy'] == {'type': 'leastLoad'}
    assert main['selector'] == ['lt-primary', 'se-primary']
    assert main['fallbackTag'] == 'auto-cdn-stage'
    assert reserve['strategy'] == {'type': 'leastPing'}
    assert reserve['fallbackTag'] == 'cdn-safe'
    candidates = [o for o in result[0]['outbounds'] if o.get('tag') in reserve['selector']]
    assert len(candidates) == 3
    assert all(o['settings']['vnext'][0]['users'][0]['id'] == 'test-lte-identity' for o in candidates)
    assert set(reserve['selector']) <= set(result[0]['burstObservatory']['subjectSelector'])
    assert result[0]['routing']['rules'][0]['inboundTag'] == ['auto-cdn-reserve']
    assert result[0]['burstObservatory']['pingConfig']['destination'] == 'https://sub.arccnet.space:18443/generate_204'
    assert result[0]['burstObservatory']['pingConfig'] == {
        'destination': 'https://sub.arccnet.space:18443/generate_204',
        'httpMethod': 'GET', 'interval': '15s', 'sampling': 2, 'timeout': '5s'}
    assert apply(result) == result


def test_no_entitlement_or_missing_pool_preserves_profiles():
    original = profiles(False)
    assert apply(original) == original
    assert apply(original[:1]) is not None
    assert apply(original[:1]) == original[:1]
