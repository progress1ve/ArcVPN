import copy
import pytest
from monitoring.subscription_balancers import apply, defaults, digest, validate


def template(name="Автовыбор"):
    return {"remarks": name, "routing": {"rules": [], "balancers": [{"tag": "balancer_main", "selector": ["proxy-main"], "fallbackTag": "proxy-back-1", "strategy": {"type": "leastLoad", "settings": {}}}]},
            "outbounds": [{"tag": "proxy-main-1", "settings": {"vnext": [{"address": "136.148.220.228", "users": [{"id": "private-identity"}]}]}},
                          {"tag": "proxy-main-2", "settings": {"vnext": [{"address": "87.251.19.197"}]}}]}


def test_no_policy_preserves_legacy_subscription():
    original = [template()]
    assert apply(original, []) is original


def test_policy_preserves_credentials_and_manual_locations():
    original = [template(), {"remarks": "Швеция"}]
    saved = copy.deepcopy(original)
    policy = defaults()[:1]
    policy[0].update(strategy="leastLoad", name="Мой выбор", members=["se"], fallback="block", weights={"se": 4})
    result = apply(original, validate(policy))
    assert original == saved
    assert result[0]["remarks"] == "Мой выбор"
    assert result[0]["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] == "private-identity"
    balancer = result[0]["routing"]["balancers"][0]
    assert balancer["selector"] == ["proxy-main-1"]
    assert balancer["fallbackTag"] == "block"
    assert balancer["strategy"]["settings"]["costs"][0]["value"] == .25
    assert result[-1] == {"remarks": "Швеция"}


def test_missing_selected_node_fails_closed():
    source = template()
    source["outbounds"] = source["outbounds"][:1]
    result = apply([source], defaults()[:1])
    assert result[0]["routing"]["balancers"][-1]["fallbackTag"] == "block"


def test_weighted_connections_use_exact_tickets_and_health_aware_reserves():
    source = template()
    source['burstObservatory'] = {'subjectSelector': ['proxy-main']}
    rendered = apply([source], validate(defaults()[:1]))[0]
    tickets = [o for o in rendered['outbounds'] if o['tag'].startswith('weighted-ticket-')]
    assert len(tickets) == 100
    assert sum(o['settings']['inboundTag'] == 'weighted-preferred-0' for o in tickets) == 61
    assert sum(o['settings']['inboundTag'] == 'weighted-preferred-1' for o in tickets) == 39
    assert rendered['burstObservatory'] == source['burstObservatory']
    assert rendered['routing']['balancers'][0]['tag'] == 'balancer_main'
    assert all(b['strategy']['type'] == 'leastPing' for b in rendered['routing']['balancers'][1:])
    assert {b['fallbackTag'] for b in rendered['routing']['balancers'] if '-reserve-' in b['tag']} == {'proxy-back-1'}


def test_finland_cannot_be_published_as_a_balancer_member():
    policy = defaults()[:1]
    policy[0]['members'] = ['fi', 'ee']
    with pytest.raises(ValueError):validate(policy)


@pytest.mark.parametrize("field,value", [("strategy", "shell"), ("members", []), ("members", ["unknown"]), ("weights", {"se": -1}), ("name", "\ninvalid")])
def test_invalid_policies_rejected(field, value):
    policy = defaults()[:1]
    policy[0][field] = value
    with pytest.raises(ValueError):
        validate(policy)


def test_preview_digest_changes_when_route_changes():
    policy = defaults()
    old = digest(policy)
    policy[0]["fallback"] = "block"
    assert digest(policy) != old


def test_weighted_users_are_sticky_and_keep_the_other_node_as_reserve():
    policy=defaults()[:1]
    policy[0].update(strategy='weightedUsers',weights={'se':3,'ee':1})
    counts={'proxy-main-1':0,'proxy-main-2':0}
    for user in range(1000):
        result=apply([template()],policy,user_id=user)[0]
        primary=result['routing']['balancers'][0]
        assert primary['selector']==apply([template()],policy,user_id=user)[0]['routing']['balancers'][0]['selector']
        counts[primary['selector'][0]]+=1
        assert primary['fallbackTag']=='policy-fallback'
        reserve=result['routing']['balancers'][-1]
        assert reserve['selector'][0]!=primary['selector'][0]
        assert reserve['fallbackTag']=='proxy-back-1'
    assert 680<counts['proxy-main-1']<820


def test_publish_requires_current_preview_and_preserves_live_until_publish(tmp_path,monkeypatch):
    import subscription_api as api
    import sqlite3
    import json
    path=tmp_path/'policies.sqlite3'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
    def db():
        conn=sqlite3.connect(path);conn.row_factory=sqlite3.Row;return conn
    def setting(key,default=None):
        with db() as conn:
            row=conn.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
            return row['value'] if row else default
    monkeypatch.setattr(api,'get_db',db)
    monkeypatch.setattr(api,'get_setting',setting)
    monkeypatch.setattr(api,'_admin_authorized',lambda permission:True)
    monkeypatch.setattr(api,'_append_admin_audit_best_effort',lambda *args,**kwargs:None)
    client=api.app.test_client()
    policy=defaults()
    headers={'Origin':'https://arccnet.space'}
    preview=client.post('/api/admin/subscription-balancers',json={'action':'preview','balancers':policy},headers=headers).get_json()
    assert setting('subscription_balancers_live') is None
    rejected=client.post('/api/admin/subscription-balancers',json={'action':'publish','balancers':policy,'revision':preview['revision'],'preview_hash':'wrong'},headers=headers)
    assert rejected.status_code==409
    published=client.post('/api/admin/subscription-balancers',json={'action':'publish','balancers':policy,'revision':preview['revision'],'preview_hash':preview['preview_hash']},headers=headers)
    assert published.status_code==200
    assert json.loads(setting('subscription_balancers_live'))==policy
    assert client.post('/api/admin/subscription-balancers',json={'action':'preview','balancers':policy},headers={'Origin':'https://other.example'}).status_code==403


def test_renamed_locations_keep_balancer_identity_and_aliases(monkeypatch):
    import subscription_api as api
    import json
    import urllib.parse
    from subscription_api import ActiveKeyRecord
    overrides={'Швеция':{'display_name':'Мой север','enabled':1,'include_in_auto':1,'sort_order':0},
               'Эстония':{'display_name':'Мой запад','enabled':1,'include_in_auto':1,'sort_order':1}}
    monkeypatch.setattr(api,'_catalog_overrides',lambda:overrides)
    monkeypatch.setattr(api,'get_setting',lambda key,default=None:default)
    monkeypatch.setattr(api,'FINLAND_BRIDGE_READY',True)
    key=ActiveKeyRecord(1,1,'test','2099-01-01',0,0,'test',1)
    links='\n'.join(f'vless://11111111-1111-1111-1111-111111111111@{host}:443?security=none&type=tcp#{urllib.parse.quote(name)}'
                    for host,name in [('se.example','Швеция'),('ee.example','Эстония')])
    profiles=json.loads(api._build_happ_json_subscription(key,links))
    names=[p['remarks'] for p in profiles]
    assert '🇸🇪 Мой север' in names and '🇪🇪 Мой запад' in names
    assert names.index('🇸🇪 Мой север')<names.index('🇪🇪 Мой запад')
    peers=[o for o in profiles[0]['outbounds'] if o['tag'].startswith('proxy-main-')]
    assert len(peers)==2
    assert {o['settings']['vnext'][0]['address'] for o in peers}=={'se.example','ee.example'}


def test_best_bypass_is_not_left_as_a_duplicate_manual_location():
    source={'remarks':'Лучший обход','outbounds':[], 'routing':{'balancers':[{'selector':[],'strategy':{'type':'leastLoad'}}]}}
    result=apply([source],defaults())
    assert len(result)==5
    assert all('balancers' in p['routing'] for p in result)


def test_publication_preserves_interleaved_manual_location():
    auto={'remarks':'Автовыбор','outbounds':[], 'routing':{'balancers':[{'selector':[]}]}}
    bypass={'remarks':'Лучший обход','outbounds':[], 'routing':{'balancers':[{'selector':[]}]}}
    manual={'remarks':'FI','outbounds':[]}
    policy=[defaults()[0],defaults()[2]]
    result=apply([auto,manual,bypass],policy)
    assert result[1]['remarks']=='FI'
    assert result[2]['remarks']=='🇪🇺 Лучший обход'
