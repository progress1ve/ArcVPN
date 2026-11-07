import copy
import json
import time
import pytest
from monitoring import owner_auto_lte as m


@pytest.fixture
def enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'STATE', tmp_path/'state')
    m.STATE.write_text(json.dumps({'enabled': True, 'expires_at': time.time()+3600}))


def source():
    return [{'remarks': 'Автовыбор', 'outbounds': [{'tag': 'nl-primary'}, {'tag': 'cdn-safe'}],
             'routing': {'balancers': [
                 {'tag': 'lt-first', 'selector': ['nl-primary'], 'fallbackTag': 'auto-cdn-stage'},
                 {'tag': 'auto-cdn-ping', 'selector': ['a', 'b', 'c', 'd'],
                  'strategy': {'type': 'leastPing'}, 'fallbackTag': 'cdn-safe'}]},
             'burstObservatory': {'pingConfig': {'interval': '15s', 'sampling': 2, 'timeout': '5s'}}}]


def test_only_reserve_and_method_differ(enabled):
    original=source();before=copy.deepcopy(original)
    result=m.apply(original,m.OWNER)
    assert original==before and result[0]==before[0]
    trial=copy.deepcopy(result[1]);assert trial.pop('remarks')==m.NAME
    assert trial['routing']['balancers'][1]['strategy']['type']=='leastLoad'
    trial['routing']['balancers'][1]['strategy']={'type':'leastPing'}
    assert trial['burstObservatory']['pingConfig'].pop('httpMethod')=='GET'
    trial['remarks']='Автовыбор'
    assert trial==before[0] and m.apply(result,m.OWNER)==result


def test_other_users_and_no_lte_unchanged(enabled):
    p=source();assert m.apply(p,123) is p
    p[0]['routing']['balancers'].pop();assert m.apply(p,m.OWNER) is p


@pytest.mark.parametrize('expires',[0,True,None,float('inf'),time.time()+90000])
def test_expiry_fail_closed(enabled,expires):
    m.STATE.write_text(json.dumps({'enabled':True,'expires_at':expires}))
    p=source();assert m.apply(p,m.OWNER) is p
