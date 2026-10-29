"""Restore the authorized Sweden peer without changing customer identities."""
import copy
import json
from pathlib import Path

STATE = Path(__file__).resolve().parents[1] / '.secrets/hostup-return-20261029.json'


def apply(profiles):
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        return profiles
    if not state.get('enabled'):
        return profiles
    result = list(profiles)
    for index, source in enumerate(profiles):
        if 'Автовыбор' not in source.get('remarks', ''):
            continue
        main = next((o for o in source.get('outbounds', []) if o.get('tag') == 'lt-primary'), None)
        if main is None:
            continue
        profile = copy.deepcopy(source)
        se = copy.deepcopy(main)
        se['tag'] = 'se-primary'
        se['settings']['vnext'][0].update(address=state['address'], port=state['port'])
        stream = se['streamSettings']
        stream.pop('finalmask', None)
        stream['realitySettings'].update({key: state[key] for key in ('serverName', 'publicKey', 'shortId')})
        profile['outbounds'].insert(2, se)
        balancer = profile['routing']['balancers'][0]
        balancer['selector'] = ['lt-primary', 'se-primary']
        balancer['strategy'] = {'type': 'leastLoad', 'settings': {
            'expected': 2, 'maxRTT': '3s', 'baselines': ['1s'], 'tolerance': 0.2}}
        profile['burstObservatory']['subjectSelector'] = ['lt-primary', 'se-primary']
        result[index] = profile
    return result
